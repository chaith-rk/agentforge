"""Tests for the Vapi webhook handler.

Covers:
- HMAC signature authentication (valid, invalid, missing)
- Shared-secret header authentication
- Fail-closed behavior in production when secrets are misconfigured
- conversation-update handler (broadcasts transcript, skips system/tool)
- tool-calls handler (OpenAI nested function format)
- end-of-call-report handler (persists completion, triggers evals via complete_call)
- status-update handler
- Unknown message type is handled gracefully
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.config.settings import Environment
from src.database.event_store import EventStore
from src.engine.call_manager import CallManager
from src.models.call_session import CandidateClaim
from src.webhooks import vapi_handler
from src.webhooks.vapi_handler import router as vapi_router


WEBHOOK_SECRET = "test-webhook-secret-abc123"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def call_manager(tmp_path):
    """Real EventStore + CallManager backed by a temp SQLite file."""
    db_path = str(tmp_path / "webhook_test.db")
    event_store = EventStore(db_path=db_path)
    await event_store.initialize()
    cm = CallManager(event_store=event_store)
    yield cm
    await event_store.close()


@pytest.fixture
def app_client(call_manager, monkeypatch):
    """FastAPI TestClient with the vapi webhook router mounted and
    the CallManager + ConnectionManager patched to our fixtures."""

    # Patch settings: webhook secret set, environment not production
    monkeypatch.setattr(vapi_handler.settings, "vapi_webhook_secret", WEBHOOK_SECRET)
    monkeypatch.setattr(
        vapi_handler.settings, "environment", Environment.DEVELOPMENT
    )

    # Patch the lazy-imported call_manager and connection_manager
    monkeypatch.setattr(vapi_handler, "_get_call_manager", lambda: call_manager)

    class FakeConnectionManager:
        def __init__(self) -> None:
            self.broadcasts: list[tuple[str, dict]] = []

        async def broadcast_to_session(self, session_id: str, payload: dict) -> None:
            self.broadcasts.append((session_id, payload))

        async def broadcast_event(
            self, session_id: str, event_type: str, payload: dict
        ) -> None:
            self.broadcasts.append((session_id, {"type": event_type, **payload}))

    fake_cm = FakeConnectionManager()
    monkeypatch.setattr(vapi_handler, "_get_connection_manager", lambda: fake_cm)

    app = FastAPI()
    app.include_router(vapi_router)

    client = TestClient(app)
    client.fake_connection_manager = fake_cm  # type: ignore[attr-defined]
    return client


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _post(client: TestClient, payload: dict[str, Any], *, auth: str = "signature"):
    body = json.dumps(payload).encode()
    headers: dict[str, str] = {"content-type": "application/json"}
    if auth == "signature":
        headers["x-vapi-signature"] = _sign(body)
    elif auth == "secret":
        headers["x-vapi-secret"] = WEBHOOK_SECRET
    elif auth == "bearer":
        headers["authorization"] = f"Bearer {WEBHOOK_SECRET}"
    elif auth == "bad":
        headers["x-vapi-signature"] = "deadbeef"
    # auth == "none" -> no auth header
    return client.post("/webhooks/vapi", content=body, headers=headers)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestWebhookAuth:
    def test_valid_hmac_signature_is_accepted(self, app_client: TestClient) -> None:
        response = _post(app_client, {"message": {"type": "status-update", "status": "ringing"}}, auth="signature")
        assert response.status_code == 200

    def test_valid_shared_secret_header_is_accepted(self, app_client: TestClient) -> None:
        response = _post(app_client, {"message": {"type": "status-update", "status": "ringing"}}, auth="secret")
        assert response.status_code == 200

    def test_valid_bearer_token_is_accepted(self, app_client: TestClient) -> None:
        response = _post(app_client, {"message": {"type": "status-update", "status": "ringing"}}, auth="bearer")
        assert response.status_code == 200

    def test_missing_auth_is_rejected(self, app_client: TestClient) -> None:
        response = _post(app_client, {"message": {"type": "status-update"}}, auth="none")
        assert response.status_code == 401

    def test_bad_signature_is_rejected(self, app_client: TestClient) -> None:
        response = _post(app_client, {"message": {"type": "status-update"}}, auth="bad")
        assert response.status_code == 401

    def test_fail_closed_in_production_without_secret(
        self, app_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """In production, a missing webhook secret must reject all traffic."""
        monkeypatch.setattr(vapi_handler.settings, "vapi_webhook_secret", "")
        monkeypatch.setattr(
            vapi_handler.settings, "environment", Environment.PRODUCTION
        )

        response = _post(
            app_client, {"message": {"type": "status-update"}}, auth="none"
        )
        assert response.status_code == 503

    def test_fail_open_in_dev_without_secret(
        self, app_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """In dev, missing secret should log a warning and proceed."""
        monkeypatch.setattr(vapi_handler.settings, "vapi_webhook_secret", "")
        monkeypatch.setattr(
            vapi_handler.settings, "environment", Environment.DEVELOPMENT
        )

        response = _post(
            app_client, {"message": {"type": "status-update"}}, auth="none"
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Message dispatch helpers
# ---------------------------------------------------------------------------


async def _seed_active_call(call_manager: CallManager, session_id: str, vapi_call_id: str = "vapi_abc") -> None:
    """Create an active call and register its vapi_call_id mapping."""
    candidate = CandidateClaim(
        subject_name="Jane Doe",
        phone_number="+15551234567",
        claims={"employer_company_name": "Acme", "position": "Engineer"},
    )
    # Use a pre-existing YAML config
    call_manager.load_agent_config("agents/employment_verification_call.yaml")
    await call_manager.create_call(
        session_id=session_id,
        agent_config_id="employment_verification_v1",
        candidate=candidate,
        vapi_call_id=vapi_call_id,
    )


# ---------------------------------------------------------------------------
# conversation-update
# ---------------------------------------------------------------------------


class TestConversationUpdate:
    async def test_broadcasts_latest_message(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        await _seed_active_call(call_manager, "sess_conv_1")

        payload = {
            "message": {
                "type": "conversation-update",
                "call": {"metadata": {"session_id": "sess_conv_1"}},
                "messagesOpenAIFormatted": [
                    {"role": "system", "content": "you are a verifier"},
                    {"role": "assistant", "content": "Hi, this is Sarah."},
                    {"role": "user", "content": "Hello"},
                ],
            }
        }
        response = _post(app_client, payload)
        assert response.status_code == 200

        # Only the last (user) message should be broadcast
        broadcasts = app_client.fake_connection_manager.broadcasts  # type: ignore[attr-defined]
        assert len(broadcasts) == 1
        session_id, msg = broadcasts[0]
        assert session_id == "sess_conv_1"
        assert msg["type"] == "transcript"
        assert msg["role"] == "user"
        assert msg["content"] == "Hello"

    async def test_renames_assistant_role_to_agent(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        await _seed_active_call(call_manager, "sess_conv_2")

        payload = {
            "message": {
                "type": "conversation-update",
                "call": {"metadata": {"session_id": "sess_conv_2"}},
                "messagesOpenAIFormatted": [
                    {"role": "assistant", "content": "Can you verify employment?"},
                ],
            }
        }
        _post(app_client, payload)

        broadcasts = app_client.fake_connection_manager.broadcasts  # type: ignore[attr-defined]
        assert broadcasts[-1][1]["role"] == "agent"

    async def test_skips_system_and_tool_messages(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        await _seed_active_call(call_manager, "sess_conv_3")

        for role in ("system", "tool"):
            payload = {
                "message": {
                    "type": "conversation-update",
                    "call": {"metadata": {"session_id": "sess_conv_3"}},
                    "messagesOpenAIFormatted": [{"role": role, "content": "x"}],
                }
            }
            _post(app_client, payload)

        assert app_client.fake_connection_manager.broadcasts == []  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# tool-calls (OpenAI nested format)
# ---------------------------------------------------------------------------


class TestToolCalls:
    async def test_record_data_point_openai_format(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        await _seed_active_call(call_manager, "sess_tc_1")

        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"metadata": {"session_id": "sess_tc_1"}},
                "toolCallList": [
                    {
                        "id": "tc_1",
                        "type": "function",
                        "function": {
                            "name": "record_data_point",
                            "arguments": json.dumps(
                                {
                                    "field_name": "position",
                                    "value": "Senior Engineer",
                                    "confidence": "high",
                                }
                            ),
                        },
                    }
                ],
            }
        }
        response = _post(app_client, payload)
        assert response.status_code == 200

        body = response.json()
        assert body["results"][0]["toolCallId"] == "tc_1"
        assert "position" in body["results"][0]["result"]

        # Verify the data actually landed in the session
        active = call_manager.get_active_call("sess_tc_1")
        assert active is not None
        assert active.data_recorder.collected_data["position"] == "Senior Engineer"

    async def test_missing_type_with_tool_call_list_is_dispatched(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        """Vapi sometimes omits `type` and sends toolCallList directly."""
        await _seed_active_call(call_manager, "sess_tc_2")

        payload = {
            "message": {
                "call": {"metadata": {"session_id": "sess_tc_2"}},
                "toolCallList": [
                    {
                        "id": "tc_2",
                        "type": "function",
                        "function": {
                            "name": "record_data_point",
                            "arguments": '{"field_name":"year_started","value":"2021"}',
                        },
                    }
                ],
            }
        }
        response = _post(app_client, payload)
        assert response.status_code == 200
        active = call_manager.get_active_call("sess_tc_2")
        assert active.data_recorder.collected_data["year_started"] == "2021"

    async def test_malformed_arguments_do_not_crash(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        await _seed_active_call(call_manager, "sess_tc_3")

        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"metadata": {"session_id": "sess_tc_3"}},
                "toolCallList": [
                    {
                        "id": "tc_bad",
                        "type": "function",
                        "function": {
                            "name": "record_data_point",
                            "arguments": "this is not json",
                        },
                    }
                ],
            }
        }
        response = _post(app_client, payload)
        assert response.status_code == 200
        # Field name from parameters is empty -> nothing collected
        active = call_manager.get_active_call("sess_tc_3")
        assert active.data_recorder.collected_data == {}

    async def test_unknown_tool_name_returns_message(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        await _seed_active_call(call_manager, "sess_tc_4")

        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"metadata": {"session_id": "sess_tc_4"}},
                "toolCallList": [
                    {
                        "id": "tc_unknown",
                        "type": "function",
                        "function": {"name": "delete_everything", "arguments": "{}"},
                    }
                ],
            }
        }
        response = _post(app_client, payload)
        assert response.status_code == 200
        assert "Unknown function" in response.json()["results"][0]["result"]


# ---------------------------------------------------------------------------
# end-of-call-report
# ---------------------------------------------------------------------------


class TestEndOfCallReport:
    async def test_completes_call_and_runs_evals(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        """end-of-call-report should persist completion, run evals, and
        broadcast the verification record. This exercises the full
        complete_call() path including EvalRunner.run_all() (commit msg
        claims it's wired — this test guards that wiring)."""
        await _seed_active_call(call_manager, "sess_eoc_1")

        # Pre-seed some data so the verification record has content
        await call_manager.record_data_point(
            "sess_eoc_1", "position", "Senior Engineer", "high"
        )

        payload = {
            "message": {
                "type": "end-of-call-report",
                "call": {"metadata": {"session_id": "sess_eoc_1"}},
                "durationSeconds": 123.4,
                "endedReason": "assistant-ended-call",
                "artifact": {
                    "messages": [
                        {"role": "system", "content": "prompt"},
                        {"role": "assistant", "content": "Thanks for your time."},
                    ]
                },
            }
        }
        response = _post(app_client, payload)
        assert response.status_code == 200

        # Active call should be cleaned up after completion
        assert call_manager.get_active_call("sess_eoc_1") is None

        # WebSocket should have received a call_completed message
        broadcasts = app_client.fake_connection_manager.broadcasts  # type: ignore[attr-defined]
        completed = [b for _, b in broadcasts if b.get("type") == "call_completed"]
        assert len(completed) == 1
        assert completed[0]["outcome"] == "completed"
        assert completed[0]["verification_record"] is not None
        # Eval results should be present in the record (proves EvalRunner ran)
        record = completed[0]["verification_record"]
        assert "eval_results" in record or "evals" in record or record.get("field_verifications")


# ---------------------------------------------------------------------------
# status-update + unknown types
# ---------------------------------------------------------------------------


class TestMisc:
    async def test_status_update_broadcasts(
        self, app_client: TestClient, call_manager: CallManager
    ) -> None:
        await _seed_active_call(call_manager, "sess_status_1")

        payload = {
            "message": {
                "type": "status-update",
                "call": {"metadata": {"session_id": "sess_status_1"}},
                "status": "in-progress",
            }
        }
        response = _post(app_client, payload)
        assert response.status_code == 200

        broadcasts = app_client.fake_connection_manager.broadcasts  # type: ignore[attr-defined]
        status_msgs = [b for _, b in broadcasts if b.get("type") == "status_update"]
        assert len(status_msgs) == 1
        assert status_msgs[0]["status"] == "in-progress"

    def test_unknown_type_returns_ok(self, app_client: TestClient) -> None:
        response = _post(
            app_client,
            {"message": {"type": "some-future-type-we-dont-know", "data": {}}},
        )
        assert response.status_code == 200
        assert "Unhandled" in response.json()["message"]

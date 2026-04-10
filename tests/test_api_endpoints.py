"""Tests for the public REST API endpoints.

Covers the endpoints that the frontend actually hits plus the security
middleware behavior. Uses the real FastAPI app with the CallManager and
EventStore swapped for isolated test fixtures so each test gets a clean
database.

Endpoints:
- GET  /health
- GET  /api/agents
- GET  /api/agents/{agent_id}
- POST /api/calls/initiate
- GET  /api/calls/{session_id}
- GET  /api/calls/{session_id}/events
- GET  /api/calls/{session_id}/result
- POST /api/calls/{session_id}/stop
- GET  /api/calls
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src import main as main_module
from src.api import calls as calls_api
from src.config.settings import Environment
from src.database.event_store import EventStore
from src.engine.call_manager import CallManager
from src.middleware import security


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_app(tmp_path, monkeypatch):
    """Yield the real FastAPI app with a fresh EventStore + CallManager.

    Also swaps the singleton references in src.main so lazy imports inside
    routers pick up the test instances.
    """
    db_path = str(tmp_path / "api_test.db")
    event_store = EventStore(db_path=db_path)
    await event_store.initialize()
    call_manager = CallManager(event_store=event_store)
    call_manager.load_agent_config("agents/employment_verification_call.yaml")

    monkeypatch.setattr(main_module, "event_store", event_store)
    monkeypatch.setattr(main_module, "call_manager", call_manager)

    # No API key, dev environment -> middleware fails open
    monkeypatch.setattr(security.settings, "api_key", "")
    monkeypatch.setattr(security.settings, "environment", Environment.DEVELOPMENT)

    yield main_module.app, call_manager, event_store

    await event_store.close()


@pytest.fixture
def client(test_app):
    app, _, _ = test_app
    return TestClient(app)


@pytest.fixture
def call_manager(test_app) -> CallManager:
    _, cm, _ = test_app
    return cm


class FakeVapiClient:
    """In-place replacement for VapiClient used in /initiate tests."""

    def __init__(self) -> None:
        self.payload: dict[str, Any] | None = None

    async def __aenter__(self) -> "FakeVapiClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def create_call(
        self,
        to_number: str,
        phone_number_id: str,
        assistant: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        self.payload = {
            "to_number": to_number,
            "phone_number_id": phone_number_id,
            "assistant": assistant or {},
            "metadata": metadata or {},
        }
        return {"id": "vapi_test_123"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "active_calls" in body


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class TestAgentsEndpoints:
    def test_list_agents(self, client: TestClient) -> None:
        response = client.get("/api/agents")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents) >= 1
        ids = {a["agent_id"] for a in agents}
        assert "employment_verification_v1" in ids

    def test_get_agent_returns_form_fields(self, client: TestClient) -> None:
        response = client.get("/api/agents/employment_verification_v1")
        assert response.status_code == 200
        body = response.json()
        assert body["agent_id"] == "employment_verification_v1"
        assert len(body["all_fields"]) > 0
        assert len(body["all_fields"]) >= len(body["form_fields"])
        assert len(body["states"]) > 0

    def test_get_unknown_agent_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/agents/totally_fake_v9")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/calls/initiate
# ---------------------------------------------------------------------------


class TestInitiateCall:
    def test_initiate_call_happy_path(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = FakeVapiClient()
        monkeypatch.setattr(calls_api, "VapiClient", lambda: fake)
        monkeypatch.setattr(calls_api.settings, "vapi_api_key", "sk_test")
        monkeypatch.setattr(
            calls_api.settings, "vapi_phone_number_id", "phone_id_test"
        )

        response = client.post(
            "/api/calls/initiate",
            json={
                "agent_config_id": "employment_verification_v1",
                "subject_name": "Jane Doe",
                "phone_number": "+15551234567",
                "candidate_claims": {
                    "employer_company_name": "Acme",
                    "position": "Engineer",
                },
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["vapi_call_id"] == "vapi_test_123"
        assert body["status"] == "initiated"

        # Vapi client should have received E.164 number + metadata
        assert fake.payload is not None
        assert fake.payload["to_number"] == "+15551234567"
        metadata = fake.payload["metadata"]
        assert metadata["subject_name"] == "Jane Doe"
        assert metadata["candidate_claims"]["employer_company_name"] == "Acme"

    def test_initiate_call_without_vapi_config_returns_503(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(calls_api.settings, "vapi_api_key", "")
        monkeypatch.setattr(calls_api.settings, "vapi_phone_number_id", "")

        response = client.post(
            "/api/calls/initiate",
            json={
                "subject_name": "Jane Doe",
                "phone_number": "+15551234567",
                "candidate_claims": {"employer_company_name": "Acme"},
            },
        )
        assert response.status_code == 503

    def test_initiate_call_with_unknown_agent_returns_400(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(calls_api, "VapiClient", lambda: FakeVapiClient())
        monkeypatch.setattr(calls_api.settings, "vapi_api_key", "sk_test")
        monkeypatch.setattr(
            calls_api.settings, "vapi_phone_number_id", "phone_id_test"
        )

        response = client.post(
            "/api/calls/initiate",
            json={
                "agent_config_id": "does_not_exist_v1",
                "subject_name": "Jane Doe",
                "phone_number": "+15551234567",
                "candidate_claims": {},
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Call status / events / result / stop / list
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded_session(
    client: TestClient, call_manager: CallManager, monkeypatch: pytest.MonkeyPatch
) -> str:
    """Initiate a real call via the API so we have a session to query."""
    fake = FakeVapiClient()
    monkeypatch.setattr(calls_api, "VapiClient", lambda: fake)
    monkeypatch.setattr(calls_api.settings, "vapi_api_key", "sk_test")
    monkeypatch.setattr(calls_api.settings, "vapi_phone_number_id", "phone_id_test")

    response = client.post(
        "/api/calls/initiate",
        json={
            "subject_name": "Jane Doe",
            "phone_number": "+15551234567",
            "candidate_claims": {
                "employer_company_name": "Acme",
                "position": "Engineer",
            },
        },
    )
    assert response.status_code == 201
    return response.json()["session_id"]


class TestCallReadEndpoints:
    async def test_get_call_status(
        self, client: TestClient, seeded_session: str
    ) -> None:
        response = client.get(f"/api/calls/{seeded_session}")
        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == seeded_session
        assert body["current_state"]  # non-empty

    def test_get_unknown_call_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/calls/does-not-exist-abc")
        assert response.status_code == 404

    async def test_get_call_events(
        self, client: TestClient, seeded_session: str
    ) -> None:
        response = client.get(f"/api/calls/{seeded_session}/events")
        assert response.status_code == 200
        events = response.json()
        # call_initiated event should be present
        assert any(e.get("event_type") == "call_initiated" for e in events)

    async def test_get_call_result_in_progress(
        self, client: TestClient, seeded_session: str
    ) -> None:
        response = client.get(f"/api/calls/{seeded_session}/result")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "in_progress"
        assert body["subject_name"] == "Jane Doe"

    async def test_list_calls(self, client: TestClient, seeded_session: str) -> None:
        response = client.get("/api/calls")
        assert response.status_code == 200
        calls = response.json()
        assert any(c.get("session_id") == seeded_session for c in calls)


class TestStopCall:
    async def test_stop_unknown_call_returns_404(self, client: TestClient) -> None:
        response = client.post("/api/calls/unknown-id/stop")
        assert response.status_code == 404

    async def test_stop_call_without_vapi_id_returns_400(
        self,
        client: TestClient,
        call_manager: CallManager,
    ) -> None:
        """Seed a call with no vapi_call_id and try to stop it."""
        from src.models.call_session import CandidateClaim

        candidate = CandidateClaim(
            subject_name="No Vapi",
            phone_number="+15550000000",
            claims={"employer_company_name": "X"},
        )
        await call_manager.create_call(
            session_id="stop_no_vapi",
            agent_config_id="employment_verification_v1",
            candidate=candidate,
            vapi_call_id="",
        )
        response = client.post("/api/calls/stop_no_vapi/stop")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# API key middleware fail-closed in production
# ---------------------------------------------------------------------------


class TestAPIKeyMiddleware:
    def test_production_without_api_key_returns_503(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(security.settings, "api_key", "")
        monkeypatch.setattr(
            security.settings, "environment", Environment.PRODUCTION
        )
        response = client.get("/api/agents")
        assert response.status_code == 503

    def test_production_with_valid_api_key_succeeds(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(security.settings, "api_key", "secret-prod-key")
        monkeypatch.setattr(
            security.settings, "environment", Environment.PRODUCTION
        )
        response = client.get(
            "/api/agents", headers={"X-API-Key": "secret-prod-key"}
        )
        assert response.status_code == 200

    def test_production_with_wrong_api_key_returns_401(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(security.settings, "api_key", "secret-prod-key")
        monkeypatch.setattr(
            security.settings, "environment", Environment.PRODUCTION
        )
        response = client.get("/api/agents", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    def test_health_endpoint_is_exempt(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """/health must work without API key even in production."""
        monkeypatch.setattr(security.settings, "api_key", "secret-prod-key")
        monkeypatch.setattr(
            security.settings, "environment", Environment.PRODUCTION
        )
        response = client.get("/health")
        assert response.status_code == 200

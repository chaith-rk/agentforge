from __future__ import annotations

import pytest

from src.api import calls
from src.config.agent_config import AgentConfig, AgentState, VoiceConfig


def _make_dummy_config() -> AgentConfig:
    """Build a minimal AgentConfig for testing."""
    return AgentConfig(
        agent_id="employment_verification_v1",
        agent_name="Employment Verification",
        version="1.0",
        states={
            "GREETING": AgentState(name="GREETING", is_terminal=True),
        },
        initial_state="GREETING",
        system_prompt_template="prompts/employment_verification.md",
        voice_config=VoiceConfig(),
    )


class DummyCallManager:
    def __init__(self) -> None:
        self.created_call: dict[str, object] | None = None
        self._agent_configs: dict[str, object] = {
            "employment_verification_v1": _make_dummy_config(),
        }

    def load_agent_config(self, config_path: str) -> None:
        pass

    async def create_call(self, **kwargs: object) -> None:
        self.created_call = kwargs


class DummyVapiClient:
    def __init__(self, response_id: str = "call_123") -> None:
        self.response_id = response_id
        self.request_payload: dict[str, object] | None = None

    async def __aenter__(self) -> DummyVapiClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def create_call(
        self,
        to_number: str,
        phone_number_id: str,
        assistant: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, str]:
        self.request_payload = {
            "to_number": to_number,
            "phone_number_id": phone_number_id,
            "assistant": assistant or {},
            "metadata": metadata or {},
        }
        return {"id": self.response_id}


@pytest.mark.asyncio
async def test_initiate_call_sends_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    cm = DummyCallManager()
    vapi_client = DummyVapiClient()

    monkeypatch.setattr(calls, "_get_call_manager", lambda: cm)
    monkeypatch.setattr(calls, "VapiClient", lambda: vapi_client)
    monkeypatch.setattr(calls.settings, "vapi_api_key", "api_key")
    monkeypatch.setattr(calls.settings, "vapi_phone_number_id", "phone_number")

    request = calls.InitiateCallRequest(
        subject_name="Jane Doe",
        phone_number="+15551234567",
        candidate_claims={
            "employer_company_name": "Acme Inc",
            "position": "Software Engineer",
        },
    )

    response = await calls.initiate_call(request)

    assert response.vapi_call_id == "call_123"
    assert vapi_client.request_payload is not None
    assert vapi_client.request_payload["to_number"] == "+15551234567"
    assert vapi_client.request_payload["phone_number_id"] == "phone_number"
    metadata = vapi_client.request_payload["metadata"]
    assert metadata["agent_config_id"] == "employment_verification_v1"
    assert metadata["subject_name"] == "Jane Doe"
    assert metadata["candidate_claims"]["employer_company_name"] == "Acme Inc"


@pytest.mark.asyncio
async def test_initiate_call_creates_session(monkeypatch: pytest.MonkeyPatch) -> None:
    cm = DummyCallManager()
    vapi_client = DummyVapiClient(response_id="call_456")

    monkeypatch.setattr(calls, "_get_call_manager", lambda: cm)
    monkeypatch.setattr(calls, "VapiClient", lambda: vapi_client)
    monkeypatch.setattr(calls.settings, "vapi_api_key", "api_key")
    monkeypatch.setattr(calls.settings, "vapi_phone_number_id", "phone_number")

    request = calls.InitiateCallRequest(
        subject_name="Jane Doe",
        phone_number="+15551234567",
        candidate_claims={"employer_company_name": "Acme Inc"},
    )

    response = await calls.initiate_call(request)

    assert response.vapi_call_id == "call_456"
    assert cm.created_call is not None
    assert cm.created_call["agent_config_id"] == "employment_verification_v1"
    assert cm.created_call["vapi_call_id"] == "call_456"

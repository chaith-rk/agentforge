from __future__ import annotations

import pytest

from src.api import calls


class DummyCallManager:
    def __init__(self) -> None:
        self.created_call: dict[str, object] | None = None

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
        assistant_id: str,
        phone_number_id: str,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, str]:
        self.request_payload = {
            "to_number": to_number,
            "assistant_id": assistant_id,
            "phone_number_id": phone_number_id,
            "metadata": metadata or {},
        }
        return {"id": self.response_id}


@pytest.mark.asyncio
async def test_initiate_call_uses_request_assistant_override(monkeypatch: pytest.MonkeyPatch) -> None:
    cm = DummyCallManager()
    vapi_client = DummyVapiClient()

    monkeypatch.setattr(calls, "_get_call_manager", lambda: cm)
    monkeypatch.setattr(calls, "VapiClient", lambda: vapi_client)
    monkeypatch.setattr(calls.settings, "vapi_api_key", "api_key")
    monkeypatch.setattr(calls.settings, "vapi_assistant_id", "default_assistant")
    monkeypatch.setattr(calls.settings, "vapi_phone_number_id", "phone_number")

    request = calls.InitiateCallRequest(
        assistant_id="override_assistant",
        subject_name="Jane Doe",
        company_name="Acme Inc",
        company_phone="+15551234567",
    )

    response = await calls.initiate_call(request)

    assert response.vapi_call_id == "call_123"
    assert vapi_client.request_payload is not None
    assert vapi_client.request_payload["assistant_id"] == "override_assistant"
    assert vapi_client.request_payload["metadata"]["assistant_id"] == "override_assistant"
    assert cm.created_call is not None
    assert cm.created_call["agent_config_id"] == "employment_verification_v1"


@pytest.mark.asyncio
async def test_initiate_call_falls_back_to_default_assistant(monkeypatch: pytest.MonkeyPatch) -> None:
    cm = DummyCallManager()
    vapi_client = DummyVapiClient(response_id="call_456")

    monkeypatch.setattr(calls, "_get_call_manager", lambda: cm)
    monkeypatch.setattr(calls, "VapiClient", lambda: vapi_client)
    monkeypatch.setattr(calls.settings, "vapi_api_key", "api_key")
    monkeypatch.setattr(calls.settings, "vapi_assistant_id", "default_assistant")
    monkeypatch.setattr(calls.settings, "vapi_phone_number_id", "phone_number")

    request = calls.InitiateCallRequest(
        subject_name="Jane Doe",
        company_name="Acme Inc",
        company_phone="+15551234567",
    )

    response = await calls.initiate_call(request)

    assert response.vapi_call_id == "call_456"
    assert vapi_client.request_payload is not None
    assert vapi_client.request_payload["assistant_id"] == "default_assistant"
    assert vapi_client.request_payload["metadata"]["assistant_id"] == "default_assistant"

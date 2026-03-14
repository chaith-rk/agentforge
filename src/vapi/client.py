"""Async Vapi API client.

Wraps the Vapi REST API for triggering outbound calls, retrieving call
details, and managing assistants. Uses httpx for async HTTP.

Vapi docs: https://docs.vapi.ai
"""

from __future__ import annotations

from typing import Any

import httpx

from src.config.settings import settings


VAPI_BASE_URL = "https://api.vapi.ai"


class VapiClient:
    """Async client for the Vapi voice AI platform.

    Usage:
        async with VapiClient() as client:
            call = await client.create_call(
                to_number="+15551234567",
                assistant_id="asst_xxx",
                phone_number_id="pn_xxx",
            )
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.vapi_api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> VapiClient:
        self._client = httpx.AsyncClient(
            base_url=VAPI_BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _ensure_client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("VapiClient must be used as async context manager")
        return self._client

    async def create_call(
        self,
        to_number: str,
        assistant_id: str,
        phone_number_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Trigger an outbound phone call via Vapi.

        Args:
            to_number: Destination E.164 phone number to call.
            assistant_id: Vapi assistant ID to use for the call.
            phone_number_id: Vapi phone number ID to place the call from.
            metadata: Additional metadata to attach to the call.

        Returns:
            Vapi call object with call_id and status.
        """
        client = self._ensure_client()

        payload: dict[str, Any] = {
            "customer": {
                "number": to_number,
            },
            "assistantId": assistant_id,
            "phoneNumberId": phone_number_id,
        }
        if metadata:
            payload["metadata"] = metadata

        response = await client.post("/call/phone", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_call(self, call_id: str) -> dict[str, Any]:
        """Get details for a specific call.

        Args:
            call_id: Vapi call ID.

        Returns:
            Call details including status, duration, transcript.
        """
        client = self._ensure_client()
        response = await client.get(f"/call/{call_id}")
        response.raise_for_status()
        return response.json()

    async def list_calls(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent calls.

        Args:
            limit: Maximum number of calls to return.

        Returns:
            List of call objects.
        """
        client = self._ensure_client()
        response = await client.get("/call", params={"limit": limit})
        response.raise_for_status()
        return response.json()

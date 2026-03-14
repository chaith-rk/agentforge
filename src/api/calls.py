"""Call management API endpoints.

Provides REST endpoints for triggering outbound verification calls,
retrieving call status, and accessing verification records.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
import httpx
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.vapi.client import VapiClient

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/calls", tags=["calls"])


# --- Request/Response Models ---


class InitiateCallRequest(BaseModel):
    """Request body for triggering a new verification call."""

    agent_config_id: str = Field(
        default="employment_verification_v1",
        description="Which agent type to use",
    )
    subject_name: str = Field(..., description="Candidate's full name")
    company_name: str = Field(..., description="Company to verify against")
    company_phone: str = Field(..., description="Phone number to call (E.164)")
    company_address: str = Field(default="", description="Company address")
    job_title: str = Field(default="", description="Claimed job title")
    start_date: str = Field(default="", description="Claimed start date")
    end_date: str = Field(default="", description="Claimed end date (empty if current)")
    employment_status: str = Field(default="", description="Full-time/part-time/contract")
    currently_employed: bool = Field(default=False)


class CallResponse(BaseModel):
    """Response after initiating a call."""

    session_id: str
    status: str
    message: str
    vapi_call_id: str = ""


class CallStatusResponse(BaseModel):
    """Current status of a call."""

    session_id: str
    current_state: str
    outcome: str
    collected_data: dict[str, Any] = Field(default_factory=dict)
    discrepancies: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str


# --- Endpoints ---


@router.post("/initiate", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(request: InitiateCallRequest) -> CallResponse:
    """Trigger a new outbound verification call.

    Creates a call session, initializes the state machine, and triggers
    the call via Vapi.
    """
    session_id = str(uuid.uuid4())

    if not settings.vapi_api_key or not settings.vapi_assistant_id or not settings.vapi_phone_number_id:
        logger.warning(
            "vapi_config_missing",
            has_api_key=bool(settings.vapi_api_key),
            has_assistant_id=bool(settings.vapi_assistant_id),
            has_phone_number_id=bool(settings.vapi_phone_number_id),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Vapi is not fully configured. Set VAPI_API_KEY, "
                "VAPI_ASSISTANT_ID, and VAPI_PHONE_NUMBER_ID."
            ),
        )

    metadata = {
        "session_id": session_id,
        "agent_config_id": request.agent_config_id,
        "subject_name": request.subject_name,
        "company_name": request.company_name,
    }

    try:
        async with VapiClient() as vapi_client:
            vapi_response = await vapi_client.create_call(
                to_number=request.company_phone,
                assistant_id=settings.vapi_assistant_id,
                phone_number_id=settings.vapi_phone_number_id,
                metadata=metadata,
            )
    except httpx.HTTPError as exc:
        logger.exception("vapi_call_initiation_failed", session_id=session_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to initiate outbound call via Vapi",
        ) from exc

    vapi_call_id = str(vapi_response.get("id", ""))

    logger.info(
        "call_initiated",
        session_id=session_id,
        agent_config_id=request.agent_config_id,
        company_name=request.company_name,
        vapi_call_id=vapi_call_id,
    )

    return CallResponse(
        session_id=session_id,
        status="initiated",
        message="Call initiated in Vapi. Track progress via webhook events.",
        vapi_call_id=vapi_call_id,
    )


@router.get("/{session_id}", response_model=CallStatusResponse)
async def get_call_status(session_id: str) -> CallStatusResponse:
    """Get current status and collected data for a call."""
    # TODO: Phase 4 — Retrieve from event store
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Session {session_id} not found",
    )


@router.get("/{session_id}/events")
async def get_call_events(session_id: str) -> list[dict[str, Any]]:
    """Get the full event history for a call (audit trail)."""
    # TODO: Phase 4 — Retrieve from event store
    return []


@router.get("/{session_id}/record")
async def get_verification_record(session_id: str) -> dict[str, Any]:
    """Get the final verification record for a completed call."""
    # TODO: Phase 4 — Generate from events
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No verification record found for session {session_id}",
    )


@router.get("")
async def list_calls(
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """List all calls with pagination and optional filtering."""
    # TODO: Phase 4 — Retrieve from event store
    return []

"""Call management API endpoints.

Provides REST endpoints for triggering outbound verification calls,
retrieving call status, and accessing verification records.
All operations go through the CallManager which coordinates the engine.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.models.call_session import CandidateClaim
from src.vapi.client import VapiClient

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _get_call_manager():
    """Lazy import to avoid circular dependency."""
    from src.main import call_manager
    return call_manager


# --- Request/Response Models ---


class InitiateCallRequest(BaseModel):
    """Request body for triggering a new verification call."""

    agent_config_id: str = Field(
        default="employment_verification_v1",
        description="Which agent type to use",
    )
    assistant_id: str = Field(
        default="",
        description="Optional Vapi assistant override for this specific call",
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
    transcript: list[dict[str, str]] = Field(default_factory=list)
    created_at: str
    updated_at: str


# --- Endpoints ---


@router.post("/initiate", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(request: InitiateCallRequest) -> CallResponse:
    """Trigger a new outbound verification call.

    Creates a call session with all engine components, then triggers
    the outbound call via Vapi.
    """
    session_id = str(uuid.uuid4())
    selected_assistant_id = request.assistant_id or settings.vapi_assistant_id

    if not settings.vapi_api_key or not selected_assistant_id or not settings.vapi_phone_number_id:
        logger.warning(
            "vapi_config_missing",
            has_api_key=bool(settings.vapi_api_key),
            has_assistant_id=bool(selected_assistant_id),
            has_phone_number_id=bool(settings.vapi_phone_number_id),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Vapi is not fully configured. Set VAPI_API_KEY, "
                "VAPI_PHONE_NUMBER_ID, and either VAPI_ASSISTANT_ID "
                "or assistant_id in the request."
            ),
        )

    # Build candidate claim from request
    candidate = CandidateClaim(
        subject_name=request.subject_name,
        company_name=request.company_name,
        company_address=request.company_address,
        company_phone=request.company_phone,
        job_title=request.job_title,
        start_date=request.start_date,
        end_date=request.end_date,
        employment_status=request.employment_status,
        currently_employed=request.currently_employed,
    )

    # Trigger call via Vapi
    metadata = {
        "session_id": session_id,
        "agent_config_id": request.agent_config_id,
        "subject_name": request.subject_name,
        "company_name": request.company_name,
        "assistant_id": selected_assistant_id,
    }

    try:
        async with VapiClient() as vapi_client:
            vapi_response = await vapi_client.create_call(
                to_number=request.company_phone,
                assistant_id=selected_assistant_id,
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

    # Create call session in the CallManager (initializes state machine,
    # data recorder, audit logger, and persists to event store)
    cm = _get_call_manager()
    await cm.create_call(
        session_id=session_id,
        agent_config_id=request.agent_config_id,
        candidate=candidate,
        vapi_call_id=vapi_call_id,
    )

    logger.info(
        "call_initiated",
        session_id=session_id,
        agent_config_id=request.agent_config_id,
        company_name=request.company_name,
        assistant_id=selected_assistant_id,
        vapi_call_id=vapi_call_id,
    )

    return CallResponse(
        session_id=session_id,
        status="initiated",
        message="Call initiated. Track via WebSocket or GET /api/calls/{session_id}.",
        vapi_call_id=vapi_call_id,
    )


@router.get("/{session_id}", response_model=CallStatusResponse)
async def get_call_status(session_id: str) -> CallStatusResponse:
    """Get current status and collected data for a call."""
    cm = _get_call_manager()
    data = await cm.get_session_data(session_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return CallStatusResponse(
        session_id=session_id,
        current_state=data.get("current_state", "unknown"),
        outcome=data.get("outcome", data.get("status", "unknown")),
        collected_data=data.get("collected_data", {}),
        discrepancies=data.get("discrepancies", []),
        transcript=data.get("transcript", []),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )


@router.get("/{session_id}/events")
async def get_call_events(session_id: str) -> list[dict[str, Any]]:
    """Get the full event history for a call (audit trail)."""
    cm = _get_call_manager()
    return await cm.get_session_events(session_id)


@router.get("/{session_id}/record")
async def get_verification_record(session_id: str) -> dict[str, Any]:
    """Get the final verification record for a completed call."""
    from src.database.event_store import EventStore
    from src.main import event_store

    # Check for snapshot (generated at call completion)
    session = await event_store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No session found for {session_id}",
        )

    if session.get("status") not in ("completed", "redirected", "no_record", "refused"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Call is still {session.get('status', 'in progress')}. Record available after completion.",
        )

    # Return the snapshot
    return session


@router.get("")
async def list_calls(
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List all calls with pagination."""
    cm = _get_call_manager()
    return await cm.list_sessions(limit=limit, offset=offset)

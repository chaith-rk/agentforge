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
from src.webhooks.vapi_handler import _build_dynamic_system_prompt, _build_tool_definitions

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _get_call_manager():
    """Lazy import to avoid circular dependency."""
    from src.main import call_manager
    return call_manager


# --- Request/Response Models ---


class InitiateCallRequest(BaseModel):
    """Request body for triggering a new verification call.

    Agent-agnostic: `candidate_claims` is a flexible dict whose keys
    correspond to field_names defined in the agent's YAML data_schema.
    The backend validates claims against the selected agent's schema.
    """

    agent_config_id: str = Field(
        default="employment_verification_v1",
        description="Which agent type to use",
    )
    subject_name: str = Field(..., description="Candidate's full name")
    phone_number: str = Field(..., description="Phone number to call (E.164)")
    candidate_claims: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific candidate claims, keyed by field_name from the agent's data_schema. "
        "For employment: employer_company_name, position, month_started, year_started, etc. "
        "For education: institution_name, degree_type, major, etc.",
    )


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

    if not settings.vapi_api_key or not settings.vapi_phone_number_id:
        logger.warning(
            "vapi_config_missing",
            has_api_key=bool(settings.vapi_api_key),
            has_phone_number_id=bool(settings.vapi_phone_number_id),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vapi is not fully configured. Set VAPI_API_KEY and VAPI_PHONE_NUMBER_ID in .env.",
        )

    # Build agent-agnostic candidate claim
    candidate = CandidateClaim(
        subject_name=request.subject_name,
        phone_number=request.phone_number,
        claims=request.candidate_claims,
    )

    # Pre-load agent config so handle_assistant_request can find it
    cm = _get_call_manager()
    config_path = f"agents/{request.agent_config_id.replace('_v1', '_call')}.yaml"
    try:
        cm.load_agent_config(config_path)
    except FileNotFoundError:
        pass  # Will fall back in create_call

    # Build the full assistant config inline so Vapi knows model/voice/tools
    config = cm._agent_configs.get(request.agent_config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown agent config: {request.agent_config_id}",
        )

    system_prompt = _build_dynamic_system_prompt(config, request.subject_name, request.candidate_claims)
    tools = _build_tool_definitions()

    assistant_config: dict[str, Any] = {
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "messages": [{"role": "system", "content": system_prompt}],
            "tools": tools,
            "temperature": config.voice_config.temperature,
        },
        "serverUrl": settings.vapi_server_url,
        "firstMessage": (
            f"Hi, my name is Sarah. I'm calling from AgentForge on a recorded line. "
            f"This call is regarding employment verification of {request.subject_name}"
            f"{' at ' + request.candidate_claims.get('employer_company_name', '') if request.candidate_claims.get('employer_company_name') else ''}. "
            f"May I speak to an authorized person who can verify employment?"
        ),
    }

    # Add voice config — use Vapi's default if no voice_id configured
    if config.voice_config.voice_id:
        assistant_config["voice"] = {
            "provider": "11labs",
            "voiceId": config.voice_config.voice_id,
        }
    else:
        assistant_config["voice"] = {
            "provider": "vapi",
            "voiceId": "Elliot",
        }

    metadata = {
        "session_id": session_id,
        "agent_config_id": request.agent_config_id,
        "subject_name": request.subject_name,
        "candidate_claims": request.candidate_claims,
    }

    try:
        async with VapiClient() as vapi_client:
            vapi_response = await vapi_client.create_call(
                to_number=request.phone_number,
                phone_number_id=settings.vapi_phone_number_id,
                assistant=assistant_config,
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
        subject_name=request.subject_name,
        vapi_call_id=vapi_call_id,
    )

    return CallResponse(
        session_id=session_id,
        status="initiated",
        message="Call initiated. Track via WebSocket or GET /api/calls/{session_id}.",
        vapi_call_id=vapi_call_id,
    )


@router.post("/{session_id}/stop")
async def stop_call(session_id: str) -> dict[str, str]:
    """Stop an active call by ending it via Vapi."""
    cm = _get_call_manager()
    active = cm.get_active_call(session_id)

    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active call for session {session_id}",
        )

    vapi_call_id = active.session.vapi_call_id
    if not vapi_call_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Vapi call ID associated with this session",
        )

    try:
        async with VapiClient() as vapi_client:
            client = vapi_client._ensure_client()
            response = await client.delete(f"/call/{vapi_call_id}")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("stop_call_failed", session_id=session_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to stop call via Vapi",
        ) from exc

    logger.info("call_stopped", session_id=session_id, vapi_call_id=vapi_call_id)
    return {"status": "stopped", "session_id": session_id}


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


@router.get("/{session_id}/result")
async def get_call_result(session_id: str) -> dict[str, Any]:
    """Get structured verification result in side-by-side format.

    For active calls, returns a partial result from the in-memory state.
    For completed calls, returns the snapshot stored at call completion.

    Args:
        session_id: The call session ID.

    Raises:
        HTTPException 404: If no session with the given ID exists.
    """
    cm = _get_call_manager()

    # Check active call first — return partial result
    active = cm.get_active_call(session_id)
    if active:
        record = cm._build_verification_record(active)
        result = record.to_report_dict()
        result["status"] = "in_progress"
        return result

    # Fall back to snapshot stored at call completion
    from src.main import event_store

    session = await event_store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return session


@router.get("")
async def list_calls(
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List all calls with pagination."""
    cm = _get_call_manager()
    return await cm.list_sessions(limit=limit, offset=offset)

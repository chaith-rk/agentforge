"""Vapi webhook handler.

Receives events from Vapi during active calls and routes them to the
CallManager which coordinates the state machine, data recorder, audit
logger, and event store.

All incoming webhooks are validated using either HMAC signature or
shared-secret authentication before processing.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from src.config.settings import settings
from src.middleware.security import validate_webhook_secret, validate_webhook_signature

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _get_call_manager():
    """Lazy import to avoid circular dependency."""
    from src.main import call_manager
    return call_manager


def _get_connection_manager():
    """Lazy import for WebSocket broadcasting."""
    from src.api.dashboard import connection_manager
    return connection_manager


@router.post("/vapi")
async def handle_vapi_webhook(request: Request) -> dict[str, Any]:
    """Main Vapi webhook receiver.

    Validates webhook authentication and dispatches to the appropriate
    handler based on message type.
    """
    body = await request.body()

    signature = request.headers.get("x-vapi-signature", "")
    secret_header = request.headers.get("x-vapi-secret", "")
    auth_header = request.headers.get("authorization", "")

    if settings.vapi_webhook_secret:
        signature_valid = bool(signature) and validate_webhook_signature(
            body, signature, settings.vapi_webhook_secret
        )
        secret_valid = validate_webhook_secret(
            secret_header,
            auth_header,
            settings.vapi_webhook_secret,
        )

        if not signature_valid and not secret_valid:
            logger.warning(
                "webhook_auth_invalid",
                path="/webhooks/vapi",
                has_signature=bool(signature),
                has_secret_header=bool(secret_header),
                has_auth_header=bool(auth_header),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook authentication",
            )

    payload = await request.json()
    message = payload.get("message", {})
    message_type = message.get("type", "")

    # Current Vapi payloads may omit `type` and send tool call lists directly.
    if not message_type and (
        message.get("toolCallList") or message.get("toolWithToolCallList")
    ):
        message_type = "tool-calls"

    logger.info("vapi_webhook_received", message_type=message_type)

    handler = WEBHOOK_HANDLERS.get(message_type)
    if handler:
        return await handler(payload)

    logger.warning("vapi_webhook_unknown_type", message_type=message_type)
    return {"status": "ok", "message": f"Unhandled message type: {message_type}"}


def _normalize_parameters(raw_parameters: Any) -> dict[str, Any]:
    """Normalize tool/function arguments into a dict."""
    if isinstance(raw_parameters, dict):
        return raw_parameters

    if isinstance(raw_parameters, str):
        try:
            parsed = json.loads(raw_parameters)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed

    return {}


async def _execute_function_call(
    function_name: str,
    parameters: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    """Execute a function call and return serialized text result."""
    function_handler = FUNCTION_HANDLERS.get(function_name)
    if not function_handler:
        logger.warning("unknown_function_call", function_name=function_name)
        return f"Unknown function: {function_name}"

    return await function_handler(parameters, payload)


def _resolve_session(payload: dict[str, Any]) -> str | None:
    """Resolve session_id from a webhook payload."""
    cm = _get_call_manager()
    return cm.resolve_session_id(payload)


# --- Webhook Handlers ---


async def handle_assistant_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle assistant-request: Vapi asks us for the assistant config.

    For now, we let Vapi use the assistant config from its dashboard.
    In the future, this is where we dynamically provide the system prompt
    with candidate details interpolated.
    """
    logger.info("assistant_request_received")

    # Return nothing — Vapi falls back to the dashboard-configured assistant
    # TODO: Phase 3+ — Dynamically build system prompt with candidate details
    return {}


async def handle_function_call(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle legacy single function-call message."""
    message = payload.get("message", {})
    function_call = message.get("functionCall", {})

    function_name = function_call.get("name", "")
    parameters = _normalize_parameters(
        function_call.get("parameters", function_call.get("arguments", {}))
    )

    logger.info("function_call_received", function_name=function_name)

    result = await _execute_function_call(function_name, parameters, payload)
    return {"result": result}


async def handle_tool_calls(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle modern tool-calls message with one or more tool invocations."""
    message = payload.get("message", {})
    tool_call_list = message.get("toolCallList", []) or []
    tool_with_tool_call_list = message.get("toolWithToolCallList", []) or []

    results: list[dict[str, str]] = []

    for tool_call in tool_call_list:
        function_name = tool_call.get("name", "")
        parameters = _normalize_parameters(
            tool_call.get("arguments", tool_call.get("parameters", {}))
        )
        tool_call_id = tool_call.get("id", "")

        result = await _execute_function_call(function_name, parameters, payload)
        results.append({"toolCallId": tool_call_id, "result": result})

    for item in tool_with_tool_call_list:
        tool_call = item.get("toolCall", {})
        tool = item.get("tool", {})

        function_name = tool_call.get("name", "") or tool.get("name", "")
        parameters = _normalize_parameters(
            tool_call.get("arguments", tool_call.get("parameters", {}))
        )
        tool_call_id = tool_call.get("id", "")

        result = await _execute_function_call(function_name, parameters, payload)
        results.append({"toolCallId": tool_call_id, "result": result})

    logger.info("tool_calls_received", count=len(results))
    return {"results": results}


async def handle_end_of_call(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle end-of-call-report: call has ended, process final data."""
    session_id = _resolve_session(payload)
    message = payload.get("message", {})

    # Extract call duration
    duration = message.get("durationSeconds", 0.0)
    ended_reason = message.get("endedReason", "unknown")

    # Map ended reason to our outcome
    outcome_map = {
        "assistant-ended-call": "completed",
        "customer-ended-call": "completed",
        "voicemail": "voicemail",
        "silence-timed-out": "dead_end",
        "phone-call-provider-closed-websocket": "dead_end",
    }
    outcome = outcome_map.get(ended_reason, "completed")

    logger.info(
        "end_of_call_received",
        session_id=session_id,
        duration=duration,
        ended_reason=ended_reason,
    )

    if session_id:
        cm = _get_call_manager()
        record = await cm.complete_call(
            session_id=session_id,
            outcome=outcome,
            duration_seconds=duration,
        )

        # Broadcast completion to dashboard
        try:
            ws = _get_connection_manager()
            await ws.broadcast_event(session_id, "call_completed", {
                "outcome": outcome,
                "duration_seconds": duration,
                "verification_record": record.to_report_dict() if record else None,
            })
        except Exception as e:
            logger.warning("websocket_broadcast_failed", error=str(e))

    return {"status": "ok"}


async def handle_transcript(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle transcript: real-time transcript update from Vapi."""
    session_id = _resolve_session(payload)
    message = payload.get("message", {})

    role = message.get("role", "unknown")
    transcript_text = message.get("transcript", "")

    if session_id and transcript_text:
        cm = _get_call_manager()
        await cm.update_transcript(session_id, role, transcript_text)

        # Broadcast to dashboard
        try:
            ws = _get_connection_manager()
            await ws.broadcast_event(session_id, "transcript_update", {
                "role": role,
                "content": transcript_text,
            })
        except Exception as e:
            logger.warning("websocket_broadcast_failed", error=str(e))

    return {"status": "ok"}


async def handle_status_update(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle status-update: call status changed (ringing, connected, ended)."""
    message = payload.get("message", {})
    call_status = message.get("status", "")
    session_id = _resolve_session(payload)

    logger.info(
        "status_update_received",
        call_status=call_status,
        session_id=session_id,
    )

    # Broadcast to dashboard
    if session_id:
        try:
            ws = _get_connection_manager()
            await ws.broadcast_event(session_id, "status_update", {
                "status": call_status,
            })
        except Exception as e:
            logger.warning("websocket_broadcast_failed", error=str(e))

    return {"status": "ok"}


# --- Function Call Handlers (invoked by the AI agent during calls) ---


async def handle_record_data_point(
    parameters: dict[str, Any], payload: dict[str, Any]
) -> str:
    """Record a verified data point from the employer."""
    session_id = _resolve_session(payload)
    field_name = parameters.get("field_name", "")
    value = parameters.get("value", "")
    confidence = parameters.get("confidence", "high")

    if session_id:
        cm = _get_call_manager()
        await cm.record_data_point(session_id, field_name, value, confidence)

        # Broadcast to dashboard
        try:
            ws = _get_connection_manager()
            await ws.broadcast_event(session_id, "data_point_recorded", {
                "field_name": field_name,
                "value": value,
                "confidence": confidence,
            })
        except Exception as e:
            logger.warning("websocket_broadcast_failed", error=str(e))

    logger.info("data_point_recorded", field_name=field_name, session_id=session_id)
    return f"Recorded {field_name}: {value}"


async def handle_record_redirect(
    parameters: dict[str, Any], payload: dict[str, Any]
) -> str:
    """Record that the employer uses a third-party verification service."""
    session_id = _resolve_session(payload)
    service_name = parameters.get("service_name", "")

    if session_id:
        cm = _get_call_manager()
        await cm.record_data_point(session_id, "third_party_redirect", service_name)

    logger.info("redirect_recorded", service_name=service_name, session_id=session_id)
    return f"Recorded redirect to {service_name}"


async def handle_record_no_record(
    parameters: dict[str, Any], payload: dict[str, Any]
) -> str:
    """Record that the employer has no record of the candidate."""
    session_id = _resolve_session(payload)

    if session_id:
        cm = _get_call_manager()
        await cm.record_data_point(session_id, "no_record", True)

    logger.info("no_record_recorded", session_id=session_id)
    return "Recorded: no record found"


async def handle_record_discrepancy(
    parameters: dict[str, Any], payload: dict[str, Any]
) -> str:
    """Record a discrepancy between candidate claim and employer response."""
    session_id = _resolve_session(payload)
    field_name = parameters.get("field_name", "")
    candidate_value = parameters.get("candidate_value", "")
    employer_value = parameters.get("employer_value", "")
    note = parameters.get("note", "")

    if session_id:
        cm = _get_call_manager()
        await cm.record_discrepancy(
            session_id, field_name, candidate_value, employer_value, note
        )

        # Broadcast to dashboard
        try:
            ws = _get_connection_manager()
            await ws.broadcast_event(session_id, "discrepancy_detected", {
                "field_name": field_name,
                "candidate_value": candidate_value,
                "employer_value": employer_value,
                "note": note,
            })
        except Exception as e:
            logger.warning("websocket_broadcast_failed", error=str(e))

    logger.info("discrepancy_recorded", field_name=field_name, session_id=session_id)
    return f"Recorded discrepancy for {field_name}"


async def handle_mark_state_transition(
    parameters: dict[str, Any], payload: dict[str, Any]
) -> str:
    """Mark a state transition in the conversation flow."""
    session_id = _resolve_session(payload)
    new_state = parameters.get("new_state", "")
    trigger = parameters.get("trigger", new_state.lower())

    if session_id:
        cm = _get_call_manager()
        success = await cm.transition_state(session_id, trigger)

        # Broadcast to dashboard
        try:
            ws = _get_connection_manager()
            call = cm.get_active_call(session_id)
            await ws.broadcast_event(session_id, "state_transition", {
                "new_state": call.session.current_state if call else new_state,
                "trigger": trigger,
                "success": success,
            })
        except Exception as e:
            logger.warning("websocket_broadcast_failed", error=str(e))

    logger.info("state_transition_marked", new_state=new_state, session_id=session_id)
    return f"Transitioned to {new_state}"


# Handler registries
WEBHOOK_HANDLERS: dict[str, Any] = {
    "assistant-request": handle_assistant_request,
    "function-call": handle_function_call,
    "tool-calls": handle_tool_calls,
    "end-of-call-report": handle_end_of_call,
    "transcript": handle_transcript,
    "status-update": handle_status_update,
}

FUNCTION_HANDLERS: dict[str, Any] = {
    "record_data_point": handle_record_data_point,
    "record_redirect": handle_record_redirect,
    "record_no_record": handle_record_no_record,
    "record_discrepancy": handle_record_discrepancy,
    "mark_state_transition": handle_mark_state_transition,
}

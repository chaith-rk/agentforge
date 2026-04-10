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

from src.config.agent_config import AgentConfig
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

    if not settings.vapi_webhook_secret:
        # No secret configured. Fail closed in production — a misconfigured
        # prod deploy must not accept unauthenticated webhooks. In dev we
        # log a loud warning and allow the request through so local testing
        # (ngrok, manual curl) is not blocked.
        if settings.is_production:
            logger.error(
                "webhook_secret_not_configured_in_production",
                path="/webhooks/vapi",
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook authentication not configured",
            )
        logger.warning(
            "webhook_secret_not_configured",
            path="/webhooks/vapi",
            environment=settings.environment.value,
        )
    else:
        signature_valid = validate_webhook_signature(
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

    Dynamically builds the system prompt from the agent's YAML config
    with candidate details interpolated. This means the Vapi dashboard
    assistant is only a fallback — the backend is the source of truth.
    """
    message = payload.get("message", {})
    call_data = message.get("call", {})
    metadata = call_data.get("metadata", {})

    agent_config_id = metadata.get("agent_config_id", "")
    candidate_claims = metadata.get("candidate_claims", {})
    subject_name = metadata.get("subject_name", "")

    logger.info(
        "assistant_request_received",
        agent_config_id=agent_config_id,
    )

    if not agent_config_id:
        # No metadata — fall back to Vapi dashboard assistant
        return {}

    cm = _get_call_manager()
    config = cm._agent_configs.get(agent_config_id)
    if not config:
        logger.warning("assistant_request_no_config", agent_config_id=agent_config_id)
        return {}

    # Build dynamic system prompt from YAML config + candidate data
    system_prompt = _build_dynamic_system_prompt(config, subject_name, candidate_claims)

    # Build tool definitions from the YAML data schema
    tools = _build_tool_definitions()

    assistant_config: dict[str, Any] = {
        "assistant": {
            "model": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "messages": [{"role": "system", "content": system_prompt}],
                "tools": tools,
                "temperature": config.voice_config.temperature,
            },
            "firstMessage": (
                f"Hi, my name is Sarah. I'm calling from AgentForge on a recorded line. "
                f"This call is regarding employment verification of {subject_name}. "
                f"May I speak to an authorized person who can verify employment?"
            ),
        }
    }

    # Add voice config if specified
    if config.voice_config.voice_id:
        assistant_config["assistant"]["voice"] = {
            "provider": "11labs",
            "voiceId": config.voice_config.voice_id,
        }

    logger.info("assistant_config_built", agent_config_id=agent_config_id)
    return assistant_config


def _build_dynamic_system_prompt(
    config: AgentConfig, subject_name: str, candidate_claims: dict[str, Any]
) -> str:
    """Build a system prompt dynamically from agent config and candidate data.

    The prompt is assembled from:
    1. Base role and rules (from the prompt template file)
    2. Candidate details (interpolated from claims)
    3. Verification questions (from data_schema question fields)
    """
    from pathlib import Path

    # Load base prompt template if it exists
    template_path = Path(config.system_prompt_template)
    if template_path.exists():
        base_prompt = template_path.read_text()
        base_prompt = _interpolate_template(base_prompt, subject_name, candidate_claims)
    else:
        # Build a minimal prompt from config
        base_prompt = (
            f"You are a {config.agent_name} calling on behalf of AgentForge, "
            f"a background screening company.\n\n"
            f"# Candidate: {subject_name}\n"
        )
        for key, value in candidate_claims.items():
            base_prompt += f"- {key}: {value}\n"

    # Append dynamically-generated verification questions from data_schema
    questions_section = "\n\n# Verification Questions (ask in this order)\n"
    questions_section += (
        "For each question below, use the record_data_point tool to record "
        "the answer with the corresponding field_name.\n\n"
    )
    has_questions = False
    for field_schema in config.data_schema:
        if not field_schema.question:
            continue
        question = _interpolate_template(
            field_schema.question, subject_name, candidate_claims
        )
        label = field_schema.display_name or field_schema.field_name
        questions_section += (
            f"- **{label}** (field_name: `{field_schema.field_name}`): "
            f"{question}\n"
        )
        has_questions = True

    if has_questions:
        base_prompt += questions_section

    return base_prompt


def _interpolate_template(
    template: str, subject_name: str, candidate_claims: dict[str, Any]
) -> str:
    """Replace {{variable}} placeholders with candidate claim values."""
    result = template.replace("{{subject_name}}", subject_name)
    for key, value in candidate_claims.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def _build_tool_definitions() -> list[dict[str, Any]]:
    """Build Vapi tool definitions for the AI agent to report data back."""
    return [
        {
            "type": "function",
            "function": {
                "name": "record_data_point",
                "description": "Record a verified data point from the employer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "field_name": {"type": "string", "description": "Which field is being verified (e.g., 'position', 'month_started')"},
                        "value": {"type": "string", "description": "What the employer said"},
                        "verbatim": {"type": "string", "description": "Exact quote from the employer"},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"], "description": "How clearly the employer stated this"},
                    },
                    "required": ["field_name", "value"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "record_discrepancy",
                "description": "Record when the employer's info differs from the candidate's claim",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "field_name": {"type": "string"},
                        "candidate_value": {"type": "string", "description": "What the candidate claimed"},
                        "employer_value": {"type": "string", "description": "What the employer said"},
                        "note": {"type": "string", "description": "Context (e.g., 'staffing agency', 'subsidiary')"},
                    },
                    "required": ["field_name", "candidate_value", "employer_value"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "record_redirect",
                "description": "Record that the employer uses a third-party verification service",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "Name of the service (e.g., The Work Number, Thomas & Company)"},
                    },
                    "required": ["service_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "record_no_record",
                "description": "Record that the employer has no record of the candidate",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "details": {"type": "string", "description": "Any additional context"},
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "mark_state_transition",
                "description": "Signal that you are moving to a new phase of the conversation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "new_state": {"type": "string", "description": "The state you are transitioning to"},
                        "trigger": {"type": "string", "description": "What caused this transition"},
                    },
                    "required": ["new_state"],
                },
            },
        },
    ]


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
        # Vapi uses OpenAI format: {id, type, function: {name, arguments}}
        func = tool_call.get("function", {})
        function_name = func.get("name", "") or tool_call.get("name", "")
        parameters = _normalize_parameters(
            func.get("arguments", tool_call.get("arguments", tool_call.get("parameters", {})))
        )
        tool_call_id = tool_call.get("id", "")

        result = await _execute_function_call(function_name, parameters, payload)
        results.append({"toolCallId": tool_call_id, "result": result})

    for item in tool_with_tool_call_list:
        tool_call = item.get("toolCall", {})
        tool = item.get("tool", {})

        # Also check nested function object
        func = tool_call.get("function", {})
        function_name = func.get("name", "") or tool_call.get("name", "") or tool.get("name", "")
        parameters = _normalize_parameters(
            func.get("arguments", tool_call.get("arguments", tool_call.get("parameters", {})))
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

        # Extract transcript from artifact if available
        artifact = message.get("artifact", {})
        artifact_messages = artifact.get("messages", [])
        if artifact_messages:
            ws = _get_connection_manager()
            for msg in artifact_messages:
                role = msg.get("role", "unknown")
                content = msg.get("message", msg.get("content", ""))
                if not content or role == "system":
                    continue
                if role == "assistant":
                    role = "agent"
                await cm.update_transcript(session_id, role, content)
                try:
                    await ws.broadcast_to_session(session_id, {
                        "type": "transcript",
                        "role": role,
                        "content": content,
                    })
                except Exception:
                    pass

        record = await cm.complete_call(
            session_id=session_id,
            outcome=outcome,
            duration_seconds=duration,
        )

        # Broadcast completion to dashboard — frontend expects {type} at top level
        try:
            ws = _get_connection_manager()
            await ws.broadcast_to_session(session_id, {
                "type": "call_completed",
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

        # Broadcast to dashboard — frontend expects {type, role, content} at top level
        try:
            ws = _get_connection_manager()
            await ws.broadcast_to_session(session_id, {
                "type": "transcript",
                "role": role,
                "content": transcript_text,
            })
        except Exception as e:
            logger.warning("websocket_broadcast_failed", error=str(e))

    return {"status": "ok"}


async def handle_conversation_update(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle conversation-update: Vapi sends the full conversation history.

    Each update fires when a new message is added. We broadcast only
    the latest message to avoid duplicates on the frontend.
    """
    session_id = _resolve_session(payload)
    message = payload.get("message", {})

    # Vapi sends messages in OpenAI format: [{role, content}, ...]
    messages = message.get("messagesOpenAIFormatted", []) or message.get("messages", [])

    if not session_id or not messages:
        return {"status": "ok"}

    # Only process the last (newest) message
    last_msg = messages[-1]
    role = last_msg.get("role", "unknown")
    content = last_msg.get("content", "")

    if not content or role == "system" or role == "tool":
        return {"status": "ok"}

    # Normalize role names
    if role == "assistant":
        role = "agent"

    cm = _get_call_manager()
    await cm.update_transcript(session_id, role, content)

    try:
        ws = _get_connection_manager()
        await ws.broadcast_to_session(session_id, {
            "type": "transcript",
            "role": role,
            "content": content,
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

    if not field_name:
        logger.warning(
            "record_data_point_missing_field_name",
            session_id=session_id,
            parameters_keys=list(parameters.keys()),
        )
        return "Error: field_name is required"

    if session_id:
        cm = _get_call_manager()
        await cm.record_data_point(session_id, field_name, value, confidence)

        # Broadcast to dashboard — frontend expects {type: "data_point", ...} at top level
        try:
            ws = _get_connection_manager()
            await ws.broadcast_to_session(session_id, {
                "type": "data_point",
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
    "conversation-update": handle_conversation_update,
    "status-update": handle_status_update,
}

FUNCTION_HANDLERS: dict[str, Any] = {
    "record_data_point": handle_record_data_point,
    "record_redirect": handle_record_redirect,
    "record_no_record": handle_record_no_record,
    "record_discrepancy": handle_record_discrepancy,
    "mark_state_transition": handle_mark_state_transition,
}

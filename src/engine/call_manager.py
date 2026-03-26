"""Call manager — central orchestrator for active verification calls.

The CallManager is the glue between all engine components. It manages
the lifecycle of each call: creating sessions, processing webhook events
through the state machine, recording data, logging to the audit trail,
persisting to the event store, and broadcasting to dashboard clients.

There is one CallManager per application instance. It holds references
to all active call sessions and their associated engine components.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from src.config.agent_config import AgentConfig
from src.config.loader import load_agent_config
from src.database.event_store import EventStore
from src.engine.audit_logger import AuditLogger
from src.engine.data_recorder import DataRecorder
from src.engine.state_machine import StateMachine
from src.models.call_session import CallOutcome, CallSession, CandidateClaim, ConfidenceLevel
from src.models.events import BaseEvent, EventType
from src.models.verification_record import FieldVerification, VerificationRecord

logger = structlog.get_logger(__name__)


class ActiveCall:
    """Holds all engine components for a single active call."""

    def __init__(
        self,
        session: CallSession,
        state_machine: StateMachine,
        data_recorder: DataRecorder,
        audit_logger: AuditLogger,
        agent_config: AgentConfig,
    ) -> None:
        self.session = session
        self.state_machine = state_machine
        self.data_recorder = data_recorder
        self.audit_logger = audit_logger
        self.agent_config = agent_config


class CallManager:
    """Central orchestrator for all active verification calls.

    Manages call lifecycle from initiation through completion. Wires
    webhook events to the appropriate engine components and persists
    everything to the event store.
    """

    def __init__(self, event_store: EventStore) -> None:
        self._event_store = event_store
        self._active_calls: dict[str, ActiveCall] = {}
        # Map vapi_call_id → session_id for webhook routing
        self._vapi_to_session: dict[str, str] = {}
        self._agent_configs: dict[str, AgentConfig] = {}

    def load_agent_config(self, config_path: str) -> AgentConfig:
        """Load and cache an agent configuration."""
        config = load_agent_config(config_path)
        self._agent_configs[config.agent_id] = config
        return config

    async def create_call(
        self,
        session_id: str,
        agent_config_id: str,
        candidate: CandidateClaim,
        vapi_call_id: str = "",
    ) -> CallSession:
        """Initialize a new call session with all engine components.

        Args:
            session_id: Unique session identifier.
            agent_config_id: Which agent config to use.
            candidate: The candidate's claimed employment details.
            vapi_call_id: Vapi's call ID for webhook correlation.

        Returns:
            The created CallSession.
        """
        # Load agent config
        config = self._agent_configs.get(agent_config_id)
        if not config:
            # Try loading from file
            config_path = f"agents/{agent_config_id.replace('_v1', '_call')}.yaml"
            try:
                config = self.load_agent_config(config_path)
            except FileNotFoundError:
                # Fallback: try the standard naming
                config = self.load_agent_config("agents/employment_verification_call.yaml")

        # Create session
        session = CallSession(
            session_id=session_id,
            agent_config_id=agent_config_id,
            current_state=config.initial_state,
            candidate=candidate,
            vapi_call_id=vapi_call_id,
        )

        # Initialize engine components
        state_machine = StateMachine(config=config, session_id=session_id)
        data_recorder = DataRecorder(session_id=session_id)
        audit_logger = AuditLogger(session_id=session_id)

        active_call = ActiveCall(
            session=session,
            state_machine=state_machine,
            data_recorder=data_recorder,
            audit_logger=audit_logger,
            agent_config=config,
        )

        self._active_calls[session_id] = active_call
        if vapi_call_id:
            self._vapi_to_session[vapi_call_id] = session_id

        # Persist to event store
        await self._event_store.create_session(
            session_id=session_id,
            agent_config_id=agent_config_id,
            initial_state=config.initial_state,
            candidate_data=candidate.model_dump(),
        )

        # Log call initiation
        await audit_logger.log_call_initiated(
            agent_config_id=agent_config_id,
            candidate_name=candidate.subject_name,
            company_name=candidate.claims.get("employer_company_name", candidate.claims.get("institution_name", "")),
        )

        # Persist initiation event
        for event in audit_logger.events:
            await self._event_store.append_event(event)

        logger.info(
            "call_session_created",
            session_id=session_id,
            agent_config_id=agent_config_id,
            vapi_call_id=vapi_call_id,
        )

        return session

    def get_active_call(self, session_id: str) -> ActiveCall | None:
        """Get an active call by session ID."""
        return self._active_calls.get(session_id)

    def get_call_by_vapi_id(self, vapi_call_id: str) -> ActiveCall | None:
        """Get an active call by Vapi call ID (for webhook routing)."""
        session_id = self._vapi_to_session.get(vapi_call_id)
        if session_id:
            return self._active_calls.get(session_id)
        return None

    def resolve_session_id(self, payload: dict[str, Any]) -> str | None:
        """Extract and resolve session ID from a Vapi webhook payload."""
        message = payload.get("message", {})
        call_data = message.get("call", {})

        # Try Vapi call ID first
        vapi_call_id = call_data.get("id", "")
        if vapi_call_id and vapi_call_id in self._vapi_to_session:
            return self._vapi_to_session[vapi_call_id]

        # Try metadata
        metadata = call_data.get("metadata", {})
        session_id = metadata.get("session_id", "")
        if session_id and session_id in self._active_calls:
            return session_id

        # Register new mapping if we find both
        if vapi_call_id and session_id:
            self._vapi_to_session[vapi_call_id] = session_id

        return session_id or None

    async def record_data_point(
        self,
        session_id: str,
        field_name: str,
        value: Any,
        confidence: str = "high",
    ) -> None:
        """Record a verified data point and persist it."""
        call = self._active_calls.get(session_id)
        if not call:
            logger.warning("record_data_point_no_session", session_id=session_id)
            return

        event = call.data_recorder.record_data_point(
            field_name=field_name,
            value=value,
            source="employer",
            confidence=confidence,
        )
        await call.audit_logger.log_event(event)
        await self._event_store.append_event(event)

        # Update session
        call.session.collected_data[field_name] = value
        call.session.updated_at = datetime.now(timezone.utc)

        logger.info(
            "data_point_persisted",
            session_id=session_id,
            field_name=field_name,
        )

    async def record_discrepancy(
        self,
        session_id: str,
        field_name: str,
        candidate_value: Any,
        employer_value: Any,
        note: str = "",
    ) -> None:
        """Record a discrepancy and persist it."""
        call = self._active_calls.get(session_id)
        if not call:
            return

        event = call.data_recorder.record_discrepancy(
            field_name=field_name,
            candidate_value=candidate_value,
            employer_value=employer_value,
            note=note,
        )
        await call.audit_logger.log_event(event)
        await self._event_store.append_event(event)

        logger.info(
            "discrepancy_persisted",
            session_id=session_id,
            field_name=field_name,
        )

    async def transition_state(
        self, session_id: str, trigger: str, payload: dict[str, Any] | None = None
    ) -> bool:
        """Process a state transition through the state machine."""
        call = self._active_calls.get(session_id)
        if not call:
            return False

        result = await call.state_machine.process_event(trigger, payload or {})

        # Persist all emitted events
        for event in result.events_emitted:
            await call.audit_logger.log_event(event)
            await self._event_store.append_event(event)

        if result.success and result.new_state:
            call.session.current_state = result.new_state
            call.session.updated_at = datetime.now(timezone.utc)
            await self._event_store.update_session_state(
                session_id, result.new_state
            )

        return result.success

    async def update_transcript(
        self, session_id: str, role: str, content: str
    ) -> None:
        """Append a transcript entry and persist it."""
        call = self._active_calls.get(session_id)
        if not call:
            return

        call.session.transcript.append({"role": role, "content": content})
        call.state_machine.context.setdefault("transcript", []).append(
            {"role": role, "content": content}
        )

        event = BaseEvent(
            session_id=session_id,
            event_type=EventType.TRANSCRIPT_UPDATED,
            payload={"role": role, "content": content},
            actor=role,
        )
        await self._event_store.append_event(event)

    async def complete_call(
        self,
        session_id: str,
        outcome: str = "completed",
        duration_seconds: float = 0.0,
    ) -> VerificationRecord | None:
        """Mark a call as complete and generate the verification record."""
        call = self._active_calls.get(session_id)
        if not call:
            return None

        # Update session
        call.session.outcome = CallOutcome(outcome) if outcome in CallOutcome.__members__.values() else CallOutcome.COMPLETED
        call.session.completed_at = datetime.now(timezone.utc)
        call.session.updated_at = datetime.now(timezone.utc)

        # Log completion
        completion_event = await call.audit_logger.log_call_completed(
            outcome=outcome,
            duration_seconds=duration_seconds,
        )
        await self._event_store.append_event(completion_event)
        await self._event_store.update_session_state(
            session_id, call.session.current_state, status=outcome
        )

        # Build verification record
        record = self._build_verification_record(call)

        # Snapshot the final state
        await self._event_store.create_snapshot(
            session_id, record.to_report_dict()
        )

        # Clean up active call
        del self._active_calls[session_id]
        # Keep vapi mapping for late-arriving webhooks
        logger.info(
            "call_completed",
            session_id=session_id,
            outcome=outcome,
            data_points=len(call.data_recorder.collected_data),
            discrepancies=len(call.data_recorder.discrepancies),
        )

        return record

    def _build_verification_record(self, call: ActiveCall) -> VerificationRecord:
        """Build a VerificationRecord from the completed call data.

        Dynamically iterates over the agent's data_schema to build
        field-by-field verifications. Works for any agent type without
        hardcoding field names.
        """
        collected = call.data_recorder.collected_data
        candidate = call.session.candidate
        candidate_claims = candidate.claims

        field_verifications = []

        # Dynamically build verifications from the agent's data schema
        for field_schema in call.agent_config.data_schema:
            field_name = field_schema.field_name

            # Skip metadata fields (verifier info, call outcome, etc.)
            if field_name in ("verifier_name", "verifier_title", "callback_number",
                              "third_party_redirect", "no_record", "call_outcome", "confidence"):
                continue

            # Get what the employer said (from collected data)
            employer_value = collected.get(field_name)

            # Get what the candidate claimed (from input)
            candidate_value = candidate_claims.get(field_name)

            # Only include fields that have at least one value
            if employer_value is not None or candidate_value is not None:
                # Determine match status
                match = None
                if employer_value is not None and candidate_value is not None:
                    match = str(employer_value).strip().lower() == str(candidate_value).strip().lower()

                field_verifications.append(FieldVerification(
                    field_name=field_name,
                    display_name=field_schema.display_name or field_schema.description,
                    candidate_value=candidate_value,
                    employer_value=employer_value,
                    match=match,
                    not_provided=employer_value is None,
                ))

        audit_event_ids = [e.event_id for e in call.audit_logger.events]

        return VerificationRecord(
            session_id=call.session.session_id,
            agent_config_id=call.session.agent_config_id,
            subject_name=candidate.subject_name,
            verifier_name=call.session.verifier_name or collected.get("verifier_name", ""),
            verifier_title=call.session.verifier_title or collected.get("verifier_title", ""),
            field_verifications=field_verifications,
            discrepancies=call.session.discrepancies,
            fields_refused=call.session.fields_refused,
            outcome=call.session.outcome,
            confidence=call.session.confidence,
            third_party_redirect=collected.get("third_party_redirect", ""),
            callback_number=collected.get("callback_number", ""),
            audit_event_ids=audit_event_ids,
            call_started_at=call.session.created_at,
            call_completed_at=call.session.completed_at,
        )

    async def get_session_data(self, session_id: str) -> dict[str, Any] | None:
        """Get current session data (from active call or event store)."""
        call = self._active_calls.get(session_id)
        if call:
            return {
                "session_id": session_id,
                "current_state": call.session.current_state,
                "outcome": call.session.outcome.value,
                "collected_data": call.data_recorder.collected_data,
                "discrepancies": call.data_recorder.discrepancies,
                "transcript": call.session.transcript,
                "created_at": call.session.created_at.isoformat(),
                "updated_at": call.session.updated_at.isoformat(),
            }

        # Fall back to event store
        return await self._event_store.get_session(session_id)

    async def get_session_events(self, session_id: str) -> list[dict[str, Any]]:
        """Get all events for a session from the event store."""
        return await self._event_store.get_events_for_session(session_id)

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List all sessions from the event store."""
        return await self._event_store.list_sessions(limit=limit, offset=offset)

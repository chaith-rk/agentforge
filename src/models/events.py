"""Event models for event-sourced architecture.

Every action in the system is recorded as an immutable event. The current state
of any call session can be reconstructed by replaying its events in order.
This provides a complete, tamper-evident audit trail — critical for compliance.

Events are the single source of truth. All other data views (call sessions,
verification records, dashboards) are derived from events.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """All event types in the system.

    Each event type maps to a specific action that occurred during a call.
    New event types can be added as the platform evolves.
    """

    CALL_INITIATED = "call_initiated"
    CALL_COMPLETED = "call_completed"
    STATE_TRANSITION = "state_transition"
    DATA_POINT_RECORDED = "data_point_recorded"
    DISCREPANCY_DETECTED = "discrepancy_detected"
    COMPLIANCE_CHECK_PASSED = "compliance_check_passed"
    COMPLIANCE_CHECK_FAILED = "compliance_check_failed"
    REDIRECT_RECORDED = "redirect_recorded"
    NO_RECORD_FOUND = "no_record_found"
    VOICEMAIL_LEFT = "voicemail_left"
    CALL_REFUSED = "call_refused"
    TRANSCRIPT_UPDATED = "transcript_updated"
    ERROR_OCCURRED = "error_occurred"
    EVAL_COMPLETED = "eval_completed"


class BaseEvent(BaseModel):
    """Base event model. All events in the system inherit from this.

    Events are immutable once created. The event_id and timestamp are
    generated automatically. The actor field tracks who/what caused the event.
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Call session this event belongs to")
    event_type: EventType = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    actor: str = Field(
        default="system",
        description="Who caused this event (system, agent, verifier, operator)",
    )


class CallInitiatedEvent(BaseEvent):
    """Emitted when a new verification call is started."""

    event_type: EventType = EventType.CALL_INITIATED


class StateTransitionEvent(BaseEvent):
    """Emitted when the conversation moves to a new state."""

    event_type: EventType = EventType.STATE_TRANSITION

    @property
    def from_state(self) -> str:
        return self.payload.get("from_state", "")

    @property
    def to_state(self) -> str:
        return self.payload.get("to_state", "")

    @property
    def trigger(self) -> str:
        return self.payload.get("trigger", "")


class DataPointRecordedEvent(BaseEvent):
    """Emitted when a verification data point is collected from the employer."""

    event_type: EventType = EventType.DATA_POINT_RECORDED

    @property
    def field_name(self) -> str:
        return self.payload.get("field_name", "")

    @property
    def value(self) -> Any:
        return self.payload.get("value")

    @property
    def source(self) -> str:
        return self.payload.get("source", "")

    @property
    def confidence(self) -> str:
        return self.payload.get("confidence", "high")


class DiscrepancyDetectedEvent(BaseEvent):
    """Emitted when employer's information differs from candidate's claim.

    Both values are recorded — the agent never comments on discrepancies
    to the employer. Matching logic happens downstream.
    """

    event_type: EventType = EventType.DISCREPANCY_DETECTED

    @property
    def field_name(self) -> str:
        return self.payload.get("field_name", "")

    @property
    def candidate_value(self) -> Any:
        return self.payload.get("candidate_value")

    @property
    def employer_value(self) -> Any:
        return self.payload.get("employer_value")

    @property
    def note(self) -> str:
        return self.payload.get("note", "")


class ComplianceCheckEvent(BaseEvent):
    """Emitted when a compliance checkpoint is evaluated."""

    @property
    def checkpoint_name(self) -> str:
        return self.payload.get("checkpoint_name", "")

    @property
    def passed(self) -> bool:
        return self.event_type == EventType.COMPLIANCE_CHECK_PASSED


class CallCompletedEvent(BaseEvent):
    """Emitted when a call ends, regardless of outcome."""

    event_type: EventType = EventType.CALL_COMPLETED

    @property
    def outcome(self) -> str:
        return self.payload.get("outcome", "")

    @property
    def duration_seconds(self) -> float:
        return self.payload.get("duration_seconds", 0.0)


class TranscriptUpdatedEvent(BaseEvent):
    """Emitted when new transcript content is available from Vapi."""

    event_type: EventType = EventType.TRANSCRIPT_UPDATED

    @property
    def role(self) -> str:
        return self.payload.get("role", "")

    @property
    def content(self) -> str:
        return self.payload.get("content", "")

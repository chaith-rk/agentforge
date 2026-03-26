"""Call session model representing an active or completed verification call.

A call session tracks the full lifecycle of a single verification call,
from initiation through completion. It holds the current state, collected
data, discrepancies, and compliance status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CallOutcome(str, Enum):
    """Final outcome of a verification call."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REDIRECTED = "redirected"
    NO_RECORD = "no_record"
    VOICEMAIL = "voicemail"
    REFUSED = "refused"
    DEAD_END = "dead_end"
    ERROR = "error"


class ConfidenceLevel(str, Enum):
    """Confidence in the verification data collected."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Discrepancy(BaseModel):
    """Records a difference between candidate's claim and employer's response."""

    field_name: str
    candidate_value: Any
    employer_value: Any
    note: str = ""
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CandidateClaim(BaseModel):
    """The candidate's claimed details — input to the verification.

    This model is agent-agnostic. The `subject_name` is always required.
    All other candidate-provided fields are stored in `claims`, a flexible
    dict validated at runtime against the agent's YAML data_schema.
    """

    subject_name: str
    phone_number: str = ""
    claims: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific candidate claims, keyed by field_name from data_schema",
    )


class CallSession(BaseModel):
    """Full state of a single verification call.

    This model is a materialized view derived from events. It's updated
    as events are appended and can be fully reconstructed by replaying
    the event stream for this session.
    """

    session_id: str
    agent_config_id: str
    current_state: str
    candidate: CandidateClaim

    # Collected verification data
    collected_data: dict[str, Any] = Field(default_factory=dict)
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    compliance_status: dict[str, bool] = Field(default_factory=dict)
    fields_refused: list[str] = Field(default_factory=list)

    # Call outcome
    outcome: CallOutcome = CallOutcome.IN_PROGRESS
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH

    # Verifier info
    verifier_name: str = ""
    verifier_title: str = ""
    callback_number: str = ""

    # Third-party redirect
    third_party_redirect: str = ""

    # Vapi call tracking
    vapi_call_id: str = ""

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    # Transcript
    transcript: list[dict[str, str]] = Field(default_factory=list)

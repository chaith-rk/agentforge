"""Verification record — the final output of a completed call.

This is the structured data that downstream systems consume. It contains
everything needed for the "apple-to-apple" matching: both the candidate's
claims and the employer's confirmations, with match indicators.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.models.call_session import CallOutcome, ConfidenceLevel, Discrepancy


class FieldVerification(BaseModel):
    """Verification result for a single field."""

    field_name: str
    candidate_value: Any = None
    employer_value: Any = None
    match: bool | None = None
    not_provided: bool = False
    note: str = ""


class VerificationRecord(BaseModel):
    """Final structured output of a completed verification call.

    This record is what gets sent to downstream matching systems.
    Every field includes both the candidate's claim and the employer's
    response, enabling the strict "apple-to-apple" comparison.
    """

    session_id: str
    agent_config_id: str

    # Subject
    subject_name: str
    company_name: str

    # Verifier
    verifier_name: str = ""
    verifier_title: str = ""

    # Field-by-field verification results
    field_verifications: list[FieldVerification] = Field(default_factory=list)

    # Discrepancies (any field where candidate != employer)
    discrepancies: list[Discrepancy] = Field(default_factory=list)

    # Fields the employer refused to share
    fields_refused: list[str] = Field(default_factory=list)

    # Overall outcome
    outcome: CallOutcome
    confidence: ConfidenceLevel

    # Third-party redirect info
    third_party_redirect: str = ""

    # Audit trail
    audit_event_ids: list[str] = Field(default_factory=list)

    # Callback for follow-up
    callback_number: str = ""

    # Timestamps
    call_started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    call_completed_at: datetime | None = None
    record_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_report_dict(self) -> dict[str, Any]:
        """Produce a flat dictionary for downstream systems and reporting.

        Returns a simplified view of the verification suitable for
        integration with existing Vetty reporting workflows.
        """
        report: dict[str, Any] = {
            "session_id": self.session_id,
            "subject_name": self.subject_name,
            "company_name": self.company_name,
            "verifier_name": self.verifier_name,
            "verifier_title": self.verifier_title,
            "outcome": self.outcome.value,
            "confidence": self.confidence.value,
            "has_discrepancies": len(self.discrepancies) > 0,
            "discrepancy_count": len(self.discrepancies),
            "fields_refused": self.fields_refused,
            "third_party_redirect": self.third_party_redirect,
            "callback_number": self.callback_number,
            "call_started_at": self.call_started_at.isoformat(),
            "call_completed_at": (
                self.call_completed_at.isoformat() if self.call_completed_at else None
            ),
        }

        # Flatten field verifications
        for fv in self.field_verifications:
            report[f"{fv.field_name}_candidate"] = fv.candidate_value
            report[f"{fv.field_name}_employer"] = fv.employer_value
            report[f"{fv.field_name}_match"] = fv.match

        return report

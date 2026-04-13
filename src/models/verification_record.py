"""Verification record — the final output of a completed call.

This is the structured data that downstream systems consume. It contains
everything needed for the "apple-to-apple" matching: both the candidate's
claims and the employer's confirmations, with match indicators.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.engine.evals.base import EvalResult
from src.models.call_session import CallOutcome, ConfidenceLevel, Discrepancy


class FieldVerification(BaseModel):
    """Verification result for a single field."""

    field_name: str
    display_name: str = ""
    candidate_value: Any = None
    employer_value: Any = None
    match: bool | None = None
    not_provided: bool = False
    note: str = ""

    @property
    def status(self) -> str:
        """Derive verification status using the Apple-to-Apple rule.

        - verified: exact match between candidate and employer values
        - review_needed: values differ in any way (even 1 day)
        - unable_to_verify: employer refused or field not asked
        """
        if self.not_provided:
            return "unable_to_verify"
        if self.match is None:
            return "unable_to_verify"
        return "verified" if self.match else "review_needed"


class VerificationRecord(BaseModel):
    """Final structured output of a completed verification call.

    Agent-agnostic: works for employment, education, or any future
    agent type. Every field includes both the candidate's claim and
    the employer's confirmation, enabling the strict "apple-to-apple" comparison.
    """

    session_id: str
    agent_config_id: str

    # Subject
    subject_name: str

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

    # Eval results
    eval_results: list[EvalResult] = Field(default_factory=list)

    # Audit trail
    audit_event_ids: list[str] = Field(default_factory=list)

    # Callback for follow-up
    callback_number: str = ""

    # Timestamps
    call_started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    call_completed_at: datetime | None = None
    record_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def overall_status(self) -> str:
        """Derive overall verification status — worst individual status wins."""
        statuses = [fv.status for fv in self.field_verifications]
        if "review_needed" in statuses:
            return "review_needed"
        if "unable_to_verify" in statuses:
            return "unable_to_verify"
        if statuses:
            return "verified"
        return "unable_to_verify"

    def to_report_dict(self) -> dict[str, Any]:
        """Produce a structured dictionary for downstream systems and the UI.

        Returns a rich view of the verification with per-field status,
        suitable for the side-by-side display and API responses.
        """
        fields = []
        for fv in self.field_verifications:
            fields.append({
                "field_name": fv.field_name,
                "display_name": fv.display_name or fv.field_name,
                "candidate_value": fv.candidate_value,
                "employer_value": fv.employer_value,
                "status": fv.status,
                "match": fv.match,
                "note": fv.note,
            })

        return {
            "session_id": self.session_id,
            "agent_config_id": self.agent_config_id,
            "subject_name": self.subject_name,
            "verifier_name": self.verifier_name,
            "verifier_title": self.verifier_title,
            "overall_status": self.overall_status,
            "outcome": self.outcome.value,
            "confidence": self.confidence.value,
            "fields": fields,
            "has_discrepancies": len(self.discrepancies) > 0,
            "discrepancy_count": len(self.discrepancies),
            "fields_refused": self.fields_refused,
            "third_party_redirect": self.third_party_redirect,
            "callback_number": self.callback_number,
            "call_started_at": self.call_started_at.isoformat(),
            "call_completed_at": (
                self.call_completed_at.isoformat() if self.call_completed_at else None
            ),
            "eval_results": [r.model_dump(mode="json") for r in self.eval_results],
            "eval_pass_rate": (
                sum(1 for r in self.eval_results if r.passed) / len(self.eval_results)
                if self.eval_results else None
            ),
        }

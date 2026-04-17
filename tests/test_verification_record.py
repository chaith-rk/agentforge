"""Tests for VerificationRecord and FieldVerification — status derivation,
count properties, and to_report_dict serialization including the new
fields for the post-call report (summary, counts, question, confidence).
"""
from __future__ import annotations

import pytest

from src.models.call_session import CallOutcome, ConfidenceLevel
from src.models.verification_record import FieldVerification, VerificationRecord


def _make_record(*fields: FieldVerification, summary: str = "") -> VerificationRecord:
    return VerificationRecord(
        session_id="sess-1",
        agent_config_id="employment_v1",
        subject_name="Jane Doe",
        field_verifications=list(fields),
        outcome=CallOutcome.COMPLETED,
        confidence=ConfidenceLevel.HIGH,
        summary=summary,
    )


# --- FieldVerification.status -------------------------------------------------


def test_status_verified_on_exact_match() -> None:
    fv = FieldVerification(field_name="title", candidate_value="Engineer", employer_value="Engineer", match=True)
    assert fv.status == "verified"


def test_status_review_needed_on_mismatch() -> None:
    fv = FieldVerification(field_name="title", candidate_value="Engineer", employer_value="Manager", match=False)
    assert fv.status == "review_needed"


def test_status_unable_to_verify_when_not_provided() -> None:
    fv = FieldVerification(field_name="title", candidate_value="Engineer", not_provided=True)
    assert fv.status == "unable_to_verify"


def test_status_unable_to_verify_when_match_is_none() -> None:
    fv = FieldVerification(field_name="title", candidate_value="Engineer", employer_value="Engineer", match=None)
    assert fv.status == "unable_to_verify"


# --- Count properties --------------------------------------------------------


def test_counts_mixed_statuses() -> None:
    record = _make_record(
        FieldVerification(field_name="a", candidate_value="x", employer_value="x", match=True),
        FieldVerification(field_name="b", candidate_value="x", employer_value="y", match=False),
        FieldVerification(field_name="c", candidate_value="x", not_provided=True),
        FieldVerification(field_name="d", candidate_value="x", employer_value="x", match=True),
    )
    assert record.confirmed_facts_count == 2
    assert record.contradictions_count == 1
    assert record.items_to_clarify_count == 1


def test_counts_all_zero_on_empty_record() -> None:
    record = _make_record()
    assert record.confirmed_facts_count == 0
    assert record.contradictions_count == 0
    assert record.items_to_clarify_count == 0


# --- to_report_dict ----------------------------------------------------------


def test_to_report_dict_includes_new_fields() -> None:
    record = _make_record(
        FieldVerification(
            field_name="title",
            display_name="Job Title",
            question="What was their job title?",
            candidate_value="Engineer",
            employer_value="Engineer",
            match=True,
            confidence="high",
        ),
        summary="The HR rep confirmed employment with no discrepancies.",
    )
    report = record.to_report_dict()

    # Record-level
    assert report["summary"] == "The HR rep confirmed employment with no discrepancies."
    assert report["confirmed_facts_count"] == 1
    assert report["contradictions_count"] == 0
    assert report["items_to_clarify_count"] == 0

    # Per-field
    assert len(report["fields"]) == 1
    field = report["fields"][0]
    assert field["question"] == "What was their job title?"
    assert field["confidence"] == "high"
    assert field["status"] == "verified"


def test_to_report_dict_defaults_when_missing() -> None:
    """Record with an empty summary and no confidence should still serialize cleanly."""
    record = _make_record(
        FieldVerification(field_name="x", candidate_value="a", employer_value="a", match=True),
    )
    report = record.to_report_dict()
    assert report["summary"] == ""
    assert report["fields"][0]["confidence"] is None
    assert report["fields"][0]["question"] == ""


# --- overall_status ----------------------------------------------------------


def test_overall_status_worst_wins() -> None:
    record = _make_record(
        FieldVerification(field_name="a", candidate_value="x", employer_value="x", match=True),
        FieldVerification(field_name="b", candidate_value="x", employer_value="y", match=False),
    )
    assert record.overall_status == "review_needed"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])

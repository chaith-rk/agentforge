"""Tests for the code-based eval checks in src/engine/evals/code_evals.py."""
from __future__ import annotations

import pytest

from src.engine.evals.code_evals import (
    CompletenessEval,
    FormatValidationEval,
    RecordedLineDisclosureEval,
    StatusAccuracyEval,
)
from src.engine.evals.runner import EvalRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _transcript(*agent_messages: str) -> list[dict]:
    """Build a minimal transcript with agent turns only."""
    return [{"role": "agent", "content": msg} for msg in agent_messages]


def _fv(
    field_name: str,
    candidate_value: str | None,
    employer_value: str | None,
    match: bool | None,
    status: str,
) -> dict:
    """Build a field_verification entry."""
    return {
        "field_name": field_name,
        "candidate_value": candidate_value,
        "employer_value": employer_value,
        "match": match,
        "status": status,
    }


# ---------------------------------------------------------------------------
# RecordedLineDisclosureEval
# ---------------------------------------------------------------------------

class TestRecordedLineDisclosureEval:
    """Tests for RecordedLineDisclosureEval."""

    @pytest.mark.asyncio
    async def test_passes_when_disclosure_in_first_turn(self) -> None:
        call_data = {
            "transcript": _transcript(
                "Hi, I'm calling from AgentForge on a recorded line. This is an employment verification.",
                "May I speak to an authorized person?",
            )
        }
        result = await RecordedLineDisclosureEval().evaluate(call_data)
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_passes_when_disclosure_in_second_turn(self) -> None:
        call_data = {
            "transcript": _transcript(
                "Hi, I'm calling from AgentForge.",
                "This is on a recorded line — employment verification of John Doe.",
            )
        }
        result = await RecordedLineDisclosureEval().evaluate(call_data)
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_fails_when_disclosure_missing(self) -> None:
        call_data = {
            "transcript": _transcript(
                "Hi, I'm calling from AgentForge.",
                "I need to verify employment for John Doe.",
            )
        }
        result = await RecordedLineDisclosureEval().evaluate(call_data)
        assert result.passed is False
        assert result.score == 0.0
        assert "NOT found" in result.details

    @pytest.mark.asyncio
    async def test_fails_when_disclosure_only_in_third_turn(self) -> None:
        """Disclosure in the third agent turn does not satisfy the requirement."""
        call_data = {
            "transcript": _transcript(
                "Hi, I'm calling from AgentForge.",
                "May I speak to HR?",
                "Just to note, this is on a recorded line.",
            )
        }
        result = await RecordedLineDisclosureEval().evaluate(call_data)
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_passes_with_mixed_roles(self) -> None:
        """Non-agent turns should be ignored when counting agent turns."""
        call_data = {
            "transcript": [
                {"role": "user", "content": "Hello?"},
                {"role": "agent", "content": "Hi, calling from AgentForge on a recorded line."},
                {"role": "user", "content": "Sure, how can I help?"},
            ]
        }
        result = await RecordedLineDisclosureEval().evaluate(call_data)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fails_with_empty_transcript(self) -> None:
        result = await RecordedLineDisclosureEval().evaluate({"transcript": []})
        assert result.passed is False
        assert result.score == 0.0


# ---------------------------------------------------------------------------
# CompletenessEval
# ---------------------------------------------------------------------------

class TestCompletenessEval:
    """Tests for CompletenessEval."""

    @pytest.mark.asyncio
    async def test_passes_with_all_required_fields(self) -> None:
        call_data = {
            "collected_data": {
                "verifier_name": "Jane Smith",
                "job_title_confirmed": "Software Engineer",
                "start_date_confirmed": "2020-01",
            },
            "outcome": "completed",
        }
        result = await CompletenessEval().evaluate(call_data)
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_passes_with_partial_fields_above_threshold(self) -> None:
        """3/3 required fields gives score=1.0, still passes."""
        call_data = {
            "collected_data": {
                "verifier_name": "Jane Smith",
                "job_title_confirmed": "Engineer",
                "start_date_confirmed": "2019-06",
            },
            "outcome": "completed",
        }
        result = await CompletenessEval().evaluate(call_data)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fails_with_no_required_fields(self) -> None:
        call_data = {
            "collected_data": {"callback_number": "555-1234"},
            "outcome": "completed",
        }
        result = await CompletenessEval().evaluate(call_data)
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_passes_for_voicemail_outcome(self) -> None:
        """Completeness is not applicable when the call goes to voicemail."""
        call_data = {"collected_data": {}, "outcome": "voicemail"}
        result = await CompletenessEval().evaluate(call_data)
        assert result.passed is True
        assert result.score == 1.0
        assert "not applicable" in result.details

    @pytest.mark.asyncio
    async def test_passes_for_refused_outcome(self) -> None:
        call_data = {"collected_data": {}, "outcome": "refused"}
        result = await CompletenessEval().evaluate(call_data)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_passes_for_no_record_outcome(self) -> None:
        call_data = {"collected_data": {}, "outcome": "no_record"}
        result = await CompletenessEval().evaluate(call_data)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_score_reflects_partial_collection(self) -> None:
        """Collecting 1 of 3 required fields gives score ~0.33 (below threshold)."""
        call_data = {
            "collected_data": {"verifier_name": "Bob"},
            "outcome": "completed",
        }
        result = await CompletenessEval().evaluate(call_data)
        assert result.passed is False
        assert abs(result.score - 1 / 3) < 0.01


# ---------------------------------------------------------------------------
# StatusAccuracyEval
# ---------------------------------------------------------------------------

class TestStatusAccuracyEval:
    """Tests for StatusAccuracyEval."""

    @pytest.mark.asyncio
    async def test_passes_with_no_field_verifications(self) -> None:
        result = await StatusAccuracyEval().evaluate({"field_verifications": []})
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_passes_when_all_statuses_correct(self) -> None:
        call_data = {
            "field_verifications": [
                _fv("job_title_confirmed", "Engineer", "Engineer", True, "verified"),
                _fv("start_date_confirmed", "2020-01", "2020-03", False, "review_needed"),
                _fv("end_date_confirmed", "2022-06", None, None, "unable_to_verify"),
            ]
        }
        result = await StatusAccuracyEval().evaluate(call_data)
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_fails_when_match_true_but_status_review_needed(self) -> None:
        call_data = {
            "field_verifications": [
                _fv("job_title_confirmed", "Engineer", "Engineer", True, "review_needed"),
            ]
        }
        result = await StatusAccuracyEval().evaluate(call_data)
        assert result.passed is False
        assert result.score < 1.0
        assert "job_title_confirmed" in result.details

    @pytest.mark.asyncio
    async def test_fails_when_match_false_but_status_verified(self) -> None:
        call_data = {
            "field_verifications": [
                _fv("start_date_confirmed", "2020-01", "2019-06", False, "verified"),
            ]
        }
        result = await StatusAccuracyEval().evaluate(call_data)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_fails_when_employer_value_none_but_status_verified(self) -> None:
        call_data = {
            "field_verifications": [
                _fv("end_date_confirmed", "2022-06", None, None, "verified"),
            ]
        }
        result = await StatusAccuracyEval().evaluate(call_data)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_score_reflects_error_ratio(self) -> None:
        """One error out of two verifications should give score = 0.5."""
        call_data = {
            "field_verifications": [
                _fv("job_title_confirmed", "Engineer", "Engineer", True, "verified"),
                _fv("start_date_confirmed", "2020-01", "2019-06", False, "verified"),  # wrong
            ]
        }
        result = await StatusAccuracyEval().evaluate(call_data)
        assert result.passed is False
        assert abs(result.score - 0.5) < 0.01

    @pytest.mark.asyncio
    async def test_skips_entries_with_empty_reported_status(self) -> None:
        """An empty reported_status string should not count as an error."""
        call_data = {
            "field_verifications": [
                _fv("company_name_confirmed", "Acme", "Acme", True, ""),
            ]
        }
        result = await StatusAccuracyEval().evaluate(call_data)
        assert result.passed is True


# ---------------------------------------------------------------------------
# FormatValidationEval
# ---------------------------------------------------------------------------

class TestFormatValidationEval:
    """Tests for FormatValidationEval."""

    @pytest.mark.asyncio
    async def test_passes_with_valid_outcome(self) -> None:
        call_data = {"collected_data": {"call_outcome": "completed"}}
        result = await FormatValidationEval().evaluate(call_data)
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_passes_with_valid_employment_status(self) -> None:
        call_data = {"collected_data": {"employment_status": "full-time"}}
        result = await FormatValidationEval().evaluate(call_data)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fails_with_invalid_call_outcome(self) -> None:
        call_data = {"collected_data": {"call_outcome": "unknown_outcome"}}
        result = await FormatValidationEval().evaluate(call_data)
        assert result.passed is False
        assert result.score == 0.0
        assert "call_outcome" in result.details

    @pytest.mark.asyncio
    async def test_fails_with_invalid_employment_status(self) -> None:
        call_data = {"collected_data": {"employment_status": "freelance"}}
        result = await FormatValidationEval().evaluate(call_data)
        assert result.passed is False
        assert "employment_status" in result.details

    @pytest.mark.asyncio
    async def test_passes_when_fields_absent(self) -> None:
        """No call_outcome or employment_status means nothing to validate — should pass."""
        call_data = {"collected_data": {"verifier_name": "Jane"}}
        result = await FormatValidationEval().evaluate(call_data)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fails_with_multiple_invalid_fields(self) -> None:
        call_data = {
            "collected_data": {
                "call_outcome": "bad_outcome",
                "employment_status": "freelance",
            }
        }
        result = await FormatValidationEval().evaluate(call_data)
        assert result.passed is False
        assert "call_outcome" in result.details
        assert "employment_status" in result.details

    @pytest.mark.asyncio
    async def test_all_valid_outcomes_pass(self) -> None:
        valid_outcomes = ["completed", "redirected", "no_record", "voicemail", "refused", "dead_end"]
        for outcome in valid_outcomes:
            call_data = {"collected_data": {"call_outcome": outcome}}
            result = await FormatValidationEval().evaluate(call_data)
            assert result.passed is True, f"Expected {outcome!r} to be a valid call_outcome"

    @pytest.mark.asyncio
    async def test_all_valid_employment_statuses_pass(self) -> None:
        valid_statuses = ["full-time", "part-time", "contract", "temporary", "intern"]
        for status in valid_statuses:
            call_data = {"collected_data": {"employment_status": status}}
            result = await FormatValidationEval().evaluate(call_data)
            assert result.passed is True, f"Expected {status!r} to be a valid employment_status"


# ---------------------------------------------------------------------------
# EvalRunner integration
# ---------------------------------------------------------------------------

class TestEvalRunner:
    """Integration-level tests for EvalRunner."""

    @pytest.mark.asyncio
    async def test_run_all_returns_result_for_every_eval(self) -> None:
        runner = EvalRunner()
        call_data = {
            "transcript": _transcript("Hi, calling from AgentForge on a recorded line."),
            "collected_data": {
                "verifier_name": "Jane",
                "job_title_confirmed": "Engineer",
                "start_date_confirmed": "2020-01",
                "call_outcome": "completed",
            },
            "field_verifications": [],
            "outcome": "completed",
        }
        results = await runner.run_all(call_data)
        assert len(results) == len(runner.evals)

    @pytest.mark.asyncio
    async def test_summary_computes_pass_rate(self) -> None:
        runner = EvalRunner()
        call_data = {
            "transcript": _transcript("Hi, calling from AgentForge on a recorded line."),
            "collected_data": {
                "verifier_name": "Jane",
                "job_title_confirmed": "Engineer",
                "start_date_confirmed": "2020-01",
                "call_outcome": "completed",
            },
            "field_verifications": [],
            "outcome": "completed",
        }
        results = await runner.run_all(call_data)
        summary = runner.summary(results)
        assert "pass_rate" in summary
        assert 0.0 <= summary["pass_rate"] <= 1.0
        assert summary["total"] == len(runner.evals)
        assert summary["passed"] <= summary["total"]

    def test_summary_with_empty_results(self) -> None:
        runner = EvalRunner()
        summary = runner.summary([])
        assert summary["pass_rate"] == 0.0
        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["by_category"] == {}

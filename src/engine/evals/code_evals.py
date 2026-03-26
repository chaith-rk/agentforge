"""Code-based (deterministic) eval checks — no LLM required."""
from __future__ import annotations

from src.engine.evals.base import BaseEval, EvalResult


class RecordedLineDisclosureEval(BaseEval):
    """Check that the agent disclosed 'recorded line' in the first 2 agent turns."""

    name = "recorded_line_disclosure"
    description = "Agent must mention 'recorded line' early in the call"
    category = "compliance"

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Return passed=True only if 'recorded line' appears in the first 2 agent turns."""
        transcript = call_data.get("transcript", [])
        agent_turns = [t for t in transcript if t.get("role") in ("agent", "assistant")]
        first_two = agent_turns[:2]
        found = any("recorded line" in t.get("content", "").lower() for t in first_two)
        return EvalResult(
            eval_name=self.name,
            category=self.category,
            passed=found,
            score=1.0 if found else 0.0,
            details=(
                "Recorded line disclosure found in opening"
                if found
                else "Recorded line disclosure NOT found in first 2 agent turns"
            ),
        )


class CompletenessEval(BaseEval):
    """Check that all required fields were collected."""

    name = "completeness"
    description = "All required fields should be collected"
    category = "completeness"

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Score completeness as fraction of required fields present in collected_data.

        Returns passed=True when the score is at or above 0.8, or when the call
        outcome makes completeness not applicable (voicemail, refused, etc.).
        """
        collected = call_data.get("collected_data", {})
        required_fields = ["verifier_name", "job_title_confirmed", "start_date_confirmed"]
        outcome = call_data.get("outcome", "")

        if outcome in ("refused", "no_record", "voicemail", "dead_end"):
            return EvalResult(
                eval_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                details=f"Call outcome was {outcome} — completeness not applicable",
            )

        collected_required = [f for f in required_fields if f in collected]
        score = len(collected_required) / len(required_fields) if required_fields else 1.0
        passed = score >= 0.8
        return EvalResult(
            eval_name=self.name,
            category=self.category,
            passed=passed,
            score=score,
            details=f"Collected {len(collected_required)}/{len(required_fields)} required fields",
        )


class StatusAccuracyEval(BaseEval):
    """Check that verified/review_needed statuses are correctly derived.

    Applies the Apple-to-Apple rule: exact match -> verified, any difference ->
    review_needed, employer_value absent -> unable_to_verify.
    """

    name = "status_accuracy"
    description = "Field statuses must follow the Apple-to-Apple rule"
    category = "accuracy"

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Validate each field_verification entry against the expected derived status."""
        field_verifications = call_data.get("field_verifications", [])
        if not field_verifications:
            return EvalResult(
                eval_name=self.name,
                category=self.category,
                passed=True,
                score=1.0,
                details="No field verifications to check",
            )

        errors: list[str] = []
        for fv in field_verifications:
            candidate_val = fv.get("candidate_value")
            employer_val = fv.get("employer_value")
            reported_status = fv.get("status", "")
            match = fv.get("match")

            # Derive expected status using Apple-to-Apple rule
            if employer_val is None:
                expected = "unable_to_verify"
            elif match is None:
                expected = "unable_to_verify"
            elif match:
                expected = "verified"
            else:
                expected = "review_needed"

            if reported_status and reported_status != expected:
                errors.append(
                    f"{fv.get('field_name')}: reported {reported_status}, expected {expected}"
                )

        passed = len(errors) == 0
        score = 1.0 - (len(errors) / len(field_verifications)) if field_verifications else 1.0
        return EvalResult(
            eval_name=self.name,
            category=self.category,
            passed=passed,
            score=max(0.0, score),
            details="; ".join(errors) if errors else "All statuses correctly derived",
        )


class FormatValidationEval(BaseEval):
    """Check that collected data values conform to expected formats and enum sets."""

    name = "format_validation"
    description = "Dates and enums should be in valid formats"
    category = "completeness"

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Validate call_outcome and employment_status enum values."""
        collected = call_data.get("collected_data", {})
        issues: list[str] = []

        valid_outcomes = {"completed", "redirected", "no_record", "voicemail", "refused", "dead_end"}
        if "call_outcome" in collected and collected["call_outcome"] not in valid_outcomes:
            issues.append(f"Invalid call_outcome: {collected['call_outcome']}")

        valid_statuses = {"full-time", "part-time", "contract", "temporary", "intern"}
        if "employment_status" in collected and collected["employment_status"] not in valid_statuses:
            issues.append(f"Invalid employment_status: {collected['employment_status']}")

        passed = len(issues) == 0
        return EvalResult(
            eval_name=self.name,
            category=self.category,
            passed=passed,
            score=1.0 if passed else 0.0,
            details="; ".join(issues) if issues else "All formats valid",
        )

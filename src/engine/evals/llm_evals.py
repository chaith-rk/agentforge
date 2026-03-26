"""LLM-based eval checks — stubs pending LLM integration."""
from __future__ import annotations

from src.engine.evals.base import BaseEval, EvalResult


class DataExtractionAccuracyEval(BaseEval):
    """LLM eval: Does each verified_value match what the employer said in the transcript?"""

    name = "data_extraction_accuracy"
    description = "Verified field values must match what the employer stated in the transcript"
    category = "accuracy"

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Stub — always passes until LLM integration is implemented.

        TODO: Use an LLM to compare each collected field value against the raw
        transcript to confirm extraction accuracy.
        """
        return EvalResult(
            eval_name=self.name,
            category=self.category,
            passed=True,
            score=1.0,
            details="LLM eval stub — not yet implemented",
        )


class NoHallucinationEval(BaseEval):
    """LLM eval: Is every verified_value grounded in (supported by) the transcript?"""

    name = "no_hallucination"
    description = "All verified values must be grounded in the transcript"
    category = "accuracy"

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Stub — always passes until LLM integration is implemented.

        TODO: Use an LLM to verify that no field value was invented by the agent
        without a corresponding employer statement in the transcript.
        """
        return EvalResult(
            eval_name=self.name,
            category=self.category,
            passed=True,
            score=1.0,
            details="LLM eval stub — not yet implemented",
        )


class NoRequestorDisclosureEval(BaseEval):
    """LLM eval: Did the agent leak who is requesting the verification?

    Uses a heuristic check for known disclosure phrases before a full LLM eval
    is implemented.
    """

    name = "no_requestor_disclosure"
    description = "Agent must never reveal who requested the verification"
    category = "compliance"

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Fail if any known disclosure phrases appear in agent turns.

        TODO: Replace the phrase list with an LLM judge for more nuanced detection.
        """
        transcript = call_data.get("transcript", [])
        agent_content = " ".join(
            t.get("content", "")
            for t in transcript
            if t.get("role") in ("agent", "assistant")
        ).lower()
        suspicious = any(
            phrase in agent_content
            for phrase in ["background check", "applying for", "job application"]
        )
        return EvalResult(
            eval_name=self.name,
            category=self.category,
            passed=not suspicious,
            score=0.0 if suspicious else 1.0,
            details=(
                "Potential requestor disclosure detected"
                if suspicious
                else "No requestor disclosure detected"
            ),
        )


class ToneProfessionalismEval(BaseEval):
    """LLM eval: Was the agent professional and respectful throughout the call?"""

    name = "tone_professionalism"
    description = "Agent must maintain a professional, respectful tone throughout"
    category = "quality"

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Stub — always passes until LLM integration is implemented.

        TODO: Use an LLM judge to score tone and flag any unprofessional language
        or pressure tactics.
        """
        return EvalResult(
            eval_name=self.name,
            category=self.category,
            passed=True,
            score=1.0,
            details="LLM eval stub — not yet implemented",
        )

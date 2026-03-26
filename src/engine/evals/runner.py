"""Eval runner — orchestrates all quality checks for a completed verification call."""
from __future__ import annotations

import structlog

from src.engine.evals.base import EvalResult
from src.engine.evals.code_evals import (
    CompletenessEval,
    FormatValidationEval,
    RecordedLineDisclosureEval,
    StatusAccuracyEval,
)
from src.engine.evals.llm_evals import (
    DataExtractionAccuracyEval,
    NoHallucinationEval,
    NoRequestorDisclosureEval,
    ToneProfessionalismEval,
)

logger = structlog.get_logger(__name__)


class EvalRunner:
    """Runs all quality evals for a completed verification call.

    Instantiate once per process (or per call) and call ``run_all`` with a
    call_data dict assembled by the engine after a call finishes.
    """

    def __init__(self) -> None:
        """Register all eval instances in execution order."""
        self.evals = [
            RecordedLineDisclosureEval(),
            CompletenessEval(),
            StatusAccuracyEval(),
            FormatValidationEval(),
            DataExtractionAccuracyEval(),
            NoHallucinationEval(),
            NoRequestorDisclosureEval(),
            ToneProfessionalismEval(),
        ]

    async def run_all(self, call_data: dict) -> list[EvalResult]:
        """Run all registered evals against the provided call data.

        Each eval is executed independently; a failure in one does not prevent
        the others from running. Errors are caught and recorded as failed results
        so the caller always receives a complete list.

        Args:
            call_data: Structured call record — see BaseEval.evaluate for schema.

        Returns:
            List of EvalResult, one per registered eval, in registration order.
        """
        results: list[EvalResult] = []
        for ev in self.evals:
            try:
                result = await ev.evaluate(call_data)
                results.append(result)
                logger.info(
                    "eval_completed",
                    eval_name=ev.name,
                    passed=result.passed,
                    score=result.score,
                )
            except Exception as e:
                logger.warning("eval_failed", eval_name=ev.name, error=str(e))
                results.append(
                    EvalResult(
                        eval_name=ev.name,
                        category=ev.category,
                        passed=False,
                        score=0.0,
                        details=f"Eval error: {e}",
                    )
                )
        return results

    def summary(self, results: list[EvalResult]) -> dict:
        """Compute summary statistics from a list of eval results.

        Args:
            results: Output of ``run_all``.

        Returns:
            Dict with keys: pass_rate (float), total (int), passed (int),
            by_category (dict mapping category -> {passed, total}).
        """
        if not results:
            return {"pass_rate": 0.0, "total": 0, "passed": 0, "by_category": {}}

        passed = sum(1 for r in results if r.passed)
        by_cat: dict[str, dict] = {}
        for r in results:
            cat = by_cat.setdefault(r.category, {"passed": 0, "total": 0})
            cat["total"] += 1
            if r.passed:
                cat["passed"] += 1

        return {
            "pass_rate": passed / len(results),
            "total": len(results),
            "passed": passed,
            "by_category": by_cat,
        }

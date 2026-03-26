"""Base classes for the eval pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class EvalResult(BaseModel):
    """Result of a single eval check."""

    eval_name: str
    category: str  # "compliance", "accuracy", "completeness", "quality"
    passed: bool
    score: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    details: str = ""
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaseEval:
    """Base class for all eval checks.

    Subclasses must set class attributes ``name``, ``description``, and
    ``category``, then implement ``evaluate``.
    """

    name: str = ""
    description: str = ""
    category: str = ""

    async def evaluate(self, call_data: dict) -> EvalResult:
        """Run the eval and return a result.

        Args:
            call_data: Dictionary with the following keys:
                - session_id: str
                - transcript: list of {role, content}
                - collected_data: dict of field_name -> value
                - field_verifications: list of {field_name, candidate_value,
                  employer_value, status, match}
                - outcome: str
                - agent_config_id: str

        Returns:
            EvalResult describing whether the check passed and a numeric score.
        """
        raise NotImplementedError

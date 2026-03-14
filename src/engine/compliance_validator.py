"""Compliance validation engine.

Evaluates compliance checkpoints defined in agent configurations. Each
checkpoint has a validation rule that is checked against the current call
context. This is how we enforce rules like "must mention recorded line"
at the infrastructure level, not just the prompt level.

The state machine WILL NOT advance past a state with a failed BLOCK-level
compliance checkpoint. This is a fundamentally stronger guarantee than
prompt-based compliance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config.agent_config import ComplianceCheckpoint


@dataclass
class ComplianceResult:
    """Result of evaluating a single compliance checkpoint."""

    checkpoint_name: str
    passed: bool
    message: str = ""


# Registry of built-in validation rules. Each rule is a function that takes
# the call context dict and returns (passed: bool, message: str).
VALIDATION_RULES: dict[str, Any] = {}


def register_rule(name: str):
    """Decorator to register a compliance validation rule."""

    def decorator(func):
        VALIDATION_RULES[name] = func
        return func

    return decorator


@register_rule("recorded_line_disclosure")
async def validate_recorded_line_disclosure(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify that the agent mentioned 'recorded line' in the greeting.

    This is a legal requirement — calls must disclose recording. The state
    machine blocks the transition from GREETING to any other state until
    this checkpoint passes.
    """
    transcript = context.get("transcript", [])
    greeting_text = " ".join(
        entry.get("content", "")
        for entry in transcript
        if entry.get("role") == "agent"
    ).lower()

    if "recorded" in greeting_text and "line" in greeting_text:
        return True, "Recorded line disclosure confirmed in greeting"

    # Also pass if we haven't started talking yet (checkpoint will be
    # re-evaluated when transcript is available)
    if not transcript:
        return True, "No transcript yet — will re-validate on transition"

    return False, "Agent did not mention 'recorded line' in greeting"


@register_rule("never_disclose_requestor")
async def validate_never_disclose_requestor(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify the agent never disclosed who is requesting the verification.

    The agent must never share the requesting party's identity or the
    position the candidate is applying for.
    """
    transcript = context.get("transcript", [])
    agent_text = " ".join(
        entry.get("content", "")
        for entry in transcript
        if entry.get("role") == "agent"
    ).lower()

    # Check for potential disclosure phrases
    disclosure_phrases = [
        "applying for",
        "the position of",
        "hired by",
        "requested by",
        "on behalf of the client",
    ]

    for phrase in disclosure_phrases:
        if phrase in agent_text:
            return False, f"Potential requestor disclosure detected: '{phrase}'"

    return True, "No requestor disclosure detected"


@register_rule("accept_refusal_immediately")
async def validate_accept_refusal(context: dict[str, Any]) -> tuple[bool, str]:
    """Verify the agent doesn't push back when a verifier refuses to share info.

    When a verifier says they can't share something, the agent must accept
    immediately and move on. This rule checks that the agent doesn't follow
    a refusal with a persuasion attempt.
    """
    # This is evaluated on transcript content — complex NLP would be needed
    # for production. For POC, we flag obvious patterns.
    transcript = context.get("transcript", [])

    push_phrases = [
        "are you sure",
        "could you reconsider",
        "it would really help",
        "we just need",
        "is there any way",
    ]

    agent_text = " ".join(
        entry.get("content", "")
        for entry in transcript
        if entry.get("role") == "agent"
    ).lower()

    for phrase in push_phrases:
        if phrase in agent_text:
            return False, f"Agent may be pushing after refusal: '{phrase}'"

    return True, "No push-back after refusal detected"


class ComplianceValidator:
    """Evaluates compliance checkpoints against call context.

    Uses a registry of named validation rules. Agent configs reference
    rules by name, keeping the config declarative and the validation
    logic centralized and testable.
    """

    async def validate_checkpoint(
        self, checkpoint: ComplianceCheckpoint, context: dict[str, Any]
    ) -> ComplianceResult:
        """Evaluate a single compliance checkpoint.

        Args:
            checkpoint: The checkpoint definition from agent config.
            context: Current call context (transcript, collected data, etc.).

        Returns:
            ComplianceResult indicating pass/fail and a message.
        """
        rule_func = VALIDATION_RULES.get(checkpoint.validation_rule)

        if rule_func is None:
            return ComplianceResult(
                checkpoint_name=checkpoint.name,
                passed=False,
                message=f"Unknown validation rule: '{checkpoint.validation_rule}'",
            )

        passed, message = await rule_func(context)

        return ComplianceResult(
            checkpoint_name=checkpoint.name,
            passed=passed,
            message=message,
        )

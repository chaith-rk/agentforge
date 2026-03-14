"""Generic async state machine engine.

This is the core of the platform. The state machine is entirely driven by
the agent's YAML configuration — no agent-specific logic lives here. This
means adding a new agent type (education verification, reference check)
requires zero changes to this engine.

The state machine enforces:
1. Only valid transitions (defined in config) are allowed
2. Compliance checkpoints must pass before state transitions
3. Every transition emits an event for the audit trail
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.config.agent_config import AgentConfig
from src.engine.compliance_validator import ComplianceResult, ComplianceValidator
from src.models.events import (
    BaseEvent,
    EventType,
    StateTransitionEvent,
)


@dataclass
class StateMachineResult:
    """Result of processing an event through the state machine."""

    success: bool
    new_state: str | None = None
    events_emitted: list[BaseEvent] = field(default_factory=list)
    compliance_violations: list[ComplianceResult] = field(default_factory=list)
    data_collected: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class StateMachine:
    """Generic, config-driven conversation state machine.

    The state machine processes events and manages transitions between
    conversation states. It delegates compliance validation to the
    ComplianceValidator and emits events for every action.

    Usage:
        config = load_agent_config("agents/employment_verification_call.yaml")
        sm = StateMachine(config=config, session_id="call-123")
        result = await sm.process_event("verifier_identified", {"name": "Jane"})
    """

    def __init__(self, config: AgentConfig, session_id: str) -> None:
        self._config = config
        self._session_id = session_id
        self._current_state = config.initial_state
        self._compliance_validator = ComplianceValidator()
        self._events: list[BaseEvent] = []
        self._context: dict[str, Any] = {}

    @property
    def current_state(self) -> str:
        """Current state name."""
        return self._current_state

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def is_complete(self) -> bool:
        """Whether the conversation has reached a terminal state."""
        state = self._config.states.get(self._current_state)
        return state.is_terminal if state else False

    @property
    def context(self) -> dict[str, Any]:
        """Mutable context dict — holds data accumulated during the call."""
        return self._context

    def get_available_transitions(self) -> list[str]:
        """Get trigger names for valid transitions from the current state."""
        state = self._config.states.get(self._current_state)
        if not state:
            return []
        return [t.trigger for t in state.transitions]

    async def process_event(
        self, event_type: str, payload: dict[str, Any] | None = None
    ) -> StateMachineResult:
        """Process an incoming event and potentially transition states.

        Args:
            event_type: The event trigger (e.g., "verifier_identified").
            payload: Event-specific data.

        Returns:
            StateMachineResult with outcome details and emitted events.
        """
        payload = payload or {}
        state = self._config.states.get(self._current_state)

        if not state:
            return StateMachineResult(
                success=False,
                error=f"Current state '{self._current_state}' not found in config",
            )

        if self.is_complete:
            return StateMachineResult(
                success=False,
                error=f"Conversation already complete in terminal state '{self._current_state}'",
            )

        # Update context with payload data
        self._context.update(payload)

        # Find matching transition
        matching_transition = None
        for transition in state.transitions:
            if transition.trigger == event_type:
                matching_transition = transition
                break

        if not matching_transition:
            return StateMachineResult(
                success=False,
                error=(
                    f"No transition for trigger '{event_type}' from state "
                    f"'{self._current_state}'. Valid triggers: "
                    f"{self.get_available_transitions()}"
                ),
            )

        # Run compliance checkpoints before allowing transition
        return await self._transition_to(
            matching_transition.target_state,
            trigger=event_type,
            payload=payload,
        )

    async def _transition_to(
        self,
        target_state: str,
        trigger: str = "",
        payload: dict[str, Any] | None = None,
    ) -> StateMachineResult:
        """Execute a state transition after compliance validation.

        This is where compliance checkpoints are enforced. If any BLOCK-level
        checkpoint fails, the transition is denied.
        """
        current_state_config = self._config.states.get(self._current_state)
        if not current_state_config:
            return StateMachineResult(
                success=False, error=f"State '{self._current_state}' not found"
            )

        # Validate compliance checkpoints for the current state
        violations: list[ComplianceResult] = []
        emitted_events: list[BaseEvent] = []

        for checkpoint in current_state_config.compliance_checkpoints:
            result = await self._compliance_validator.validate_checkpoint(
                checkpoint, self._context
            )
            event_type = (
                EventType.COMPLIANCE_CHECK_PASSED
                if result.passed
                else EventType.COMPLIANCE_CHECK_FAILED
            )
            emitted_events.append(
                BaseEvent(
                    session_id=self._session_id,
                    event_type=event_type,
                    payload={
                        "checkpoint_name": checkpoint.name,
                        "passed": result.passed,
                        "message": result.message,
                    },
                    actor="compliance_engine",
                )
            )

            if not result.passed:
                violations.append(result)
                if checkpoint.failure_action.value == "block":
                    return StateMachineResult(
                        success=False,
                        new_state=None,
                        events_emitted=emitted_events,
                        compliance_violations=violations,
                        error=f"Compliance checkpoint blocked: {checkpoint.error_message}",
                    )

        # Also check global compliance checkpoints
        for checkpoint in self._config.compliance_checkpoints:
            result = await self._compliance_validator.validate_checkpoint(
                checkpoint, self._context
            )
            if not result.passed:
                violations.append(result)

        # Execute transition
        from_state = self._current_state
        self._current_state = target_state

        transition_event = StateTransitionEvent(
            session_id=self._session_id,
            payload={
                "from_state": from_state,
                "to_state": target_state,
                "trigger": trigger,
                **(payload or {}),
            },
            actor="state_machine",
        )
        emitted_events.append(transition_event)
        self._events.extend(emitted_events)

        return StateMachineResult(
            success=True,
            new_state=target_state,
            events_emitted=emitted_events,
            compliance_violations=violations,
        )

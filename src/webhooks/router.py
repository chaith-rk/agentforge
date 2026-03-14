"""Event router — dispatches Vapi events to engine components.

This module bridges the webhook layer and the engine. It translates Vapi
event payloads into engine operations (state transitions, data recording,
compliance checks).
"""

from __future__ import annotations

from typing import Any

import structlog

from src.engine.audit_logger import AuditLogger
from src.engine.data_recorder import DataRecorder
from src.engine.state_machine import StateMachine, StateMachineResult

logger = structlog.get_logger(__name__)


class EventRouter:
    """Routes incoming call events to the appropriate engine components.

    Each active call has its own StateMachine, DataRecorder, and AuditLogger.
    The EventRouter coordinates between them.
    """

    def __init__(
        self,
        state_machine: StateMachine,
        data_recorder: DataRecorder,
        audit_logger: AuditLogger,
    ) -> None:
        self._state_machine = state_machine
        self._data_recorder = data_recorder
        self._audit_logger = audit_logger

    async def route_event(
        self, event_type: str, payload: dict[str, Any]
    ) -> StateMachineResult:
        """Route an event through the engine pipeline.

        1. Process through state machine (may trigger transition)
        2. Record any data points
        3. Log everything to audit trail

        Args:
            event_type: The event trigger.
            payload: Event-specific data.

        Returns:
            StateMachineResult with transition outcome.
        """
        # Process through state machine
        result = await self._state_machine.process_event(event_type, payload)

        # Log all emitted events
        await self._audit_logger.log_events(result.events_emitted)

        if not result.success:
            logger.warning(
                "event_routing_failed",
                event_type=event_type,
                error=result.error,
                session_id=self._state_machine.session_id,
            )

        return result

    async def record_data(
        self, field_name: str, value: Any, source: str = "employer", confidence: str = "high"
    ) -> None:
        """Record a data point and log it."""
        event = self._data_recorder.record_data_point(field_name, value, source, confidence)
        await self._audit_logger.log_event(event)

    async def record_discrepancy(
        self, field_name: str, candidate_value: Any, employer_value: Any, note: str = ""
    ) -> None:
        """Record a discrepancy and log it."""
        event = self._data_recorder.record_discrepancy(
            field_name, candidate_value, employer_value, note
        )
        await self._audit_logger.log_event(event)

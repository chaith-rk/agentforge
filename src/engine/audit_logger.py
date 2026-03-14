"""Audit logger — immutable event log for compliance.

Every action in the system flows through the audit logger. Events are
appended to the event store and can never be modified or deleted. This
provides a tamper-evident audit trail for compliance reviews.
"""

from __future__ import annotations

import structlog
from typing import Any

from src.models.events import BaseEvent, EventType


logger = structlog.get_logger(__name__)


class AuditLogger:
    """Immutable audit logger for all system events.

    In production, this writes to the event store database. For the POC,
    it also logs to structured stdout for debugging.
    """

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._events: list[BaseEvent] = []

    @property
    def events(self) -> list[BaseEvent]:
        """All logged events for this session."""
        return list(self._events)

    async def log_event(self, event: BaseEvent) -> None:
        """Append an event to the audit trail.

        Events are immutable once logged. This is the single entry point
        for all event persistence.
        """
        self._events.append(event)

        # Structured log output (PII redaction happens in the logging middleware)
        logger.info(
            "audit_event",
            session_id=event.session_id,
            event_type=event.event_type.value,
            event_id=event.event_id,
            actor=event.actor,
            timestamp=event.timestamp.isoformat(),
        )

    async def log_events(self, events: list[BaseEvent]) -> None:
        """Append multiple events to the audit trail."""
        for event in events:
            await self.log_event(event)

    async def log_call_initiated(
        self, agent_config_id: str, candidate_name: str, company_name: str
    ) -> BaseEvent:
        """Log a call initiation event."""
        event = BaseEvent(
            session_id=self._session_id,
            event_type=EventType.CALL_INITIATED,
            payload={
                "agent_config_id": agent_config_id,
                "candidate_name": candidate_name,
                "company_name": company_name,
            },
            actor="operator",
        )
        await self.log_event(event)
        return event

    async def log_call_completed(
        self, outcome: str, duration_seconds: float = 0.0
    ) -> BaseEvent:
        """Log a call completion event."""
        event = BaseEvent(
            session_id=self._session_id,
            event_type=EventType.CALL_COMPLETED,
            payload={
                "outcome": outcome,
                "duration_seconds": duration_seconds,
            },
            actor="system",
        )
        await self.log_event(event)
        return event

    async def log_error(self, error_message: str, details: dict[str, Any] | None = None) -> BaseEvent:
        """Log an error event."""
        event = BaseEvent(
            session_id=self._session_id,
            event_type=EventType.ERROR_OCCURRED,
            payload={
                "error_message": error_message,
                "details": details or {},
            },
            actor="system",
        )
        await self.log_event(event)
        return event

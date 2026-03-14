"""Generic data recorder for collecting verification fields.

Records data points as events, validates against the agent's data schema,
and tracks discrepancies between candidate claims and employer responses.
All operations are event-sourced.
"""

from __future__ import annotations

from typing import Any

from src.config.agent_config import DataPointSchema
from src.models.events import (
    BaseEvent,
    DataPointRecordedEvent,
    DiscrepancyDetectedEvent,
    EventType,
)


class DataRecorder:
    """Records and validates verification data collected during calls.

    Each data point is stored as an event. Discrepancies are automatically
    detected when the recorded value differs from the candidate's claim.
    """

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._data: dict[str, Any] = {}
        self._events: list[BaseEvent] = []
        self._discrepancies: list[dict[str, Any]] = []

    @property
    def collected_data(self) -> dict[str, Any]:
        """All data points collected so far."""
        return dict(self._data)

    @property
    def discrepancies(self) -> list[dict[str, Any]]:
        """All discrepancies detected so far."""
        return list(self._discrepancies)

    @property
    def events(self) -> list[BaseEvent]:
        """All events emitted by this recorder."""
        return list(self._events)

    def record_data_point(
        self,
        field_name: str,
        value: Any,
        source: str = "employer",
        confidence: str = "high",
    ) -> DataPointRecordedEvent:
        """Record a single verified data point.

        Args:
            field_name: The field being recorded (e.g., "job_title_confirmed").
            value: The value provided by the employer.
            source: Who provided this data (employer, verifier, system).
            confidence: Confidence level (high, medium, low).

        Returns:
            The event that was emitted.
        """
        self._data[field_name] = value

        event = DataPointRecordedEvent(
            session_id=self._session_id,
            payload={
                "field_name": field_name,
                "value": value,
                "source": source,
                "confidence": confidence,
            },
            actor=source,
        )
        self._events.append(event)
        return event

    def record_discrepancy(
        self,
        field_name: str,
        candidate_value: Any,
        employer_value: Any,
        note: str = "",
    ) -> DiscrepancyDetectedEvent:
        """Record a discrepancy between candidate claim and employer response.

        Both values are recorded without judgment. The "apple-to-apple"
        matching logic happens downstream — the agent just records facts.

        Args:
            field_name: The field with a discrepancy.
            candidate_value: What the candidate claimed.
            employer_value: What the employer confirmed.
            note: Additional context (e.g., "staffing agency", "subsidiary").

        Returns:
            The event that was emitted.
        """
        discrepancy = {
            "field_name": field_name,
            "candidate_value": candidate_value,
            "employer_value": employer_value,
            "note": note,
        }
        self._discrepancies.append(discrepancy)

        event = DiscrepancyDetectedEvent(
            session_id=self._session_id,
            payload=discrepancy,
            actor="system",
        )
        self._events.append(event)
        return event

    def validate_against_schema(
        self, data_schema: list[DataPointSchema]
    ) -> list[str]:
        """Validate collected data against the agent's data schema.

        Returns a list of validation errors (empty if all valid).
        Checks required fields are present and enum values are valid.
        """
        errors: list[str] = []

        for field_def in data_schema:
            if field_def.required and field_def.field_name not in self._data:
                errors.append(f"Required field '{field_def.field_name}' not collected")

            if field_def.field_name in self._data and field_def.enum_values:
                value = self._data[field_def.field_name]
                if value not in field_def.enum_values:
                    errors.append(
                        f"Field '{field_def.field_name}' value '{value}' not in "
                        f"allowed values: {field_def.enum_values}"
                    )

        return errors

    def record_field_refused(self, field_name: str) -> BaseEvent:
        """Record that the employer refused to share a specific field."""
        event = BaseEvent(
            session_id=self._session_id,
            event_type=EventType.DATA_POINT_RECORDED,
            payload={
                "field_name": field_name,
                "value": None,
                "source": "employer",
                "refused": True,
            },
            actor="employer",
        )
        self._data[field_name] = None
        self._events.append(event)
        return event

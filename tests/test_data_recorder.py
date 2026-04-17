"""Tests for DataRecorder — specifically confidence tracking per field,
which powers the confidence column in the post-call report.
"""
from __future__ import annotations

from src.engine.data_recorder import DataRecorder


def test_confidence_defaults_to_high() -> None:
    recorder = DataRecorder(session_id="sess-1")
    recorder.record_data_point(field_name="title", value="Engineer")
    assert recorder.confidence_map == {"title": "high"}


def test_confidence_per_field_tracked_separately() -> None:
    recorder = DataRecorder(session_id="sess-1")
    recorder.record_data_point(field_name="title", value="Engineer", confidence="high")
    recorder.record_data_point(field_name="salary", value="85000", confidence="low")
    recorder.record_data_point(field_name="start_date", value="2022-03", confidence="medium")

    assert recorder.confidence_map == {
        "title": "high",
        "salary": "low",
        "start_date": "medium",
    }


def test_confidence_overwritten_on_re_record() -> None:
    recorder = DataRecorder(session_id="sess-1")
    recorder.record_data_point(field_name="title", value="Engineer", confidence="low")
    recorder.record_data_point(field_name="title", value="Senior Engineer", confidence="high")
    assert recorder.confidence_map == {"title": "high"}


def test_confidence_map_is_a_copy() -> None:
    """The property returns a copy so callers can't mutate internal state."""
    recorder = DataRecorder(session_id="sess-1")
    recorder.record_data_point(field_name="title", value="x", confidence="high")
    snapshot = recorder.confidence_map
    snapshot["title"] = "tampered"
    assert recorder.confidence_map == {"title": "high"}

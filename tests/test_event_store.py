"""Tests for the async SQLite event store.

Covers:
- Database initialization and table creation
- Appending single and batch events
- Session CRUD (create, get, list, update)
- Event querying with type filters
- Snapshots
- Stats aggregation
- Error handling for uninitialized store
"""
from __future__ import annotations

import pytest

from src.database.event_store import EventStore
from src.models.events import BaseEvent, EventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def store(tmp_path) -> EventStore:
    """Create a fresh EventStore backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_calls.db")
    es = EventStore(db_path=db_path)
    await es.initialize()
    yield es
    await es.close()


def _event(
    session_id: str = "sess_1",
    event_type: EventType = EventType.CALL_INITIATED,
    payload: dict | None = None,
    actor: str = "system",
) -> BaseEvent:
    return BaseEvent(
        session_id=session_id,
        event_type=event_type,
        payload=payload or {},
        actor=actor,
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestEventStoreInit:

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, store: EventStore) -> None:
        # If we got here without error, tables were created
        events = await store.get_events_for_session("nonexistent")
        assert events == []

    @pytest.mark.asyncio
    async def test_double_initialize_is_safe(self, store: EventStore) -> None:
        await store.initialize()  # second init should not raise
        events = await store.get_events_for_session("x")
        assert events == []

    @pytest.mark.asyncio
    async def test_operations_fail_before_init(self, tmp_path) -> None:
        es = EventStore(db_path=str(tmp_path / "uninit.db"))
        with pytest.raises(RuntimeError, match="not initialized"):
            await es.append_event(_event())
        with pytest.raises(RuntimeError, match="not initialized"):
            await es.get_events_for_session("x")
        with pytest.raises(RuntimeError, match="not initialized"):
            await es.create_session("x", "agent", "GREETING", {})


# ---------------------------------------------------------------------------
# Append & query events
# ---------------------------------------------------------------------------

class TestAppendEvents:

    @pytest.mark.asyncio
    async def test_append_single_event(self, store: EventStore) -> None:
        evt = _event(session_id="sess_1", event_type=EventType.CALL_INITIATED)
        await store.append_event(evt)

        events = await store.get_events_for_session("sess_1")
        assert len(events) == 1
        assert events[0]["event_type"] == "call_initiated"
        assert events[0]["session_id"] == "sess_1"

    @pytest.mark.asyncio
    async def test_append_multiple_events(self, store: EventStore) -> None:
        evts = [
            _event(session_id="sess_2", event_type=EventType.CALL_INITIATED),
            _event(session_id="sess_2", event_type=EventType.STATE_TRANSITION, payload={"from_state": "GREETING", "to_state": "VERIFY"}),
            _event(session_id="sess_2", event_type=EventType.CALL_COMPLETED, payload={"outcome": "completed"}),
        ]
        await store.append_events(evts)

        events = await store.get_events_for_session("sess_2")
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_filter_events_by_type(self, store: EventStore) -> None:
        await store.append_events([
            _event(session_id="sess_3", event_type=EventType.CALL_INITIATED),
            _event(session_id="sess_3", event_type=EventType.DATA_POINT_RECORDED, payload={"field_name": "position", "value": "Engineer"}),
            _event(session_id="sess_3", event_type=EventType.DATA_POINT_RECORDED, payload={"field_name": "start_date", "value": "2020-01"}),
            _event(session_id="sess_3", event_type=EventType.CALL_COMPLETED),
        ])

        data_events = await store.get_events_for_session("sess_3", event_type=EventType.DATA_POINT_RECORDED)
        assert len(data_events) == 2
        assert all(e["event_type"] == "data_point_recorded" for e in data_events)

    @pytest.mark.asyncio
    async def test_events_isolated_by_session(self, store: EventStore) -> None:
        await store.append_event(_event(session_id="a"))
        await store.append_event(_event(session_id="b"))

        assert len(await store.get_events_for_session("a")) == 1
        assert len(await store.get_events_for_session("b")) == 1
        assert len(await store.get_events_for_session("c")) == 0


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

class TestSessions:

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, store: EventStore) -> None:
        await store.create_session(
            session_id="sess_10",
            agent_config_id="employment_verification_v1",
            initial_state="GREETING",
            candidate_data={"name": "John"},
        )
        session = await store.get_session("sess_10")
        assert session is not None
        assert session["session_id"] == "sess_10"
        assert session["agent_config_id"] == "employment_verification_v1"
        assert session["current_state"] == "GREETING"
        assert session["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_none(self, store: EventStore) -> None:
        session = await store.get_session("nonexistent")
        assert session is None

    @pytest.mark.asyncio
    async def test_update_session_state(self, store: EventStore) -> None:
        await store.create_session("sess_11", "agent_v1", "GREETING", {})
        await store.update_session_state("sess_11", "VERIFY_TITLE", "in_progress")

        session = await store.get_session("sess_11")
        assert session["current_state"] == "VERIFY_TITLE"

    @pytest.mark.asyncio
    async def test_update_session_to_completed(self, store: EventStore) -> None:
        await store.create_session("sess_12", "agent_v1", "GREETING", {})
        await store.update_session_state("sess_12", "END", "completed")

        session = await store.get_session("sess_12")
        assert session["status"] == "completed"
        assert session["current_state"] == "END"

    @pytest.mark.asyncio
    async def test_list_sessions_pagination(self, store: EventStore) -> None:
        for i in range(5):
            await store.create_session(f"sess_{i}", "agent_v1", "GREETING", {})

        all_sessions = await store.list_sessions(limit=50)
        assert len(all_sessions) == 5

        page = await store.list_sessions(limit=2, offset=0)
        assert len(page) == 2

        page2 = await store.list_sessions(limit=2, offset=2)
        assert len(page2) == 2

        page3 = await store.list_sessions(limit=2, offset=4)
        assert len(page3) == 1


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

class TestSnapshots:

    @pytest.mark.asyncio
    async def test_create_snapshot(self, store: EventStore) -> None:
        await store.create_session("sess_snap", "agent_v1", "GREETING", {})
        await store.create_snapshot("sess_snap", {"state": "VERIFY", "collected": {"name": "Jane"}})
        # No error means success — snapshots are write-only in the current API


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:

    @pytest.mark.asyncio
    async def test_stats_empty_database(self, store: EventStore) -> None:
        stats = await store.get_stats()
        assert stats["total"] == 0
        assert stats["outcomes"] == {}
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_with_sessions(self, store: EventStore) -> None:
        await store.create_session("s1", "agent_v1", "GREETING", {})
        await store.create_session("s2", "agent_v1", "GREETING", {})
        await store.update_session_state("s1", "END", "completed")

        stats = await store.get_stats()
        assert stats["total"] == 2
        assert stats["outcomes"]["completed"] == 1
        assert stats["outcomes"]["in_progress"] == 1
        assert stats["success_rate"] == 0.5

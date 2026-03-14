"""Async event store backed by SQLite.

The event store is the persistence layer for the event-sourced architecture.
Events are append-only — nothing is ever updated or deleted. The current
state of any call session is reconstructed by replaying events.

Tables:
- events: Immutable event log (the source of truth)
- call_sessions: Materialized view of current session state (for queries)
- data_snapshots: Point-in-time snapshots (optimization to avoid full replay)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from src.models.events import BaseEvent, EventType


class EventStore:
    """Async SQLite-backed event store.

    All writes are append-only. The event log is the single source of truth.
    Materialized views (sessions, snapshots) are derived from events and
    can be rebuilt at any time.
    """

    def __init__(self, db_path: str = "data/calls.db") -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create database and tables if they don't exist."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)

        # Enable WAL mode for better concurrent read performance
        await self._db.execute("PRAGMA journal_mode=WAL")

        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                actor TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_events_session_id
                ON events(session_id);
            CREATE INDEX IF NOT EXISTS idx_events_event_type
                ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp);

            CREATE TABLE IF NOT EXISTS call_sessions (
                session_id TEXT PRIMARY KEY,
                agent_config_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                current_state TEXT NOT NULL,
                candidate_json TEXT NOT NULL DEFAULT '{}',
                collected_data_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS data_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES call_sessions(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_session_id
                ON data_snapshots(session_id);
        """)
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def append_event(self, event: BaseEvent) -> None:
        """Append an immutable event to the store.

        This is the only write operation. Events are never modified or deleted.
        """
        if not self._db:
            raise RuntimeError("EventStore not initialized. Call initialize() first.")

        await self._db.execute(
            """
            INSERT INTO events (event_id, session_id, event_type, timestamp, payload_json, actor)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.session_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                json.dumps(event.payload),
                event.actor,
            ),
        )
        await self._db.commit()

    async def append_events(self, events: list[BaseEvent]) -> None:
        """Append multiple events in a single transaction."""
        if not self._db:
            raise RuntimeError("EventStore not initialized. Call initialize() first.")

        await self._db.executemany(
            """
            INSERT INTO events (event_id, session_id, event_type, timestamp, payload_json, actor)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    e.event_id,
                    e.session_id,
                    e.event_type.value,
                    e.timestamp.isoformat(),
                    json.dumps(e.payload),
                    e.actor,
                )
                for e in events
            ],
        )
        await self._db.commit()

    async def get_events_for_session(
        self, session_id: str, event_type: EventType | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve all events for a session, ordered by timestamp.

        Args:
            session_id: The call session ID.
            event_type: Optional filter by event type.

        Returns:
            List of event dicts.
        """
        if not self._db:
            raise RuntimeError("EventStore not initialized.")

        query = "SELECT * FROM events WHERE session_id = ?"
        params: list[Any] = [session_id]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        query += " ORDER BY timestamp ASC"

        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def create_session(
        self,
        session_id: str,
        agent_config_id: str,
        initial_state: str,
        candidate_data: dict[str, Any],
    ) -> None:
        """Create a new call session record."""
        if not self._db:
            raise RuntimeError("EventStore not initialized.")

        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            """
            INSERT INTO call_sessions
                (session_id, agent_config_id, status, current_state, candidate_json, created_at, updated_at)
            VALUES (?, ?, 'in_progress', ?, ?, ?, ?)
            """,
            (session_id, agent_config_id, initial_state, json.dumps(candidate_data), now, now),
        )
        await self._db.commit()

    async def update_session_state(self, session_id: str, new_state: str, status: str = "in_progress") -> None:
        """Update the materialized session state."""
        if not self._db:
            raise RuntimeError("EventStore not initialized.")

        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE call_sessions SET current_state = ?, status = ?, updated_at = ? WHERE session_id = ?",
            (new_state, status, now, session_id),
        )
        await self._db.commit()

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a session record."""
        if not self._db:
            raise RuntimeError("EventStore not initialized.")

        async with self._db.execute(
            "SELECT * FROM call_sessions WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List sessions with pagination."""
        if not self._db:
            raise RuntimeError("EventStore not initialized.")

        async with self._db.execute(
            "SELECT * FROM call_sessions ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def create_snapshot(self, session_id: str, snapshot_data: dict[str, Any]) -> None:
        """Create a point-in-time snapshot of session state."""
        if not self._db:
            raise RuntimeError("EventStore not initialized.")

        await self._db.execute(
            "INSERT INTO data_snapshots (session_id, snapshot_json) VALUES (?, ?)",
            (session_id, json.dumps(snapshot_data)),
        )
        await self._db.commit()

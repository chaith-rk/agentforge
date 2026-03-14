"""WebSocket endpoint for real-time dashboard updates.

Streams call events to connected dashboard clients in real-time.
When a call is active, the dashboard sees transcript updates, state
transitions, and data point collections as they happen.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["dashboard"])


class ConnectionManager:
    """Manages WebSocket connections for real-time updates.

    Tracks active connections per session so that events for a specific
    call are broadcast only to clients watching that call.
    """

    def __init__(self) -> None:
        # session_id → list of connected WebSocket clients
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept a new WebSocket connection for a session."""
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = []
        self._connections[session_id].append(websocket)
        logger.info("websocket_connected", session_id=session_id)

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a disconnected client."""
        if session_id in self._connections:
            self._connections[session_id] = [
                ws for ws in self._connections[session_id] if ws != websocket
            ]
            if not self._connections[session_id]:
                del self._connections[session_id]
        logger.info("websocket_disconnected", session_id=session_id)

    async def broadcast_to_session(self, session_id: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all clients watching a specific session."""
        connections = self._connections.get(session_id, [])
        disconnected: list[WebSocket] = []

        for websocket in connections:
            try:
                await websocket.send_json(data)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, session_id)

    async def broadcast_event(self, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcast a typed event to session watchers."""
        await self.broadcast_to_session(
            session_id,
            {"type": event_type, "data": payload},
        )

    @property
    def active_sessions(self) -> list[str]:
        """List session IDs with active WebSocket connections."""
        return list(self._connections.keys())


# Singleton connection manager
connection_manager = ConnectionManager()


@router.websocket("/api/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for streaming call events.

    Clients connect to watch a specific call session in real-time.
    Events include transcript updates, state transitions, data points,
    and compliance check results.
    """
    await connection_manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive; client can also send messages
            data = await websocket.receive_text()
            # Handle client messages (e.g., ping/pong)
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, session_id)

"""Dashboard statistics API endpoint.

Provides aggregate call statistics for the AgentForge platform dashboard.
Stats are computed directly from the SQLite event store at query time.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/stats", tags=["stats"])


# --- Response Model ---


class StatsResponse(BaseModel):
    """Aggregate statistics for the platform dashboard."""

    total_calls: int
    active_calls: int
    completed_calls: int
    success_rate: float
    avg_duration_seconds: float
    calls_today: int
    calls_this_week: int
    outcomes: dict[str, int]


# --- Endpoint ---


@router.get("", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Return aggregate call statistics for the dashboard.

    Combines live in-memory counts (active calls) with persisted
    database counts (completed/historical sessions) so the numbers
    are always up-to-date without waiting for a call to finish.
    """
    from src.main import call_manager, event_store

    db_stats = await event_store.get_stats()
    active_calls = len(call_manager._active_calls)

    return StatsResponse(
        total_calls=db_stats.get("total", 0) + active_calls,
        active_calls=active_calls,
        completed_calls=db_stats.get("total", 0),
        success_rate=db_stats.get("success_rate", 0.0),
        avg_duration_seconds=db_stats.get("avg_duration", 0.0),
        calls_today=db_stats.get("calls_today", 0),
        calls_this_week=db_stats.get("calls_this_week", 0),
        outcomes=db_stats.get("outcomes", {}),
    )

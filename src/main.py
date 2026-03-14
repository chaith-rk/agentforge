"""FastAPI application entry point.

Initializes the application with all middleware, routers, the event store,
and the call manager. Uses lifespan for clean startup/shutdown.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.calls import router as calls_router
from src.api.dashboard import router as dashboard_router
from src.config.settings import settings
from src.database.event_store import EventStore
from src.engine.call_manager import CallManager
from src.middleware.security import APIKeyMiddleware
from src.webhooks.vapi_handler import router as vapi_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)

# Global instances — shared across the application
event_store = EventStore()
call_manager = CallManager(event_store=event_store)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — initialize and cleanup resources."""
    # Startup
    logger.info("application_starting", environment=settings.environment.value)
    await event_store.initialize()
    logger.info("event_store_initialized")

    # Pre-load agent configs
    try:
        call_manager.load_agent_config("agents/employment_verification_call.yaml")
        logger.info("agent_config_loaded", agent_id="employment_verification_v1")
    except Exception as e:
        logger.warning("agent_config_load_failed", error=str(e))

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await event_store.close()


app = FastAPI(
    title="Vetty Voice AI Platform",
    description="AI voice agent platform for automated employment verification calls",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)

# --- Routers ---
app.include_router(vapi_router)
app.include_router(calls_router)
app.include_router(dashboard_router)


# --- Health Check ---
@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "active_calls": str(len(call_manager._active_calls)),
    }

# ADR-001: Async FastAPI for Backend

**Status:** Accepted
**Date:** 2026-03-14
**Decision Maker:** Chaitanya Rajkumar

## Context

The platform backend needs to handle multiple concurrent verification calls, each generating real-time webhook events from Vapi, WebSocket connections from dashboard clients, and database operations. We evaluated three Python web frameworks:

- **Flask:** Synchronous by default. Requires additional libraries (gevent/eventlet) for concurrency. No native WebSocket support.
- **Django:** Full-featured but heavyweight. Async support is partial. REST framework adds complexity.
- **FastAPI:** Async-native, built on Starlette/Pydantic, native WebSocket support, automatic OpenAPI docs.

## Decision

Use **async FastAPI** as the backend framework.

## Consequences

### Positive
- Native `async/await` handles concurrent calls without threads or worker processes
- Built-in WebSocket support for real-time dashboard (no additional dependencies)
- Pydantic integration aligns with our config validation approach
- Automatic OpenAPI documentation makes the API self-documenting
- High performance: handles 50+ concurrent calls on a single instance
- Strong typing throughout the request/response chain

### Negative
- Team must understand async Python patterns
- Some libraries may not have async equivalents (mitigated: aiosqlite, httpx are mature)
- Debugging async code can be more complex

### Neutral
- FastAPI's ecosystem is smaller than Django's, but sufficient for our needs
- We chose FastAPI over Django REST Framework despite DRF's richer tooling because our needs are API-first and real-time, not admin-panel-first

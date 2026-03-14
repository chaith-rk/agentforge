# ADR-003: WebSockets for Real-Time Dashboard

**Status:** Accepted
**Date:** 2026-03-14
**Decision Maker:** Chaitanya Rajkumar

## Context

The demo dashboard needs to display call events (transcript, state transitions, data points) in real-time as they happen during a live call. We considered:

- **Polling:** Dashboard requests updates every N seconds. Simple but adds latency and unnecessary server load.
- **Server-Sent Events (SSE):** Server pushes updates to client. Simpler than WebSockets but unidirectional.
- **WebSockets:** Bidirectional, persistent connection. More complex but enables future features.

## Decision

Use **WebSockets** for real-time dashboard communication.

## Consequences

### Positive
- Sub-second event delivery — transcript appears as it's spoken
- Bidirectional: enables future features like supervisor sending instructions mid-call
- FastAPI has native WebSocket support (no additional dependencies)
- ConnectionManager pattern cleanly handles multiple clients watching different calls
- The live demo impact: leadership watches data populate in real-time

### Negative
- More complex than polling or SSE
- Requires connection lifecycle management (reconnection logic in frontend)
- Stateful connections — harder to scale horizontally (mitigated: sticky sessions or Redis pub/sub)

### Neutral
- For the POC with a single server, WebSocket scaling is not a concern
- If we needed pure simplicity, SSE would suffice, but WebSockets give us room to grow

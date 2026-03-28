# ADR-004: Event-Sourced Database

**Status:** Accepted
**Date:** 2026-03-14
**Decision Maker:** Chaitanya Rajkumar

## Context

The platform stores verification call data including PII, compliance events, and audit records. We need to choose between:

- **Traditional CRUD:** Tables with rows that are created, read, updated, and deleted. Simple and familiar.
- **Event sourcing:** All changes stored as immutable events. Current state is derived by replaying events. Nothing is ever updated or deleted.

This decision is heavily influenced by our compliance requirements. AgentForge operates as a Consumer Reporting Agency (CRA) under FCRA. Verification records may be subject to regulatory audit, legal discovery, or consumer dispute.

## Decision

Use **event sourcing** as the primary data persistence pattern.

## Consequences

### Positive
- **Immutable audit trail:** Every action during every call is recorded permanently. Events cannot be modified or deleted through the application.
- **Tamper evidence:** If someone modifies the database directly, the event sequence will be inconsistent — detectable via event replay.
- **Complete reconstruction:** The full history of any call can be reconstructed by replaying its events. This is invaluable for dispute resolution.
- **Compliance confidence:** When a regulator or legal team asks "what happened on this call?", the event log provides a second-by-second answer.
- **Debugging:** Production issues can be diagnosed by replaying the event stream.
- **Temporal queries:** "What was the state of this call at 2:47 PM?" is answerable.

### Negative
- More complex than CRUD for simple queries (mitigated: materialized views for common queries)
- Event schemas must be carefully versioned as the system evolves
- Storage grows faster than CRUD (every change is a new row, not an update)
- Queries that aggregate across sessions require materialized views or projections

### Why This Matters for AgentForge Specifically
1. **FCRA compliance:** Verification records must be accurate and defensible. Event sourcing provides the strongest possible evidence of what happened.
2. **Dispute resolution:** When a candidate disputes a verification result, event replay shows exactly what the employer said, when, and what the agent did with that information.
3. **Security posture:** For a manager focused on "never getting into a lawsuit scenario," event sourcing is the gold standard for data integrity.
4. **No silent data loss:** In a CRUD system, an UPDATE overwrites history. In event sourcing, history is preserved by definition.

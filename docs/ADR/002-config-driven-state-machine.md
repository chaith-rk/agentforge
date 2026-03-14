# ADR-002: Config-Driven State Machine

**Status:** Accepted
**Date:** 2026-03-14
**Decision Maker:** Chaitanya Rajkumar

## Context

The voice agent needs to follow a structured conversation flow with defined states, transitions, and compliance checkpoints. We considered two approaches:

- **Hardcoded state machine:** States and transitions defined in Python code (`if state == "GREETING": ...`). Each agent type requires new code.
- **Config-driven state machine:** States, transitions, data schemas, and compliance rules defined in YAML. The engine is generic and reads configuration at runtime.

## Decision

Use a **config-driven state machine** where agent behavior is defined entirely in YAML and validated by Pydantic models at load time.

## Consequences

### Positive
- **Platform play:** Adding a new agent type (education verification, reference check) requires only a new YAML file — zero code changes to the engine
- **Separation of concerns:** Conversation designers (operations team) can modify agent behavior without touching engine code
- **Validation at startup:** Pydantic catches config errors (invalid transitions, missing states) before any call happens
- **Version control:** YAML diffs show exactly what changed in agent behavior
- **Testability:** Same engine, different configs = test the engine once, validate each config independently

### Negative
- YAML configs can become complex for agents with many states
- Some edge case logic may be awkward to express declaratively
- Debugging requires understanding both the config and the engine

### Neutral
- The engine handles ~15 states for employment verification. This is manageable in YAML. If agent complexity grows beyond ~30 states, we may need a visual config editor.

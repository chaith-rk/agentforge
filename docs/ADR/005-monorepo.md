# ADR-005: Monorepo Structure

**Status:** Accepted
**Date:** 2026-03-14
**Decision Maker:** Chaitanya Rajkumar

## Context

The platform consists of a Python backend, React dashboard, YAML agent configurations, system prompts, and documentation. We considered:

- **Monorepo:** Everything in one repository
- **Multi-repo:** Separate repos for backend, frontend, configs, docs

## Decision

Use a **monorepo** structure for the entire platform.

## Consequences

### Positive
- Single clone to get the entire system running
- Agent configs, prompts, and code are versioned together — changes are atomic
- Easier onboarding: one repo, one README, one setup process
- Single CI/CD pipeline
- Cross-component refactoring in a single commit
- Documentation lives with the code it describes

### Negative
- Repository will grow as the frontend is added
- Frontend and backend dependencies are co-located (mitigated: separate `requirements.txt` and `package.json`)
- Build times may increase as repo grows

### Neutral
- At POC/pilot scale, monorepo overhead is negligible
- If the platform grows to multiple teams, we can split repos later — monorepo-to-multirepo is easier than the reverse

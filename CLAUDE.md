# AgentForge Platform

## Project Overview
AI voice agent platform for automated verification calls (employment, education, etc.). Built as an internal service at AgentForge (background screening company). The platform supports multiple agent types via YAML configuration — adding a new agent or modifying fields requires zero code changes.

## Key Documents
- **`docs/GRAND_PLAN.md`** — Full MVP build plan (pages, API contracts, build order)
- **`docs/PROGRESS.md`** — Current status of all phases
- **`docs/PRASHANT_WORKFLOW_INSIGHTS.md`** — Prashant Singh's verification workflow (the ground truth for how agents should behave)
- **`docs/ARCHITECTURE.md`** — Component architecture and data flow
- **`docs/PRD.md`** — Product requirements

## Tech Stack
- **Backend:** Python 3.11+, async FastAPI
- **Voice:** Vapi (telephony + STT + TTS + LLM orchestration)
- **Database:** SQLite with event sourcing (aiosqlite)
- **Frontend:** React + TypeScript + Vite + Tailwind + shadcn/ui (planned, not started)
- **Config:** YAML agent definitions validated by Pydantic
- **Deployment:** Docker, docker-compose

## Multi-Agent Architecture
- **API is agent-agnostic:** `POST /api/calls/initiate` accepts `agent_config_id` + `candidate_claims: dict[str, Any]`. No agent-specific fields in the API layer.
- **System prompt is dynamic:** `handle_assistant_request` webhook builds prompts from YAML config + candidate data per call. Vapi dashboard is fallback only.
- **Status auto-derived:** `FieldVerification.status` property computes `verified`/`review_needed`/`unable_to_verify` using the Apple-to-Apple rule (exact match only = verified, any difference = review_needed).
- **YAML fields drive everything:**
  - `question` → AI asks this during the call
  - `is_candidate_input` → field shown in the New Call form
  - `display_name` → friendly label in UI
  - `pii_level` → encryption at rest
- **To add/modify fields:** Edit the YAML in `agents/`, restart app. No code changes.
- **To add a new agent type:** Create a new YAML file in `agents/` + a prompt template in `prompts/`. No code changes.

## Coding Conventions
- **Python:** Strict typing everywhere. Use `from __future__ import annotations`.
- **Async:** All I/O operations must be async. Never use blocking calls.
- **Models:** Pydantic v2 for all data structures. No raw dicts for structured data.
- **Config:** YAML for agent definitions. Pydantic for validation.
- **Naming:** snake_case for Python, kebab-case for API endpoints.
- **Docstrings:** Required on all classes and public methods.

## Security Rules — CRITICAL
- **NEVER** log PII (names, dates, SSNs, phone numbers). Use the `redact_pii()` utility.
- **NEVER** commit `.env` files or secrets. Use `.env.example` for templates.
- **ALWAYS** validate Vapi webhook signatures (HMAC).
- **ALWAYS** encrypt PII fields (pii_level: medium/high) at rest using Fernet.
- **ALWAYS** use parameterized queries. No string interpolation in SQL.
- **NEVER** expose internal errors to API consumers. Return generic error messages.

## Testing
- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Red team scenarios in `tests/red_team/`
- Run: `pytest tests/`

## Git Conventions
- Branch naming: `feature/`, `fix/`, `docs/`
- Commit messages: imperative mood, concise
- Never commit to main directly — use PRs

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
- **Frontend:** React 19 + TypeScript + Vite + Tailwind 4 + shadcn/ui (8 pages, live transcript, WebSocket)
- **Config:** YAML agent definitions validated by Pydantic
- **Deployment:** Railway (backend) + Vercel (frontend), Docker

## Multi-Agent Architecture
- **API is agent-agnostic:** `POST /api/calls/initiate` accepts `agent_config_id` + `candidate_claims: dict[str, Any]`. No agent-specific fields in the API layer.
- **System prompt is dynamic:** Inline assistant config built at call time from YAML config + candidate data. Passed directly to Vapi in the create call payload (no assistant-request webhook flow).
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

## Vapi Integration Notes
- **API endpoint:** `POST https://api.vapi.ai/call` (not `/call/phone`)
- **Inline assistant config:** Must include `model` (with `provider`, `model`, `messages`, `tools`), `voice`, `firstMessage`, and `serverUrl` inside the `assistant` object
- **Webhook events:** Vapi sends `conversation-update` (full transcript), `tool-calls` (OpenAI format with `function.name`/`function.arguments`), `end-of-call-report` (final transcript in `artifact.messages`), `status-update`, `speech-update`
- **Tool call format:** `{id, type: "function", function: {name, arguments}}` — arguments is a JSON string
- **Phone numbers:** Must be E.164 format with `+` prefix

## Testing
- Tests in `tests/` — run: `pytest tests/`
- 33 tests: 2 API call tests + 31 eval tests
- Test gaps: webhook handler, API endpoints, agent config loading, event store

## Git Conventions
- Branch naming: `feature/`, `fix/`, `docs/`
- Commit messages: imperative mood, concise
- Never commit to main directly — use PRs

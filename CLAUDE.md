# Vetty Voice AI Platform

## Project Overview
AI voice agent platform for automated employment verification calls. Built as an internal service at Vetty (background screening company). The platform is designed to support multiple agent types via YAML configuration.

## Tech Stack
- **Backend:** Python 3.11+, async FastAPI
- **Voice:** Vapi (telephony + STT + TTS + LLM orchestration)
- **Database:** SQLite with event sourcing (aiosqlite)
- **Frontend:** React (dashboard for real-time call monitoring)
- **Config:** YAML agent definitions validated by Pydantic
- **Deployment:** Docker, docker-compose

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

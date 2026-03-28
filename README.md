# AgentForge Platform

AI-powered voice agent platform for automated employment verification calls, built for [AgentForge](https://agentforge.co) background screening operations.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AgentForge Platform                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌─────────────────────┐    ┌───────────────────┐  │
│  │ Agent Configs │───▶│  Agent Runtime      │───▶│   Vapi            │  │
│  │   (YAML)      │    │  Engine (FastAPI)    │    │   (Telephony)     │  │
│  │               │    │                     │    │                   │  │
│  │ - States      │    │ - State Machine     │    │ - STT / TTS       │  │
│  │ - Transitions │    │ - Compliance Engine │    │ - LLM Orchestr.   │  │
│  │ - Data Schema │    │ - Data Recorder     │    │ - Phone Calls     │  │
│  │ - Compliance  │    │ - Audit Logger      │    │                   │  │
│  └──────────────┘    └────────┬────────────┘    └───────────────────┘  │
│                               │                                         │
│                    ┌──────────▼──────────┐    ┌───────────────────────┐ │
│                    │  Event Store        │    │  Demo Dashboard       │ │
│                    │  (SQLite)           │───▶│  (React + WebSocket)  │ │
│                    │                    │    │                       │ │
│                    │ - Immutable Events  │    │ - Live Call Monitor   │ │
│                    │ - PII Encryption    │    │ - Transcript Stream   │ │
│                    │ - Audit Trail       │    │ - State Visualization │ │
│                    └────────────────────┘    └───────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- A [Vapi](https://vapi.ai) account (for telephony)
- [ngrok](https://ngrok.com) (for local webhook tunneling during development)

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd agentforge-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Vapi API key, webhook secret, and encryption key

# Generate a PII encryption key
python scripts/generate_encryption_key.py
# Copy the output into .env as PII_ENCRYPTION_KEY

# Run the application
uvicorn src.main:app --reload --port 8000
```

### Docker

```bash
docker-compose up --build
```

### Development with ngrok

```bash
# In a separate terminal, expose localhost:8000 for Vapi webhooks
ngrok http 8000
# Copy the HTTPS URL and configure it as your Vapi webhook endpoint
```

## Current Vapi Runtime Behavior

- Live call persona, first message, and script currently come from the Vapi
  assistant configured in Vapi's dashboard, not from `prompts/*.md` in this
  repo.
- This backend does not yet build the assistant dynamically. It triggers Vapi
  with an `assistantId` and then processes webhook events from
  `/webhooks/vapi`.
- `VAPI_ASSISTANT_ID` is the default assistant, but `/api/calls/initiate`
  now accepts an optional `assistant_id` field so you can test a different
  assistant for a single call without editing `.env`.
- If `VAPI_WEBHOOK_SECRET` is blank, leave Vapi server auth off. If you change
  `.env`, restart `uvicorn` so the running process reloads the new values.

Example one-off call using a different Vapi assistant:

```bash
set -a; source .env; set +a
curl -X POST http://localhost:8000/api/calls/initiate \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "assistant_id": "your-vapi-assistant-id",
    "subject_name": "Jane Doe",
    "company_name": "Acme Inc",
    "company_phone": "+15551234567",
    "job_title": "Software Engineer",
    "start_date": "2022-01-01"
  }'
```

## Project Structure

```
agentforge-platform/
├── agents/                          # YAML agent configurations
│   ├── employment_verification_call.yaml   # Employment verification agent
│   └── education_verification_call.yaml    # Education verification (skeleton)
├── prompts/                         # System prompt templates
│   └── employment_verification_call.md
├── src/
│   ├── main.py                      # FastAPI application entry point
│   ├── api/
│   │   ├── calls.py                 # Call management REST endpoints
│   │   └── dashboard.py             # WebSocket endpoint for real-time updates
│   ├── config/
│   │   ├── agent_config.py          # Pydantic models for YAML config validation
│   │   ├── loader.py                # YAML config loader with validation
│   │   └── settings.py              # Environment-based app settings
│   ├── database/
│   │   ├── encryption.py            # Fernet PII encryption utilities
│   │   └── event_store.py           # Async SQLite event store
│   ├── engine/
│   │   ├── audit_logger.py          # Immutable audit event logger
│   │   ├── compliance_validator.py  # Compliance checkpoint engine
│   │   ├── data_recorder.py         # Verification data recorder
│   │   └── state_machine.py         # Config-driven conversation state machine
│   ├── middleware/
│   │   └── security.py              # API key auth, HMAC validation, PII redaction
│   ├── models/
│   │   ├── call_session.py          # Call session model
│   │   ├── events.py                # Event-sourced event models
│   │   └── verification_record.py   # Final verification output model
│   ├── vapi/
│   │   └── client.py                # Async Vapi API client
│   └── webhooks/
│       ├── router.py                # Event router (webhooks → engine)
│       └── vapi_handler.py          # Vapi webhook receiver
├── scripts/
│   └── generate_encryption_key.py   # Fernet key generator
├── docs/                            # Documentation
│   ├── PRD.md                       # Product Requirements Document
│   ├── ARCHITECTURE.md              # Architecture & design
│   ├── PROGRESS.md                  # Phase tracker
│   ├── THREAT_MODEL.md              # Security threat model
│   ├── PRESENTATION_OUTLINE.md      # Leadership presentation plan
│   └── ADR/                         # Architecture Decision Records
├── Dockerfile                       # Multi-stage, non-root container
├── docker-compose.yml               # Local deployment orchestration
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project config (ruff, mypy, pytest)
└── .env.example                     # Environment variable template
```

## Key Features

### Config-Driven Agents
Define new agent types entirely in YAML. No code changes required. Each config specifies states, transitions, data schema, compliance rules, and voice settings. The engine is generic; the config is specific.

### Event-Sourced Audit Trail
Every action during a call is recorded as an immutable event. Call state can be reconstructed by replaying events. The event log provides a tamper-evident audit trail for compliance reviews and dispute resolution.

### Compliance State Machine
Compliance rules are enforced at the infrastructure level, not just the prompt level. BLOCK-level checkpoints prevent state transitions until they pass. The state machine will not advance past a state with a failed compliance check, regardless of what the LLM attempts.

### Real-Time Dashboard
WebSocket-based live call monitoring. Connected clients receive transcript updates, state transitions, and data point collections as they happen during active calls.

### PII Encryption at Rest
Fields classified as MEDIUM or HIGH PII sensitivity are encrypted at rest using Fernet symmetric encryption. Encryption decisions are driven by the agent's data schema, ensuring consistent protection across all agent types.

## Security

This platform handles sensitive PII during employment verification. Security measures include:

| Layer | Mechanism |
|-------|-----------|
| **Webhook Authentication** | HMAC-SHA256 signature validation and shared-secret header validation on Vapi webhooks |
| **API Authentication** | API key validation via `X-API-Key` header on all client endpoints |
| **PII Encryption** | Fernet symmetric encryption for MEDIUM/HIGH PII fields at rest |
| **PII in Logs** | Regex-based PII redaction in all structured log output |
| **Container Security** | Non-root user (`agentforge`) in multi-stage Docker build |
| **Rate Limiting** | In-memory rate limiter (Redis-backed in production) |
| **SQL Injection** | Parameterized queries only; no string interpolation in SQL |
| **Secret Management** | All secrets via environment variables; `.env` in `.gitignore` |
| **CORS** | Configurable allowed origins |
| **Compliance** | State-machine-enforced compliance checkpoints (recorded line disclosure, no requestor disclosure, accept refusals) |

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the full threat model.

## Documentation

- [Vapi Setup Guide](docs/VAPI_SETUP.md)
- [Product Requirements Document](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Progress Tracker](docs/PROGRESS.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Presentation Outline](docs/PRESENTATION_OUTLINE.md)
- [Architecture Decision Records](docs/ADR/README.md)

## License

Proprietary. Internal use at AgentForge only.

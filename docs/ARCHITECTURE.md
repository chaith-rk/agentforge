# Architecture — AgentForge Platform

**Version:** 1.0
**Date:** 2026-03-14

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  AGENTFORGE VOICE AI PLATFORM                    │
│                                                                 │
│  ┌─────────────┐   ┌──────────────────┐   ┌────────────────┐  │
│  │ Agent Config │──▶│  Runtime Engine   │──▶│     Vapi       │  │
│  │   (YAML)     │   │   (FastAPI)       │   │  (Telephony)   │  │
│  └─────────────┘   └────────┬─────────┘   └───────┬────────┘  │
│                              │                      │           │
│                    ┌─────────▼─────────┐   ┌───────▼────────┐  │
│                    │   Event Store     │   │  Phone Network  │  │
│                    │   (SQLite)        │   │  (PSTN/VoIP)   │  │
│                    └─────────┬─────────┘   └────────────────┘  │
│                              │                                  │
│                    ┌─────────▼─────────┐                       │
│                    │  Demo Dashboard   │                       │
│                    │  (React + WS)     │                       │
│                    └───────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Configuration Layer (`src/config/`)

**Purpose:** Define agent behavior entirely in YAML. The engine reads config; it never contains agent-specific logic.

| Component | File | Responsibility |
|-----------|------|---------------|
| Agent Config Models | `agent_config.py` | Pydantic models that define the YAML schema: states, transitions, data fields, compliance rules, voice settings |
| Config Loader | `loader.py` | Loads and validates YAML against Pydantic models. Catches all config errors at startup, not during live calls |
| App Settings | `settings.py` | Environment-based settings via pydantic-settings. All secrets from env vars |

**Design decision:** Agent configs are validated at load time with cross-references checked (all transition targets exist, initial state exists, terminal state exists, data field references valid). See [ADR-002](ADR/002-config-driven-state-machine.md).

### 2. Engine Layer (`src/engine/`)

**Purpose:** Generic runtime that executes any agent config. The engine is the same whether running employment verification or education verification.

| Component | File | Responsibility |
|-----------|------|---------------|
| State Machine | `state_machine.py` | Processes events, manages transitions, enforces compliance checkpoints before allowing state changes |
| Compliance Validator | `compliance_validator.py` | Evaluates named compliance rules against call context. Rules are registered via decorator and referenced by name in YAML |
| Data Recorder | `data_recorder.py` | Records verification data points with per-field confidence, detects discrepancies, validates against schema |
| Audit Logger | `audit_logger.py` | Logs every event with timestamp, session ID, event type, and actor |
| Summary Generator | `summary_generator.py` | Post-call narrative summary via Anthropic Messages API (PII-redacted input, graceful degrade on failure). Optional — requires `ANTHROPIC_API_KEY`. |

**Key design:** The state machine checks compliance checkpoints *before* allowing transitions. A BLOCK-level checkpoint (like `recorded_line_disclosure`) physically prevents the conversation from advancing. This is infrastructure-enforced compliance — stronger than prompt-based compliance.

### 3. Data Layer (`src/database/`, `src/models/`)

**Purpose:** Event-sourced persistence. Every action is an immutable event. Current state is derived from events.

| Component | File | Responsibility |
|-----------|------|---------------|
| Event Store | `event_store.py` | Async SQLite with append-only events, materialized session views, snapshots |
| Encryption | `encryption.py` | Fernet encryption/decryption for PII fields |
| Event Models | `models/events.py` | Typed event classes (12 event types) |
| Call Session | `models/call_session.py` | Materialized view of current call state |
| Verification Record | `models/verification_record.py` | Final structured output with `to_report_dict()` |

**Event sourcing rationale:** See [ADR-004](ADR/004-event-sourced-database.md). In a compliance-heavy domain, immutable event logs provide a tamper-evident audit trail. Nothing is UPDATE'd or DELETE'd.

### 4. API Layer (`src/api/`, `src/webhooks/`)

**Purpose:** REST API for triggering calls and retrieving data. WebSocket for real-time dashboard updates. Webhook receiver for Vapi events.

| Component | File | Responsibility |
|-----------|------|---------------|
| Call API | `api/calls.py` | REST endpoints: initiate calls, get status, list calls, get verification records |
| Dashboard WS | `api/dashboard.py` | WebSocket endpoint with ConnectionManager for real-time event streaming |
| Vapi Handler | `webhooks/vapi_handler.py` | Receives Vapi webhooks (function-call, tool-calls, transcript, status, end-of-call) |
| Event Router | `webhooks/router.py` | Bridges webhook events to engine components |

### 5. Security Layer (`src/middleware/`)

**Purpose:** Defense-in-depth security across all request paths.

| Mechanism | Implementation | Scope |
|-----------|---------------|-------|
| Webhook auth | HMAC signature + shared secret + Bearer token | `/webhooks/vapi` |
| API auth | API key in `X-API-Key` header | All `/api/` endpoints |
| PII redaction | Regex-based redaction of SSNs, phones, emails | All log output |
| Rate limiting | In-memory sliding window (Redis in production) | All endpoints |
| CORS | Configurable allowed origins | All endpoints |

### 6. Voice Layer (`src/vapi/`)

**Purpose:** Thin async client wrapping Vapi's REST API.

The voice layer is deliberately thin — Vapi handles STT, TTS, LLM orchestration, and telephony. Our backend controls what the agent knows (system prompt), what it can do (function/tool calls), and what it records (webhook events).

---

## Call Lifecycle Data Flow

```
1. Operator triggers call via POST /api/calls/initiate
   └──▶ Creates call session in event store
   └──▶ Calls Vapi API to initiate outbound call
   └──▶ Returns session_id + vapi_call_id

2. Vapi connects call, sends assistant-request webhook
   └──▶ Backend returns system prompt + function definitions

3. During call, Vapi sends webhooks:
   ├── transcript (real-time) ──▶ Broadcast to dashboard via WebSocket
   ├── tool-calls (data collection) ──▶ Process through engine:
   │   ├── State machine evaluates transition
   │   ├── Compliance validator checks checkpoints
   │   ├── Data recorder stores field values
   │   └── Audit logger records events
   └── status-update ──▶ Update session state

4. Call ends, Vapi sends end-of-call-report
   └──▶ Generate final verification record
   └──▶ Store completion event
   └──▶ Notify dashboard via WebSocket
```

---

## Security Architecture

### PII Data Flow

```
Candidate PII (input)                Employer PII (collected)
       │                                      │
       ▼                                      ▼
  System Prompt                         Data Recorder
  (template interpolation)              (field values)
       │                                      │
       ▼                                      ▼
  Vapi (in-memory only,              Event Store
  not persisted by us)                (encrypted if pii_level ≥ MEDIUM)
                                              │
                                              ▼
                                        Verification Record
                                        (encrypted fields)
```

**PII boundaries:**
- PII enters the system via the `initiate_call` request
- PII is interpolated into the system prompt template (sent to Vapi, not stored by us)
- Collected PII from employers is encrypted at rest based on `pii_level` in the data schema
- PII is **never** written to application logs (redaction middleware)
- PII is **never** in error messages returned to API consumers

### Compliance Enforcement

```
Prompt-based compliance (weak):
  "Please mention recorded line" ──▶ LLM might ignore

State-machine compliance (strong):
  GREETING state ──▶ compliance checkpoint: recorded_line_disclosure
                 ──▶ if FAIL + BLOCK: transition denied
                 ──▶ agent physically cannot proceed
```

---

## Deployment Architecture

### Development (POC)
```
Developer Machine
├── uvicorn (port 8000)
├── ngrok tunnel (HTTPS → localhost:8000)
└── SQLite (data/calls.db)

Vapi Cloud ──webhook──▶ ngrok ──▶ localhost:8000/webhooks/vapi
```

### Production (Future)
```
Cloud Provider (AWS/GCP)
├── Load Balancer (HTTPS)
├── Container Instances (Docker)
│   └── FastAPI (stateless)
├── PostgreSQL (event store)
├── Redis (rate limiting, caching)
└── S3 (call recording storage)

Vapi Cloud ──webhook──▶ Load Balancer ──▶ Container
```

---

## Scalability Path

| Stage | Concurrency | Infrastructure |
|-------|-------------|---------------|
| POC | 1-5 calls | Local + SQLite |
| Pilot | 10-50 calls | Single server + PostgreSQL |
| Production | 100+ calls | Multiple containers + PostgreSQL + Redis |
| Scale | 1000+ calls | Auto-scaling containers + read replicas |

The async architecture and stateless design mean scaling is an infrastructure change, not a code change. See [ADR-001](ADR/001-async-fastapi.md).

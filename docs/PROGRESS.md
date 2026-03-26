# Progress Tracker — Vetty Voice AI Platform

**Last Updated:** 2026-03-25

## Current Status

**Foundation complete. Platform is fully multi-agent.** All hardcoded
employment-specific code has been replaced with generic, config-driven logic.
Adding a new agent type or modifying fields is a YAML-only change. Dynamic
system prompt generation is implemented — Vapi dashboard is no longer the
source of truth for assistant config.

**Next:** Build the React frontend (command center) and complete Vapi
integration testing. See `docs/GRAND_PLAN.md` for the full build plan.

---

## Completed Work

### Phase 1: Vapi Setup + Hello World ✅
**Completed:** 2026-03-14

- [x] Vapi account, test assistant, phone number provisioned
- [x] Outbound calls working via VapiClient
- [x] Voice speed tuned (1.2x), interruption handling configured

### Phase 2: Agent Config + System Prompt ✅
**Completed:** 2026-03-25

- [x] YAML config format with Pydantic models (`src/config/agent_config.py`)
- [x] `employment_verification_call.yaml` — 17 states, 20 fields
- [x] `education_verification_call.yaml` — 7 states, 5 fields
- [x] System prompt template (`prompts/employment_verification_call.md`)
- [x] Config loading + validation (`src/config/loader.py`)
- [x] All configs auto-loaded from `agents/` directory at startup
- [x] `DataPointSchema` extended with `display_name`, `question`, `is_candidate_input`
- [ ] Add `question` fields to employment YAML data_schema entries
- [ ] Add `question` fields to education YAML data_schema entries

### Phase 3: Vapi Integration — Dynamic Prompt 🟡
**Completed:** Backend ready. Needs live testing.

- [x] Dynamic `handle_assistant_request` — builds system prompt from YAML + candidate data per call
- [x] Tool definitions generated dynamically (`record_data_point`, `record_discrepancy`, `record_redirect`, `record_no_record`, `mark_state_transition`)
- [x] Candidate claims injected into system prompt template variables
- [x] Verification questions appended from `data_schema.question` fields
- [x] Webhook URL configured (ngrok → local FastAPI)
- [ ] Configure voice (professional, moderate pace)
- [ ] Live test: Does dynamic prompt work end-to-end with Vapi?
- [ ] Test all 9 scenarios (happy path, discrepancy, redirect, refusal, etc.)

### Phase 4: Backend Runtime Engine 🟡
**Status:** Multi-agent foundation complete. Webhook wiring partially done.

**Completed:**
- [x] FastAPI project structure
- [x] Generic state machine engine (config-driven, zero agent-specific code)
- [x] Generic data recorder + audit logger
- [x] Call session manager
- [x] Event store (SQLite, event-sourced, append-only)
- [x] PII encryption utilities
- [x] Security middleware (API key, webhook auth, PII redaction, rate limiting)
- [x] Vapi client (outbound call triggering)
- [x] **Multi-agent API** — `CandidateClaim` uses generic `claims: dict[str, Any]`
- [x] **Multi-agent result** — `_build_verification_record()` iterates `data_schema` dynamically
- [x] **Apple-to-Apple status** — `FieldVerification.status` auto-derives `verified`/`review_needed`/`unable_to_verify`
- [x] **Rich report output** — `to_report_dict()` returns per-field status, display_name, overall_status
- [x] Webhook handlers broadcast to WebSocket (transcript, data points, state transitions, discrepancies, call completion)

**Remaining:**
- [ ] New endpoints: `GET /api/agents`, `GET /api/agents/{id}`, `GET /api/calls/{id}/result`, `GET /api/stats`
- [ ] End-to-end test: trigger call → conversation → structured verification record
- [ ] Confirm transcript/tool-call events persist from production Vapi payloads

### Phase 5: Demo Dashboard 🔲
**Status:** Not started — see `docs/GRAND_PLAN.md` Phase B for full spec.

Pages planned: Dashboard, New Call (with pre-fill test data), Call Detail (transcript + side-by-side results), Call History, Agents, Evals, API Docs, Settings.

### Phase 6: Eval Pipeline 🔲
**Status:** Not started — see `docs/GRAND_PLAN.md` Phase A4.

Code-based evals: recorded_line_disclosure, completeness, status_accuracy, format_validation.
LLM-based evals: data_extraction_accuracy, no_hallucination, no_requestor_disclosure, tone.

### Phase 7: Red-Teaming 🔲
**Status:** Not started — 11 scenarios defined.

---

## Key Architecture Decisions (2026-03-25)

1. **API is agent-agnostic:** `POST /api/calls/initiate` accepts `agent_config_id` + `candidate_claims: dict`. No employment-specific fields in the API.
2. **System prompt is dynamic:** `handle_assistant_request` webhook builds the prompt from YAML config + candidate data. Vapi dashboard assistant is fallback only.
3. **Status is auto-derived:** `FieldVerification.status` computes `verified`/`review_needed`/`unable_to_verify` from the Apple-to-Apple rule. AI agent just records what employer says.
4. **Fields drive everything:** Adding `question` to a `data_schema` entry → AI asks it. Adding `is_candidate_input: true` → field appears in the call form. Adding `display_name` → UI shows a friendly label.

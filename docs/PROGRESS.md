# Progress Tracker — AgentForge Platform

**Last Updated:** 2026-04-10

## Current Status

**Code is production-ready; deployment is paused.** End-to-end call flow
works locally. Today's session hardened the codebase for prod (fail-closed
auth, volume-aware SQLite, PII redaction in logs, 105 tests) and produced
a full deploy runbook at `docs/RUNBOOK.md`. The Railway project exists
but has no backend service yet. Vercel not started.

**Next (separate session):** Work through `docs/RUNBOOK.md` §0.2 onward —
create Railway backend service from GitHub, mount volume at `/app/data`,
set env vars, deploy, smoke test, then Vercel and Vapi wiring.

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
- [x] `question` fields added to employment YAML data_schema entries

### Phase 3: Vapi Integration — Dynamic Prompt ✅
**Completed:** 2026-03-28

- [x] Dynamic system prompt built from YAML + candidate data per call
- [x] Tool definitions generated dynamically (`record_data_point`, `record_discrepancy`, `record_redirect`, `record_no_record`, `mark_state_transition`)
- [x] Candidate claims injected into system prompt template variables
- [x] Verification questions appended from `data_schema.question` fields
- [x] Inline assistant config passed to Vapi (model, voice, tools, serverUrl)
- [x] Default Vapi voice configured when none set in YAML
- [x] Prompt template placeholders aligned with frontend claim field names
- [x] Phone number E.164 normalization (auto-prepend +)
- [x] Vapi API endpoint corrected (`POST /call` not `/call/phone`)
- [x] Live tested: outbound calls connect, AI agent speaks, verification flow works

### Phase 4: Backend Runtime Engine ✅
**Completed:** 2026-03-28

- [x] FastAPI project structure
- [x] Generic state machine engine (config-driven, zero agent-specific code)
- [x] Generic data recorder + audit logger
- [x] Call session manager
- [x] Event store (SQLite, event-sourced, append-only)
- [x] PII encryption utilities
- [x] Security middleware (API key, webhook auth, PII redaction, rate limiting)
- [x] Vapi client (outbound call triggering with inline assistant config)
- [x] **Multi-agent API** — `CandidateClaim` uses generic `claims: dict[str, Any]`
- [x] **Multi-agent result** — `_build_verification_record()` iterates `data_schema` dynamically
- [x] **Apple-to-Apple status** — `FieldVerification.status` auto-derives `verified`/`review_needed`/`unable_to_verify`
- [x] **Rich report output** — `to_report_dict()` returns per-field status, display_name, overall_status
- [x] Webhook handlers: `conversation-update`, `tool-calls`, `end-of-call-report`, `status-update`, `transcript`
- [x] WebSocket broadcast (transcript, data points, state transitions, call completion)
- [x] `POST /api/calls/{id}/stop` endpoint — kills active call via Vapi API
- [x] All endpoints: `/api/agents`, `/api/agents/{id}`, `/api/calls/{id}/result`, `/api/stats`
- [x] Tool call parsing fixed for OpenAI format (`function.name`, `function.arguments`)

### Phase 5: React Frontend ✅
**Completed:** 2026-03-28

- [x] 8 pages: Dashboard, New Call, Call Detail, Call History, Agents, Evals, API Docs, Settings
- [x] Live transcript via WebSocket (`conversation-update` → frontend)
- [x] Verification results table (side-by-side candidate vs employer values)
- [x] End Call button (stops active call via Vapi API)
- [x] Download Report button (JSON export)
- [x] Status badges, auto-scroll transcript, call timer
- [x] API URLs configurable via `VITE_*` env vars (not hardcoded localhost)
- [x] WebSocket auto-detects `wss://` in production

### Phase 6: Eval Pipeline ✅
**Completed:** 2026-03-25

- [x] 4 code-based evals: `RecordedLineDisclosureEval`, `CompletenessEval`, `StatusAccuracyEval`, `FormatValidationEval`
- [x] `EvalRunner` with `run_all()` and `summary()` methods
- [x] `EvalRunner` wired into `complete_call()` — every completed call is scored and results are persisted via `EVAL_COMPLETED` event + snapshot
- [x] 105 tests passing (31 eval + 2 API call + 37 agent config + 18 event store + 17 webhook handler tests)
- [ ] LLM-based evals: stubs created, not implemented

### Phase 7: Production Deployment 🟡
**Status:** Code hardened for prod. Deployment paused — to resume in a separate session using `docs/RUNBOOK.md` as the single source of truth.

Code readiness (done 2026-04-10):
- [x] Dockerfile (multi-stage, non-root user, health check)
- [x] `.dockerignore` for smaller images
- [x] `railway.json` deployment config
- [x] Webhook HMAC auth + API key middleware fail closed in production when secrets missing (previously fail-open, a deploy-blocking vulnerability)
- [x] `settings.database_path` wired into `EventStore` so Railway volume mounts at `/app/data` actually persist writes
- [x] PII scrub of structured logs: removed `subject_name` from `call_initiated` and `assistant_request_received`; removed `tool_calls_payload_debug` dump
- [x] Bug fix: `record_data_point` with missing `field_name` now returns an error instead of persisting empty-keyed data
- [x] Webhook handler test suite (17 tests) covering auth modes, message dispatch, OpenAI tool-call format, EvalRunner wiring, fail-closed behavior
- [x] API endpoint test suite (18 tests) covering `/health`, `/api/agents/*`, `/api/calls/*`, middleware fail-closed
- [x] `frontend/.env.example` documenting `VITE_API_BASE`, `VITE_WS_HOST`, `VITE_API_KEY`
- [x] Production runbook at `docs/RUNBOOK.md` — one-shot deploy guide + ops reference

Deploy actions remaining (to do next session):
- [ ] Create backend service inside the Railway project (from GitHub repo)
- [ ] Mount persistent volume at `/app/data` (critical — SQLite wipes on deploy without this)
- [ ] Set Railway env vars per runbook §0.2
- [ ] Smoke test backend: `/health`, `/api/agents` with and without API key
- [ ] Create Vercel project with `VITE_*` env vars pointing at Railway domain
- [ ] Update Railway `CORS_ORIGINS` to include Vercel domain
- [ ] Update Vapi dashboard Server URL + Secret to Railway values
- [ ] End-to-end prod smoke test with a real outbound call

### Phase 8: Red-Teaming 🔲
**Status:** Not started — 11 scenarios defined.

---

## Key Architecture Decisions

1. **API is agent-agnostic:** `POST /api/calls/initiate` accepts `agent_config_id` + `candidate_claims: dict`. No employment-specific fields in the API.
2. **System prompt is dynamic:** Inline assistant config built at call time from YAML + candidate data. Passed directly to Vapi in the create call payload.
3. **Status is auto-derived:** `FieldVerification.status` computes `verified`/`review_needed`/`unable_to_verify` from the Apple-to-Apple rule. AI agent just records what employer says.
4. **Fields drive everything:** Adding `question` to a `data_schema` entry → AI asks it. Adding `is_candidate_input: true` → field appears in the call form. Adding `display_name` → UI shows a friendly label.
5. **No assistant-request webhook flow:** Vapi's current API requires inline assistant config or assistantId. We pass full inline config per call for maximum flexibility.
6. **Deployment:** Railway (backend, persistent server for WebSockets + webhooks) + Vercel (frontend, static React build).

---

## Bugs Fixed / Hardening (2026-04-10)

| Issue | Impact | Fix |
|-----|--------|-----|
| Webhook HMAC auth returned True when secret unset | Prod deploy with missing `VAPI_WEBHOOK_SECRET` would accept unauthenticated webhooks | `validate_webhook_signature` / `validate_webhook_secret` now return False on missing secret; handler fails closed with 503 in production, fails open with warning in dev |
| API key middleware returned 200 when `API_KEY` unset | Prod deploy with missing `API_KEY` would expose the dashboard API | Middleware returns 503 in production when `API_KEY` is missing |
| BaseHTTPMiddleware was raising `HTTPException` | FastAPI doesn't catch middleware exceptions → 500 instead of 401/503 | Middleware now returns `JSONResponse` directly |
| `EventStore` used hardcoded `data/calls.db` path, ignoring settings | Railway volume mount couldn't redirect the DB location | Added `settings.database_path`; `main.py` passes it to `EventStore(db_path=...)` |
| `record_data_point` handler persisted empty-keyed data on malformed tool args | Noise in collected data, potential empty UI rows | Handler now returns error string when `field_name` is empty |
| `subject_name` logged in `call_initiated` + `assistant_request_received` | Names are PII per project rules | Removed from structured log calls |
| `tool_calls_payload_debug` dumped raw 500-char tool call payloads per call | Employer-spoken PII leaked to logs on every tool call | Debug log removed entirely |

## Bugs Fixed (2026-03-28)

| Bug | Impact | Fix |
|-----|--------|-----|
| Wrong Vapi API endpoint (`/call/phone`) | Calls created as wrong type | Changed to `POST /call` |
| `serverUrl` at top level of payload | Vapi rejected payload | Moved inside inline `assistant` object |
| Missing `+` in phone numbers | Vapi rejected E.164 format | Auto-prepend `+` |
| No `assistant` in create call payload | Vapi said "Need assistant or assistantId" | Build and pass full inline assistant config |
| No voice configured | AI agent had no voice | Added default Vapi voice ("Elliot") |
| Prompt placeholder mismatch | `{{company_name}}` never resolved | Updated to match frontend field names (`{{employer_company_name}}`) |
| `conversation-update` not handled | No live transcript on frontend | Added handler, registered in webhook dispatch |
| WebSocket message format wrong | Frontend couldn't parse events | Changed from nested `{type, data: {}}` to flat `{type, role, content}` |
| Tool call `function_name` empty | Verification results never populated | Fixed parsing for OpenAI nested format (`function.name`) |

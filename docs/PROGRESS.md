# Progress Tracker — AgentForge Platform

**Last Updated:** 2026-04-16

## Current Status

**Deployed to production.** Backend on Railway
(`agentforge-production-8b4f.up.railway.app`), frontend on Vercel
(`agentforge-iota.vercel.app`). Outbound calls work end-to-end. Call
completion, transcript display, and verification results all render in
the dashboard for completed calls.

**🟡 In progress — Post-Call Report feature (2026-04-16):**
Competitor-style post-call report added. Backend + frontend code merged
to `claude/priceless-blackwell` branch, unit tests passing (124 total,
up from 105). **End-to-end testing pending** — not yet validated against
a real completed call in local dev, not yet deployed to Railway/Vercel.
See "Phase 9" below.

**Known remaining issues (non-blocking):**
- Real-time transcript streaming over WebSocket is intermittent;
  transcript reliably loads after call completion via REST fallback.
- Vapi `conversation-update` broadcasts may not always arrive at
  connected clients — investigate websocket broadcast from
  `handle_conversation_update` in a follow-up session.
- Phantom "Live" state when revisiting some old calls — mitigated but
  if `/result` errors, frontend now defaults to not-active rather than
  showing a fake live call.
- Verification "Claimed" column shows `—` for all fields (candidate
  claims not flowing through to the verification record).
- Agent frequently records `"Yes"`/`"No"` as the employer value instead
  of the actual data — prompt tuning issue, not a code bug.

**Deploy fixes applied this session (2026-04-14):**
- Railway `startCommand` removed from `railway.json` — now uses
  Dockerfile CMD (`sh -c` form) for proper `${PORT}` expansion.
- Entrypoint script (`entrypoint.sh`) chowns `/app/data` to the
  `agentforge` user before dropping privileges, so the SQLite volume
  mount (owned by root by default on Railway) is writable.
- Healthcheck uses dynamic `${PORT}` env var, not hardcoded 8000.
- `get_call_result` endpoint now reads from `data_snapshots` for
  completed calls (was reading `call_sessions` which had empty
  `collected_data_json`).
- New `/api/calls/{id}/transcript` endpoint reconstructs transcript
  from the event log for historical calls.
- `list_sessions` now parses JSON string columns and exposes the
  candidate name at the top level for the call history table.
- `verified_value` → `employer_value` in `to_report_dict()` — frontend
  was reading `employer_value` so the "Confirmed" column was blank.
- Structlog now reaches stdout (previously no Python logging root was
  configured, so all app logs were silently dropped in Railway).
- `CallDetail` page now checks the call's completion state on mount
  before connecting the WebSocket, eliminating the phantom timer on
  historical calls.

**Next session:**
- Investigate why real-time transcript broadcasts aren't reaching
  connected WebSocket clients — likely either a session ID resolution
  issue or an exception being swallowed in the broadcast path.
- Fix candidate claims flowing into the verification record so
  "Claimed" column populates.
- Prompt-tune so the agent records actual employer responses
  verbatim, not summary "Yes"/"No".

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

### Phase 9: Post-Call Verification Report 🟡
**Status:** Code merged to `claude/priceless-blackwell`, unit tests passing. End-to-end testing pending. Not yet deployed.
**Started:** 2026-04-16

Competitor-inspired post-call report that replaces the compact
verification table on the Call Detail page once a call is completed.
Includes a narrative summary, Cross-Verification Summary (Confirmed
Facts / Items to Clarify / Contradictions counts), and a 5-column
report table (Question / Prior Answer / Call Answer / Status /
Confidence).

Code done:
- [x] `FieldVerification` extended with `question` and `confidence` (`src/models/verification_record.py`)
- [x] `VerificationRecord` extended with `summary` field and three count properties (`confirmed_facts_count`, `contradictions_count`, `items_to_clarify_count`)
- [x] `DataRecorder.confidence_map` — per-field confidence from the agent's tool calls is now persisted (previously stripped)
- [x] `_build_verification_record()` plumbs `question` + `confidence` into `FieldVerification`
- [x] `to_report_dict()` surfaces all new fields
- [x] `src/engine/summary_generator.py` — new module, calls Anthropic API (Claude Haiku by default) with PII-redacted transcript/results; fails gracefully to empty string
- [x] `CallManager.complete_call()` invokes summary generation post-eval, pre-snapshot
- [x] `ANTHROPIC_API_KEY` + `SUMMARY_MODEL` added to `Settings` and `.env.example`
- [x] Frontend types extended in `frontend/src/lib/api.ts`
- [x] Three new components: `CallSummary.tsx`, `CrossVerificationSummary.tsx`, `VerificationReportTable.tsx`
- [x] `CallDetail.tsx` composes the new report on completed calls; keeps compact table for live calls
- [x] 19 new unit tests: `tests/test_verification_record.py` (9), `tests/test_data_recorder.py` (4), `tests/test_summary_generator.py` (6)

Testing pending:
- [ ] Local end-to-end: restart backend with `ANTHROPIC_API_KEY` set, place a test call, verify narrative summary renders, counts match, confidence pills populate
- [ ] Failure mode: confirm graceful degrade when `ANTHROPIC_API_KEY` is unset (report still renders, summary section empty)
- [ ] PII safety: confirm no candidate names / phone numbers appear in summary-generation logs
- [ ] Production deploy: push branch, set `ANTHROPIC_API_KEY` in Railway, redeploy frontend to Vercel, place live test call
- [ ] Confirm the existing "Yes"/"No" employer-value bug doesn't make the new report misleading (prompt tuning follow-up)

Graceful degrade properties:
- If Anthropic API is unreachable or the key is missing, the summary field is empty and the rest of the report renders unchanged. No blocking of call completion.
- PII redaction via `redact_pii()` applied to transcript + results before any outbound API call.

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

# Progress Tracker — AgentForge Platform

**Last Updated:** 2026-03-28

## Current Status

**End-to-end call flow working.** Outbound calls via Vapi connect, AI agent
conducts verification, live transcript streams to the frontend via WebSocket.
Platform is deployed on Railway (backend) with Vercel deployment pending
(frontend). Production deployment config is in place.

**Next:** Complete Vercel frontend deployment, test verification results table
in production, write comprehensive automated tests.

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
- [x] 33 tests passing (31 eval tests + 2 API call tests)
- [ ] LLM-based evals: stubs created, not implemented
- [ ] Eval integration with `complete_call()` flow

### Phase 7: Production Deployment 🟡
**Status:** In progress.

- [x] Dockerfile (multi-stage, non-root user, health check)
- [x] `.dockerignore` for smaller images
- [x] `railway.json` deployment config
- [x] Railway backend deployed (older commit active, latest needs env vars)
- [ ] Railway env vars configured + latest commit deployed
- [ ] Vercel frontend deployment
- [ ] CORS origins updated for production domain
- [ ] Vapi dashboard Server URL updated to production

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

# Progress Tracker — Vetty Voice AI Platform

**Last Updated:** 2026-03-14

## Current Status

**Phase 2 in progress.** Project scaffolding complete. Core backend, agent configs, infrastructure, and documentation delivered. Next: Vapi account setup and integration testing.

---

## Phase 1: Vapi Setup + Hello World
**Status:** 🔲 Not Started
**Target:** Day 1

- [ ] Create Vapi account
- [ ] Explore dashboard: assistants, phone numbers, function calls, webhooks
- [ ] Create a trivial test assistant
- [ ] Provision a phone number
- [ ] Make a test outbound call
- [ ] Review recording, assess voice quality and latency

**Success criteria:** You've heard your AI agent on a real phone call.

---

## Phase 2: Agent Config + System Prompt
**Status:** 🟡 In Progress
**Target:** Day 1–3

- [x] Define YAML config format with Pydantic models (`src/config/agent_config.py`)
- [x] Write `employment_verification_call.yaml` with full call flow
- [x] Write system prompt (`prompts/employment_verification_call.md`)
- [x] Define function/tool call schemas for Vapi
- [x] Config loading and validation (`src/config/loader.py`)
- [x] Education verification skeleton (`agents/education_verification_call.yaml`)
- [ ] Test config loading end-to-end with unit tests
- [ ] Iterate on system prompt after first Vapi test calls

**Success criteria:** Agent config loads cleanly, system prompt covers all scenarios.

---

## Phase 3: Vapi Assistant + Calling
**Status:** 🔲 Not Started
**Target:** Day 3–5

- [ ] Create employment verification assistant in Vapi dashboard
- [ ] Set system prompt from `prompts/employment_verification_call.md`
- [ ] Register function/tool calls in Vapi (record_data_point, etc.)
- [ ] Configure voice (professional, moderate pace, clear diction)
- [ ] Configure webhook URL (ngrok → local FastAPI)
- [ ] Follow `docs/VAPI_SETUP.md` for auth configuration
- [ ] Make test calls, iterate on prompt
- [ ] Test: Does it follow Prashant's script?
- [ ] Test: Does it read back candidate details correctly?
- [ ] Test: Does it handle "I can only confirm dates and title"?

**Success criteria:** Agent conducts a recognizable verification call.

---

## Phase 4: Backend Runtime Engine
**Status:** 🟡 Scaffolding Complete
**Target:** Day 5–8

- [x] FastAPI project structure
- [x] Config loader (YAML → Pydantic)
- [x] Generic state machine engine
- [x] Vapi webhook handler (function-call + tool-calls)
- [x] Generic data recorder
- [x] Audit logger
- [x] Call session manager
- [x] Verification record model
- [x] Event store (SQLite, event-sourced)
- [x] PII encryption utilities
- [x] Security middleware (API key, webhook auth, PII redaction, rate limiting)
- [x] Vapi client (outbound call triggering)
- [ ] Wire webhook events to state machine (full integration)
- [ ] Wire webhook events to data recorder
- [ ] Wire events to WebSocket broadcast
- [ ] End-to-end test: trigger call → conversation → data extracted → record generated
- [ ] Configure ngrok for development

**Success criteria:** Complete call produces a structured verification record with audit trail.

---

## Phase 5: Demo Dashboard
**Status:** 🔲 Not Started
**Target:** Day 8–10

- [ ] React app setup (agent-agnostic design)
- [ ] Call trigger UI (input candidate details, company, phone number)
- [ ] Real-time transcript view (WebSocket)
- [ ] State machine visualization (current state highlighted)
- [ ] Data extraction card (fields populate with match/mismatch indicators)
- [ ] Edge case indicators (redirect, no record, limited policy)
- [ ] Call outcome summary
- [ ] Call history view

**Success criteria:** Leadership watches a live call with full visibility.

---

## Phase 6: Red-Teaming
**Status:** 🔲 Not Started
**Target:** Day 10–12

- [ ] Happy path: cooperative verifier confirms everything
- [ ] Discrepancy: different dates (even by one day)
- [ ] Discrepancy: different title ("surgical tech" vs "surgical technician")
- [ ] Discrepancy: different company name (staffing agency / subsidiary)
- [ ] Limited policy: "I can only confirm dates and title"
- [ ] Redirect: "We use The Work Number / Thomas & Company"
- [ ] No record: "We have no record of this person"
- [ ] Voicemail: no one answers
- [ ] Hostile: "I'm not providing any information"
- [ ] Over-sharing: verifier volunteers info about candidate's performance
- [ ] Social engineering: "Who's requesting this check? What job are they applying for?"

**Success criteria:** All scenarios handled correctly.

---

## Phase 7: Platform Validation
**Status:** 🔲 Not Started
**Target:** Day 12–14

- [x] Write skeleton `education_verification_call.yaml`
- [ ] Load in engine, verify it initializes
- [ ] Demo to leadership: "Agent #1 works. Agent #2 is a config file away."

**Success criteria:** Leadership sees the platform potential.

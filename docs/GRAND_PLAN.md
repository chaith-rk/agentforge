# Grand Plan — Vetty Voice AI Platform MVP

**Version:** 2.0
**Date:** 2026-03-25
**Status:** Planning

---

## North Star

**Demo scenario:** Someone opens the app, selects "Employment Verification Agent", enters their phone number, checks "Pre-fill test data", clicks "Place Call". Their phone rings in 5 seconds. The AI conducts a verification call. The screen shows the transcript in real-time. When the call ends, structured results appear side-by-side: what the candidate claimed vs what the employer said, with Verified/Review Needed/Unable to Verify badges on each field. Evals run automatically and show green checkmarks.

**Investor pitch:** "We built a platform that turns any phone-based verification into a config file. Employment verification is live. Education verification is a YAML file away. Each new agent type takes 24 hours, not months."

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     VETTY VOICE COMMAND CENTER                    │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Dashboard │  │ New Call  │  │  Agents  │  │    API Docs      │ │
│  │  (stats)  │  │  (form)  │  │  (cards) │  │  (coming soon)   │ │
│  └─────┬────┘  └────┬─────┘  └──────────┘  └──────────────────┘ │
│        │             │                                           │
│  ┌─────▼─────────────▼─────┐  ┌──────────┐  ┌──────────────┐   │
│  │     Call Detail          │  │  Evals   │  │  Settings    │   │
│  │  (transcript + results) │  │  (auto)  │  │  (+ MCP soon)│   │
│  └─────────────┬───────────┘  └────┬─────┘  └──────────────┘   │
│                │                    │                            │
│  ──────────────▼────────────────────▼──── React Frontend ────── │
│                         │                                        │
│  ═══════════════════════╪════════════════ API Boundary ═════════ │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │                  FastAPI Backend                           │   │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐  │   │
│  │  │ Call API │ │ Agent API│ │Stats API│ │  Eval Engine │  │   │
│  │  └────┬────┘ └──────────┘ └─────────┘ └──────┬───────┘  │   │
│  │       │                                       │           │   │
│  │  ┌────▼────────────────────────────────────────▼───────┐  │   │
│  │  │              Engine Layer                           │  │   │
│  │  │  State Machine → Data Recorder → Audit Logger      │  │   │
│  │  │  Compliance Validator → Eval Pipeline               │  │   │
│  │  └────────────────────┬───────────────────────────────┘  │   │
│  │                       │                                   │   │
│  │  ┌────────────────────▼───────────────────────────────┐  │   │
│  │  │   Event Store (SQLite) + PII Encryption            │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                        │
│  ═══════════════════════╪════════════ External Services ════════ │
│                         │                                        │
│  ┌──────────────────────▼─────────┐                             │
│  │         Vapi (Voice AI)        │                             │
│  │  Telephony + STT + TTS + LLM  │                             │
│  └────────────────────────────────┘                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Workstreams

### WS1: Backend Completion (Foundation)
Everything the frontend needs to function.

### WS2: React Frontend (Command Center)
The web application — 8 pages.

### WS3: Vapi Integration (Voice)
The AI assistant that actually makes calls.

### WS4: Eval Pipeline (Quality)
Automated quality checks on every call.

---

## Detailed Build Plan

### Phase A: Backend API Completion [WS1]
**Goal:** All API endpoints working, returning correct data.

#### A1. Align data model to actual Vetty workflow
The input/output fields must match the candidate intake form and Prashant's verification process.

**Call Initiation Input:**
```json
{
  "agent_type": "employment_verification",
  "phone_number": "+15551234567",
  "candidate": {
    "name": "John Smith"
  },
  "candidate_claims": {
    "employer_company_name": "Larkins Hospital",
    "position": "Phlebotomy Supervisor",
    "month_started": "September",
    "year_started": "2023",
    "is_self_employed": false,
    "still_work_here": false,
    "month_ended": "December",
    "year_ended": "2023",
    "company_address": "123 Main St",
    "city": "Tampa",
    "state": "FL",
    "zip_code": "33601"
  }
}
```

**Structured Result Output (per field):**
```json
{
  "verification_result": {
    "overall_status": "review_needed",
    "verified_by": "AI Agent v1",
    "verified_at": "2026-03-25T14:30:00Z",
    "call_duration_seconds": 154,
    "call_recording_url": "https://...",
    "call_outcome": "completed",
    "verifier_name": "Jane Doe (encrypted)",
    "verifier_title": "HR Manager",
    "fields": [
      {
        "field_name": "employer_company_name",
        "display_name": "Employer Company Name",
        "candidate_value": "Larkins Hospital",
        "verified_value": "Larkins Hospital",
        "status": "verified",
        "confidence": "high",
        "comments": "",
        "verbatim": "Yes, this is Larkins Hospital"
      },
      {
        "field_name": "position",
        "display_name": "Position",
        "candidate_value": "Phlebotomy Supervisor",
        "verified_value": "Associate",
        "status": "review_needed",
        "confidence": "high",
        "comments": "Title mismatch: candidate claimed Phlebotomy Supervisor, employer records show Associate",
        "verbatim": "She was listed as an associate in our system"
      }
    ]
  }
}
```

**Status auto-derivation rules (Apple to Apple):**
- Exact string match (case-insensitive) → `verified`
- Fuzzy match within tolerance (e.g., "Sept 2023" = "September 2023" = "09/2023") → `verified`
- Any real difference (even 1 day, even "tech" vs "technician") → `review_needed`
- Employer refused to answer / not asked → `unable_to_verify`
- Overall status = worst individual status (any `review_needed` → overall `review_needed`)

#### A2. New API endpoints

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `GET /api/agents` | GET | List all available agents (from YAML configs) | Must |
| `GET /api/agents/{id}` | GET | Agent detail (states, fields, description) | Must |
| `GET /api/calls/{id}/result` | GET | Structured verification result (side-by-side format) | Must |
| `GET /api/stats` | GET | Dashboard stats (total calls, success rate, avg duration) | Must |
| `GET /api/calls/{id}/evals` | GET | Eval results for a specific call | High |
| `GET /api/evals/summary` | GET | Aggregate eval scores across calls | High |

#### A3. Wire webhook → engine → result pipeline
- Vapi webhook events → State machine transitions
- Tool call events → Data recorder (field-by-field)
- End-of-call → Generate structured verification result
- End-of-call → Trigger eval pipeline
- All events → WebSocket broadcast to frontend

#### A4. Eval pipeline implementation
After each call completes, run:

**Code-based evals (instant, no LLM cost):**
1. `recorded_line_disclosure` — Did agent say "recorded line" in first 2 turns?
2. `completeness` — Were all required fields asked about?
3. `status_accuracy` — Is verified/review_needed correctly derived from values?
4. `format_validation` — Are dates in expected format? Are enums valid?

**LLM-based evals (async, ~$0.01/eval):**
5. `data_extraction_accuracy` — Does each `verified_value` match what the employer actually said in the transcript?
6. `no_hallucination` — Is every verified_value supported by the transcript?
7. `no_requestor_disclosure` — Did agent leak who's requesting the check?
8. `tone_professionalism` — Was the agent professional, especially after refusals?

Store results in `eval_results` table: `call_id, eval_name, passed (bool), details (json), evaluated_at`.

---

### Phase B: React Frontend [WS2]
**Goal:** 8-page command center web application.

**Tech stack:** React + TypeScript + Vite + Tailwind CSS + shadcn/ui

#### B1. Project setup & layout
- React app with routing (React Router)
- Sidebar navigation: Dashboard, Agents, Call History, Evals, API, Settings
- Top bar with Vetty branding
- Responsive layout (desktop-first, but not broken on tablet)

#### B2. Dashboard page (home)
- Summary cards: Total Calls, Success Rate, Active Calls, Avg Duration
- Recent calls table (last 10) with status badges
- "New Call" CTA button
- Data from `GET /api/stats` + `GET /api/calls?limit=10`

#### B3. New Call page
- **Step 1:** Agent type selector — cards for each agent (Employment, Education, etc.)
  - Data from `GET /api/agents`
  - Employment Verification card is active; Education shows "Coming Soon"
- **Step 2:** Dynamic form based on selected agent
  - For Employment Verification:

    | Field | Component | Required |
    |-------|-----------|----------|
    | Candidate Name | Text input | Yes |
    | Phone Number (employer's) | Phone input with formatting | Yes |
    | Employer Company Name | Text input | Yes |
    | Position / Title | Text input | Yes |
    | Month Started | Dropdown (Jan-Dec) | Yes |
    | Year Started | Dropdown (2015-2026) | Yes |
    | I am self-employed | Checkbox | No |
    | I still work here | Checkbox | No |
    | Month Ended | Dropdown (conditional) | If not "still work here" |
    | Year Ended | Dropdown (conditional) | If not "still work here" |
    | Company Address | Text input | No |
    | City | Text input | No |
    | State | Dropdown (US states) | No |
    | Zip Code | Text input (5-digit) | No |

  - **"Pre-fill Test Data" checkbox** at top — fills all fields with:
    - Candidate: "Kevin Strickland"
    - Employer: "Surgeon's Choice"
    - Position: "Surgical Technician"
    - Start: January 2021
    - End: December 2024
    - Address: "4521 Medical Center Blvd", Tampa, FL, 33612

- **"Place Call" button** → `POST /api/calls/initiate` → redirect to Call Detail page

#### B4. Call Detail page (the money page)
Three sections, updating in real-time via WebSocket:

**Section 1: Call Status Bar**
- Agent type, phone number, current state (e.g., "VERIFY_DATES")
- Duration timer
- Status indicator (In Progress / Completed / Failed)

**Section 2: Live Transcript**
- Scrolling transcript with speaker labels (Agent / Employer)
- Auto-scroll to bottom
- Timestamps on each message

**Section 3: Verification Results (side-by-side)**
- Table with columns: Field, Candidate Claimed, Employer Confirmed, Status, Comments
- Fields populate in real-time as the agent collects data
- Status badges: green "Verified", orange "Review Needed", gray "Unable to Verify", dimmed "Pending"
- Confidence indicators (high/medium/low)
- Overall status badge at top

**Post-call additions:**
- Call recording audio player (from Vapi recording URL)
- Eval results panel (passed/failed badges)
- Audit trail (expandable, chronological event list)
- "Download Report" button (JSON)

#### B5. Call History page
- Table: Date, Agent Type, Candidate, Company, Outcome, Duration, Overall Status
- Filters: agent type dropdown, date range picker, outcome filter
- Sort by date (newest first)
- Click row → navigate to Call Detail
- Pagination

#### B6. Agents page
- Cards for each agent type:
  - Employment Verification (active, green badge)
  - Education Verification (draft, gray badge)
  - Reference Check (coming soon, dimmed)
- Click card → shows read-only agent config:
  - Description, version, states (visual flow), data fields, compliance rules
- "Create New Agent" button → disabled with tooltip "Coming soon — currently configured via YAML"

#### B7. Evals page
- **Summary section:**
  - Overall pass rate (e.g., "94.2% — 47/50 calls passed all evals")
  - Per-category bar chart: Compliance, Data Accuracy, Completeness, Tone, Hallucination Check
  - Time range selector (7d / 30d / All)
- **Recent failures list:**
  - Call ID, eval name, failure reason, timestamp
  - Click → navigates to Call Detail with evals panel open
- **Trend chart:**
  - Line chart showing pass rate over time (weekly buckets)

#### B8. API Docs page
- Clean, Stripe-style documentation layout
- **Available endpoints** (with curl + Python + Node.js examples):
  - `POST /api/calls/initiate` — Place a verification call
  - `GET /api/calls/{id}` — Get call status
  - `GET /api/calls/{id}/result` — Get structured verification result
  - `GET /api/calls` — List calls with filters
  - `WS /api/ws/{session_id}` — Real-time call events
- **Authentication section** — API key in `X-API-Key` header
- **Webhook callbacks** — "Coming Soon" badge
  - "Register a URL to receive call completion notifications"
- **Batch API** — "Coming Soon" badge
  - "Upload CSV with multiple verifications, receive results via webhook"
- **MCP Server** — "Coming Soon" badge
  - "Connect Vetty Voice to any MCP-compatible AI assistant"

#### B9. Settings page
- API key display (masked, copy button)
- Webhook URL configuration (text input + test button) — "Coming Soon"
- MCP Server connection card — "Coming Soon"
  - One-liner: "Connect Vetty Voice to any MCP-compatible AI assistant for verification workflows"

---

### Phase C: Vapi Integration [WS3]
**Goal:** AI assistant that follows Prashant's exact workflow.

#### C1. Update system prompt with candidate details injection
- Template variables filled at call initiation time
- Include ALL candidate claims so agent can use confirm/deny approach

#### C2. Register tool calls in Vapi
The agent needs these tools to report data back during the call:

```json
[
  {
    "name": "record_data_point",
    "description": "Record a verified data point from the employer",
    "parameters": {
      "field_name": "string (e.g., 'position', 'month_started')",
      "value": "string (what the employer said)",
      "verbatim": "string (exact quote from employer)",
      "confidence": "high | medium | low"
    }
  },
  {
    "name": "record_discrepancy",
    "description": "Record when employer's info differs from candidate's claim",
    "parameters": {
      "field_name": "string",
      "candidate_value": "string",
      "employer_value": "string",
      "note": "string (e.g., 'staffing agency', 'subsidiary')"
    }
  },
  {
    "name": "record_redirect",
    "parameters": { "service_name": "string" }
  },
  {
    "name": "record_no_record",
    "parameters": { "details": "string" }
  },
  {
    "name": "end_verification",
    "description": "Call when all verification questions are complete",
    "parameters": { "outcome": "completed | refused | redirected | no_record | voicemail" }
  }
]
```

#### C3. Configure voice settings
- Professional female voice (warm but efficient)
- Speed: 1.0-1.2x
- Low temperature (0.3) for consistency
- Interruption handling configured

#### C4. Test call scenarios
Run through each scenario with a real phone:
1. Happy path — confirm everything
2. Title discrepancy
3. Date discrepancy (1 day off)
4. "We can only confirm dates and title"
5. "We use The Work Number"
6. "No record of that person"
7. Voicemail
8. Refusal / hostile
9. "Who's requesting this check?"

---

### Phase D: Integration & Polish [WS1+WS2+WS3]
**Goal:** Everything works end-to-end.

#### D1. End-to-end flow testing
- Place call from UI → phone rings → conversation → structured result on screen
- Verify WebSocket updates in real-time
- Verify eval pipeline runs post-call
- Verify call history populates

#### D2. Pre-fill test data
- Ensure test data is realistic and covers the demo scenario well
- Test with actual phone call to verify the agent handles the test data correctly

#### D3. Error states and edge cases
- What happens if Vapi is down? (Show error message, not crash)
- What if call drops mid-conversation? (Partial result with what was collected)
- What if webhook delivery fails? (Retry logic / graceful degradation)

#### D4. Visual polish
- Loading states for all async operations
- Empty states ("No calls yet — place your first call!")
- Consistent status badge colors across all pages
- Responsive sidebar collapse

---

## Build Order (Recommended)

```
Week 1:
├── Day 1-2: Phase A1-A2 (align data model, new endpoints)
├── Day 3-4: Phase B1-B3 (React setup, dashboard, new call form)
└── Day 5:   Phase C1-C2 (system prompt injection, tool registration)

Week 2:
├── Day 1-2: Phase A3 (webhook → engine wiring)
├── Day 3-4: Phase B4 (call detail page — transcript + results)
├── Day 5:   Phase C3-C4 (voice config, test calls)

Week 3:
├── Day 1:   Phase D1 (end-to-end testing)
├── Day 2:   Phase A4 (eval pipeline)
├── Day 3:   Phase B5-B6 (call history, agents page)
├── Day 4:   Phase B7 (evals page)
└── Day 5:   Phase B8-B9 + D4 (API docs, settings, polish)
```

**Critical path:** A1 → A2 → A3 → B4 → C1 → C2 → D1
Everything else can be parallelized or deferred.

---

## What's Explicitly NOT in MVP

| Item | Why Not |
|------|---------|
| User authentication / multi-tenancy | Hardcode single user for demo |
| Batch CSV upload (functional) | Mention on API page as "Coming Soon" |
| Agent creation UI | Show config read-only; creation via YAML |
| MCP server (functional) | Just the teaser card |
| Email verification channel | Voice only for MVP |
| Work Number / third-party integration | Record redirect, handle separately |
| Document verification | Outside scope — voice call only |
| PostgreSQL migration | SQLite is fine for demo |
| Production deployment (cloud) | Local + ngrok for demo |
| Mobile responsive design | Desktop-first; don't break on tablet |

---

## Success Criteria

The MVP is done when:

1. **Demo flow works:** Enter phone number → phone rings → AI conducts verification → structured result appears
2. **Side-by-side display:** Candidate claims vs employer responses with correct status badges
3. **Real-time transcript:** Updates as the call progresses
4. **Pre-fill test data:** One checkbox fills the form for instant demo
5. **Multiple agents visible:** Employment active, Education as "coming soon"
6. **Evals run automatically:** At least compliance + accuracy checks post-call
7. **API docs page exists:** Shows the API surface with code examples
8. **Call history works:** Previous calls listed and viewable

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Vapi latency makes calls feel unnatural | High | Tune voice speed, test extensively |
| AI goes off-script / hallucinates data | Critical | Low temperature, strong system prompt, eval pipeline catches it |
| WebSocket drops during live call | Medium | Reconnect logic, poll fallback |
| Transcript-to-data extraction inaccuracy | High | Verbatim field captures exact quote, LLM eval validates |
| Demo person gives unexpected responses | Medium | System prompt handles edge cases; eval shows how we catch issues |
| Vapi webhook delivery unreliable (ngrok) | Medium | Retry logic, manual testing before demos |

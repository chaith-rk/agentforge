# Product Requirements Document — Vetty Voice AI Platform

**Version:** 1.0
**Author:** Chaitanya Rajkumar
**Date:** 2026-03-14
**Status:** Draft

---

## 1. Executive Summary

The Vetty Voice AI Platform automates outbound employment verification phone calls — the single most time-intensive step in Vetty's background screening workflow. An AI voice agent follows Vetty's exact verification script, collects structured data, and produces audit-ready verification records.

The platform is designed as a **multi-agent system**: the employment verification agent is the first module, but the architecture supports education verification, reference checks, and other agent types through YAML configuration — no code changes required.

---

## 2. Problem Statement

### Current State
- Each employment verification requires a **manual outbound call** by a trained analyst
- Calls follow a **repeatable script** — confirm candidate-claimed details with the employer
- Average call duration: **3–5 minutes** of analyst time per verification
- Analysts spend significant time on **hold, voicemail, callbacks, and re-attempts**
- Manual data entry introduces **transcription errors** that require rework
- Verification calls are the **primary bottleneck** in the 4-day fulfillment cycle

### Impact
- High labor cost for a repetitive, scriptable process
- Analyst capacity is consumed by routine calls instead of complex exception cases
- Data quality issues from manual entry lead to downstream rework
- Scalability is limited by headcount

### Opportunity
The verification call is **highly structured** (confirm/deny against known data points), follows a **deterministic script**, and has **well-defined edge cases** — making it an ideal candidate for AI automation.

---

## 3. Solution Overview

An AI voice agent that:
1. **Initiates outbound calls** to employers via Vapi telephony
2. **Follows Vetty's verification script** (based on Operations Manager Prashant Singh's workflow)
3. **Confirms candidate details** using a confirm/deny approach (not open-ended questioning)
4. **Records structured data** for every field verified
5. **Handles edge cases**: third-party redirects, no record, limited policy, hostile verifiers
6. **Enforces compliance** at the infrastructure level (recorded line disclosure, never disclose requestor)
7. **Produces an audit-ready verification record** with full event history

---

## 4. User Personas

### Operations Analyst
- **Currently:** Spends 50%+ of time on routine verification calls
- **With platform:** Reviews AI-completed verifications, handles only exception cases
- **Key need:** Trust that the AI follows the correct script and records accurate data

### Operations Manager (Prashant Singh)
- **Currently:** Trains analysts on verification script, monitors quality
- **With platform:** Configures agent behavior via YAML, reviews call outcomes
- **Key need:** Confidence that the AI matches the quality of trained analysts

### Leadership / VP
- **Currently:** Wants to scale operations without proportional headcount growth
- **With platform:** Sees measurable ROI from automated verification calls
- **Key need:** Proof that this works, is secure, and scales

### Compliance / Legal
- **Currently:** Ensures FCRA compliance, recording consent, data protection
- **With platform:** Reviews threat model, audit trails, compliance checkpoints
- **Key need:** Immutable audit trail, PII protection, regulatory compliance

---

## 5. Functional Requirements

### 5.1 Call Flow

The agent follows a deterministic state machine with these states:

| State | Description | Data Collected |
|-------|-------------|----------------|
| GREETING | Open with recorded line disclosure, request authorized verifier | — |
| IDENTIFY_VERIFIER | Collect verifier name and title | verifier_name, verifier_title |
| VERIFY_COMPANY | Confirm company name matches claim | company_name_confirmed, match status |
| VERIFY_TITLE | Confirm job title matches claim | job_title_confirmed, match status |
| VERIFY_DATES | Confirm employment dates match claim | start/end dates, match status |
| VERIFY_EMPLOYMENT_STATUS | Confirm full-time/part-time/contract | employment_status |
| VERIFY_LOCATION | Confirm office/location | location_confirmed |
| VERIFY_REHIRE_ELIGIBILITY | Ask about rehire (most commonly refused) | eligible_for_rehire |
| CLOSING | Thank verifier, collect callback number | callback_number |

### 5.2 Edge Case States

| State | Trigger | Outcome |
|-------|---------|---------|
| RECORD_REDIRECT | Employer uses third-party service (TWN, Thomas & Co) | Record service name, end call |
| RECORD_NO_RECORD | Employer has no record of candidate | Confirm spelling, accept finding |
| RECORD_DEAD_END | Wrong number, business closed, disconnected | Record finding |
| LEAVE_VOICEMAIL | No answer | Leave standard voicemail |
| END_CALL_REFUSED | Verifier refuses or is hostile | Accept immediately, end call |

### 5.3 Compliance Requirements

| Rule | Enforcement | Level |
|------|-------------|-------|
| Recorded line disclosure | State machine blocks GREETING exit without it | BLOCK |
| Never disclose requesting party | Global compliance check on transcript | WARN |
| Accept refusal immediately | Global compliance check — no push-back | WARN |
| Record both values on discrepancy | Data recorder captures candidate + employer values | System |

### 5.4 API Requirements

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/calls/initiate` | POST | Trigger outbound verification call |
| `/api/calls/{id}` | GET | Get call status and collected data |
| `/api/calls/{id}/events` | GET | Get full audit event history |
| `/api/calls/{id}/record` | GET | Get final verification record |
| `/api/calls` | GET | List calls with pagination/filters |
| `/api/ws/{id}` | WS | Real-time call event stream |
| `/webhooks/vapi` | POST | Vapi webhook receiver |
| `/health` | GET | Health check |

---

## 6. Non-Functional Requirements

### 6.1 Security
- PII fields encrypted at rest (Fernet symmetric encryption)
- No PII in application logs (regex-based redaction)
- Webhook authentication (HMAC + shared secret)
- API key authentication on all client endpoints
- Non-root Docker container
- Secrets loaded from environment variables only
- Parameterized SQL queries (no string interpolation)

### 6.2 Scalability
- Async FastAPI backend handles concurrent calls
- Stateless request handling (state in database, not memory)
- Horizontally scalable — add instances behind a load balancer
- Event-sourced database allows read replicas

### 6.3 Auditability
- Every action recorded as immutable event
- Call state reconstructable from event replay
- Tamper-evident event log (append-only)
- Timestamped with actor attribution

### 6.4 Reliability
- Health check endpoint for monitoring
- Docker health checks with auto-restart
- Structured logging for observability
- Graceful error handling — calls fail safely

---

## 7. Data Requirements

| Field | Type | Required | PII Level | Notes |
|-------|------|----------|-----------|-------|
| verifier_name | string | yes | MEDIUM | Encrypted at rest |
| verifier_title | string | no | LOW | |
| company_name_confirmed | string | yes | LOW | |
| company_name_match | boolean | yes | NONE | |
| company_name_discrepancy_note | string | no | NONE | Subsidiary, rebrand, staffing |
| job_title_confirmed | string | yes | LOW | |
| job_title_match | boolean | yes | NONE | |
| start_date_confirmed | date | yes | MEDIUM | Encrypted at rest |
| start_date_match | boolean | yes | NONE | |
| end_date_confirmed | date | no | MEDIUM | Encrypted at rest |
| end_date_match | boolean | no | NONE | |
| currently_employed | boolean | yes | NONE | |
| employment_status | enum | no | NONE | full-time/part-time/contract |
| location_confirmed | string | no | LOW | |
| eligible_for_rehire | boolean | no | NONE | Most commonly refused |
| callback_number | string | no | MEDIUM | Encrypted at rest |
| third_party_redirect | string | no | NONE | |
| no_record | boolean | no | NONE | |
| call_outcome | enum | yes | NONE | |
| confidence | enum | yes | NONE | |

### The "Apple to Apple" Rule
Only exact matches across ALL fields = verified/clear. Any discrepancy, no matter how small (even one day), triggers "review needed." The voice agent records both versions; matching logic is downstream.

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Call completion rate (cooperative scenario) | >90% | Completed calls / total attempts |
| Data extraction accuracy | >85% | Correct field values / total fields |
| Recorded line disclosure compliance | 100% | Enforced by state machine |
| Limited policy handling | 100% | Red team testing |
| Redirect handling | 100% | Red team testing |
| No-record handling | 100% | Red team testing |
| Never discloses requesting party | 100% | Compliance validator |
| Never pushes after refusal | 100% | Compliance validator |
| Call duration | <3 minutes | Vapi call duration metric |
| New agent type configuration time | <1 day | Time to create and test YAML |

---

## 9. Constraints and Assumptions

### Constraints
- POC uses SQLite (migrate to PostgreSQL for production)
- Voice quality dependent on Vapi infrastructure
- LLM selection through Vapi (Claude or GPT-4)
- Manual steps upstream (DNC check, TWN lookup) and downstream (apple-to-apple matching) remain unchanged

### Assumptions
- Vapi provides sufficient voice quality for professional calls
- Employers will interact with AI agents similarly to human callers
- The confirm/deny approach constrains LLM behavior sufficiently
- State machine + compliance checkpoints prevent off-script behavior

---

## 10. Future Vision

### Near-Term (Post-POC)
- Education verification agent (YAML config)
- Reference check agent (YAML config)
- Integration with Vetty's case management system
- Production deployment on cloud infrastructure

### Medium-Term (Platform)
- Multi-channel orchestration (call + email + portal)
- Automated retry logic across channels
- TWN automated lookup integration
- Contact database auto-update after each call
- QA agent that scores every interaction

### Long-Term (AI Orchestration)
- End-to-end verification automation (intake → verification → report)
- Intelligent routing (which cases need humans vs AI)
- Cross-verification intelligence (patterns across cases)
- Self-improving prompts based on call outcome analysis

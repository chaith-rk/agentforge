# Threat Model — Vetty Voice AI Platform

**Version:** 1.0
**Date:** 2026-03-14
**Classification:** Internal — Confidential

---

## 1. Assets

| Asset | Description | Sensitivity |
|-------|-------------|-------------|
| Candidate PII | Names, employment dates, SSNs (upstream), phone numbers | **HIGH** |
| Employer PII | Verifier names, direct phone numbers | **MEDIUM** |
| Call Recordings | Audio of verification calls (stored by Vapi) | **HIGH** |
| Call Transcripts | Text transcripts of verification calls | **HIGH** |
| Verification Records | Structured output of completed verifications | **HIGH** |
| API Keys | Vapi API key, webhook secret, dashboard API key | **CRITICAL** |
| Encryption Keys | Fernet key for PII encryption at rest | **CRITICAL** |
| Agent Configurations | YAML configs defining agent behavior and compliance rules | **MEDIUM** |

---

## 2. Threat Actors

| Actor | Motivation | Capability |
|-------|-----------|------------|
| External attacker | Data theft, system disruption | Network-based attacks, API abuse |
| Social engineering caller | Extract information during calls | Manipulate AI agent via conversation |
| Malicious insider | Data exfiltration | Access to systems and data |
| Competitor | Industrial intelligence | Targeted attacks |

---

## 3. Attack Vectors and Mitigations

### 3.1 Webhook Spoofing
**Threat:** Attacker sends fake Vapi webhooks to inject false data or manipulate call state.

| Risk | Mitigation | Status |
|------|-----------|--------|
| Forged webhook payloads | HMAC-SHA256 signature validation | ✅ Implemented |
| Replay attacks | Timestamp validation (TODO) | 🔲 Planned |
| Shared secret compromise | Separate `x-vapi-secret` and Bearer token auth | ✅ Implemented |

### 3.2 API Abuse
**Threat:** Unauthorized access to call data, triggering unauthorized calls.

| Risk | Mitigation | Status |
|------|-----------|--------|
| Unauthenticated access | API key required on all `/api/` endpoints | ✅ Implemented |
| Brute-force API key | Rate limiting (60 req/min per client) | ✅ Implemented |
| Excessive call triggering | Vapi config validation before call initiation | ✅ Implemented |
| Missing Vapi credentials | 503 response with non-leaking error | ✅ Implemented |

### 3.3 PII Exfiltration
**Threat:** Sensitive personal data leaked through logs, API responses, or database access.

| Risk | Mitigation | Status |
|------|-----------|--------|
| PII in application logs | Regex-based PII redaction (SSN, phone, email patterns) | ✅ Implemented |
| PII in database at rest | Fernet encryption for MEDIUM/HIGH PII fields | ✅ Implemented |
| PII in error responses | Generic error messages to API consumers | ✅ Implemented |
| PII in version control | `.env` in `.gitignore`, no hardcoded secrets | ✅ Implemented |

### 3.4 Prompt Injection / Voice Agent Manipulation
**Threat:** Caller attempts to manipulate the AI agent into disclosing information or deviating from script.

| Risk | Mitigation | Status |
|------|-----------|--------|
| "Who requested this check?" | System prompt: refuse and redirect. Global compliance rule: `never_disclose_requestor` | ✅ Implemented |
| "What position are they applying for?" | Same as above | ✅ Implemented |
| Attempt to extract candidate details | Confirm/deny approach means agent reads back known data, not new data | ✅ By design |
| Jailbreak attempt on voice agent | Low LLM temperature (0.3), state machine constrains available actions | ✅ Implemented |
| Agent deviates from script | State machine enforces valid transitions only | ✅ Implemented |

### 3.5 Social Engineering During Calls
**Threat:** Verifier attempts to extract information the agent should not share.

| Risk | Mitigation | Status |
|------|-----------|--------|
| Verifier asks who the client is | Compliance rule blocks disclosure, scripted refusal response | ✅ Implemented |
| Verifier tries to get the agent to comment on discrepancies | System prompt: record both values without commenting | ✅ By design |
| Verifier pushes agent to share candidate documents | System prompt: agent has no access to documents | ✅ By design |

### 3.6 Data Tampering
**Threat:** Modification or deletion of verification records after the fact.

| Risk | Mitigation | Status |
|------|-----------|--------|
| Record modification | Event-sourced database: append-only, no UPDATE/DELETE | ✅ Implemented |
| Event deletion | Events table has no DELETE operations in code | ✅ By design |
| Database file tampering | File-level integrity (checksums in production) | 🔲 Planned |

### 3.7 Container / Infrastructure
**Threat:** Container breakout, privilege escalation.

| Risk | Mitigation | Status |
|------|-----------|--------|
| Root container execution | Non-root user (`vetty`) in Dockerfile | ✅ Implemented |
| Unnecessary packages | Multi-stage build, slim base image | ✅ Implemented |
| Container health | Docker HEALTHCHECK with auto-restart | ✅ Implemented |

---

## 4. OWASP Top 10 Mapping

| OWASP | Applicability | Mitigation |
|-------|--------------|-----------|
| A01: Broken Access Control | API endpoints require authentication | API key middleware |
| A02: Cryptographic Failures | PII stored in database | Fernet encryption at rest |
| A03: Injection | SQL queries, webhook payloads | Parameterized queries, Pydantic validation |
| A04: Insecure Design | Agent could be manipulated | State machine + compliance checkpoints |
| A05: Security Misconfiguration | Default settings, exposed endpoints | Secure defaults, env-based config |
| A06: Vulnerable Components | Third-party dependencies | Pinned versions, security linting (ruff S rules) |
| A07: Auth Failures | API and webhook access | API key + HMAC + shared secret |
| A08: Data Integrity Failures | Verification data tampering | Event sourcing (append-only) |
| A09: Logging Failures | Insufficient audit trail | Every event logged with timestamp and actor |
| A10: SSRF | Outbound calls to arbitrary numbers | Vapi config validation, operator-initiated only |

---

## 5. Compliance Considerations

### FCRA (Fair Credit Reporting Act)
- Vetty operates as a Consumer Reporting Agency (CRA)
- Verification records must be accurate and complete
- Consumers have the right to dispute inaccurate information
- **Platform support:** Immutable event log provides evidence trail. Both candidate and employer versions of disputed data are recorded.

### State Recording Consent Laws
- Different states have different consent requirements for call recording
- "Recorded line" disclosure in greeting addresses most requirements
- **Platform support:** State machine BLOCKS conversation advancement without recorded line disclosure. This is enforced at the infrastructure level.
- **TODO:** Add state-specific consent logic for two-party consent states

### Data Retention
- Verification records must be retained per FCRA requirements
- Event store provides complete, immutable history
- **TODO:** Implement configurable retention policies with compliant deletion (when legally required)

---

## 6. PII Data Flow Diagram

```
                    ┌──────────────────────────────┐
                    │     CALL INITIATION           │
                    │                              │
                    │  Candidate PII enters via     │
                    │  POST /api/calls/initiate     │
                    │  (subject_name, company,      │
                    │   dates, title, phone)        │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     SYSTEM PROMPT             │
                    │                              │
                    │  PII interpolated into        │
                    │  prompt template              │
                    │  Sent to Vapi (in-memory)     │
                    │  NOT stored by our backend    │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     VAPI (External)           │
                    │                              │
                    │  PII in LLM context during    │
                    │  call (Vapi's responsibility)  │
                    │  Call recording stored by Vapi │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     WEBHOOK EVENTS            │
                    │                              │
                    │  Collected data arrives via    │
                    │  tool-calls webhooks          │
                    │  Validated, then stored        │
                    └──────────────┬───────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
    ┌─────────▼──────────┐ ┌──────▼───────┐ ┌──────────▼──────────┐
    │   EVENT STORE       │ │  APP LOGS    │ │  WEBSOCKET           │
    │                    │ │              │ │  (Dashboard)          │
    │  MEDIUM/HIGH PII   │ │  PII         │ │                      │
    │  → Fernet encrypted │ │  REDACTED    │ │  PII sent to         │
    │                    │ │  (regex)     │ │  authenticated        │
    │  LOW/NONE PII      │ │              │ │  clients only         │
    │  → stored plaintext │ │              │ │                      │
    └────────────────────┘ └──────────────┘ └──────────────────────┘
```

---

## 7. Recommendations for Production

| Priority | Action | Effort |
|----------|--------|--------|
| HIGH | Migrate to PostgreSQL with row-level encryption | Medium |
| HIGH | Add webhook replay attack protection (timestamp + nonce) | Low |
| HIGH | Implement TLS certificate pinning for Vapi API calls | Low |
| MEDIUM | Add state-specific recording consent logic | Medium |
| MEDIUM | Redis-backed rate limiting | Low |
| MEDIUM | Database file integrity monitoring | Medium |
| LOW | Penetration testing by third party | External |
| LOW | SOC 2 Type II audit preparation | High |

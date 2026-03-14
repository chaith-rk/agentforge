# Leadership Presentation Outline — Vetty Voice AI Platform

**Purpose:** Secure budget approval and time allocation for the Voice AI Platform.
**Audience:** Manager (security/compliance-focused), DevOps, Engineering leadership
**Duration:** 15–20 minutes + 5 min live demo

---

## Slide 1: The Problem — What Verification Costs Us Today

### Talking Points
- "Every employment verification requires a manual outbound call"
- Quantify: X calls/day × 3–5 min/call = Y analyst-hours/month
- Cost: Y hours × analyst hourly rate = $Z/month
- Error rate: manual data entry introduces discrepancies → rework
- Bottleneck: verification calls are the #1 delay in our fulfillment cycle

### Data to Gather Before Presentation
- [ ] Average daily verification call volume (ask Prashant)
- [ ] Average call duration
- [ ] Analyst hourly cost (fully loaded)
- [ ] Current error/rework rate
- [ ] Average time-to-fulfillment

### Key Message
> "We're spending $[X] per month on a repetitive, scriptable process. Every hour an analyst spends on a routine call is an hour they're NOT spending on complex cases that need human judgment."

---

## Slide 2: The Solution — AI Voice Agent

### Talking Points
- AI agent follows Prashant's exact verification script
- Confirm/deny approach — reads back candidate details, employer confirms
- Not replacing analysts — augmenting. AI handles routine, humans handle exceptions
- Every call produces a structured verification record with full audit trail

### Visual
- Side-by-side: Manual Process vs. AI-Assisted Process

### Key Message
> "The AI follows the same script our best analysts use. It doesn't improvise. It doesn't skip steps. It produces cleaner data because it records exactly what the employer says."

---

## Slide 3: LIVE DEMO

### Setup
- Dashboard open on screen
- Pre-fill test candidate data (fictional, no real PII)
- Trigger call to your phone or a colleague playing the employer

### What They See
1. Call initiated from dashboard
2. Real-time transcript streaming
3. State machine — current step highlighted
4. Data fields populating as employer confirms
5. Compliance checkpoints passing (green indicators)
6. Final verification record generated

### Backup
- Pre-recorded 2-min video of a successful call in case of technical issues

### Key Message
> "The transcript, data extraction, compliance checks — all automatic. The agent flagged the date discrepancy and produced an audit-ready record."

---

## Slide 4: Architecture — Why This Isn't a Toy

### Talking Points
- Config-driven: each agent type is a YAML file
- Event-sourced database: immutable audit trail
- State machine with compliance checkpoints: agent cannot skip required steps
- PII encrypted at rest, never in logs
- Async architecture: handles concurrent calls

### For the Manager Specifically
- "I've documented a full threat model"
- "Every state transition is timestamped and immutable"
- "The agent cannot advance past the greeting without the recorded line disclosure — enforced by the state machine, not just the prompt"

### Key Message
> "Security, audit trail, and compliance are foundational — not afterthoughts."

---

## Slide 5: The Platform Play — Why This Scales

### Talking Points
- Employment verification is Agent #1
- Education verification, reference checks — each is a YAML config file
- Show two YAML files side by side
- "Agent #1: 2 weeks. Agent #2: 2 days. Agent #3: 2 days."

### Key Message
> "We're building a platform. Every verification type can become an agent. The marginal cost of each new type drops dramatically."

---

## Slide 6: Security & Compliance

### Talking Points
- Walk through the threat model (hand out document)
- PII handling: field-level encryption, no PII in logs
- FCRA: recorded line disclosure enforced, full audit trail
- Webhook security: HMAC + shared secret
- OWASP Top 10 addressed

### Key Message
> "I built this assuming a compliance auditor would review every decision. Here's the threat model."

---

## Slide 7: The Ask

### Budget

| Item | Monthly Cost |
|------|-------------|
| Vapi (voice AI platform) | ~$50–100 |
| Phone number | ~$3–5 |
| Cloud hosting (post-POC) | ~$30–50 |
| **Total** | **~$85–155/mo** |

### Time Allocation
- X% of your time for 4–6 weeks
- Occasional input from Prashant for workflow validation
- DevOps: 2–3 hours for production deployment review

### ROI Projection
- X calls/day automated × Y min saved = Z hours/month
- At analyst cost → $B/month savings
- Break-even: month one

### Key Message
> "For less than $200/month, we can start automating our highest-volume verification type."

---

## Slide 8: Roadmap

| Phase | Timeline | Deliverable |
|-------|----------|------------|
| Foundation | Weeks 1–2 ✅ | Architecture, configs, backend |
| Working Agent | Weeks 2–4 | Live calls, data extraction |
| Dashboard | Weeks 4–5 | Real-time monitoring |
| Red-Teaming | Weeks 5–6 | Edge case validation |
| Platform Demo | Week 6 | Second agent type |

### Post-POC (If Approved)
- Production deployment
- Education + reference check agents
- Integration with Vetty's systems
- Multi-channel orchestration

---

## Appendix: Objection Handling

| Objection | Response |
|-----------|----------|
| "What about PII/security?" | Hand them the threat model. PII encrypted, no PII in logs, HMAC webhooks, non-root container. |
| "What if the AI says something wrong?" | State machine constrains behavior. Compliance checkpoints enforce rules. Every call recorded and auditable. |
| "Can this scale?" | Async architecture, stateless backend, horizontally scalable. |
| "Why not use an existing tool?" | Built on Prashant's actual workflow with our compliance requirements baked in. |
| "What if Vapi changes pricing?" | Voice provider is one integration layer. Swapping providers doesn't rebuild the system. |
| "You're a PM, can you maintain this?" | Industry-standard patterns. Every decision documented in ADRs. Any Python engineer can extend it. |

---

## Pre-Presentation Checklist

- [ ] Gather call volume and cost data from Prashant
- [ ] Calculate ROI with real numbers
- [ ] Prepare fictional test data for demo (no real PII)
- [ ] Dry run the live demo
- [ ] Print threat model for manager
- [ ] Record backup video of successful call
- [ ] Have architecture diagram as fallback if demo fails

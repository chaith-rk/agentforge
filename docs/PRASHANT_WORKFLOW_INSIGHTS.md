# Prashant Singh — Employment Verification Workflow Insights

**Source:** Recorded walkthrough session with Prashant Singh (Operations Manager)
**Transcript:** `/tmp/prashant_employment_verification.txt`
**Date:** Pre-2026-03-14

---

## Standard Call Script

**Opening (exact wording):**
> "Hi, my name is Prashant. I'm calling from Vetty on a recorded line. This call is regarding employment verification of [candidate name]. May I speak to an authorized person who can verify employment?"

**Key elements that MUST be included:**
1. Agent name
2. "From Vetty"
3. "On a recorded line" (legal requirement)
4. Candidate name
5. Request for authorized person

---

## Verification Workflow (Decision Tree)

```
1. Check client instructions (e.g., University of Miami has specific rules)
2. Check "Permission to Contact" flag
   ├── If NO → Cannot contact employer directly
   │   └── Check third-party options (Work Number, etc.)
   └── If YES → Proceed with contact
3. Check Work Number (search by company name, verify spelling via Google)
   ├── If listed → Run Work Number (uses SSN)
   └── If not listed → Continue to next step
4. Check Vetty's internal Contact Database (Google Sheet)
   ├── If found → Use stored email/phone, fulfillment method noted
   └── If not found → Google search for contact info
5. Google search for employer contact info
   └── Look for: main phone, HR number, payroll number, website contact
6. Call + Email employer (parallel attempts)
   └── Repeat for 4 days (Day 1 through Day 4)
7. If no response after 4 days → Fall back to candidate-provided documents
```

---

## The "Apple to Apple" Rule (CRITICAL)

**This is the single most important business rule:**

- A field is **"Verified"** ONLY if the employer's answer is an **exact match** to the candidate's claim
- Even **one day difference** in dates → "Review Needed"
- Even **slight title variations** (e.g., "surgical tech" vs "surgical tech supervisor") → "Review Needed"
- The entire file can only go **"Clear"** if ALL fields are marked "Verified" — which Prashant says is **rare**
- The voice agent's job is to **record exactly what the employer says** — the comparison/matching is downstream

---

## Status Definitions

| Status | When Applied |
|--------|-------------|
| **Verified** | Employer's answer is an exact (apple-to-apple) match to candidate's claim |
| **Review Needed** | Any discrepancy, however small. Also: all document-based verifications |
| **Unable to Verify** | Employer refuses to share, or field was not asked |

---

## Key Scenarios from Prashant

### 1. Third-Party Redirect
- Employer says "We use The Work Number / Thomas & Company / CCC Verify"
- Record the service name, end call
- Run the third-party service separately (not part of voice call)

### 2. Staffing Agency Mismatch
- Candidate says "Surgeon's Choice" but Work Number returns "TriNet" (staffing agency)
- If dates match the employment period → mark as Verified
- Add comment: "Verification obtained through [staffing agency name] (staffing agency)"
- **Cannot verify the staffing relationship** — accepted as-is

### 3. Subsidiary / Parent Company
- Employer says "verification is handled at parent company level"
- Verify affiliation on Google before accepting
- If affiliation confirmed → mark as Verified with note
- If NO affiliation found → do NOT accept the verification

### 4. Document Fallback
- Documents are ALWAYS secondary to source verification
- Even if documents arrive on Day 1, continue attempting source verification for 4 days
- If source verification arrives later, it **supersedes** the document
- Documents that meet criteria: candidate name, entity name, dates, on letterhead
- ALL document-based verifications marked as **"Review Needed"** (never "Verified")
- Canned note: "Despite numerous attempts, the company remained unresponsive. Verification has been updated based on the candidate-provided [document type]."
- Documents are considered potentially fake — Vetty has no authority to verify authenticity

### 5. Currently Employed Discrepancy
- Candidate says "I still work here = No" but employer/TWN says "ACTIVE"
- Mark as "Review Needed"
- If TWN shows active in current month, can be assumed as proper (edge case)

### 6. DNC (Do Not Contact)
- If Permission to Contact = No AND no third-party available
- Email candidate for documents immediately
- Still attempt third-party verification if fee approved

### 7. Fee Approval for Third-Party Services
- Each client has instructions (some have "blanket fee approval")
- Without blanket approval → email client using HubSpot template
- Template includes: candidate name, check type, amount, third-party name, employer name
- Wait for client approval before running paid service

---

## Contact Rules

- **Phone:** Only call numbers published on Google that indicate they belong to the company
- **Email:** Only email professional addresses (company domain). Never Gmail, Yahoo, Apple, etc.
- **On recorded line:** If someone asks for candidate details to verify against, Prashant provides them (since email-based verification already provides this info)

---

## Post-Call Documentation

### Canned Notes (Standardized Client-Facing)
Each scenario has a standardized note template:

| Scenario | Note Template |
|----------|--------------|
| Source verified, all match | (Standard close, fields marked Verified) |
| Source verified, discrepancy | Fields with discrepancies marked Review Needed |
| Unresponsive + document | "Despite numerous attempts, the company remained unresponsive. Verification updated based on candidate-provided [document type]." |
| Third-party (Work Number) | "Verification obtained through online source [The Work Number]." |
| Staffing agency via TWN | "Verification obtained through online source [TWN]. [Staffing Co] (staffing agency)." |
| Parent company via TWN | "Verification obtained through online source [TWN]. [Parent Co]." |
| Document missing criteria | Note which criteria not met (e.g., "document is not dated") |

### Attachments
- **Email verification:** Attach the email
- **Phone verification:** No attachment (recording is backup for disputes)
- **Work Number:** Attach the report
- **Candidate documents:** Attach in additional documents section

---

## Quality Management
- Prashant designed a QMS to audit recordings
- Can audit files to check if process was followed
- Researchers can be penalized for not following protocol
- Recording serves as backup evidence for disputes

---

## Implications for AI Voice Agent

1. **Agent only handles the phone call portion** — not TWN, not email, not documents
2. **Agent must record verbatim** what the employer says — matching logic is separate
3. **"On a recorded line" is non-negotiable** — must be in first utterance
4. **Never volunteer candidate details upfront** — use confirm/deny approach
5. **If asked for details to verify against** — it's acceptable to provide (mirrors email workflow)
6. **Accept refusals immediately** — especially rehire eligibility
7. **Confidence scoring** should reflect clarity of response:
   - "Yes, she was here from September 2023" → high confidence
   - "I think so, around that time" → medium confidence
   - "I'm not sure, you'd have to check with HR" → low confidence

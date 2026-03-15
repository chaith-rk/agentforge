# Vapi Setup (Vetty Voice Platform)

This guide configures Vapi for this repository and validates the local webhook.

## 1. Local environment

From the project root:

```bash
cp .env.example .env
```

Set these values in `.env`:

```bash
VAPI_API_KEY=<your_vapi_private_key>
VAPI_WEBHOOK_SECRET=<shared_secret_for_webhooks_or_leave_blank>
VAPI_ASSISTANT_ID=<asst_xxx>
VAPI_PHONE_NUMBER_ID=<pn_xxx>
```

Notes:
- `VAPI_API_KEY` must be your **private** key (server-side).
- `VAPI_WEBHOOK_SECRET` is optional for local testing. If it is blank, leave
  Vapi server auth off.
- If you change `.env`, restart the app so the running process reloads the
  updated settings.

## 2. Run app + tunnel

Terminal 1:

```bash
uvicorn src.main:app --reload --port 8000
```

Terminal 2:

```bash
ngrok http 8000
```

Copy your HTTPS URL from ngrok (example: `https://abc123.ngrok-free.app`).

Your webhook URL will be:

```text
https://abc123.ngrok-free.app/webhooks/vapi
```

## 3. Configure webhook auth in Vapi

Only do this if `VAPI_WEBHOOK_SECRET` is non-empty.

In Vapi dashboard:

1. Open the area where Vapi manages custom/server credentials.
2. Create a credential for server URL auth.
3. Choose one of these auth options:
   - Shared secret header: `x-vapi-secret`
   - Bearer token header: `Authorization: Bearer <secret>`
4. Use the exact same secret value as `VAPI_WEBHOOK_SECRET` in `.env`.
5. Save it and attach it to the assistant server settings.

Compatibility in this backend:
- Accepts `x-vapi-signature` (legacy HMAC), `x-vapi-secret`, or `Authorization: Bearer ...`.

If `VAPI_WEBHOOK_SECRET` is blank:
- Leave Vapi auth as `No authentication`
- Do not attach a credential

## 4. Configure assistant server URL

In Vapi dashboard:

1. Open your target assistant.
2. Go to the assistant's messaging/server settings.
3. Set `Server URL` to:
   - `https://<your-ngrok-domain>/webhooks/vapi`
4. Attach the credential from step 3 only if webhook auth is enabled.
5. Save assistant.

Important:
- The live script, persona, `firstMessage`, and voicemail message come from the
  Vapi assistant you select here.
- This backend currently does not serve the prompt dynamically; it only starts
  a call with an assistant ID and processes the resulting webhooks.

## 5. Enable server messages/events

Ensure assistant server messages include at least:
- `assistant-request`
- `status-update`
- `speech-update`
- `transcript`
- `end-of-call-report`
- `function-call` (legacy)
- `tool-calls` (current)

This backend handles both `function-call` and `tool-calls`.

## 6. Add assistant functions

Add these tool/function names in Vapi assistant so webhooks map correctly:
- `record_data_point`
- `record_redirect`
- `record_no_record`
- `record_discrepancy`
- `mark_state_transition`

## 7. Validate webhook connectivity

Run this local check:

```bash
curl -i http://localhost:8000/health
```

Expected: `200 OK` with a JSON status payload.

Once Vapi is configured, initiate a call and verify logs include:
- `vapi_webhook_received`

If you see `Invalid webhook authentication`:
- re-check secret value in both Vapi credential and `.env`
- ensure assistant is attached to the correct credential
- if you recently changed `.env`, restart `uvicorn`
- confirm ngrok URL is current (it changes each run unless reserved)

## 8. Trigger call from this backend

Call the local endpoint:

```bash
curl -X POST http://localhost:8000/api/calls/initiate \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "agent_config_id": "employment_verification_v1",
    "subject_name": "Jane Doe",
    "company_name": "Acme Inc",
    "company_phone": "+15551234567",
    "company_address": "123 Main St",
    "job_title": "Software Engineer",
    "start_date": "2022-01-01",
    "end_date": "",
    "employment_status": "full-time",
    "currently_employed": true
  }'
```

Expected response:
- `status: initiated`
- non-empty `vapi_call_id`

Optional:
- Include `"assistant_id": "<vapi_assistant_id>"` in the request body to override
  `VAPI_ASSISTANT_ID` for a single call without editing `.env`.
- Use this for one-off demo assistants so you do not have to keep swapping the
  default assistant in `.env`.

## Security

- Never commit `.env`.
- Rotate private keys if they were shared in plain text.
- Restrict key scope in Vapi (assistants/origins) where possible.

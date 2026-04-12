# Production Runbook — AgentForge Platform

**Audience:** you (Chaitanya). This doc is the single source for deploying,
operating, and debugging the platform in production. Ignore stale bits in
`docs/PROGRESS.md` — this file is authoritative for prod.

---

## 0. One-time deploy (get to first prod call)

Do these in order. Each step should take ~5 min.

### 0.1 Generate prod secrets

You need three secrets. Generate them locally, store in a password manager
labeled "AgentForge prod", and do **not** commit them anywhere.

```bash
# PII encryption key (Fernet format) — LOSING THIS MAKES ENCRYPTED DATA UNRECOVERABLE
venv/bin/python -c "from cryptography.fernet import Fernet; print('PII_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Dashboard API key
venv/bin/python -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"

# Vapi webhook HMAC secret (must also be set in Vapi dashboard)
venv/bin/python -c "import secrets; print('VAPI_WEBHOOK_SECRET=' + secrets.token_urlsafe(32))"
```

Store all three in a password manager immediately. The `PII_ENCRYPTION_KEY`
in particular: if you lose it, every encrypted field in the event store
becomes unrecoverable and there is no recovery path.

You also need two values from the Vapi dashboard (https://dashboard.vapi.ai):

- `VAPI_API_KEY` — under **API Keys**
- `VAPI_PHONE_NUMBER_ID` — under **Phone Numbers**, the UUID of your number

### 0.2 Railway backend deploy

1. Railway dashboard → your project. If there is no service yet (empty
   project with only project-level Variables), click **+ New** →
   **GitHub Repo** → select `chaith-rk/agentforge-platform`. Railway
   reads `railway.json` and starts a Dockerfile build. The first build
   may crash on startup — that's expected, env vars aren't set yet.

2. Service → **Settings** → **Networking** → **Generate Domain**.
   Note the domain (e.g. `agentforge-production-abc.up.railway.app`) —
   you'll need it in steps below and in the Vercel deploy.

3. Service → **Variables** tab. Paste this block. Substitute the three
   generated secrets from §0.1, the two Vapi values from the Vapi
   dashboard, and `<railway-backend-domain>` from step 2:

   ```
   ENVIRONMENT=production
   LOG_LEVEL=INFO

   # From §0.1 (paste from your password manager)
   PII_ENCRYPTION_KEY=<generated Fernet key>
   API_KEY=<generated token>
   VAPI_WEBHOOK_SECRET=<generated token>

   # From the Vapi dashboard (https://dashboard.vapi.ai)
   VAPI_API_KEY=<paste from Vapi dashboard → API Keys>
   VAPI_PHONE_NUMBER_ID=<paste from Vapi dashboard → Phone Numbers>
   VAPI_SERVER_URL=https://<railway-backend-domain>/webhooks/vapi

   # Database — must point at the volume mount (see step 0.3 below)
   DATABASE_PATH=/app/data/calls.db

   # CORS — start permissive, lock down in §0.4 once Vercel is deployed
   CORS_ORIGINS=["http://localhost:5173"]
   ```

   Notes:
   - `CORS_ORIGINS` must be valid JSON (brackets + quoted strings).
     A malformed value will crash the app on startup.
   - `VAPI_SERVER_URL` is a convenience reference only — the backend
     does not call this URL. What matters is that Vapi is configured
     to call `https://<railway-backend-domain>/webhooks/vapi`.

4. Service → **Settings** → **Volumes** → **+ New Volume**:
   - Mount path: `/app/data`
   - Size: 1 GB is plenty for MVP
   - This is **critical** — without a volume, SQLite data is wiped on
     every deploy. The app will silently start with an empty DB and
     there is no recovery.

5. Redeploy the service (Deployments tab → three-dot menu → Redeploy).
   Wait for the deploy to show green/Active.

6. Verify:

   ```bash
   curl https://<railway-domain>/health
   # expect: {"status":"healthy","version":"0.1.0","active_calls":"0"}

   curl https://<railway-domain>/api/agents
   # expect: 503 (API key not configured in request)

   curl -H "X-API-Key: <your API_KEY>" https://<railway-domain>/api/agents
   # expect: JSON list including employment_verification_v1
   ```

### 0.3 Vercel frontend deploy

1. Vercel → **Add New Project** → import the GitHub repo.
2. **Root directory**: `frontend`
3. **Framework**: Vite (auto-detected)
4. **Build command**: `npm run build` (default)
5. **Output directory**: `dist` (default)
6. **Environment variables**:
   ```
   VITE_API_BASE=https://<railway-domain>/api
   VITE_WS_HOST=<railway-domain>
   VITE_API_KEY=<your API_KEY — same value as in Railway>
   ```
   Note: `VITE_WS_HOST` is the host **without** scheme — the frontend
   picks `wss://` automatically since the page is served over HTTPS.
7. Deploy.
8. Note the Vercel domain (e.g. `agentforge.vercel.app`).

### 0.4 Update Railway CORS + Vapi server URL

1. Railway → Variables → update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=["https://<vercel-domain>"]
   ```
2. Railway → Variables → update `VAPI_SERVER_URL`:
   ```
   VAPI_SERVER_URL=https://<railway-domain>/webhooks/vapi
   ```
3. Railway: redeploy (env var changes trigger this automatically).
4. Vapi dashboard → your assistant (if using dashboard assistant) →
   **Server URL** → set to `https://<railway-domain>/webhooks/vapi`.
   Also set **Secret** to the same value as `VAPI_WEBHOOK_SECRET` so
   Vapi signs webhooks with it.

### 0.5 First prod smoke test

1. Open `https://<vercel-domain>` — the dashboard should load.
2. New Call → fill in a candidate record, use **your own phone number**
   as the phone number for the first test.
3. Expect:
   - Call connects within ~5 sec
   - Live transcript streams into the dashboard
   - Tool calls populate the verification results table as the AI
     records data points
   - On hangup, the verification record finalizes and is downloadable

If any of those fail, see **Troubleshooting** below before debugging blind.

---

## 1. Environment variable reference

### Backend (Railway)

| Var | Required? | Purpose |
|---|---|---|
| `ENVIRONMENT` | yes in prod | Must be `production` — toggles fail-closed auth. |
| `VAPI_API_KEY` | yes | From Vapi dashboard → API Keys. |
| `VAPI_PHONE_NUMBER_ID` | yes | From Vapi dashboard → Phone Numbers. |
| `VAPI_WEBHOOK_SECRET` | yes in prod | HMAC secret. Must match what Vapi sends. If unset in prod, webhooks return 503. |
| `VAPI_SERVER_URL` | optional | Reference only; the backend doesn't call this. |
| `API_KEY` | yes in prod | Dashboard API key. If unset in prod, `/api/*` returns 503. |
| `PII_ENCRYPTION_KEY` | yes | Fernet key for encrypted fields. **Losing this = losing encrypted data.** |
| `DATABASE_PATH` | yes in prod | Point at the volume mount, e.g. `/app/data/calls.db`. |
| `CORS_ORIGINS` | yes in prod | JSON array of allowed frontend origins. |
| `LOG_LEVEL` | optional | Default `INFO`. Set to `DEBUG` temporarily when debugging. |

### Frontend (Vercel)

| Var | Required? | Purpose |
|---|---|---|
| `VITE_API_BASE` | yes | Full backend API URL, e.g. `https://backend.railway.app/api`. |
| `VITE_WS_HOST` | yes | Backend host without scheme, e.g. `backend.railway.app`. |
| `VITE_API_KEY` | yes | Must match backend `API_KEY`. |

---

## 2. Common ops

### End a stuck call

If a call shows "in progress" but is actually dead:

```bash
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  https://<railway-domain>/api/calls/<session_id>/stop
```

This calls Vapi's `DELETE /call/<id>`, which ends the call on their side.
The `end-of-call-report` webhook will arrive shortly and finalize the record.

If Vapi rejects (e.g. the call already ended on their side), the session
will remain in memory until the backend restarts. This is cosmetic.

### Read a call's full audit trail

```bash
curl -H "X-API-Key: $API_KEY" \
  https://<railway-domain>/api/calls/<session_id>/events
```

Returns every event in append-only order. This is the ground truth for
"what actually happened" on a call.

### Download a verification report

Use the "Download Report" button on the Call Detail page, or:

```bash
curl -H "X-API-Key: $API_KEY" \
  https://<railway-domain>/api/calls/<session_id>/result
```

### Rotate API key

1. Generate new: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Railway → update `API_KEY`
3. Vercel → update `VITE_API_KEY`
4. Redeploy both.
5. Old key is dead immediately.

### Rotate webhook secret

1. Generate new: same as above
2. Railway → update `VAPI_WEBHOOK_SECRET`
3. Vapi dashboard → update Secret
4. Redeploy Railway.
5. Briefly, in-flight calls may get 401s on webhooks — tolerable for MVP.

### **Do not rotate `PII_ENCRYPTION_KEY`.** Rotating it invalidates all existing encrypted PII in the event store. If you must rotate, you need a key-rotation migration that decrypts with the old key and re-encrypts with the new — not implemented yet.

### Back up the Railway volume

Railway dashboard → service → Volumes → snapshot. Do this weekly until
Postgres migration happens. There's no retention policy; it's on you.

### Tail logs

Railway dashboard → service → Logs. They are structured JSON
(via structlog). For a specific session:

```
# In Railway log search:
session_id "abc-123"
```

---

## 3. Known limitations / things to migrate next

- **SQLite, not Postgres.** Fine for MVP, low volume. Migrate when you
  start seeing concurrent write contention or want cross-region reads.
- **In-memory rate limiter.** Resets on every deploy. Replace with Redis
  when you have real traffic.
- **No Sentry / error tracking.** Add `sentry-sdk[fastapi]` when you want
  error aggregation.
- **Active call registry is in-process.** A restart drops active calls'
  in-memory state (transcript is preserved in the event store, but the
  active state machine is not). For MVP this means: **don't redeploy
  during a live call.** Check `/health` → `active_calls` first.
- **LLM evals are stubs.** Only code-based evals run today.

---

## 4. Troubleshooting

### Symptom: `/health` returns 200 but `/api/agents` returns 503

You forgot `API_KEY` in Railway. Add it, redeploy.

### Symptom: Webhooks return 401 in Railway logs

Either Vapi is signing with a different secret than `VAPI_WEBHOOK_SECRET`
or Vapi isn't signing at all. Check the Vapi assistant's Server URL
secret matches Railway.

### Symptom: Webhooks return 503 in Railway logs

`VAPI_WEBHOOK_SECRET` is not set and `ENVIRONMENT=production`. This is the
fail-closed guard. Set the secret.

### Symptom: Call connects but no transcript appears in the dashboard

- Check browser devtools → Network → WS: is the WebSocket connection
  established? If not, `VITE_WS_HOST` is wrong.
- Check Railway logs for `websocket_broadcast_failed` — means the
  session exists but no WS clients are connected for it.
- Confirm `VAPI_SERVER_URL` in Railway and the Vapi dashboard point at
  Railway, not localhost or ngrok.

### Symptom: Call completes but verification results table is empty

Tool calls aren't being parsed. Check Railway logs for
`data_point_persisted` events. If none appear, the AI never emitted
`record_data_point` tool calls — likely a prompt issue, not infra.

### Symptom: After a deploy, call history is empty

Railway volume was not mounted or `DATABASE_PATH` doesn't point at it.
Add/verify the volume, set `DATABASE_PATH=/app/data/calls.db`, redeploy.
The history is gone — there's no undo unless you have a snapshot.

### Symptom: CORS error in the browser console

`CORS_ORIGINS` in Railway doesn't include your Vercel domain. It must
be valid JSON: `["https://agentforge.vercel.app"]`.

---

## 5. Red-team scenarios (to run before real candidates)

11 scenarios live in `tests/red_team/`. Run them once deploy is stable,
ideally against a staging deploy before prod. Not automated today; each
is a scripted conversation you dial yourself.

---

## 6. Quick reference: what changed in the 2026-04-10 productionization session

- **Security**: webhook auth + API key middleware now fail closed in
  production when secrets are missing (previously fail-open).
- **Database**: `settings.database_path` added; `main.py` passes it to
  `EventStore`. Railway requires the volume mount to be consistent with
  this path.
- **Tests**: 70 → 105 passing. Added webhook handler tests (HMAC, all
  message types, malformed tool args) and API endpoint tests
  (`/health`, `/api/agents`, `/api/calls/*`, middleware fail-closed).
- **Bug fix**: `record_data_point` with missing `field_name` no longer
  silently persists an empty-keyed data point; now returns an error
  string to the AI.
- **PII**: removed `subject_name` from `call_initiated` and
  `assistant_request_received` logs. Removed the verbose
  `tool_calls_payload_debug` log that dumped raw tool call payloads.
- **Frontend**: `frontend/.env.example` created with the three
  `VITE_*` vars used by the code.

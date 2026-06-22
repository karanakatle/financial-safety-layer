# Hosted Backend Deployment Runbook

This runbook gets FinSaathi from local INT testing to Hosted SIT/UAT readiness.

## Decision

Use a stable HTTPS backend with durable storage before Hosted SIT, Device SIT, UAT, or Play/internal testing.

The backend currently uses FastAPI and SQLite:

- App entrypoint: `backend.main:app`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Durable SQLite env var: `PILOT_DB_PATH`
- Public health endpoint: `/api/health`
- Admin storage check: `/api/literacy/storage-health`

## Recommended First Host

Start with Render because the repo already has `render.yaml`.

Use a paid/stable web service with persistent disk for pilot storage. Avoid ephemeral-only hosting for SIT/UAT because pilot telemetry and feedback can be lost after restart.

The updated `render.yaml` uses:

```text
service name: finsaathi-api
healthCheckPath: /api/health
PILOT_DB_PATH=/var/data/pilot_research.db
persistent disk mounted at /var/data
```

If Render is not available, use the same requirements on Railway, Fly.io, or another HTTPS host:

- Python 3.11
- install `requirements.txt`
- run `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- set `PILOT_DB_PATH` to a durable volume path
- set a non-default `PILOT_ADMIN_API_KEY`

## Required Environment Variables

Set these in the host dashboard:

```text
PILOT_DB_PATH=/var/data/pilot_research.db
PILOT_ADMIN_API_KEY=<strong-secret-value>
```

Optional:

```text
OPENAI_API_KEY=<only if voice/AI provider testing needs it>
```

Do not use `pilot-admin-local` for hosted environments.

## Deploy Steps On Render

1. Push this branch to GitHub and merge after review.
2. In Render, create a new Blueprint from the GitHub repo or update the existing service from `render.yaml`.
3. Confirm the service name is `finsaathi-api`.
4. Confirm disk is mounted at `/var/data`.
5. Add `PILOT_ADMIN_API_KEY` in the Render dashboard.
6. Deploy.
7. Copy the public backend URL.

Expected URL shape:

```text
https://finsaathi-api.onrender.com
```

## Hosted Smoke Test

Run:

```bash
cd Finsaathi
BASE_URL=https://your-hosted-backend.example.com \
PILOT_ADMIN_KEY=<same-value-as-PILOT_ADMIN_API_KEY> \
scripts/hosted_backend_smoke.sh
```

Required pass criteria:

- `/api/health` returns `{"status":"ok"}`
- `/api/pilot/meta` returns pilot metadata
- `/api/literacy/status` returns valid JSON
- `/api/literacy/sms-ingest` accepts a risky SMS sample and returns safe guidance
- `/api/literacy/storage-health` returns `db_path` pointing to durable storage, not the repo-local default

## Android Build After Backend Is Live

Set:

```bash
export BASE_URL=https://your-hosted-backend.example.com/
```

Build debug APK for hosted SIT:

```bash
cd ArthamantriAndroid
./gradlew --no-daemon :app:assembleDebug -PAPI_BASE_URL="$BASE_URL"
```

Build release APK:

```bash
./gradlew --no-daemon :app:assembleRelease \
  -PAPI_BASE_URL="$BASE_URL" \
  -PPRIVACY_POLICY_URL=https://karanakatle.github.io/finsaathi-legal/privacy-policy.html
```

## Test Order After Hosting

1. Hosted Backend SIT:
   - health
   - API contract
   - redaction/privacy
   - durable storage
2. Android Hosted Integration:
   - debug build points to hosted URL
   - app handles backend success/failure
3. Physical Device SIT:
   - SMS permission
   - notification access
   - usage access
   - overlay
   - monitoring start/stop
   - one red-risk alert
4. UAT:
   - comprehension
   - usefulness
   - trust
   - notification/overlay irritation
5. Release QA:
   - privacy URL
   - Play declarations
   - no secrets committed
   - legal/privacy gate status

## Do Not Start External Pilot Until

- `PILOT_ADMIN_API_KEY` is non-default
- storage health confirms durable path
- hosted smoke passes
- at least two physical-device smoke tests pass
- legal/privacy review is recorded for any external pilot beyond internal testing

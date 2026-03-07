# Arthamantri Prototype (v1)

A working **event-driven financial safety agent** prototype to demonstrate agentic intervention logic, explainable alerts, and voice-based interaction.

## Why this exists
This is intentionally a **research-oriented prototype** (not a production fintech app). It is designed to test:
- Intervention timing
- Alert messaging clarity and trust
- User response to agent suggestions

## Features
- Event input (income/expense)
- Financial state engine (`balance`, `avg_daily_spend`, `days_to_zero`, `safe_spend_today`)
- Rule-based intervention engine
- Explainable alerts with priorities
- Voice query endpoint + browser speech interface
- Alert history for behavior analysis

## Architecture
```
User Device (Android/Web)
        ↓
Event Inputs Layer
(SMS parser / manual entry / simulator)
        ↓
Financial State Engine
(balance, burn rate, days-to-zero)
        ↓
Intervention Decision Engine
(when to alert, what to say)
        ↓
Notification & Interaction Layer
(push alerts + voice query)
        ↓
User Feedback Capture
(action taken / ignored)

```

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Then open http://localhost:8000.

## How to test it
### 1) Unit tests (fastest)
```bash
pytest -q
```

### 2) Manual UI test
1. Start server with `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`.
2. Open `http://localhost:8000`.
3. Add an `expense` event and verify:
   - balance updates
   - a post-spend guidance alert appears
4. Add a large expense and verify low-balance warning triggers.
5. Ask: `Kitna paisa bacha hai?` and verify response text + TTS output.

### 3) API smoke test (scripted)
With server running:
```bash
./scripts/smoke_test.sh
```
Optional custom URL:
```bash
./scripts/smoke_test.sh http://localhost:8000
```


## Deploy as a mobile application

### Option A: Installable PWA (fastest)
This repo now includes a web app manifest + service worker so the app can be installed on Android from Chrome.

1. Start the backend on all interfaces (local LAN test):
   ```bash
   ./scripts/mobile_lan_run.sh
   ```
   If you prefer manual startup:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
2. Find your laptop LAN IP and open `http://<LAN_IP>:8000` from Android Chrome on the same Wi-Fi.
   - Example: `http://192.168.1.54:8000`
   - `localhost:8000` on phone points to the phone itself, not your laptop.
3. If LAN URL fails:
   - allow incoming connections for Terminal/Python in macOS Firewall
   - disable VPN/proxy temporarily on laptop and phone
   - confirm server is still running on port `8000`
4. For install prompt + service worker validation, use HTTPS URL:
   - deploy app (Render/Railway/Fly) and open deployed `https://...` URL, or
   - expose local app via HTTPS tunnel (Cloudflare Tunnel/ngrok)
5. In Android Chrome on HTTPS:
   - open app URL
   - tap **Add to Home Screen / Install app**
   - launch from home screen in standalone mode

### Option B: Deploy backend on Render (fixed HTTPS URL)
Use this for real-device testing and Play Store builds, so app API base URL is stable.

1. Push this repository to GitHub.
2. In Render: **New -> Blueprint**.
3. Select your GitHub repo.
4. Render reads `render.yaml` and creates service `arthamantri-api`.
5. Wait until deploy is healthy.
6. Copy backend URL, for example:
   - `https://arthamantri-api.onrender.com`
7. Verify API from browser:
   - `https://arthamantri-api.onrender.com/api/literacy/status`

### Option C: Publish to Play Store with Capacitor
If you want Play Store distribution without rewriting the frontend:

1. Keep backend deployed (HTTPS) and note your API base URL.
2. In a new wrapper project:
   ```bash
   npm init @capacitor/app
   npm install
   npx cap add android
   ```
3. Point the app to your hosted web URL in `capacitor.config.*` (`server.url`).
4. Open Android Studio and build/sign an `.aab`:
   ```bash
   npx cap open android
   ```
5. Upload the signed bundle to Google Play Console.

### Android Native App release flow (ArthamantriAndroid)
If you are shipping the native Android app from `ArthamantriAndroid`:

1. Deploy backend first on Render (or any fixed HTTPS host).
2. Build Android release using deployed API URL:
   ```bash
   cd ArthamantriAndroid
   ./gradlew :app:bundleRelease \
     -PAPI_BASE_URL=https://arthamantri-api.onrender.com/ \
     -PPRIVACY_POLICY_URL=https://your-privacy-page-url
   ```
3. AAB output:
   - `ArthamantriAndroid/app/build/outputs/bundle/release/app-release.aab`
4. Optional APK (sideload/testing):
   ```bash
   ./gradlew :app:assembleRelease \
     -PAPI_BASE_URL=https://arthamantri-api.onrender.com/ \
     -PPRIVACY_POLICY_URL=https://your-privacy-page-url
   ```
5. APK output:
   - `ArthamantriAndroid/app/build/outputs/apk/release/app-release.apk`

### Production checklist
- Restrict CORS to your app domain (replace `allow_origins=["*"]`).
- Use HTTPS for voice/microphone features.
- Add persistence (database) if you need user/account continuity.
- Add auth before handling real financial data.

## Example API
- `GET /api/state`
- `POST /api/transaction`
- `GET /api/alerts`
- `POST /api/voice-query`
- `POST /api/literacy/sms-ingest` (simulate bank SMS expense feed)
- `POST /api/literacy/upi-open` (simulate UPI app open trigger)
- `GET /api/literacy/status`
- `GET /api/pilot/meta` (research-pilot disclaimer and alert policy)
- `POST /api/pilot/consent` (store participant consent)
- `POST /api/pilot/feedback` (collect pilot feedback)
- `POST /api/pilot/app-log` (store app-side activity logs in backend)
- `GET /api/pilot/summary` (pilot aggregate metrics)
- `GET /api/pilot/analytics` (event and stage analytics for research)

## Financial Literacy Safety Flow (v1)
This prototype now supports the first two-step financial safety nudges:
1. Threshold nudge: when daily spending is about to exceed the safe amount.
2. UPI nudge: first time user opens a UPI app after threshold risk is active.

Policy is configurable via environment variables:
- `LITERACY_DAILY_SAFE_LIMIT` (default: `1200`)
- `LITERACY_WARNING_RATIO` (default: `0.9`)
- `LITERACY_STAGE1_MESSAGE`
- `LITERACY_STAGE2_OVER_LIMIT_TEMPLATE` (supports `{daily_overage}` and `{weekly_impact}`)
- `LITERACY_STAGE2_CLOSE_LIMIT_MESSAGE`
- `LITERACY_WARMUP_DAYS` (default: `3`)
- `LITERACY_WARMUP_SEED_MULTIPLIER` (default: `1.2`)
- `LITERACY_WARMUP_EXTREME_SPIKE_RATIO` (default: `0.4`)

Per-user policy override APIs:
- `GET /api/literacy/policy?participant_id=<id>`
- `POST /api/literacy/policy` with body:
  - `participant_id`
  - `daily_safe_limit`
  - `warning_ratio`
- `POST /api/literacy/alert-feedback` to capture alert usefulness actions (`useful`, `not_useful`, `dismissed`)

Adaptive behavior:
- Backend stores daily spend history per participant and auto-recalibrates auto-managed policy using recent 7-day spend median.
- Manual policy overrides are not replaced by auto recalibration.

Local test sequence:
```bash
curl -X POST http://localhost:8000/api/literacy/sms-ingest \
  -H "Content-Type: application/json" \
  -d '{"participant_id":"pilot-user-001","amount":950,"category":"upi","note":"SMS detected payment"}'

curl -X POST http://localhost:8000/api/literacy/upi-open \
  -H "Content-Type: application/json" \
  -d '{"participant_id":"pilot-user-001","app_name":"PhonePe","intent_amount":120}'

curl "http://localhost:8000/api/literacy/status?participant_id=pilot-user-001"
```

## Research Pilot APIs
For a 50-60 participant pilot run:
```bash
curl http://localhost:8000/api/pilot/meta

curl -X POST http://localhost:8000/api/pilot/consent \
  -H "Content-Type: application/json" \
  -d '{"participant_id":"pilot-user-001","accepted":true,"language":"en"}'

curl -X POST http://localhost:8000/api/pilot/feedback \
  -H "Content-Type: application/json" \
  -d '{"participant_id":"pilot-user-001","rating":4,"comment":"Alert was useful","language":"en"}'

curl http://localhost:8000/api/pilot/analytics
```

Pilot persistence:
- Pilot consent/feedback/events are stored in local SQLite: `data/pilot_research.db`
- This allows analysis across backend restarts during research pilots.

## Research docs
- `research/hypotheses.md`
- `research/metrics.md`
- `docs/architecture.md`
- `docs/agent_logic.md`

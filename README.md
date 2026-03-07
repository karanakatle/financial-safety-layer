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
- `GET /api/literacy/policy` (per-user effective policy)
- `POST /api/literacy/policy` (manual per-user policy override)
- `POST /api/literacy/reset` (soft reset: state only)
- `POST /api/literacy/reset-hard` (hard reset: state + policy/history/feedback/features)
- `POST /api/literacy/alert-feedback` (capture alert action: useful/not_useful/dismissed)
- `GET /api/pilot/meta` (research-pilot disclaimer and alert policy)
- `POST /api/pilot/consent` (store participant consent)
- `POST /api/pilot/feedback` (collect pilot feedback)
- `POST /api/pilot/app-log` (store app-side activity logs in backend)
- `GET /api/pilot/summary` (pilot aggregate metrics)
- `GET /api/pilot/analytics` (event and stage analytics for research)

## Financial Literacy Safety Flow (current)
Current logic supports:
1. Stage-1 threshold nudge when projected daily spend nears/exceeds limit.
2. Stage-2 UPI-open nudge on first UPI-open after risk becomes active.
3. Catastrophic override for high-impact transactions (including warm-up days).
4. Context-aware alert intensity and suppression.
5. Continuous policy adaptation for auto-managed users.

Policy is configurable via environment variables:
- `LITERACY_DAILY_SAFE_LIMIT` (default: `1200`)
- `LITERACY_WARNING_RATIO` (default: `0.9`)
- `LITERACY_STAGE1_MESSAGE`
- `LITERACY_STAGE2_OVER_LIMIT_TEMPLATE` (supports `{daily_overage}` and `{weekly_impact}`)
- `LITERACY_STAGE2_CLOSE_LIMIT_MESSAGE`
- `LITERACY_WARMUP_DAYS` (default: `3`)
- `LITERACY_WARMUP_SEED_MULTIPLIER` (default: `1.2`)
- `LITERACY_WARMUP_EXTREME_SPIKE_RATIO` (default: `0.4`)
- `LITERACY_CATASTROPHIC_ABSOLUTE` (default: `5000`)
- `LITERACY_CATASTROPHIC_MULTIPLIER` (default: `2.5`)
- `LITERACY_CATASTROPHIC_PROJECTED_CAP` (default: `1.8`)

Per-user policy override APIs:
- `GET /api/literacy/policy?participant_id=<id>`
- `POST /api/literacy/policy` with body:
  - `participant_id`
  - `daily_safe_limit`
  - `warning_ratio`
- `POST /api/literacy/alert-feedback` to capture alert usefulness actions (`useful`, `not_useful`, `dismissed`)
- `POST /api/literacy/reset` to clear only current literacy state for the participant
- `POST /api/literacy/reset-hard` to clear state + policy + history + feedback + alert features

Adaptive behavior:
- Backend stores daily spend history per participant and auto-recalibrates auto-managed policy using recent 7-day spend median.
- Auto-managed `warning_ratio` is refined using contextual outcomes (risk/confidence/hard-rate/suppressed-rate/dismissals).
- Manual policy overrides are not replaced by auto recalibration.

Contextual scoring and logging:
- On each emitted alert, backend computes and stores:
  - `alert_id, participant_id, timestamp`
  - `amount, projected_spend, daily_safe_limit, spend_ratio`
  - `txn_anomaly_score, hour_of_day, rapid_txn_flag, upi_open_flag`
  - `recent_dismissals_24h, risk_score, confidence_score`
  - `tone_selected, frequency_bucket`
- For very high-risk UPI-open alerts, backend returns `pause_seconds=5` (used by Android app for pause-and-confirm friction).

Deterministic scored model (current approach before ML):
- Risk-context score (0-100 style, implemented as normalized risk score internally) is derived from:
  - spend vs limit (`projected_spend / daily_safe_limit`)
  - transaction size anomaly (`amount` vs recent median behavior)
  - time/context (`hour_of_day`)
  - rapid consecutive spend flag
  - UPI-open context after stage-1
  - recent dismissals (fatigue-aware dampening/suppression path)
- Confidence is action confidence (signal alignment strength), not truth certainty.
- Tone selection maps contextual risk to intervention style:
  - low risk -> supportive
  - medium risk -> caution
  - high risk -> strong intervention
- Frequency control:
  - `hard/soft/suppressed` bucket selection per alert
  - suppression path reduces repetitive popup fatigue
  - stage-gating remains active (stage-1 once per day, stage-2 once on first UPI-open after stage-1)
- Purpose:
  - fewer false-positive hard alerts
  - better trust retention for volatile spenders
  - cleaner supervision data for future ML weight/tone optimization

### Scoring specification (research baseline)
Use a simple deterministic scored model first (no ML), then learn weights/timing later from logs.

Risk-context score (0-100 style points):
- Spend vs limit:
  - `projected/limit > 1.2` -> `+30`
  - `projected/limit > 1.0` -> `+20`
  - `projected/limit > 0.9` -> `+10`
- Transaction size anomaly:
  - `amount > 1.8 * 7-day median txn` -> `+20`
- Time/context:
  - late night spend -> `+10`
  - rapid consecutive spends -> `+10`
  - UPI-open after stage1 -> `+15`
- Recent dismissals:
  - many dismissals -> reduce hard score by `-10` (fatigue control)

Confidence (action confidence, not truth confidence):
- one weak signal -> low confidence
- multiple aligned signals (for example SMS + app-open + recency) -> high confidence

Tone mapping:
- Low -> supportive info (`Aaj ka spend high hai, dhyaan rakhein`)
- Medium -> caution (`Aap safe limit ke kareeb hain`)
- High -> strong intervention (`Pause karein, payment verify karein`)

Frequency control:
- hard cap target: `max hard alerts/day = 1` (optionally `2`)
- cooldown target between hard alerts: `2 hours`
- if cap reached: soft-only cards, no hard popup

Why this helps:
- reduces false-positive irritation
- preserves trust for volatile users
- keeps alerts rarer and more meaningful
- creates clean supervision data for later ML tuning

Implementation status:
- Implemented now: contextual scoring, confidence estimate, tone selection, `hard/soft/suppressed`,
  UPI high-risk pause friction, persistence of alert features and feedback.
- Planned next hardening: exact point-table/cap/cooldown as explicit configurable policy constants.

Local test sequence:
```bash
curl -X POST http://localhost:8000/api/literacy/sms-ingest \
  -H "Content-Type: application/json" \
  -d '{"participant_id":"pilot-user-001","amount":950,"category":"upi","note":"SMS detected payment"}'

curl -X POST http://localhost:8000/api/literacy/upi-open \
  -H "Content-Type: application/json" \
  -d '{"participant_id":"pilot-user-001","app_name":"PhonePe","intent_amount":120}'

curl "http://localhost:8000/api/literacy/status?participant_id=pilot-user-001"

curl "http://localhost:8000/api/literacy/policy?participant_id=pilot-user-001"
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

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

1. Deploy the FastAPI app over HTTPS (Render/Railway/Fly.io/etc.):
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
2. Open your deployed URL in Android Chrome.
3. Tap **Add to Home Screen / Install app**.
4. Launch it from the home screen in standalone mode.

### Option B: Publish to Play Store with Capacitor
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

## Research docs
- `research/hypotheses.md`
- `research/metrics.md`
- `docs/architecture.md`
- `docs/agent_logic.md`

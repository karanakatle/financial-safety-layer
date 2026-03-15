# ArthamantriAndroid

Native Android companion app for the existing FastAPI backend in `Python-OOS-Project`.

## What it does
- Listens for bank SMS debit messages (`SMS_RECEIVED`).
- Listens for UPI/bank transaction notifications (`NotificationListenerService`).
- Sends parsed expenses to backend: `POST /api/literacy/sms-ingest`.
- Monitors foreground app and detects UPI apps.
- Sends UPI-open event to backend: `POST /api/literacy/upi-open`.
- Shows USSD-like full-screen warning overlay plus high-priority notification.
- Applies pause-and-confirm friction for very high-risk stage-2 alerts (`pause_seconds` from backend).
- Shows explainable alerts (risk level, why-this-alert, next-safe-action, essential-goal impact) via backend message payload.
- Keeps payment warnings action-first (`Pause / Decline / Proceed`) for risky approval-style payment requests.
- Keeps cashflow alerts separate and supports optional `Useful / Not useful` feedback on those alerts.
- Queues fallback app logs / feedback offline and replays them idempotently with stable `event_id`s.
- Renders severity-aware alerts from backend payload:
  - `soft`: calmer advisory styling
  - `medium`: caution styling
  - `hard`: high-risk styling with strongest urgency
- Enforces first-run research consent and supports pilot feedback submission.
- Includes **Facilitator Setup Pack** (2-minute assisted onboarding checklist with one-tap actions).

## Backend compatibility
This app is plug-and-play with backend endpoints already added in:
- `backend/main.py`
  - `POST /api/literacy/sms-ingest`
  - `POST /api/literacy/upi-open`
  - `GET /api/literacy/status`
  - `GET /api/literacy/policy`
  - `POST /api/literacy/policy`
  - `GET /api/literacy/essential-goals`
  - `POST /api/literacy/essential-goals`
  - `POST /api/literacy/reset`
  - `POST /api/literacy/reset-hard`
  - `POST /api/literacy/alert-feedback`
  - `GET /api/literacy/debug-trace`
  - `GET /api/pilot/meta`
  - `POST /api/pilot/app-log`
  - `POST /api/pilot/consent`
  - `POST /api/pilot/feedback`
  - `POST /api/pilot/grievance`
  - `GET /api/pilot/grievance`
  - `POST /api/pilot/grievance/status`
  - `GET /api/pilot/summary`
  - `GET /api/pilot/analytics`
  - `GET /api/pilot/review`
  - `POST /api/research/assignment`
  - `POST /api/research/event`

Per-user literacy state:
- Android sends a stable `participant_id` (device Android ID) with literacy events.
- Backend tracks threshold/alert stages per participant to avoid cross-user state mixing.
- `participant_id` is app-scoped on Android (can differ from `adb shell settings get secure android_id`
  across debug/release package IDs and signing keys). Prefer the `participantId` shown in app logcat.

## Quick start
1. Ensure backend is running and reachable from phone over HTTPS.
   - Recommended for live testing: deploy backend using Render Blueprint (`render.yaml`).
   - Example fixed URL: `https://arthamantri-api.onrender.com/`
2. Open `ArthamantriAndroid` in Android Studio.
3. Sync Gradle.
4. Run app on physical Android phone.
5. In app:
   - On first launch, select language and accept pilot consent.
   - App prompts **Money Setup Lite** (cohort + up to 2 essential goals, skip optional).
   - App then prompts permission onboarding flow (runtime + notification access + usage + overlay).
   - Start monitoring from the home dashboard.
   - Use left-swipe menu for Manage Access, feedback, Money Setup Lite, Facilitator Setup Pack, help, and privacy policy.
   - Money Setup Lite can be reopened later from the menu or Help dialog for profile/goal edits without reinstalling.
   - Use **Facilitator Setup Pack** from menu/help for assisted onboarding in field pilots.
6. Trigger events:
   - Receive/simulate bank debit SMS.
   - Open PhonePe/GPay/Paytm/BHIM.

## Render deployment (fixed API URL)
1. Push repo to GitHub.
2. Render -> New -> Blueprint -> select repo.
3. Render creates service from `render.yaml`.
4. Wait for healthy deploy.
5. Verify backend:
   - `https://<your-service>.onrender.com/api/literacy/status`

## Release builds
Build with deployed backend + privacy policy URL:

```bash
cd ArthamantriAndroid
./gradlew :app:bundleRelease \
  -PAPI_BASE_URL=https://<your-service>.onrender.com/ \
  -PPRIVACY_POLICY_URL=https://<your-privacy-policy-url>
```

Optional release APK:

```bash
./gradlew :app:assembleRelease \
  -PAPI_BASE_URL=https://<your-service>.onrender.com/ \
  -PPRIVACY_POLICY_URL=https://<your-privacy-policy-url>
```

Outputs:
- AAB: `app/build/outputs/bundle/release/app-release.aab`
- APK: `app/build/outputs/apk/release/app-release.apk`

## Build profiles workflow (Debug + Release APK + Release AAB)

Use three profiles:
- `debug` for day-to-day development/testing (Android Studio + emulator/device)
- `release APK` for sideload testing on real devices
- `release AAB` for Play Console upload

This is not restricted to Android Studio only. You can use Android Studio or CLI commands.

### A) Keep only debug app installed during development

```bash
adb uninstall com.arthamantri.android
adb uninstall com.arthamantri.android.dev
cd /Users/karanakatle/Personal/Python-OOS-Project/ArthamantriAndroid
./gradlew :app:assembleDebug -PAPI_BASE_URL=https://arthamantri-api.onrender.com/
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Verify only debug package exists:

```bash
adb shell pm list packages | grep arthamantri
```

Expected:
- `package:com.arthamantri.android.dev`

Open debug app:

```bash
adb shell am start -n com.arthamantri.android.dev/com.arthamantri.android.MainActivity
```

### B) Build release artifacts (do not auto-install)

```bash
cd /Users/karanakatle/Personal/Python-OOS-Project/ArthamantriAndroid
./gradlew :app:assembleRelease \
  -PAPI_BASE_URL=https://arthamantri-api.onrender.com/ \
  -PPRIVACY_POLICY_URL=https://arthamantri-api.onrender.com/privacy-policy.html

./gradlew :app:bundleRelease \
  -PAPI_BASE_URL=https://arthamantri-api.onrender.com/ \
  -PPRIVACY_POLICY_URL=https://arthamantri-api.onrender.com/privacy-policy.html
```

Outputs:
- APK: `app/build/outputs/apk/release/app-release.apk`
- AAB: `app/build/outputs/bundle/release/app-release.aab`

## Project structure
- `app/src/main/java/com/arthamantri/android/MainActivity.kt`
- `.../sms/BankSmsReceiver.kt`
- `.../sms/SmsParser.kt`
- `.../usage/AppUsageForegroundService.kt`
- `.../api/LiteracyApi.kt`
- `.../repo/LiteracyRepository.kt`
- `.../notify/AlertNotifier.kt`
- `app/src/main/res/layout/dialog_money_setup.xml`
- `app/src/main/res/layout/dialog_facilitator_pack.xml`
- `app/src/main/res/layout/dialog_help_setup.xml`

## Facilitator assets
- Printable assisted onboarding card:
  - `docs/FACILITATOR_ONBOARDING_CARD.md`

## Important notes
- Play Store has strict policies around SMS and usage-access permissions.
- `Notification access` is separate from ordinary app notification permission. Payment-warning monitoring depends on `TransactionNotificationListenerService` being enabled in Android Special App Access.
- Base URL is configurable at build time using `-PAPI_BASE_URL`.
- Privacy policy URL is configurable using `-PPRIVACY_POLICY_URL`.
- `keystore.properties` is required for real release signing (see `PRODUCTION_SETUP.md`).
- Onboarding state is persisted locally (for example: language/consent/money-setup/permission completion).
- The Android app uses a stable per-install `participant_id` (Android ID). Backend longitudinal state only remains stable across deploys/restarts if backend `PILOT_DB_PATH` points to durable storage.
- Retrofit/OkHttp clients are reused per active base URL to avoid rebuilding the network stack on every repository call.
- Local onboarding flag keys include:
  - `KEY_LANGUAGE_SELECTED`
  - `KEY_CONSENT_ACCEPTED`
  - `KEY_MONEY_SETUP_DONE`
  - `KEY_PERMISSION_ONBOARDING_DONE`

## Literacy test reset commands
Use the backend participant id for deterministic retesting:

```bash
curl -X POST \
  -H "x-pilot-admin-key: pilot-admin-local" \
  "https://<your-service>.onrender.com/api/literacy/reset?participant_id=<participant_id>"
```
- Soft reset: clears only literacy runtime state.

```bash
curl -X POST \
  -H "x-pilot-admin-key: pilot-admin-local" \
  "https://<your-service>.onrender.com/api/literacy/reset-hard?participant_id=<participant_id>"
```
- Hard reset: clears literacy state + participant policy + spend history + literacy events +
  alert feedback + alert features.

## Emulator severity verification checklist
Use this when validating that Android visual behavior matches backend `severity`.

1. Start backend and install the debug app on emulator/device.
2. Grant:
   - SMS access
   - Usage access
   - Overlay access
   - Notification access
3. Capture your active `participant_id` from logcat after a successful `sms-ingest`.
4. Hard reset before each isolated test:

```bash
curl -X POST "https://<your-service>.onrender.com/api/literacy/reset-hard?participant_id=<participant_id>"
```

### A) Soft alert check
Goal: verify calmer advisory styling.

1. Send a modest near-threshold SMS, for example:
```bash
adb emu sms send 12345 "INR 900 debited via UPI to shop"
```
2. Expected:
   - badge/tag shows soft advisory copy
   - calmer badge/text/scrim colors
   - no pause countdown
   - backend alert payload has `severity=soft`

### B) Medium alert check
Goal: verify caution styling without high-risk pause.

1. Reset hard.
2. Send a stronger threshold-crossing SMS, for example:
```bash
adb emu sms send 12345 "INR 1400 debited via UPI to merchant"
```
3. Expected:
   - caution alert tag/styling
   - no pause countdown
   - backend alert payload has `severity=medium`

### C) Hard alert check
Goal: verify strongest styling for catastrophic or stage-2 risk.

1. Reset hard.
2. Send a catastrophic SMS, for example:
```bash
adb emu sms send 12345 "INR 6000 debited via UPI to merchant"
```
3. Expected:
   - high-risk tag/styling
   - strongest badge/title color
   - backend alert payload has `severity=hard`

### D) Hard UPI-open pause check
Goal: verify high-risk stage-2 friction.

1. Trigger stage-1 first with a qualifying spend.
2. Open a tracked UPI app while monitoring is active.
3. Expected:
   - stage-2 alert shown
   - if backend returns `pause_seconds=5`, buttons remain disabled until countdown finishes
   - payload should include `severity=hard` and `pause_seconds=5`

### Debug tip
If visual severity looks wrong, inspect:
- Android logcat for parsed alert payload
- backend `/api/literacy/debug-trace?participant_id=<participant_id>`

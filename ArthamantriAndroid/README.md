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
- Enforces first-run research consent and supports pilot feedback submission.

## Backend compatibility
This app is plug-and-play with backend endpoints already added in:
- `backend/main.py`
  - `POST /api/literacy/sms-ingest`
  - `POST /api/literacy/upi-open`
  - `GET /api/literacy/status`
  - `GET /api/literacy/policy`
  - `POST /api/literacy/policy`
  - `POST /api/literacy/reset`
  - `POST /api/literacy/reset-hard`
  - `POST /api/literacy/alert-feedback`
  - `GET /api/pilot/meta`
  - `POST /api/pilot/consent`
  - `POST /api/pilot/feedback`

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
   - App prompts permission onboarding flow (runtime + usage + overlay).
   - Start monitoring from the home dashboard.
   - Use left-swipe menu for Manage Access, feedback, help, and privacy policy.
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

## Important notes
- Play Store has strict policies around SMS and usage-access permissions.
- Base URL is configurable at build time using `-PAPI_BASE_URL`.
- Privacy policy URL is configurable using `-PPRIVACY_POLICY_URL`.
- `keystore.properties` is required for real release signing (see `PRODUCTION_SETUP.md`).

## Literacy test reset commands
Use the backend participant id for deterministic retesting:

```bash
curl -X POST "https://<your-service>.onrender.com/api/literacy/reset?participant_id=<participant_id>"
```
- Soft reset: clears only literacy runtime state.

```bash
curl -X POST "https://<your-service>.onrender.com/api/literacy/reset-hard?participant_id=<participant_id>"
```
- Hard reset: clears literacy state + participant policy + spend history + literacy events +
  alert feedback + alert features.

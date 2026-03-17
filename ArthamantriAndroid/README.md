> 📱 Android Client for Real-Time Financial Safety • 🧠 Explainable Alerts • ⚠️ Risk Detection from Phone Signals • 🔄 Offline-Resilient
![Platform](https://img.shields.io/badge/Platform-Android-green)
![Backend](https://img.shields.io/badge/Backend-FastAPI-blue)
![Architecture](https://img.shields.io/badge/Architecture-Event--Driven-orange)
![AI](https://img.shields.io/badge/AI-Agentic--Workflow-purple)
![Status](https://img.shields.io/badge/Status-Research--Prototype-yellow)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![Domain](https://img.shields.io/badge/Domain-Fintech-red)
![Focus](https://img.shields.io/badge/Focus-Financial--Inclusion-brightgreen)
![UX](https://img.shields.io/badge/UX-Explainable--AI-blueviolet)

# 📱 ArthamantriAndroid

> Native Android client for a research-driven financial safety platform that detects risky payment moments from phone-native signals and shows explainable warnings in real time.

---

## 🚀 Overview

`ArthamantriAndroid` is the Android companion app for the backend in `Python-OOS-Project`.

It is designed for **low-confidence digital finance users** and acts as a **real-time financial safety layer** on the device.

Instead of requiring direct bank integration, the app uses **phone-native signals** such as:

- SMS messages
- payment app notifications
- foreground payment app activity

These signals are converted into:

- explainable payment warnings
- cashflow safety guidance
- user feedback and telemetry for pilot research

---

## ⚠️ What it does

The app:

- listens for bank SMS messages
- listens for UPI / bank transaction notifications
- detects foreground UPI app usage
- sends payment/cashflow context to backend APIs
- shows full-screen / overlay warnings for risky situations
- supports action-first payment warnings:
  - `Pause`
  - `Decline`
  - `Proceed`
- supports optional usefulness feedback for cashflow alerts
- queues logs and feedback offline and replays them later
- supports facilitator-assisted onboarding for pilot usage

---

## 🏗️ Android Runtime Flow

```mermaid
flowchart TB
A[Phone Signals] --> B[Android Capture Layer]
B --> C[SMS Parser / Notification Listener / App Usage Monitor]
C --> D[Backend API]
D --> E[Risk / Guidance Response]
E --> F[Overlay / Fullscreen Warning UI]
F --> G[User Action / Feedback]
G --> H[Telemetry + Offline Replay]
````

---

## ✨ Key Capabilities

### 🔍 Signal Capture

* `SMS_RECEIVED` handling for bank/payment messages
* `NotificationListenerService` for payment notifications
* foreground app monitoring for UPI-capable apps

### ⚠️ Warning Surfaces

* USSD-like full-screen warning overlay
* high-priority notifications
* severity-aware rendering:

  * `soft`
  * `medium`
  * `hard`

### 🧠 Explainable Guidance

Backend payloads can include:

* risk level
* why this alert
* safest next action
* essential-goal impact

### ✅ Action-First Interventions

Payment warnings focus on:

* `Pause`
* `Decline`
* `Proceed`

Cashflow alerts remain separate and can collect:

* `Useful`
* `Not useful`

### 📡 Offline Resilience

* queues app logs / feedback locally
* idempotent replay using stable `event_id`

### 🤝 Pilot Readiness

* first-run research consent
* pilot feedback submission
* Facilitator Setup Pack for assisted onboarding

---

## 🔌 Backend Compatibility

This app is designed to work with the FastAPI backend in `Python-OOS-Project`.

Core endpoints used include:

* `POST /api/literacy/sms-ingest`
* `POST /api/literacy/upi-open`
* `GET /api/literacy/status`
* `GET /api/literacy/policy`
* `POST /api/literacy/policy`
* `GET /api/literacy/essential-goals`
* `POST /api/literacy/essential-goals`
* `POST /api/literacy/alert-feedback`
* `POST /api/pilot/app-log`
* `POST /api/pilot/consent`
* `POST /api/pilot/feedback`

Additional operator/research endpoints are supported through the backend as well.

### Per-user state

* Android sends a stable `participant_id` using device Android ID
* backend tracks literacy/runtime state per participant
* note that Android ID can vary across debug/release package IDs and signing keys

---

## ⚡ Quick Start

1. Ensure backend is deployed and reachable over HTTPS.

   * Recommended: Render Blueprint deployment using `render.yaml`
2. Open `ArthamantriAndroid` in Android Studio
3. Sync Gradle
4. Run app on a physical Android phone
5. Complete onboarding:

   * select language
   * accept pilot consent
   * complete Money Setup Lite
   * grant required permissions
6. Start monitoring from the home dashboard
7. Trigger events:

   * receive/simulate bank SMS
   * open PhonePe / GPay / Paytm / BHIM

---

## 📦 Release Builds

Build with deployed backend and privacy policy URL:

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

* AAB: `app/build/outputs/bundle/release/app-release.aab`
* APK: `app/build/outputs/apk/release/app-release.apk`

---

# 🔬 Technical Deep Dive

---

## Detailed Capabilities

* Listens for bank SMS debit messages (`SMS_RECEIVED`)
* Listens for UPI/bank transaction notifications (`NotificationListenerService`)
* Sends parsed expenses to backend: `POST /api/literacy/sms-ingest`
* Monitors foreground app and detects UPI apps
* Sends UPI-open event to backend: `POST /api/literacy/upi-open`
* Shows USSD-like full-screen warning overlay plus high-priority notification
* Applies pause-and-confirm friction for very high-risk stage-2 alerts (`pause_seconds` from backend)
* Shows explainable alerts via backend payload
* Keeps payment warnings action-first (`Pause / Decline / Proceed`)
* Keeps cashflow alerts separate with optional `Useful / Not useful` feedback
* Queues fallback app logs / feedback offline and replays them idempotently
* Enforces first-run research consent
* Includes **Facilitator Setup Pack**

---

## Build Profiles Workflow

Use three profiles:

* `debug` for development/testing
* `release APK` for sideload testing
* `release AAB` for Play Console upload

### A) Debug install

```bash
adb uninstall com.arthamantri.android
adb uninstall com.arthamantri.android.dev
cd /Users/karanakatle/Personal/Python-OOS-Project/ArthamantriAndroid
./gradlew :app:assembleDebug -PAPI_BASE_URL=https://arthamantri-api.onrender.com/
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Verify installed package:

```bash
adb shell pm list packages | grep arthamantri
```

Expected:

* `package:com.arthamantri.android.dev`

Open debug app:

```bash
adb shell am start -n com.arthamantri.android.dev/com.arthamantri.android.MainActivity
```

### B) Build release artifacts

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

* APK: `app/build/outputs/apk/release/app-release.apk`
* AAB: `app/build/outputs/bundle/release/app-release.aab`

---

## Project Structure

* `app/src/main/java/com/arthamantri/android/MainActivity.kt`
* `.../sms/BankSmsReceiver.kt`
* `.../sms/SmsParser.kt`
* `.../usage/AppUsageForegroundService.kt`
* `.../api/LiteracyApi.kt`
* `.../repo/LiteracyRepository.kt`
* `.../notify/AlertNotifier.kt`
* `app/src/main/res/layout/dialog_money_setup.xml`
* `app/src/main/res/layout/dialog_facilitator_pack.xml`
* `app/src/main/res/layout/dialog_help_setup.xml`

---

## Facilitator Assets

* Printable assisted onboarding card:

  * `docs/FACILITATOR_ONBOARDING_CARD.md`

---

## Important Notes

* Play Store has strict policies around SMS and usage-access permissions
* `Notification access` is separate from normal notification permission
* Base URL is configurable using `-PAPI_BASE_URL`
* Privacy policy URL is configurable using `-PPRIVACY_POLICY_URL`
* `keystore.properties` is required for real release signing
* Onboarding state is persisted locally
* Android uses a stable per-install `participant_id`
* Retrofit/OkHttp clients are reused per active base URL

Local onboarding keys include:

* `KEY_LANGUAGE_SELECTED`
* `KEY_CONSENT_ACCEPTED`
* `KEY_MONEY_SETUP_DONE`
* `KEY_PERMISSION_ONBOARDING_DONE`

---

## Literacy Test Reset Commands

Soft reset:

```bash
curl -X POST \
  -H "x-pilot-admin-key: pilot-admin-local" \
  "https://<your-service>.onrender.com/api/literacy/reset?participant_id=<participant_id>"
```

Hard reset:

```bash
curl -X POST \
  -H "x-pilot-admin-key: pilot-admin-local" \
  "https://<your-service>.onrender.com/api/literacy/reset-hard?participant_id=<participant_id>"
```

---

## Emulator Severity Verification Checklist

Use this when validating Android visual behavior against backend `severity`.

### A) Soft alert

```bash
adb emu sms send 12345 "INR 900 debited via UPI to shop"
```

Expected:

* soft advisory styling
* no pause countdown
* backend payload has `severity=soft`

### B) Medium alert

```bash
adb emu sms send 12345 "INR 1400 debited via UPI to merchant"
```

Expected:

* caution styling
* no pause countdown
* backend payload has `severity=medium`

### C) Hard alert

```bash
adb emu sms send 12345 "INR 6000 debited via UPI to merchant"
```

Expected:

* strongest risk styling
* backend payload has `severity=hard`

### D) Hard UPI-open pause

Expected:

* stage-2 alert shown
* if backend returns `pause_seconds=5`, buttons stay disabled until countdown finishes
* payload includes `severity=hard` and `pause_seconds=5`

Debug tip:

* inspect Android logcat
* inspect backend `/api/literacy/debug-trace?participant_id=<participant_id>`

---

## 🔗 Repository

## 🧠 Backend System
https://github.com/karanakatle/Python-OOS-Project

---
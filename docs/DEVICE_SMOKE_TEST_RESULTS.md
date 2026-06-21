# FinSaathi Device Smoke Test Results

**Date:** 2026-06-21  
**Branch:** `release/finsaathi-mvp-safety-slice`  
**Story:** 7.5 Run Final Device And Release Candidate Smoke  
**Status:** automated release-candidate gates passed; physical-device smoke blocked because no Android devices were attached.

## Device Availability

| Check | Result |
|---|---|
| `adb devices` | No connected devices listed |
| Physical Android device count | 0 |
| Required physical Android device count | 2 |
| Physical smoke status | Blocked |

## Automated Gates Completed

| Gate | Command | Result |
|---|---|---|
| Backend tests | `.venv/bin/python -m pytest` | `149 passed` |
| Android unit tests | `./gradlew --no-daemon :app:testDebugUnitTest` | `BUILD SUCCESSFUL` |
| Android debug build | `./gradlew --no-daemon :app:assembleDebug` | `BUILD SUCCESSFUL` |
| Android release build | `./gradlew --no-daemon :app:assembleRelease -PAPI_BASE_URL=https://api.yourdomain.com/ -PPRIVACY_POLICY_URL=https://karanakatle.github.io/finsaathi-legal/privacy-policy.html` | `BUILD SUCCESSFUL` |

## Release Candidate Artifact

- Release APK: `ArthamantriAndroid/app/build/outputs/apk/release/app-release.apk`
- Release signing: local ignored `keystore.properties` and `finsaathi-release.keystore`
- Release privacy URL configured in BuildConfig: `https://karanakatle.github.io/finsaathi-legal/privacy-policy.html`
- Privacy URL verification: GitHub Pages returned `HTTP 200`.
- Known release blocker: a stable HTTPS backend URL must be restored or selected, then supplied explicitly with `-PAPI_BASE_URL=...` for release builds.

## Physical Smoke Checklist Not Yet Executed

These checks still require at least two physical Android devices:

- install APK on two physical devices
- complete onboarding in English
- complete onboarding in Hindi where possible
- verify SMS permission request and grant/deny behavior
- verify notification listener access path
- verify usage access path
- verify overlay access path
- verify post-notification permission behavior
- start and stop monitoring
- trigger a red-risk SMS or notification
- confirm expected Red warning path and fallback behavior
- document any OEM/vendor-specific permission or overlay issues

## Required Follow-Up

Run the following after connecting each physical device:

```bash
adb devices
adb install -r ArthamantriAndroid/app/build/outputs/apk/release/app-release.apk
```

Then manually record:

- device model
- Android version
- language tested
- permissions granted/denied
- whether overlay appears
- whether notification fallback appears
- whether sample risk alert appears
- user-visible issue, if any

## Current Decision

FinSaathi is automated-test-clean and release-candidate-buildable. It is not ready for external pilot or public release until physical-device smoke testing is completed and the hosted privacy policy URL is restored.

# FinSaathi Release Configuration Checkpoint

**Date:** 2026-06-21  
**Branch:** `release/finsaathi-mvp-safety-slice`  
**Story:** 7.3 Close Release Configuration Gates  
**Status:** local signing and release build completed; hosted privacy URL resolved.

## Completed Locally

| Gate | Result |
|---|---|
| Local release keystore | Created at `ArthamantriAndroid/finsaathi-release.keystore` |
| Local signing properties | Created at `ArthamantriAndroid/keystore.properties` |
| Git ignore check | Both signing files are ignored by Git |
| Release build | `BUILD SUCCESSFUL` |
| Release artifact | `ArthamantriAndroid/app/build/outputs/apk/release/app-release.apk` |
| APK signing verification | Signer DN is `CN=FinSaathi, OU=FinSaathi, O=FinSaathi, L=Pune, ST=Maharashtra, C=IN` |
| BuildConfig privacy URL | `https://karanakatle.github.io/finsaathi-legal/privacy-policy.html` |

## Release Build Command

```bash
ANDROID_HOME=/Users/karanakatle/Library/Android/sdk \
GRADLE_USER_HOME=/tmp/gradle-home \
./gradlew --no-daemon :app:assembleRelease \
  -PAPI_BASE_URL=https://arthamantri-api.onrender.com/ \
  -PPRIVACY_POLICY_URL=https://karanakatle.github.io/finsaathi-legal/privacy-policy.html
```

## Current Privacy URL Status

The privacy policy has been moved from Render to GitHub Pages:

`https://karanakatle.github.io/finsaathi-legal/privacy-policy.html`

This URL was verified over HTTPS with `HTTP 200`.

## Current Backend Blocker

The backend API URL still points to `https://arthamantri-api.onrender.com/`. If that Render service remains unavailable, app features that require the backend will still fail until the backend is restored or the app is rebuilt with a new `API_BASE_URL`.

## Required Follow-Up

- Confirm Play Console App content uses the GitHub Pages privacy URL.
- Restore the backend Render service or choose a replacement backend host before production launch.
- Back up `finsaathi-release.keystore` and the keystore passwords outside the repository.
- Do not commit `keystore.properties`, keystore files, or signing passwords.

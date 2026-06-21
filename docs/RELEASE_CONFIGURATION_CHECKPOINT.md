# FinSaathi Release Configuration Checkpoint

**Date:** 2026-06-21  
**Branch:** `release/finsaathi-mvp-safety-slice`  
**Story:** 7.3 Close Release Configuration Gates  
**Status:** local signing and release build completed; hosted privacy URL blocked.

## Completed Locally

| Gate | Result |
|---|---|
| Local release keystore | Created at `ArthamantriAndroid/finsaathi-release.keystore` |
| Local signing properties | Created at `ArthamantriAndroid/keystore.properties` |
| Git ignore check | Both signing files are ignored by Git |
| Release build | `BUILD SUCCESSFUL` |
| Release artifact | `ArthamantriAndroid/app/build/outputs/apk/release/app-release.apk` |
| APK signing verification | Signer DN is `CN=FinSaathi, OU=FinSaathi, O=FinSaathi, L=Pune, ST=Maharashtra, C=IN` |
| BuildConfig privacy URL | `https://arthamantri-api.onrender.com/privacy-policy.html` |

## Release Build Command

```bash
ANDROID_HOME=/Users/karanakatle/Library/Android/sdk \
GRADLE_USER_HOME=/tmp/gradle-home \
./gradlew --no-daemon :app:assembleRelease \
  -PAPI_BASE_URL=https://arthamantri-api.onrender.com/ \
  -PPRIVACY_POLICY_URL=https://arthamantri-api.onrender.com/privacy-policy.html
```

## Current Blocker

The configured privacy URL is HTTPS, but it currently returns `HTTP 503` from Render with `x-render-routing: suspend`.

Until the privacy policy URL returns a successful `2xx` response, this release build should be treated as a signed release candidate, not a production-launch-ready artifact.

## Required Follow-Up

- Restore or replace the hosted privacy policy URL.
- Rebuild with the live privacy URL.
- Re-run APK signing verification.
- Back up `finsaathi-release.keystore` and the keystore passwords outside the repository.
- Do not commit `keystore.properties`, keystore files, or signing passwords.

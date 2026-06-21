# Production Setup (Play Store / Production)

Use this when creating a real release build for testers/users.

## 0) Package identity

- Release application ID: `com.finsaathi.android`
- Debug application ID: `com.finsaathi.android.dev`
- Android source namespace: `com.finsaathi.android`

Do not change `applicationId` after the first public Play Store release. See `PACKAGE_MIGRATION_PLAN.md`.

## 1) Configure backend and privacy URLs

You can pass URLs using Gradle properties or environment variables.

- `API_BASE_URL`
  Example: `https://api.yourdomain.com/`
- `PRIVACY_POLICY_URL`
  Example: `https://yourdomain.com/privacy-policy`

### Option A: one-time command

```bash
cd ArthamantriAndroid
./gradlew :app:bundleRelease \
  -PAPI_BASE_URL=https://api.yourdomain.com/ \
  -PPRIVACY_POLICY_URL=https://yourdomain.com/privacy-policy
```

### Option B: export environment variables

```bash
export API_BASE_URL=https://api.yourdomain.com/
export PRIVACY_POLICY_URL=https://yourdomain.com/privacy-policy
cd ArthamantriAndroid
./gradlew :app:bundleRelease
```

## 2) Release behavior included

- API HTTP logs are enabled only in debug builds.
- Release builds disable OkHttp logging.
- Drawer menu includes a Privacy Policy item that opens the configured URL.
- Privacy policy and Play Console Data Safety wording must match the exact production permissions:
  - SMS access for risky money-message checks.
  - Notification listener access for payment/financial prompt checks.
  - Usage access for UPI/payment app-open timing.
  - Overlay access for high-risk stop-and-verify warnings.
  - Notifications, foreground service, and boot receiver for monitoring and alert delivery.

## 2.1) Play Console privacy readiness

Before uploading a release:

- Host `frontend/privacy-policy.html` at a public HTTPS URL.
- Pass the hosted policy URL through `PRIVACY_POLICY_URL`.
- Recheck `PLAY_CONSOLE_CHECKLIST.md` against the production manifest.
- Do not claim raw message text never leaves the device. Current payment/risk inspection can send selected raw notification or payment-request text to the backend when needed for classification.
- Keep store listing copy aligned with onboarding: FinSaathi gives safety warnings and does not give loans, sell investments, replace banks, or ask for OTP, UPI PIN, Aadhaar, PAN, bank passwords, card details, or exact balance.

## 3) Configure release signing

Create a local file at project root:
- `keystore.properties` (never commit this file)

You can start from:
- `keystore.properties.example`

Required keys in `keystore.properties`:
- `storeFile`
- `storePassword`
- `keyAlias`
- `keyPassword`

If `keystore.properties` is missing, release builds fail instead of falling back to debug signing.

## 4) Build release AAB

```bash
cd ArthamantriAndroid
./gradlew :app:bundleRelease \
  -PAPI_BASE_URL=https://api.yourdomain.com/ \
  -PPRIVACY_POLICY_URL=https://yourdomain.com/privacy-policy
```

## 5) Output

- AAB path: `app/build/outputs/bundle/release/app-release.aab`

## 6) Recommended dev vs release usage

- During development, run only `debug` variant (`com.finsaathi.android.dev`).
- Keep release app uninstalled from emulator/device to avoid confusion.
- Build `release APK`/`release AAB` only when you need sideload or Play upload.

Debug install flow:

```bash
adb uninstall com.finsaathi.android
adb uninstall com.finsaathi.android.dev
cd /Users/karanakatle/Personal/BMAD/Finsaathi/ArthamantriAndroid
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell pm list packages | grep finsaathi
```

Debug builds default to `http://10.0.2.2:8765/` for emulator-to-local-backend testing. Pass `-PAPI_BASE_URL=...` only when you want a debug build to target another backend.

Expected package:
- `package:com.finsaathi.android.dev`

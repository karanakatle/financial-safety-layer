# Production Setup (Play Store / Pilot)

Use this when creating a real release build for testers/users.

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

If `keystore.properties` is missing, release build falls back to debug signing (not for production upload).

## 4) Build release AAB

```bash
cd ArthamantriAndroid
./gradlew :app:bundleRelease \
  -PAPI_BASE_URL=https://api.yourdomain.com/ \
  -PPRIVACY_POLICY_URL=https://yourdomain.com/privacy-policy
```

## 5) Output

- AAB path: `app/build/outputs/bundle/release/app-release.aab`

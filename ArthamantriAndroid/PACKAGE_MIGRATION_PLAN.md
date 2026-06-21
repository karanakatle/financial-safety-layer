# FinSaathi Package / Data Migration Plan

Last updated: 2026-06-20

## Decision

FinSaathi should use the final public Android application ID before the first Play Store listing:

- Release application ID: `com.finsaathi.android`
- Debug application ID: `com.finsaathi.android.dev`
- App name: `FinSaathi`

The inherited Kotlin source namespace remains temporarily:

- Internal source namespace: `com.arthamantri.android`
- Internal source path: `app/src/main/java/com/arthamantri/android`

This is deliberate. The public package identity is what matters for Play Store release continuity. A broad Kotlin namespace/source-path rename can be handled later as an internal refactor, but it should not block the first production package identity.

## Current Identifiers

| Identifier | Current value | Release decision |
|---|---|---|
| Gradle `applicationId` | `com.finsaathi.android` | Final public package ID |
| Debug app ID | `com.finsaathi.android.dev` | Separate dev install |
| Gradle `namespace` | `com.arthamantri.android` | Temporarily retained internal namespace |
| App prefs | `finsaathi_prefs` | Final pre-release app prefs |
| Config prefs | `finsaathi_android_prefs` | Final pre-release config prefs |
| Safety notification channel | `finsaathi_safety_alerts` | Final pre-release channel ID |
| Savings notification channel | `finsaathi_savings_nudges` | Final pre-release channel ID |
| Savings broadcast action | `com.finsaathi.android.action.RUN_SAVINGS_NUDGE` | Final action |

## Why Migrate Before First Public Release

Changing `applicationId` after Play Store release creates a different Android app identity. Existing users cannot receive it as a normal update, and app data/signing/reviews/store listing continuity become painful.

Because FinSaathi has not yet been publicly released, the package ID should be finalized now.

## Data Migration Position

For pre-release/debug testers:

- Existing `com.arthamantri.android.dev` installs should be uninstalled before installing `com.finsaathi.android.dev`.
- Existing local prefs may reset because this is a pre-release identity correction.
- Legacy pref backup exclusions are retained to avoid restoring old debug/internal state.

For public release:

- No public-user data migration is required if the first Play listing uses `com.finsaathi.android`.
- After public release, do not change `applicationId`.

## If Internal Namespace Is Renamed Later

If the Kotlin source namespace is later renamed to `com.finsaathi.android`, do it as a separate refactor:

1. Move source/test folders from `com/arthamantri/android` to `com/finsaathi/android`.
2. Rewrite Kotlin package declarations and imports.
3. Update ProGuard rules and documentation references.
4. Keep `applicationId = "com.finsaathi.android"` unchanged.
5. Run unit tests, debug build, release build, and device smoke tests.

## Release Notes Guidance

For internal testers:

> FinSaathi now uses its final Android package identity. Please uninstall older Arthamantri/FinSaathi dev builds before installing this build.

For Play release:

> First public FinSaathi Android release. Package identity: `com.finsaathi.android`.

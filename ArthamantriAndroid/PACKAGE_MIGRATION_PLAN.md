# FinSaathi Package / Data Migration Plan

Last updated: 2026-06-21

## Decision

FinSaathi should use the final public Android application ID before the first Play Store listing:

- Release application ID: `com.finsaathi.android`
- Debug application ID: `com.finsaathi.android.dev`
- Android source namespace: `com.finsaathi.android`
- App name: `FinSaathi`

The inherited Kotlin source namespace has now been migrated to FinSaathi before public release. The public package identity and source namespace are aligned.

## Current Identifiers

| Identifier | Current value | Release decision |
|---|---|---|
| Gradle `applicationId` | `com.finsaathi.android` | Final public package ID |
| Debug app ID | `com.finsaathi.android.dev` | Separate dev install |
| Gradle `namespace` | `com.finsaathi.android` | Final source namespace |
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

- Existing local prefs may reset when moving from old pre-release builds because this was a pre-release identity correction.
- Backup/data-extraction exclusions cover the current FinSaathi prefs and the old generic `pilot_prefs` file. Old-brand config-pref exclusions were removed because the current app no longer uses the inherited preference file name.

For public release:

- No public-user data migration is required if the first Play listing uses `com.finsaathi.android`.
- After public release, do not change `applicationId`.

## Completed Source Namespace Migration

Completed in Story 7.6 before public release:

1. Source/test folders moved to `com/finsaathi/android`.
2. Kotlin package declarations and imports use `com.finsaathi.android`.
3. Gradle namespace uses `com.finsaathi.android`.
4. ProGuard rules and active developer documentation were updated.
5. `applicationId = "com.finsaathi.android"` remains unchanged.
6. Unit tests, debug build, release build, and emulator launcher verification passed.

## Release Notes Guidance

For internal testers:

> FinSaathi now uses its final Android package identity and source namespace. Please uninstall older pre-release dev builds before installing this build.

For Play release:

> First public FinSaathi Android release. Package identity: `com.finsaathi.android`.

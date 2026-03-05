# Constants Guide

This project uses centralized constants to avoid scattered hardcoded values.

## Where to put what

- UI/localized text:
  - `app/src/main/res/values/strings.xml`
  - `app/src/main/res/values-hi/strings.xml`
  - Rule: any user-facing text must be in string resources, not Kotlin literals.

- Non-UI app constants:
  - `app/src/main/java/com/arthamantri/android/core/AppConstants.kt`
  - Use for:
    - preference keys
    - request codes
    - notification IDs/channel IDs
    - intent extra keys
    - timing/debounce values
    - secure settings keys
    - domain defaults and parser keyword lists
    - log tags

## Current sections in `AppConstants`

- `Locale`
- `Prefs`
- `RequestCodes`
- `Notifications`
- `Timing`
- `IntentExtras`
- `SecureSettings`
- `Domain`
- `Parsing`
- `LogTags`

## Rules for contributors

- Do not hardcode repeated keys/IDs/numbers in feature files.
- Add new constants to the most relevant `AppConstants` section.
- If no section fits, add a new section with a clear name.
- Keep constants names descriptive and stable.
- If a value is user-visible, keep it in string resources (not `AppConstants`).

## Quick examples

- Good:
  - `getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, MODE_PRIVATE)`
  - `delay(AppConstants.Timing.MONITOR_LOOP_DELAY_MS)`
  - `NotificationCompat.Builder(context, AppConstants.Notifications.SAFETY_CHANNEL_ID)`

- Avoid:
  - `getSharedPreferences("pilot_prefs", MODE_PRIVATE)`
  - `delay(3000)`
  - `NotificationCompat.Builder(context, "arthamantri_safety_alerts")`

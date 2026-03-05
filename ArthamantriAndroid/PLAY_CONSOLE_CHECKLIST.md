# Play Console Checklist (Arthamantri)

Use this before uploading `app-release.aab`.

## 1) App Content

- Privacy Policy URL is public and working over HTTPS.
- Contact email/support details are filled.
- Target audience and content declarations completed.

## 2) Data Safety Form

Document what is collected, why, and whether shared:

- Financial/sensitive behavioral data:
  - SMS-derived spend events
  - UPI/open-app risk events
  - Participant feedback and logs
- Device/app identifiers:
  - Android ID or pilot participant ID
- App activity data:
  - Monitoring state/actions

For each declared data type:
- Purpose: app functionality, analytics, fraud/safety support.
- Encryption in transit: `Yes` (HTTPS).
- Deletion request mechanism: define support email/process.

## 3) Permissions + Justifications

Ensure in-app explanation + policy text covers why each is needed:

- `RECEIVE_SMS` / `READ_SMS`: detect bank debit SMS for overspend/fraud signals.
- Notification listener service: detect UPI/payment notifications for risk alerts.
- Usage access: detect opening of UPI apps for stage-2 warning flow.
- Overlay (`SYSTEM_ALERT_WINDOW`): show USSD-style intervention overlay.
- `POST_NOTIFICATIONS`: fallback/high-priority alerts.
- Foreground service permissions: continuous monitoring service.

## 4) Sensitive Permission Declarations

For any restricted permission in Play declaration forms:
- Match declaration wording with in-app behavior.
- Provide demo video/screenshots if requested.
- Show clear user benefit and opt-in controls.

## 5) Release Readiness

- AAB built with production backend + privacy policy URL.
- Release signing configured with `keystore.properties`.
- Crash-free smoke tests on at least 2 physical Android devices.
- API endpoints reachable and stable.
- No debug/test URLs left in release build.

## 6) Store Listing Assets

- App name, short description, full description.
- Screenshots (phone, and optionally tablet).
- High-res icon and feature graphic.
- Privacy policy URL and support contact.

## 7) Testing Tracks

- Upload to Internal testing first.
- Validate install, onboarding, permissions, SMS/UPI flows.
- Then move to Closed testing (50–60 users).


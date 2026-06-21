# Play Console Checklist (FinSaathi)

Use this before uploading `app-release.aab`.

## 0) Package Identity

- Final Play Store application ID: `com.finsaathi.android`.
- Debug/development application ID: `com.finsaathi.android.dev`.
- Internal Kotlin namespace may still be `com.arthamantri.android`; this is not the Play Store app identity.
- Do not change `applicationId` after first public Play release.
- Review `PACKAGE_MIGRATION_PLAN.md` before creating the Play listing.

## 1) App Content

- Privacy Policy URL is public and working over HTTPS.
- Contact email/support details are filled.
- Target audience and content declarations completed.
- Store listing does not promise regulated financial advice, loan approval, investment returns, bank replacement, or fraud-prevention guarantees.
- Store listing uses the same positioning as onboarding: "financial safety warnings for risky money messages and payment moments."

## 2) Data Safety Form Draft

Use this as the first-pass Play Console Data Safety draft. Final answers must be rechecked before upload against the exact production build and backend configuration.

### Data Collected

- Personal info:
  - No name, email, phone number, Aadhaar, PAN, OTP, UPI PIN, bank password, card details, or exact bank balance is required by the app.
  - Incidental personal data may be processed if it appears inside SMS, notifications, sender IDs, payee labels, UPI handles, raw URLs, or payment-request text.
- Financial info:
  - Parsed spend/payment signals, approximate amounts, payment-request context, selected essential goals, optional rough money range/current-balance band, and safety-check outcomes.
- Messages:
  - Incoming SMS may be locally scanned when SMS access is granted.
  - SMS sender IDs, parsed categories, confidence, amount, timestamp, OTP/link/UPI flags, and URL/domain signals may be processed.
  - Notification title and text from non-messaging apps may be locally inspected when notification access is granted.
  - Complete SMS text is not sent for normal cashflow ingestion; parsed category/confidence/amount/timestamp/sender and risk signals are sent.
  - Selected raw notification or payment-request text can be sent for risk inspection when needed to classify payment, scam, or account-access risk.
- App activity:
  - Foreground UPI/payment app open events, selected link-context app open events such as WhatsApp, monitoring state, permission/setup state, language, consent state, alert actions, and user feedback.
- Web browsing:
  - Raw URLs, UPI deep links, clicked-link context, URL host, and resolved domain may be processed when they are present in messages, notifications, or inbound app links.
- Device or other IDs:
  - Android ID or generated participant/device identifier.
- Diagnostics:
  - App logs, event IDs, delivery state, queued telemetry state, crash/reliability diagnostics if enabled.

### Data Use Purposes

- App functionality: safety monitoring, warning generation, language/setup state, essential-goal personalization.
- Fraud prevention, security, and compliance: risky message/payment/account-access detection.
- Analytics and product improvement: usefulness feedback, false-positive learning, reliability diagnostics.

### Sharing, Encryption, and Deletion

- Data is transmitted over HTTPS.
- Data may be processed by infrastructure providers needed to run the backend, database, logging, diagnostics, or hosting.
- Data is not sold.
- Deletion request process: user contacts `support@finsaathi.app`.

## 3) Permissions + Justifications

Ensure in-app explanation + policy text covers why each is needed:

- `RECEIVE_SMS`: receive and scan newly incoming SMS for overspend/fraud signals.
- Notification listener service: detect UPI/payment notifications for risk alerts.
- Usage access: detect opening of UPI/payment apps and selected link-context apps so warnings can be timed.
- Overlay (`SYSTEM_ALERT_WINDOW`): show stop-and-verify warnings over the screen for important payment, cashflow, setup, fallback, or account-access moments.
- `POST_NOTIFICATIONS`: fallback/high-priority alerts.
- Foreground service permissions: continuous monitoring service.
- `RECEIVE_BOOT_COMPLETED`: restart monitoring after device reboot when the user has enabled monitoring.

## 4) Sensitive Permission Declarations

For any restricted permission in Play declaration forms:
- Match declaration wording with in-app behavior.
- Provide demo video/screenshots if requested.
- Show clear user benefit and opt-in controls.
- Explain that SMS and notification access are core to the safety-warning feature.
- Explain that usage access is used to detect relevant UPI/payment app opens and selected link-context app opens, not to build a general browsing/profile history.
- Explain that overlay is used for important safety warnings and has notification/activity fallback behavior when overlay is unavailable.
- Avoid claiming "raw text never leaves the device"; current implementation can send selected raw notification or payment-request text, sender/link metadata, payee labels, UPI handles, and raw URLs for inspection.

## 5) Store Listing Draft Copy

Short description draft:

> FinSaathi gives simple money-safety warnings for risky SMS, payment prompts, and UPI moments.

Full description guardrail copy:

> FinSaathi helps users pause before risky money decisions. With consent, it checks financial SMS, payment notifications, UPI app-open moments, selected link-context app moments, and suspicious payment/account-access prompts. It gives simple safety warnings in plain language and reminds users not to share OTP, UPI PIN, Aadhaar, PAN, bank passwords, or card details.
>
> FinSaathi does not give loans, sell investments, guarantee fraud prevention, or replace banks or financial advisors.

In-app permission copy alignment:

- Onboarding says FinSaathi checks financial SMS, notifications, selected payment-app/link moments, and alert actions for risky money messages and unsafe access signals.
- Permission setup says SMS/notifications are for risky money-message and payment-prompt checks.
- Usage access copy says it times warnings when payment apps or selected link-context apps are opened.
- Overlay copy says it shows stop-and-verify warnings for important safety moments.
- Consent copy discloses limited telemetry/feedback for safety, reliability, and research validation.

## 6) Release Readiness

- AAB built with production backend + privacy policy URL.
- Release signing configured with `keystore.properties`.
- Release package verified as `com.finsaathi.android`.
- Compliance/legal review completed before external pilot or public testing; see `docs/compliance-review-gate.md`.
- Crash-free smoke tests on at least 2 physical Android devices.
- API endpoints reachable and stable.
- No debug/test URLs left in release build.
- Data Safety form matches the production privacy policy and the exact permissions in `AndroidManifest.xml`.

### Compliance / Legal Review Gate

Before any external pilot, closed testing beyond the internal team, or partner-assisted rollout:

- complete the compliance/legal review in `docs/compliance-review-gate.md`
- confirm app copy does not contain investment advice, loan recommendation, lender ranking, or product sales
- confirm alerts do not recommend a specific financial product
- confirm high-risk or ambiguous cases have official-source, human-review, bank, NGO, or BC escalation wording
- confirm future AI explanation copy has hallucination/advice review before user exposure

## 7) Store Listing Assets

- App name, short description, full description.
- Screenshots (phone, and optionally tablet).
- High-res icon and feature graphic.
- Privacy policy URL and support contact.

## 8) Testing Tracks

- Upload to Internal testing first.
- Validate install, onboarding, permissions, SMS/UPI flows.
- Then move to Closed testing (50–60 users).

# FinSaathi External Legal / Privacy Review Packet

**Prepared date:** 2026-06-21  
**Prepared for:** qualified fintech legal reviewer, privacy reviewer, and partner-compliance reviewer  
**Product branch:** `release/finsaathi-mvp-safety-slice`  
**Review status:** pending external review  

## 1. Review Objective

This packet gives a reviewer enough product, privacy, permission, and compliance context to assess whether FinSaathi can proceed to a controlled pilot, partner-assisted pilot, internal testing track, or public release.

This packet is not legal advice. It is a structured review input for a qualified reviewer.

## 2. Product Scope

FinSaathi is a financial safety guardrail for risky money messages, payment prompts, suspicious schemes, and account-access moments.

FinSaathi can:

- detect potentially risky SMS, notification, payment-app, link, and UPI/payment contexts
- show simple Green, Yellow, or Red safety warnings
- explain why a message, offer, or payment prompt may be risky
- remind users not to share sensitive credentials or documents
- suggest safe next steps such as pause, verify through official sources, ask a trusted person, or contact bank support
- escalate ambiguous high-risk cases to human review or official-source verification

FinSaathi must not:

- give investment advice
- recommend loans or lenders
- rank lenders, apps, banks, or investment products
- sell financial products
- guarantee fraud prevention, income, returns, approval, or savings outcomes
- ask for OTP, UPI PIN, Aadhaar, PAN, bank password, card details, or exact bank balance

## 3. Demo Flow For Review

Screenshots are not attached in this packet. Use this demo flow and the local release-candidate app build for review. Product architecture diagrams are available under `docs/diagrams/`.

Current local review artifact:

- Release-candidate APK: `ArthamantriAndroid/app/build/outputs/apk/release/app-release.apk`
- Release configuration checkpoint: `docs/RELEASE_CONFIGURATION_CHECKPOINT.md`
- Important limitation: this APK is signed and buildable, but the configured hosted privacy URL currently returns `HTTP 503`, so it is not production-launch-ready.

Recommended reviewer walkthrough:

1. Install the release candidate APK.
2. Open FinSaathi.
3. Review product identity and consent copy.
4. Review permission explanation screens:
   - SMS
   - notification access
   - usage access
   - overlay access
   - post notifications
5. Complete Money Setup Lite with non-sensitive approximate values.
6. Trigger or inspect a safe sample risk alert.
7. Verify alert language:
   - risk label
   - reason for warning
   - safe next step
   - no loan, investment, lender, or product recommendation
8. Use the human-review escalation path for ambiguous/high-risk cases.
9. Review privacy policy, Play Data Safety draft, and compliance gate.

Relevant review files:

- `frontend/privacy-policy.html`
- `ArthamantriAndroid/PLAY_CONSOLE_CHECKLIST.md`
- `docs/compliance-review-gate.md`
- `docs/PERMISSION_TRUST_PILOT_SCRIPT.md`
- `docs/LEGAL_PRIVACY_REVIEW_DECISION_LOG.md`
- `research/pilot_rollout_checklist.md`
- `docs/IMPLEMENTATION_CHECKPOINT.md`
- `docs/RELEASE_CONFIGURATION_CHECKPOINT.md`

## 4. Android Permissions And Data Boundaries

| Permission / access | User benefit | Data processed | Boundary / concern for review |
|---|---|---|---|
| `RECEIVE_SMS` / `READ_SMS` | Detect debit, UPI, scam, OTP, account-access, and risky finance SMS signals | Incoming SMS may be locally scanned; parsed sender ID, amount, category, timestamp, risk flags, URL/domain/OTP/UPI signals may be processed | Complete SMS text should not be sent for normal cashflow ingestion; selected risky context may need backend inspection; verify Play policy fit |
| Notification listener | Detect payment, finance, account-access, and risky notification prompts | Non-messaging notification title/text, app/source, event metadata, risk signals | Avoid broad personal-notification profiling; verify exclusions and disclosures |
| Usage access | Time alerts when UPI/payment apps or selected link-context apps are opened | Foreground app events for supported payment/link contexts | Must not become general browsing/app profiling; review explanation and minimization |
| Overlay access | Show stop-and-verify warnings at high-risk moments | Alert title, message, risk level, user action | Must avoid dark patterns, fear, and excessive interruption; review fallback behavior |
| `POST_NOTIFICATIONS` | Show fallback/high-priority safety alerts | Notification alert content and user action | Must avoid spam and generic nudges; review opt-out and burden |
| Foreground service | Keep user-enabled monitoring active | Monitoring state, service status, diagnostics | Must clearly show persistent monitoring behavior |
| `RECEIVE_BOOT_COMPLETED` | Restart monitoring only after setup when user has enabled monitoring | Boot event and monitoring state | Must respect disabled monitoring state |
| Internet | Backend risk classification, telemetry, review export, support paths | Parsed signals, selected raw risk context, telemetry, feedback, participant/device identifier | Review transport, retention, deletion, and processor disclosures |

## 5. Data Collected / Processed

FinSaathi may process:

- SMS sender IDs, parsed spend/payment signals, amounts, timestamps, categories, and risk flags
- selected raw notification or payment-request text when needed for risk inspection
- URL, domain, and UPI deep-link signals when present
- app foreground context for supported payment and link-context apps
- alert risk level, alert reason, alert action, feedback, and delivery diagnostics
- language, consent status, permission state, selected essential goals, and optional approximate money setup values
- participant/device identifier for pilot instrumentation and reliability

FinSaathi does not require:

- OTP
- UPI PIN
- Aadhaar
- PAN
- bank password
- card details
- exact bank balance
- bank login
- investment account credentials

## 6. Backend / Upload Boundary

Normal cashflow ingestion should use parsed/minimized signals instead of full raw SMS text.

Selected risky notification, payment-request, link, or account-access context may be sent to the backend because risk classification needs context. This must be reviewed against the privacy policy, Play Data Safety draft, and user consent language.

Human review exports must avoid raw private SMS, OTPs, account details, PAN, Aadhaar, card details, UPI PINs, or bank passwords.

## 7. Prohibited Output Policy

FinSaathi must not display:

- investment advice: buy, sell, hold, switch, SIP, mutual fund, ETF, stock, crypto, gold scheme, bond, or allocation recommendation
- loan recommendation: specific lender, app, loan type, where to borrow, or whether a lender is best
- lender ranking, comparison, or marketplace guidance
- product sales or cross-selling for loans, credit cards, insurance, investments, pensions, or accounts
- guaranteed fraud prevention, guaranteed return, guaranteed income, guaranteed approval, or guaranteed repayment claims
- credit approval or repayment-capacity certification
- instructions to bypass bank/app security controls
- requests for OTP, UPI PIN, Aadhaar, PAN, bank password, card details, exact balance, or login credentials

Allowed safe outputs:

- risk labels: Green, Yellow, Red
- plain-language risk reason
- pause and verify guidance
- official-source escalation
- trusted-person/facilitator support
- general financial-literacy explanation
- non-product-specific safety reminders

## 8. Play Data Safety Draft Summary

The first-pass Play Data Safety draft is in `ArthamantriAndroid/PLAY_CONSOLE_CHECKLIST.md`.

Reviewer should verify:

- whether Play allows requested SMS access for this use case
- whether notification listener, usage access, and overlay declarations are acceptable
- whether incidental personal/financial data inside messages and notifications is disclosed correctly
- whether backend upload boundaries match actual implementation
- whether deletion and support processes are sufficient
- whether the store listing avoids regulated advice and overclaiming

## 9. Pilot Scope For Review

Proposed controlled pilot:

- facilitator-assisted or partner-assisted install
- 20-60 participants
- no unaudited self-serve public rollout
- no product sales
- no financial product recommendations
- no paid acquisition before legal/privacy review

Pilot must pause if:

- privacy policy does not match app behavior
- consent copy is unclear
- alert copy gives regulated advice
- app asks for sensitive credentials/documents
- user harm, harassment, or high false-alert burden is observed
- partner role, data access, or grievance handling is unclear

## 10. AI Safety Boundary

Current implemented AI explanation behavior is guarded and future-facing. It must remain constrained by:

- redacted/minimized input
- deterministic risk category and approved templates
- refusal of regulated product recommendations
- uncertainty wording and official-source verification
- human review for ambiguous high-risk cases
- output safety filter before display

Do not expose broader agentic AI behavior to real users until a separate hallucination/advice review passes.

## 11. Known Open Issues

| Issue | Current status | Reviewer concern |
|---|---|---|
| Hosted privacy policy URL | Configured URL currently returns `HTTP 503` from Render | Public/Play release must wait until a stable HTTPS URL is live |
| External legal/privacy review | Pending | Required before external pilot, scaled pilot, partner rollout, or public release |
| Physical-device smoke | Pending | Sensitive Android permissions and overlays need real-device validation |
| Keystore backup | Owner action pending | Release key continuity risk if local keystore/passwords are lost |
| Play SMS permission approval | Not yet reviewed by Google / legal | SMS permission may be policy-sensitive |

## 12. Reviewer Decision Log

Use `docs/LEGAL_PRIVACY_REVIEW_DECISION_LOG.md` to record reviewer identity, scope, findings, required changes, and Go / No-Go decision.

No external pilot, partner-assisted rollout, Play testing track, or public release should proceed until the relevant decision is recorded.

## 13. Packet Send Checklist

Before sending this packet to an external reviewer, include or confirm:

- `docs/LEGAL_PRIVACY_REVIEW_PACKET.md`
- `docs/LEGAL_PRIVACY_REVIEW_DECISION_LOG.md`
- `frontend/privacy-policy.html`
- `ArthamantriAndroid/PLAY_CONSOLE_CHECKLIST.md`
- `docs/compliance-review-gate.md`
- `docs/PERMISSION_TRUST_PILOT_SCRIPT.md`
- `research/pilot_rollout_checklist.md`
- `docs/IMPLEMENTATION_CHECKPOINT.md`
- `docs/RELEASE_CONFIGURATION_CHECKPOINT.md`
- release-candidate APK path or secure APK sharing link
- note that the hosted privacy policy URL is currently unavailable and must be fixed before Play/public release

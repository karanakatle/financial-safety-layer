# FinSaathi Permission Trust Pilot Script

## Purpose

Use this script to test whether 5-10 pilot users are willing to grant SMS, notification, usage access, and overlay permissions. The goal is to decide whether FinSaathi can work as a direct install, assisted install, or partner-led install.

Do not collect OTPs, UPI PINs, bank passwords, card details, Aadhaar, PAN, account numbers, or raw private SMS/notification content.

## Before The Session

- Use `docs/FACILITATOR_ONBOARDING_CARD.md` as the setup pack.
- Assign a participant code, not a real name.
- Confirm language preference.
- Prepare a timer.
- Prepare the observation sheet below.
- Tell the participant they can stop any time.

## Opening Script

Read this aloud:

FinSaathi gives simple safety nudges when a money message, payment app, or suspicious offer may create risk. It does not give loans, sell investments, or ask for OTP, UPI PIN, bank password, card details, Aadhaar, or PAN. Today we are only testing whether the setup feels understandable and trustworthy.

Ask:

- Are you comfortable trying the setup?
- Can I note your reactions without recording private messages?
- If anything feels confusing, irritating, or scary, please say it openly.

## Pilot Flow

1. Start timer when the app opens.
2. Ask participant to choose language.
3. Read consent aloud.
4. Ask participant to proceed through permissions:
   - SMS
   - Notification access
   - Usage access
   - Overlay access
5. Let the participant react naturally. Do not force a permission.
6. If the participant refuses, ask one gentle reason question:
   - What made this permission uncomfortable?
7. Trigger a safe sample alert or setup verification alert.
8. Ask overlay reaction:
   - Useful
   - Irritating
   - Scary
   - Confusing
9. Record whether the user would prefer:
   - Direct install
   - Assisted install
   - Bank/BC/NGO/college/community-assisted install

## Observation Sheet

| Field | Notes |
|---|---|
| Participant code | |
| Segment | Student / homemaker / daily wage / driver / shop worker / other |
| City | |
| Phone owner | Self / family / shared |
| Language | |
| Install mode tested | Direct / assisted / partner-led simulation |
| Start time | |
| End time | |
| Completed setup? | Yes / partial / no |
| Drop-off point | Language / consent / SMS / notification / usage / overlay / money setup / start monitoring |
| SMS permission outcome | Granted / denied / skipped |
| SMS denial reason | |
| Notification permission outcome | Granted / denied / skipped |
| Notification denial reason | |
| Usage access outcome | Granted / denied / skipped |
| Usage denial reason | |
| Overlay access outcome | Granted / denied / skipped |
| Overlay denial reason | |
| Overlay reaction | Useful / irritating / scary / confusing |
| Exact quote, if consented | |
| Facilitator help needed? | None / light / heavy |
| Recommended install motion | Direct / assisted / partner-led |
| Privacy boundary respected? | Yes / no |

## App Log Events To Check

The app should emit these safe events where applicable:

- `permission_onboarding_prompted`
- `permission_onboarding_deferred`
- `permission_step_sms_prompted`
- `permission_step_sms_granted`
- `permission_step_sms_denied`
- `permission_step_notifications_prompted`
- `permission_step_notifications_granted`
- `permission_step_notifications_denied`
- `permission_step_usage_prompted`
- `permission_step_usage_granted`
- `permission_step_usage_denied`
- `permission_step_overlay_prompted`
- `permission_step_overlay_granted`
- `permission_step_overlay_denied`
- `overlay_reaction_useful`
- `overlay_reaction_irritating`
- `overlay_reaction_scary` (facilitator-coded note, if observed)
- `overlay_reaction_confusing` (facilitator-coded note, if observed)

## Summary Endpoint

After sessions, use:

```bash
curl -s "$BASE/api/pilot/permission-trust-summary" \
  -H "x-pilot-admin-key: $PILOT_ADMIN_KEY"
```

Use the endpoint summary together with facilitator notes. The endpoint does not replace human notes because denial reasons and emotional reactions often need observation.

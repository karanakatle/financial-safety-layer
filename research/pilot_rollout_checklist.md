# FinSaathi Pilot Rollout Checklist

## Purpose
- Provide an operational checklist for a controlled research pilot rollout.
- Reduce rollout errors in identity tracking, storage durability, and onboarding quality.
- Freeze the first field week around correctness, not feature churn.

## Scope
This checklist is for:
- facilitator-assisted Android pilot rollout
- 20-60 participants
- controlled research deployment

This checklist is not for:
- open public consumer launch
- unaudited self-serve installs

## 0. Compliance / Legal Gate Before External Pilot

Before any external pilot, scaled pilot, or bank/NGO/BC-assisted field rollout:

- complete `docs/compliance-review-gate.md`
- record compliance/legal review owner and decision
- confirm no alert, script, or store copy contains investment advice, loan recommendation, lender ranking, or product sales
- confirm FinSaathi does not recommend a specific financial product
- confirm high-risk/ambiguous cases escalate to official bank support, NGO facilitator, BC/business correspondent, or human review
- confirm future AI explanation has hallucination/advice review before user exposure

No-Go conditions:

- privacy policy does not match SMS, notification, usage access, overlay, backend, or telemetry behavior
- consent copy does not explain sensitive permissions clearly
- alert copy gives regulated financial advice
- any workflow asks for OTP, UPI PIN, Aadhaar, PAN, bank password, card details, or exact balance
- partner onboarding lacks documented roles, grievance handling, and data-sharing boundaries

## 1. Backend Readiness
Run these against the deployed backend before the first participant.

```bash
BASE="https://arthamantri-api.onrender.com"
curl -s "$BASE/api/health"
curl -s "$BASE/api/literacy/storage-health"
curl -s "$BASE/api/literacy/status?participant_id=test_user"
curl -s "$BASE/api/literacy/debug-trace?participant_id=test_user"
```

Expected:
- health endpoint returns successfully
- `storage-health` returns the configured DB path
- literacy status/debug endpoints return JSON without error

## 2. Persistent Storage Verification
For deployed pilot environments:
1. use persistent disk
2. configure:

```text
PILOT_DB_PATH=/var/data/pilot_research.db
```

3. redeploy
4. verify:

```bash
curl -s "$BASE/api/literacy/storage-health"
```

Required outcome:
- DB path points to durable storage, not ephemeral app filesystem

## 3. Pilot Config Freeze
Before first participant:
- freeze backend URL
- freeze experiment name
- freeze variant assignment logic
- freeze literacy env vars unless a blocker is found

Do not tune live policy during week 1 unless correcting a real defect.

## 4. Build Pilot App
From the Android repo:

### Debug / internal validation
```bash
cd /Users/karanakatle/Personal/Python-OOS-Project/ArthamantriAndroid
./gradlew :app:assembleDebug -PAPI_BASE_URL=$BASE
```

### Pilot release APK
```bash
./gradlew :app:assembleRelease \
  -PAPI_BASE_URL=$BASE \
  -PPRIVACY_POLICY_URL=$BASE/privacy-policy.html
```

### Pilot AAB
```bash
./gradlew :app:bundleRelease \
  -PAPI_BASE_URL=$BASE \
  -PPRIVACY_POLICY_URL=$BASE/privacy-policy.html
```

## 5. Internal Dry Runs
Complete 3 dry runs before real users:
1. women-led cautious household
2. daily-cashflow worker
3. shared-phone/noise case

For each dry run:
- install app
- complete onboarding
- grant all required permissions
- save Money Setup Lite
- trigger SMS ingest
- trigger UPI-open path
- inspect debug trace

## 6. Facilitator Install Flow
For each real participant:
1. open app
2. select language
3. accept consent
4. complete Money Setup Lite
5. grant:
   - SMS/runtime permissions
   - notification access
   - usage access
   - overlay access
6. start monitoring
7. open Facilitator Setup Pack and verify all steps show complete

### Permission Trust Experiment
For 5-10 pilot users, run `docs/PERMISSION_TRUST_PILOT_SCRIPT.md` while using `docs/FACILITATOR_ONBOARDING_CARD.md`.

Capture:
- permission granted/denied/skipped outcome for SMS, notification access, usage access, and overlay access
- participant-stated denial reason where possible
- overlay reaction as useful, irritating, scary, or confusing
- whether facilitator help was none, light, or heavy
- final install-motion recommendation: direct, assisted, or partner-led

Check aggregate results:

```bash
curl -s "$BASE/api/pilot/permission-trust-summary" \
  -H "x-pilot-admin-key: $PILOT_ADMIN_KEY"
```

Use `research/permission_trust_pilot_report_template.md` for the final decision write-up.

## 7. Participant Identity Verification
For every participant:
- record the stable `participant_id`
- keep it in the pilot tracker sheet

Verify:

```bash
PID="<participant_id>"
curl -s "$BASE/api/literacy/debug-trace?participant_id=$PID"
```

Required outcome:
- one stable participant ID per install/profile
- no accidental participant collisions

## 8. Functional Live Checks

### SMS ingest path
After sending a qualifying debit SMS:

```bash
curl -s "$BASE/api/literacy/status?participant_id=$PID"
curl -s "$BASE/api/literacy/debug-trace?participant_id=$PID"
```

Confirm:
- daily spend updated
- recent literacy events include SMS activity
- alert features/log rows exist when alert fired

### UPI-open path
If risk is active, trigger UPI-open and verify:
- stage-2 alert appears
- pause applies on very high-risk cases

Manual API validation:

```bash
curl -X POST "$BASE/api/literacy/upi-open" \
  -H "Content-Type: application/json" \
  -d "{\"participant_id\":\"$PID\",\"app_name\":\"TestUPI\",\"intent_amount\":100}"
```

## 9. Research Instrumentation Checks
Assign experiment variant:

```bash
curl -X POST "$BASE/api/research/assignment" \
  -H "Content-Type: application/json" \
  -d "{\"participant_id\":\"$PID\",\"experiment_name\":\"adaptive_alerts_v1\"}"
```

Verify export path:

```bash
curl -s "$BASE/api/research/export/experiment-events"
```

Required outcome:
- experiment events are actually written before scaling enrollment

## 10. Week-1 Monitoring Routine
Check daily:
1. `storage-health`
2. 3 sample `debug-trace` calls
3. useful/dismiss feedback ratio
4. participants with zero activity
5. duplicate/missing participant IDs
6. alert burden anomalies

### Detector Calibration Review Loop
Run this once per week during the pilot, and after any serious participant complaint about a wrong or missed financial-risk alert:

```bash
curl -s "$BASE/api/pilot/detector-calibration-summary" \
  -H "x-pilot-admin-key: $PILOT_ADMIN_KEY"
```

Review categories:
- `false_positive_candidate`: the detector showed an alert, but the participant marked it `not_useful` or dismissed it. This does not automatically mean the detector was wrong; the team must confirm whether the alert was actually benign.
- `false_negative_candidate`: an approved ground-truth sample has a risky label such as `payment_outflow_risk` or `account_access_risk`, but the detector heuristic was benign, generic, unknown, or blank.

Regression sample process:
1. For a confirmed missed scam/risk sample, add a consent-safe or synthetic equivalent to `FinancialRiskMessageFixtures.missedScamRegressionSamples` through the fixture list and expect a non-green result.
2. For a confirmed benign Red alert, add a consent-safe or synthetic equivalent to `FinancialRiskMessageFixtures.benignSuppressionSamples` through the fixture list and expect a non-red result.
3. Do not copy raw private SMS, notification text, OTPs, account details, phone numbers, PAN, Aadhaar, card numbers, or UPI PINs into fixtures, Git, docs, or exports.
4. Update detector rules only after the fixture reproduces the miss or false alarm.
5. Rerun the Android detector tests and backend calibration-summary tests before changing pilot thresholds.

## 11. Stop Conditions
Pause new enrollment if any of these happen:
1. participant state resets unexpectedly
2. SMS ingest stops appearing
3. alert burden spikes abnormally
4. multiple installs share the same participant ID
5. Hindi/English alert rendering breaks

## 12. Freeze Rule For First Live Week
Allowed:
- correctness bug fixes
- deployment/storage fixes
- logging fixes

Not allowed:
- feature additions
- threshold tuning without evidence
- UI churn unrelated to correctness

## 13. Minimum Pilot Artifacts
Maintain:
- participant tracker sheet
- facilitator install log
- issue log
- weekly research export snapshot
- dropout note for each participant who stops using the app

## 14. Rollout Sequence
Recommended order:
1. 3 internal dry runs
2. 5 assisted pilot users
3. 10-15 users after 3 stable days
4. 20-30 users after week-1 stability
5. 50-60 users only after instrumentation and persistence are stable

## 15. Final Go/No-Go Gate
Go only if:
1. backend persistence is verified
2. Android build is installed and validated
3. onboarding + permissions are working
4. SMS + UPI-open loop is verified
5. debug-trace and research export are verified
6. compliance/legal review is complete for the external pilot scope

## Bottom Line
The rollout should be treated as:
- facilitator-assisted
- storage-audited
- instrumentation-first
- feature-frozen during the first live week

That is the correct shape for a research-grade pilot rather than a consumer launch.

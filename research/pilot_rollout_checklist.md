# Arthamantri Pilot Rollout Checklist

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

## Bottom Line
The rollout should be treated as:
- facilitator-assisted
- storage-audited
- instrumentation-first
- feature-frozen during the first live week

That is the correct shape for a research-grade pilot rather than a consumer launch.

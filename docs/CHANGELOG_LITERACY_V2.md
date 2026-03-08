# Literacy Safety v2 Changelog

## Implemented

### 1) Continuous adaptation
- Auto policy adapts both `daily_safe_limit` and `warning_ratio`.
- Adaptation uses recent spend behavior with smoothing to avoid abrupt changes.
- Files:
  - `backend/main.py`
  - `backend/pilot/storage.py`

### 2) Catastrophic-risk override
- Added explicit catastrophic override logic:
  - absolute amount threshold
  - amount vs limit multiplier threshold
  - projected spend vs limit cap threshold
- Override works during warm-up as well.
- Config/env:
  - `LITERACY_CATASTROPHIC_ABSOLUTE`
  - `LITERACY_CATASTROPHIC_MULTIPLIER`
  - `LITERACY_CATASTROPHIC_PROJECTED_CAP`
- Files:
  - `backend/literacy/safety_monitor.py`
  - `backend/config/literacy_policy.py`

### 3) Proactive UPI-open gating + friction
- If risk is active on UPI-open, stage-2 alert is generated.
- If risk is very high, backend returns `pause_seconds=5`.
- Android overlay/fullscreen alerts enforce countdown before confirm actions.
- No formal bank/UPI-company integration required for this flow.
- Files:
  - `backend/main.py`
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/model/LiteracyDtos.kt`
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/notify/AlertNotifier.kt`
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/notify/OverlayAlertWindow.kt`
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/notify/AlertDisplayActivity.kt`

### 4) Contextual alert intensity + scoring + persistence
- Added contextual scoring pipeline.
- Persisted alert features in SQLite `alert_features`.
- Logged fields:
  - `alert_id`
  - `participant_id`
  - `timestamp`
  - `amount`
  - `projected_spend`
  - `daily_safe_limit`
  - `spend_ratio`
  - `txn_anomaly_score`
  - `hour_of_day`
  - `rapid_txn_flag`
  - `upi_open_flag`
  - `recent_dismissals_24h`
  - `risk_score`
  - `confidence_score`
  - `tone_selected`
  - `frequency_bucket`
- Added suppression bucket `suppressed` and tone selection (`soft`/`firm`/`hard`).
- Files:
  - `backend/main.py`
  - `backend/pilot/storage.py`

### 5) warning_ratio contextual adaptation upgrade
- `warning_ratio` now adapts using contextual aggregates, not only volatility.
- Inputs include:
  - volatility from spend history
  - average risk score
  - average confidence score
  - hard-alert rate
  - suppressed-alert rate
  - dismissals in last 7 days
- Ratio behavior:
  - clamped to `0.82 - 0.95`
  - smoothed with previous value
- Files:
  - `backend/main.py`
  - `backend/pilot/storage.py`

### 6) Data consistency and debugging improvements
- Event logging now consistently writes `participant_id` in literacy event paths.
- Added hard reset endpoint for deterministic retesting:
  - `POST /api/literacy/reset-hard`
- Added Android-side participant-id trace in SMS ingest logs for diagnosis.
- Files:
  - `backend/main.py`
  - `backend/pilot/storage.py`
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/repo/LiteracyRepository.kt`
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/sms/BankSmsReceiver.kt`
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/model/LiteracyDtos.kt`

## Validation
- Python tests: `10 passed`.
- Android compile check: `:app:compileDebugKotlin` passed.
- Added/updated tests include:
  - catastrophic override test in `tests/test_literacy_monitor.py`
  - policy/feature summary checks in `tests/test_pilot_storage_policy.py`

## Notes
- Existing unrelated modified files were intentionally not reverted.
- Render free-instance restarts can reset effective state expectations for test sessions unless persistence strategy is used.

## Added in this update

### 7) Money Setup Lite + essential-goal envelope
- Added participant-level profile API:
  - `GET /api/literacy/essential-goals`
  - `POST /api/literacy/essential-goals`
- Profile stores:
  - cohort (`women_led_household` / `daily_cashflow_worker`)
  - up to 2 essential goals
  - language and setup-skipped flag
- Alert scoring now incorporates goal-protection pressure.

### 8) Explainability and trust enrichment
- Alert payload now includes:
  - `risk_level`
  - `why_this_alert`
  - `next_best_action`
  - `essential_goal_impact`
- Alert message body now carries transparent “why + next step” lines in user language.

### 9) Research observability + experiment plumbing
- Added participant-level debug trace:
  - `GET /api/literacy/debug-trace`
- Added storage health endpoint:
  - `GET /api/literacy/storage-health`
- Added A/B research APIs:
  - `POST /api/research/assignment`
  - `POST /api/research/event`
  - `GET /api/research/export/experiment-events`

### 10) Pilot customer-protection workflow
- Added grievance APIs for complaint-to-resolution path:
  - `POST /api/pilot/grievance`
  - `GET /api/pilot/grievance`
  - `POST /api/pilot/grievance/status`

### 11) Durability support
- Backend now accepts `PILOT_DB_PATH` env var to place SQLite DB on durable storage.

### 12) Confidence-gated essential classification + anti-bias feedback learning
- Added confidence-gated transaction goal inference with `unknown` fallback when evidence is weak.
- Added merchant-memory layer for participant-specific improvement over time.
- Added bias guards:
  - memory-only essential inference is confidence-capped
  - essential learning updates are constrained to explicit supported goals
- Added feedback API:
  - `POST /api/literacy/essential-feedback`
  - stores structured feedback and updates goal memory safely
- Added persistence tables:
  - `goal_memory`
  - `goal_feedback`
  - `alert_goal_context`
- Added alert explainability fields:
  - `txn_goal_inferred`
  - `txn_goal_confidence`
  - `txn_goal_confidence_gate_passed`
  - `txn_goal_inference_source`
- Files:
  - `backend/main.py`
  - `backend/pilot/storage.py`
  - `tests/test_literacy_api_extensions.py`
  - `tests/test_pilot_storage_policy.py`

## Validation (latest)
- Python tests: `18 passed`.
- Python compile checks: `backend/main.py`, `backend/pilot/storage.py`, test modules compile cleanly.

### 13) Android onboarding and facilitator-assisted setup wiring
- Money Setup Lite is now wired in Android onboarding sequence:
  - language -> consent -> money setup -> permission setup -> monitoring.
- Added Money Setup entry points:
  - drawer menu item: `Money Setup Lite`
  - Help dialog button: `Edit Money Setup`
- Added Facilitator-assisted onboarding pack in app:
  - drawer menu item: `Facilitator Setup Pack`
  - Help dialog button: `Open Facilitator Pack`
  - step-status dialog with one-tap actions (language, consent, money setup, permissions, start monitoring)
- Added printable field card for assisted onboarding:
  - `docs/FACILITATOR_ONBOARDING_CARD.md`
- Files:
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/MainActivity.kt`
  - `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/core/AppConstants.kt`
  - `ArthamantriAndroid/app/src/main/res/layout/activity_main.xml`
  - `ArthamantriAndroid/app/src/main/res/layout/dialog_money_setup.xml`
  - `ArthamantriAndroid/app/src/main/res/layout/dialog_facilitator_pack.xml`
  - `ArthamantriAndroid/app/src/main/res/layout/dialog_help_setup.xml`
  - `ArthamantriAndroid/app/src/main/res/menu/drawer_menu_collapsed.xml`
  - `ArthamantriAndroid/app/src/main/res/menu/drawer_menu_expanded.xml`
  - `ArthamantriAndroid/app/src/main/res/values/strings.xml`
  - `ArthamantriAndroid/app/src/main/res/values-hi/strings.xml`

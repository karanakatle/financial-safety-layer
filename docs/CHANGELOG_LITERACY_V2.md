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

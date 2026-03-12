# Arthamantri Pilot Protocol v1 (Research-First)

## Scope Freeze
- Cohorts:
  - `women_led_household`
  - `daily_cashflow_worker`
- Use cases:
  - overspending prevention
  - fraud prevention
  - essential-goal savings behavior

## Readiness Note
- Simulator phase-1 is frozen as the pre-pilot baseline:
  - `research/simulator/PHASE1_FREEZE.md`
  - `research/simulator/SWEEP_INTERPRETATION.md`
- Next work priority is pilot/readiness planning, not further uncontrolled simulator expansion.
- Phase-2 learning path is documented in:
  - `research/parameter_learning_plan_v1.md`
- Operational rollout checklist is documented in:
  - `research/pilot_rollout_checklist.md`

## Study Design
- Design: randomized A/B at participant level.
- Experiment name: `adaptive_alerts_v1`.
- Variants:
  - `adaptive`: full contextual pipeline (`risk/confidence/tone/frequency/pause`).
  - `static_baseline`: baseline intervention policy for comparative analysis.
- Assignment API: `POST /api/research/assignment`.

## Minimum Sample
- Pilot target: 50-60 participants.
- Minimum analysis-ready sample:
  - >= 20 participants per variant, or
  - >= 14 days of active telemetry per variant.

## Primary Hypotheses
1. Adaptive variant reduces hard-alert fatigue vs static baseline.
2. Explainable alert content improves useful-feedback rate.
3. Essential-goal envelope reduces late-week risk concentration.

## Primary Metrics
- `useful_rate`: useful / (useful + not_useful + dismissed)
- `dismiss_rate`: dismissed / total_feedback_events
- `hard_alert_rate`: hard_bucket_alerts / total_alerts
- `suppression_rate`: suppressed / candidate_alerts
- `stage2_conversion`: stage2_alerts / stage1_sessions
- `goal_pressure_incidence`: alerts with `essential_goal_impact` / total alerts

## Secondary Metrics
- 7-day spend stabilization (variance and spike count).
- Time-to-action after alert feedback event.
- Retention proxy: active days per participant/week.
- Hindi/English split performance for useful-rate.

## Data Collection
- Structured events:
  - `POST /api/research/event`
  - `GET /api/research/export/experiment-events`
- Debug/audit:
  - `GET /api/literacy/debug-trace?participant_id=<id>`
- Alert features persisted in `alert_features` table.

## Quality Gates Before Analysis
1. Participant identity consistency verified (single active `participant_id` per install profile).
2. At least one stage1 and one stage2 path observed in each variant.
3. Hard reset only for controlled test sessions, not production pilot users.
4. Storage durability verified (`PILOT_DB_PATH` on durable disk in deployed environments).

## Analysis Plan
- Compare adaptive vs static baseline with:
  - effect size for useful-rate and dismiss-rate.
  - confidence intervals for hard-alert-rate and suppression-rate.
- Segment analysis:
  - cohort-wise (`women_led_household` vs `daily_cashflow_worker`)
  - language-wise (`en` vs `hi`)
- Report both:
  - aggregate outcomes
  - per-participant distribution to detect outlier bias.

## Phase-2 Calibration Bridge
After the first pilot telemetry window:
- fit interpretable response models for `useful`, `dismiss`, and `prevent`
- calibrate simulator severity assumptions from real participant outcomes
- convert learned evidence into conservative production threshold updates

See:
- `research/parameter_learning_plan_v1.md`

## Exclusion Rules
- participants with < 3 active days.
- sessions with inconsistent clock/timestamp errors.
- synthetic emulator load tests mixed into production pilot telemetry.

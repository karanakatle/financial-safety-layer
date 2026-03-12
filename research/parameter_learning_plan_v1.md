# Arthamantri Phase-2 Parameter Learning Plan

## Purpose
- Replace simulator-only assumptions with pilot-calibrated response parameters.
- Learn how real participants respond to `soft`, `medium`, and `hard` alerts.
- Use pilot evidence to improve:
  - simulator realism
  - production alert policy
  - research claims for papers/patent work

## Why This Exists
The current simulator includes hand-set behavioral assumptions such as severity response bonuses in `research/simulator/runner.py`.

Those values are useful for Phase-1 synthetic research, but they are still assumptions. Phase-2 converts them into evidence-backed estimates from real pilot telemetry.

## Key Question
For each cohort and context, estimate:
- when an alert is likely to be useful
- when it is likely to be dismissed
- when it is likely to prevent risky action
- when it is protective but inconvenient

## Phase-2 Scope
- Research-first, not production ML deployment.
- Start with interpretable models, not black-box agents.
- Use participant-level pilot data from real Android usage.
- Keep current deterministic guardrails in production while learning.

## Logging Requirements
The following fields should be available per alert decision or feedback event.

### Core Identity
- `alert_id`
- `participant_id`
- `timestamp`
- `variant` (`adaptive` / `static_baseline`)
- `language`
- `cohort`

### Decision Context
- `severity`
- `risk_level`
- `risk_score`
- `confidence_score`
- `tone_selected`
- `frequency_bucket`
- `pause_seconds`
- `threshold_risk_active`
- `stage`
- `source` (`bank_sms`, `upi_open`, etc.)

### Financial Context
- `amount`
- `projected_spend`
- `daily_safe_limit`
- `spend_ratio`
- `txn_anomaly_score`
- `hour_of_day`
- `rapid_txn_flag`
- `upi_open_flag`
- `recent_dismissals_24h`

### Goal/Resilience Context
- `essential_goal_impact`
- `txn_goal_inferred`
- `txn_goal_confidence`
- `txn_goal_confidence_gate_passed`
- `txn_goal_inference_source`

### Outcome Labels
- `feedback_action`
  - `useful`
  - `not_useful`
  - `dismissed`
  - `ignored`
- `preventive_inconvenient`
- `followed_by_risky_spend_within_window`
- `followed_by_upi_open_within_window`
- `retained_day_7`
- `retained_day_14`

## Derived Labels To Train
From the logged data, define these supervised targets.

### 1. Useful Alert Model
Target:
- `y_useful = 1` if user explicitly marked useful
- else `0`

Goal:
- estimate probability that a given alert style is perceived as useful

### 2. Dismissal Model
Target:
- `y_dismiss = 1` if dismissed
- else `0`

Goal:
- estimate fatigue/rejection risk

### 3. Prevention Model
Target:
- `y_prevent = 1` if risky follow-up did not occur inside a fixed observation window after a stage-2 or high-risk alert`
- else `0`

Recommended first window:
- 15 minutes for UPI-open
- same-day for SMS threshold events

### 4. Protective But Inconvenient Model
Target:
- `y_inconvenient = 1` if user marks not useful/dismissed but no risky follow-up occurs and goal-protection context is present

Goal:
- separate “annoying but helpful” from pure false positives

## First Models To Fit
Use interpretable baselines first.

### Model A: Useful Probability
- Logistic regression
- Inputs:
  - `severity`
  - `risk_score`
  - `confidence_score`
  - `spend_ratio`
  - `txn_anomaly_score`
  - `recent_dismissals_24h`
  - `cohort`
  - `language`
  - `source`
  - `essential_goal_impact`

### Model B: Dismiss Probability
- Logistic regression
- Inputs:
  - `severity`
  - `tone_selected`
  - `frequency_bucket`
  - `pause_seconds`
  - `recent_dismissals_24h`
  - `cohort`
  - `shared_phone_proxy`

### Model C: Prevention Probability
- Logistic regression or shallow gradient boosting
- Inputs:
  - `severity`
  - `risk_score`
  - `confidence_score`
  - `pause_seconds`
  - `source`
  - `fraud_like_proxy`
  - `stage`

## Shared-Phone Proxy
If no explicit shared-phone flag exists yet, approximate with:
- inconsistent app-open patterns
- conflicting goal feedback
- high merchant/noise variance
- repeated language/context shifts on one device

This should remain a research proxy until explicit assisted/shared-phone data is available.

## Training Strategy
1. Fit models on pilot week-1 to week-4 data.
2. Use participant-level train/validation split, not event-level random split.
3. Evaluate separately for:
  - `women_led_household`
  - `daily_cashflow_worker`
  - Hindi vs English
  - normal vs fraud-heavy vs essential-pressure contexts

## Metrics For Model Quality
- AUROC
- calibration error
- precision/recall for `y_useful`
- precision/recall for `y_dismiss`
- prevention lift vs baseline for `y_prevent`

Do not optimize only for AUROC. Calibration matters because policy thresholds depend on well-scaled probabilities.

## How To Use Learned Parameters

### 1. Update Simulator
Replace hand-set severity response assumptions in `research/simulator/runner.py` with learned coefficients or lookup tables.

Example:
- instead of fixed `hard -> +0.18`, estimate:
  - `hard` benefit by cohort
  - `medium` benefit by cohort
  - dismissal penalty by cohort and context

### 2. Update Production Policy Conservatively
Do not replace deterministic guardrails immediately.

Use learned results to tune:
- when to downgrade from `hard` to `medium`
- when to suppress
- when to add pause friction
- when to soften alerts for essential-goal contexts
- when to strengthen fraud-week handling

### 3. Keep Guardrails Deterministic
Even after learning:
- catastrophic override stays rule-based
- high-confidence fraud-risk escalation stays bounded
- stage-2 pause remains gated by deterministic safety limits

## Hypotheses For Phase-2
1. `hard` severity improves prevention for fraud-prone users more than for cautious users.
2. `medium` severity gives the best usefulness-to-dismissal tradeoff for women-led households.
3. `pause_seconds` improves prevention in UPI-open high-risk contexts, but hurts usefulness if overused.
4. `shared_phone` conditions require lower escalation frequency to preserve trust.

## Minimal Sample Guidance
Before trusting learned parameters:
- at least 200-300 alert events total
- at least 30-50 stage-2 / high-risk events
- at least 15+ participants per main cohort

Below that, use results only directionally.

## Deliverables
Phase-2 should produce:
1. a pilot-calibrated parameter table
2. a model evaluation note
3. simulator updates with learned values
4. a conservative production tuning proposal
5. research figures for paper/patent appendix

## Output Artifact Template
- `research/phase2_parameter_estimates.csv`
- `research/phase2_model_report.md`
- `research/phase2_policy_update_proposal.md`

## Recommended Order
1. finish pilot logging verification
2. run 4-8 weeks pilot
3. export experiment data
4. fit simple interpretable models
5. validate calibration by cohort
6. update simulator
7. update production thresholds conservatively
8. run next A/B cycle

## What Not To Do Yet
- do not deploy an unconstrained agentic policy directly to production
- do not train black-box models before baseline telemetry quality is verified
- do not merge simulator-only assumptions into publication claims as if they were human-validated findings

## Bottom Line
Phase-2 parameter learning is the bridge between:
- deterministic prototype logic
- real pilot evidence
- later ML / agentic policy research

It is the step that turns “reasonable assumptions” into “measured participant response behavior.”

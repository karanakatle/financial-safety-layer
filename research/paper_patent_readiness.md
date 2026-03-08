# Paper + Patent Readiness Checklist

## Current Stage
- Status: prototype + telemetry-ready system.
- Suitable now for:
  - system/demo paper
  - pilot protocol paper
- Not yet sufficient alone for:
  - strong empirical full paper
  - final patent claims without pilot evidence.

## Novelty Stack to Evidence
1. Multi-signal risk-confidence scoring for low-data users.
2. Adaptive intervention intensity (`hard/soft/suppressed`) with fatigue-aware control.
3. UPI-open pre-payment friction (`pause_seconds`) conditioned on high risk.
4. Essential-goal envelope for resilience-aware alerting.

## Evidence Needed for Strong Publication
1. A/B comparison (`adaptive` vs `static_baseline`) with confidence intervals.
2. Ablation study:
   - remove confidence
   - remove suppression
   - remove goal envelope
   and measure degradation.
3. Outcome stability over at least 8-12 weeks.
4. Language parity analysis for Hindi vs English.

## Evidence Needed Before Final Patent Filing
1. Architecture diagram + flow claims tied to implemented endpoints.
2. Method claims with deterministic scoring + adaptation loop.
3. Pilot evidence packet:
   - reduced alert fatigue
   - improved useful-response rate
   - improved risk intervention timing.
4. Defensive prior-art mapping against generic budgeting/alert apps.

## Suggested Publication Path
1. Short-term (now):
   - workshop/system paper on architecture + deterministic policy + early pilot telemetry.
2. Mid-term (after pilot):
   - full empirical paper with A/B + ablation + cohort outcomes.
3. Long-term:
   - paper on adaptive low-literacy financial copilot design for underserved populations.

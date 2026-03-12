# Scenario Sweep Interpretation

This note explains how to read the simulator phase-1 sweep output.

## How to read delta columns
- Positive delta means `adaptive` is higher than `static_baseline`.
- Negative delta means `adaptive` is lower than `static_baseline`.

Metric direction matters:
- `useful Δ`: higher is better
- `beneficial Δ`: higher is better
- `dismiss Δ`: lower is better
- `hard Δ`: lower is better
- `prevent Δ`: higher is better
- `retain Δ`: higher is better

## Phase-1 conclusion
Across the current preset sweep, the adaptive policy shows a clear and repeatable burden reduction effect:
- lower `hard_alert_rate`
- lower `dismiss_rate`

This is the strongest stable result in the simulator.

At the same time, adaptive is not yet uniformly better on total protection value:
- `beneficial_rate` is mixed or slightly worse in several scenarios
- `prevent_rate` still weakens in some fraud/emergency conditions
- `retain_rate` is currently flat in the sweep

## Research interpretation
The correct reading is:

`adaptive is clearly gentler than static, but not yet consistently smarter in fraud and emergency scenarios`

That means the current policy is improving fatigue/burden management, but still needs further calibration before it can be claimed as the stronger overall intervention strategy.

## Scenario-level reading
- `default`: adaptive is promising; burden drops and protection is directionally competitive
- `festival_spend`: adaptive is less harsh and less dismissed, but net benefit still needs work for some personas
- `fraud_week`: adaptive remains too soft in concentrated fraud conditions
- `medical_emergency`: adaptive is calmer, but must be careful not to under-protect genuine emergency risk
- `shared_phone_noise_heavy`: adaptive now improves the targeted shared-phone persona under the dedicated noise-heavy preset

## What Phase-1 proves
- the simulator can reveal subgroup differences, not only averages
- adaptive burden reduction is real
- shared-phone and essential-spend personas need dedicated handling
- scenario-specific tuning is necessary for rigorous policy development

## What Phase-1 does not prove
- real user trust
- real-world retention
- field effectiveness
- ML or agentic superiority

## Next step
Move from simulator iteration to pilot/readiness planning:
1. facilitator-led onboarding and consent
2. deployment durability checks
3. participant identity consistency checks
4. A/B pilot execution with real telemetry

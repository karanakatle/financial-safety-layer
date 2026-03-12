# Simulator Phase-1 Freeze

## Status
Simulator phase-1 is frozen as the current pre-pilot research baseline.

## Included in Phase-1
- deterministic cohort/persona simulator
- adaptive vs static baseline comparison
- per-persona comparison output
- scenario presets:
  - `default`
  - `fraud_week`
  - `festival_spend`
  - `medical_emergency`
  - `shared_phone_noise_heavy`
- severity-aware alert mix (`soft`, `medium`, `hard`)
- split feedback outcomes:
  - `useful`
  - `preventive_inconvenient`
  - `dismissed`
  - `ignored`

## Exit criteria met
- all simulator tests passing
- scenario presets runnable from CLI
- aggregate and per-persona deltas visible
- targeted shared-phone and cautious-persona tuning path established

## Not part of Phase-1
- real-user trust validation
- ML or agentic policy learning
- causal outcome claims beyond simulation

## Next focus
Move effort from simulator expansion to pilot/readiness planning:
1. participant recruitment and facilitator workflow
2. pilot instrumentation sanity checks
3. durable deployment verification
4. field protocol execution and A/B data collection

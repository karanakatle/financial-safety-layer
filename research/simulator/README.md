# Synthetic Cohort Simulator

This package provides a deterministic, rule-based simulation scaffold for Arthamantri research.

## Purpose
- stress-test alert policy before field deployment
- compare `adaptive` vs `static_baseline`
- simulate happy-path and adverse-path cohort behavior
- generate reproducible research metrics without claiming real-user trust

## Files
- `personas.py`: cohort/persona definitions
- `scenarios.py`: synthetic event timeline generation
- `runner.py`: monitor-driven simulation execution
- `metrics.py`: aggregate outcome metrics
- scenario presets: `default`, `fraud_week`, `festival_spend`, `medical_emergency`, `shared_phone_noise_heavy`

## Design boundaries
- This is not a substitute for a field pilot.
- This is not an ML agent.
- This is a deterministic baseline to tune policy and generate pre-pilot evidence.
- The adaptive simulator policy is persona-aware: it is intentionally calmer for cautious/shared-phone personas and stricter for fraud-prone personas.

## Example
```python
from research.simulator import SimulationConfig, SimulationRunner, default_personas

runner = SimulationRunner(SimulationConfig(days=14, seed=21))
report = runner.run(default_personas(), variant="adaptive")
print(report.aggregate())
```

## One-command comparison
```bash
./scripts/run_simulator_comparison.sh
```

## One-command scenario sweep
```bash
./scripts/run_simulator_sweep.sh
```

Optional:
```bash
./scripts/run_simulator_comparison.sh --days 30 --seed 31
./scripts/run_simulator_comparison.sh --format json
./scripts/run_simulator_comparison.sh --no-adverse-events
./scripts/run_simulator_comparison.sh --scenario fraud_week
./scripts/run_simulator_comparison.sh --scenario festival_spend
./scripts/run_simulator_comparison.sh --scenario medical_emergency
./scripts/run_simulator_comparison.sh --scenario shared_phone_noise_heavy
./scripts/run_simulator_sweep.sh --days 30 --seed 31
```

The CLI prints:
- aggregate adaptive vs static metrics
- persona-by-persona comparison blocks with alert mix, usefulness, dismissal, prevention, retention, and final trust score
- `preventive_inconvenient_rate` and `beneficial_rate` so protective-but-annoying alerts are not collapsed into pure failure

## Suggested use
1. Run `adaptive` and `static_baseline` on the same persona set.
2. Compare:
   - `useful_rate`
   - `preventive_inconvenient_rate`
   - `beneficial_rate`
   - `dismiss_rate`
   - `hard_alert_rate`
   - `prevention_rate`
   - `retention_rate`
3. Inspect persona-by-persona output to find which cohort/profile benefits or degrades under the adaptive policy.
4. Tune policy before live-pilot rollout.

## Phase-1 freeze
Simulator phase-1 is now frozen as the pre-pilot baseline.
See:
- `research/simulator/PHASE1_FREEZE.md`
- `research/simulator/SWEEP_INTERPRETATION.md`

## Scenario presets
- `default`: mixed everyday spending with occasional adverse events
- `fraud_week`: concentrated suspicious UPI attempts across the window
- `festival_spend`: temporary overspend pressure around a festival cluster
- `medical_emergency`: one major essential emergency spend spike in the window
- `shared_phone_noise_heavy`: repeated shared-device noise and context contamination stress test

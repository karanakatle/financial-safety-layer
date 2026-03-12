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

## Design boundaries
- This is not a substitute for a field pilot.
- This is not an ML agent.
- This is a deterministic baseline to tune policy and generate pre-pilot evidence.

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

Optional:
```bash
./scripts/run_simulator_comparison.sh --days 30 --seed 31
./scripts/run_simulator_comparison.sh --format json
./scripts/run_simulator_comparison.sh --no-adverse-events
```

## Suggested use
1. Run `adaptive` and `static_baseline` on the same persona set.
2. Compare:
   - `useful_rate`
   - `dismiss_rate`
   - `hard_alert_rate`
   - `prevention_rate`
   - `retention_rate`
3. Tune policy before live-pilot rollout.

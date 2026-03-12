from __future__ import annotations

import argparse
import json

from research.simulator.personas import default_personas
from research.simulator.runner import SimulationConfig, SimulationRunner


def build_comparison(days: int, seed: int, include_adverse_events: bool) -> dict:
    personas = default_personas()
    runner = SimulationRunner(
        SimulationConfig(days=days, seed=seed, include_adverse_events=include_adverse_events)
    )
    adaptive = runner.run(personas, variant="adaptive").aggregate()
    static = runner.run(personas, variant="static_baseline").aggregate()
    delta = {
        key: round(adaptive[key] - static[key], 4)
        for key in adaptive.keys()
        if isinstance(adaptive[key], (int, float)) and key in static
    }
    return {
        "config": {
            "days": days,
            "seed": seed,
            "include_adverse_events": include_adverse_events,
            "persona_count": len(personas),
        },
        "adaptive": adaptive,
        "static_baseline": static,
        "delta_adaptive_minus_static": delta,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare adaptive vs static Arthamantri simulator policy.")
    parser.add_argument("--days", type=int, default=14, help="Number of simulated days per persona.")
    parser.add_argument("--seed", type=int, default=21, help="Deterministic seed for scenario generation.")
    parser.add_argument(
        "--no-adverse-events",
        action="store_true",
        help="Disable adverse scenarios like catastrophic spend and suspicious UPI attempts.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args()

    result = build_comparison(
        days=args.days,
        seed=args.seed,
        include_adverse_events=not args.no_adverse_events,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    print("Arthamantri Synthetic Cohort Comparison")
    print(
        f"days={result['config']['days']} seed={result['config']['seed']} "
        f"adverse_events={result['config']['include_adverse_events']} personas={result['config']['persona_count']}"
    )
    print("")
    print("Metric                 Adaptive   Static     Delta")
    for metric in (
        "participants",
        "total_alerts",
        "total_soft_alerts",
        "total_medium_alerts",
        "total_hard_alerts",
        "useful_rate",
        "dismiss_rate",
        "soft_alert_rate",
        "medium_alert_rate",
        "hard_alert_rate",
        "prevention_rate",
        "retention_rate",
    ):
        adaptive_value = result["adaptive"][metric]
        static_value = result["static_baseline"][metric]
        delta_value = result["delta_adaptive_minus_static"][metric]
        print(f"{metric:20} {str(adaptive_value):>9} {str(static_value):>9} {str(delta_value):>9}")


if __name__ == "__main__":
    main()

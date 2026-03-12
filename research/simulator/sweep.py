from __future__ import annotations

import argparse
import json

from research.simulator.compare import build_comparison
from research.simulator.scenarios import SCENARIO_PRESETS


def build_sweep(days: int, seed: int, include_adverse_events: bool) -> dict:
    scenario_reports = {
        scenario: build_comparison(
            days=days,
            seed=seed,
            include_adverse_events=include_adverse_events,
            scenario=scenario,
        )
        for scenario in sorted(SCENARIO_PRESETS)
    }

    summary_rows = []
    for scenario, report in scenario_reports.items():
        adaptive = report["adaptive"]
        static = report["static_baseline"]
        delta = report["delta_adaptive_minus_static"]
        summary_rows.append(
            {
                "scenario": scenario,
                "adaptive_useful_rate": adaptive["useful_rate"],
                "adaptive_beneficial_rate": adaptive["beneficial_rate"],
                "static_useful_rate": static["useful_rate"],
                "static_beneficial_rate": static["beneficial_rate"],
                "delta_useful_rate": delta["useful_rate"],
                "delta_beneficial_rate": delta["beneficial_rate"],
                "delta_dismiss_rate": delta["dismiss_rate"],
                "delta_hard_alert_rate": delta["hard_alert_rate"],
                "delta_prevention_rate": delta["prevention_rate"],
                "delta_retention_rate": delta["retention_rate"],
            }
        )

    return {
        "config": {
            "days": days,
            "seed": seed,
            "include_adverse_events": include_adverse_events,
            "scenario_count": len(scenario_reports),
        },
        "scenarios": scenario_reports,
        "summary_rows": summary_rows,
    }


def _print_row(row: dict) -> None:
    print(
        f"{row['scenario']:24} "
        f"{str(row['delta_useful_rate']):>10} "
        f"{str(row['delta_beneficial_rate']):>12} "
        f"{str(row['delta_dismiss_rate']):>10} "
        f"{str(row['delta_hard_alert_rate']):>10} "
        f"{str(row['delta_prevention_rate']):>12} "
        f"{str(row['delta_retention_rate']):>10}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Arthamantri simulator comparison across all scenario presets."
    )
    parser.add_argument("--days", type=int, default=14, help="Number of simulated days per persona.")
    parser.add_argument("--seed", type=int, default=21, help="Deterministic seed for scenario generation.")
    parser.add_argument(
        "--no-adverse-events",
        action="store_true",
        help="Disable adverse scenarios while keeping the scenario preset structure.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args()

    result = build_sweep(
        days=args.days,
        seed=args.seed,
        include_adverse_events=not args.no_adverse_events,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    print("Arthamantri Scenario Sweep")
    print(
        f"days={result['config']['days']} seed={result['config']['seed']} "
        f"adverse_events={result['config']['include_adverse_events']} "
        f"scenarios={result['config']['scenario_count']}"
    )
    print("")
    print(
        f"{'scenario':24} {'useful Δ':>10} {'beneficial Δ':>12} {'dismiss Δ':>10} "
        f"{'hard Δ':>10} {'prevent Δ':>12} {'retain Δ':>10}"
    )
    for row in result["summary_rows"]:
        _print_row(row)


if __name__ == "__main__":
    main()

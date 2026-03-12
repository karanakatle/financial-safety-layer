from __future__ import annotations

import argparse
import json

from research.simulator.personas import default_personas
from research.simulator.runner import SimulationConfig, SimulationRunner
from research.simulator.scenarios import SCENARIO_PRESETS


def _numeric_delta(left: dict, right: dict) -> dict:
    return {
        key: round(left[key] - right[key], 4)
        for key in left.keys()
        if isinstance(left[key], (int, float)) and isinstance(right.get(key), (int, float))
    }


def _build_per_persona(adaptive_rows: list[dict], static_rows: list[dict]) -> list[dict]:
    adaptive_by_id = {row["participant_id"]: row for row in adaptive_rows}
    static_by_id = {row["participant_id"]: row for row in static_rows}
    participant_ids = sorted(set(adaptive_by_id) | set(static_by_id))

    rows = []
    for participant_id in participant_ids:
        adaptive = adaptive_by_id.get(participant_id, {})
        static = static_by_id.get(participant_id, {})
        rows.append(
            {
                "participant_id": participant_id,
                "adaptive": adaptive,
                "static_baseline": static,
                "delta_adaptive_minus_static": _numeric_delta(adaptive, static),
            }
        )
    return rows


def build_comparison(days: int, seed: int, include_adverse_events: bool, scenario: str = "default") -> dict:
    personas = default_personas()
    runner = SimulationRunner(
        SimulationConfig(
            days=days,
            seed=seed,
            include_adverse_events=include_adverse_events,
            scenario=scenario,
        )
    )
    adaptive_report = runner.run(personas, variant="adaptive")
    static_report = runner.run(personas, variant="static_baseline")
    adaptive = adaptive_report.aggregate()
    static = static_report.aggregate()
    delta = _numeric_delta(adaptive, static)
    return {
        "config": {
            "days": days,
            "seed": seed,
            "include_adverse_events": include_adverse_events,
            "scenario": scenario,
            "persona_count": len(personas),
        },
        "adaptive": adaptive,
        "static_baseline": static,
        "delta_adaptive_minus_static": delta,
        "per_persona": _build_per_persona(
            adaptive_report.by_participant(),
            static_report.by_participant(),
        ),
    }


def _print_metric_row(metric: str, adaptive_value, static_value, delta_value) -> None:
    print(f"{metric:20} {str(adaptive_value):>9} {str(static_value):>9} {str(delta_value):>9}")


def _print_persona_section(rows: list[dict]) -> None:
    print("")
    print("Per-Persona Comparison")
    print("")
    for row in rows:
        adaptive = row["adaptive"]
        static = row["static_baseline"]
        delta = row["delta_adaptive_minus_static"]

        print(f"[{row['participant_id']}]")
        for metric in (
            "active_days",
            "alert_count",
            "soft_alert_count",
            "medium_alert_count",
            "hard_alert_count",
            "useful_rate",
            "preventive_inconvenient_rate",
            "beneficial_rate",
            "dismiss_rate",
            "prevention_rate",
            "retention_value",
            "trust_score_final",
        ):
            _print_metric_row(
                metric,
                adaptive.get(metric),
                static.get(metric),
                delta.get(metric),
            )
        print(f"{'retained':20} {str(adaptive.get('retained')):>9} {str(static.get('retained')):>9} {'-':>9}")
        print(
            f"{'uninstall_day':20} "
            f"{str(adaptive.get('uninstall_day')):>9} "
            f"{str(static.get('uninstall_day')):>9} {'-':>9}"
        )
        print("")


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
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIO_PRESETS),
        default="default",
        help="Scenario preset to stress the same policy under a specific real-world condition.",
    )
    args = parser.parse_args()

    result = build_comparison(
        days=args.days,
        seed=args.seed,
        include_adverse_events=not args.no_adverse_events,
        scenario=args.scenario,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    print("Arthamantri Synthetic Cohort Comparison")
    print(
        f"days={result['config']['days']} seed={result['config']['seed']} "
        f"scenario={result['config']['scenario']} "
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
        "preventive_inconvenient_rate",
        "beneficial_rate",
        "dismiss_rate",
        "soft_alert_rate",
        "medium_alert_rate",
        "hard_alert_rate",
        "prevention_rate",
        "retention_rate",
    ):
        _print_metric_row(
            metric,
            result["adaptive"][metric],
            result["static_baseline"][metric],
            result["delta_adaptive_minus_static"][metric],
        )
    _print_persona_section(result["per_persona"])


if __name__ == "__main__":
    main()

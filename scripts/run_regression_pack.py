#!/usr/bin/env python3
"""Print or run the regression pack for a failed FinSaathi test/story ID.

The map is intentionally repo-local and dependency-light. It uses a small
YAML subset parser so the runner works without installing PyYAML.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = REPO_ROOT / "qa" / "regression-impact-map.yml"


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"[]", "null", "None"}:
        return [] if value == "[]" else None
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    if value[0] in {'"', "'"} and value[-1:] == value[0]:
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the constrained YAML shape used by regression-impact-map.yml."""
    data: dict[str, Any] = {}
    section: str | None = None
    item_name: str | None = None
    list_key: str | None = None

    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            item_name = None
            list_key = None
            if line.endswith(":"):
                section = line[:-1]
                data[section] = {}
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = parse_scalar(value)
                section = None
                continue

        if section not in {"commands", "areas"}:
            raise ValueError(f"Unsupported YAML shape at {path}:{lineno}: {raw_line}")

        if indent == 2 and line.endswith(":"):
            item_name = line[:-1]
            data[section][item_name] = {}
            list_key = None
            continue

        if indent == 4 and item_name and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[section][item_name][key] = parse_scalar(value)
                list_key = None
            else:
                data[section][item_name][key] = []
                list_key = key
            continue

        if indent == 6 and item_name and list_key and line.startswith("- "):
            data[section][item_name][list_key].append(parse_scalar(line[2:]))
            continue

        raise ValueError(f"Unsupported YAML shape at {path}:{lineno}: {raw_line}")

    return data


def load_map(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Regression impact map not found: {path}")

    data = parse_simple_yaml(path)
    data.setdefault("commands", {})
    data.setdefault("areas", {})
    return data


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def areas_for_test(data: dict[str, Any], test_id: str) -> dict[str, dict[str, Any]]:
    test_id = test_id.upper()
    matches: dict[str, dict[str, Any]] = {}
    for area_name, area in data["areas"].items():
        triggers = [str(item).upper() for item in area.get("trigger_tests", [])]
        if test_id in triggers:
            matches[area_name] = area
    return matches


def build_pack(data: dict[str, Any], test_id: str) -> dict[str, Any]:
    matches = areas_for_test(data, test_id)
    if not matches:
        known = sorted(
            {
                str(test).upper()
                for area in data["areas"].values()
                for test in area.get("trigger_tests", [])
            }
        )
        raise KeyError(
            f"No regression impact entry found for {test_id}. "
            f"Known IDs include: {', '.join(known[:20])}"
            + (" ..." if len(known) > 20 else "")
        )

    automated: list[str] = []
    manual: list[str] = []
    conditional: list[str] = []
    links: list[str] = []
    commands: list[str] = []

    for area in matches.values():
        automated.extend(map(str, area.get("automated_reruns", [])))
        manual.extend(map(str, area.get("manual_reruns", [])))
        conditional.extend(map(str, area.get("conditional_reruns", [])))
        links.extend(map(str, area.get("jira_links", [])))
        commands.extend(map(str, area.get("run_commands", [])))

    return {
        "test_id": test_id.upper(),
        "areas": [
            {"name": name, "description": area.get("description", "")}
            for name, area in matches.items()
        ],
        "automated_reruns": unique(automated),
        "manual_reruns": unique(manual),
        "conditional_reruns": unique(conditional),
        "jira_links": unique(links),
        "run_commands": unique(commands),
    }


def print_pack(data: dict[str, Any], pack: dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(pack, indent=2))
        return

    print(f"Regression pack for {pack['test_id']}")
    print("=" * (20 + len(pack["test_id"])))

    print("\nImpacted areas:")
    for area in pack["areas"]:
        print(f"- {area['name']}: {area['description']}")

    print("\nAutomated/local reruns:")
    for item in pack["automated_reruns"] or ["None"]:
        print(f"- {item}")

    print("\nManual/device/UAT/release checks:")
    for item in pack["manual_reruns"] or ["None"]:
        print(f"- {item}")

    print("\nConditional reruns:")
    for item in pack["conditional_reruns"] or ["None"]:
        print(f"- {item}")

    print("\nJira/repo links to record:")
    for item in pack["jira_links"] or ["None"]:
        print(f"- {item}")

    print("\nRunnable command pack:")
    commands = data["commands"]
    for command_id in pack["run_commands"] or []:
        command = commands.get(command_id, {})
        print(f"- {command_id}: {command.get('description', '')}")
        print(f"  {command.get('command', '[missing command]')}")
    if not pack["run_commands"]:
        print("- None")


def markdown_pack(data: dict[str, Any], pack: dict[str, Any]) -> str:
    lines: list[str] = [
        f"## Regression Pack: `{pack['test_id']}`",
        "",
        "### Impacted Areas",
    ]

    for area in pack["areas"]:
        lines.append(f"- **{area['name']}**: {area['description']}")

    lines.extend(["", "### Automated Reruns"])
    for item in pack["automated_reruns"] or ["None"]:
        lines.append(f"- [ ] `{item}`")

    lines.extend(["", "### Manual Verification Required"])
    lines.append(
        "> Complete these in the PR body/comment or a manual evidence log after phone/user testing."
    )
    for item in pack["manual_reruns"] or ["None"]:
        lines.append(f"- [ ] `{item}`")

    lines.extend(["", "### Conditional Verification"])
    lines.append("> Mark each item as completed, not impacted, or not applicable with a short reason.")
    for item in pack["conditional_reruns"] or ["None"]:
        lines.append(f"- [ ] {item}")

    lines.extend(["", "### Links / Evidence To Record"])
    for item in pack["jira_links"] or ["None"]:
        lines.append(f"- {item}")

    lines.extend(["", "### Runnable Command Pack"])
    commands = data["commands"]
    for command_id in pack["run_commands"] or []:
        command = commands.get(command_id, {})
        lines.append(f"- `{command_id}`: {command.get('description', '')}")
        lines.append("")
        lines.append("```bash")
        lines.append(command.get("command", "# missing command"))
        lines.append("```")
    if not pack["run_commands"]:
        lines.append("- None")

    lines.append("")
    return "\n".join(lines)


def list_coverage(data: dict[str, Any]) -> None:
    rows: list[tuple[str, str]] = []
    for area_name, area in data["areas"].items():
        for test_id in area.get("trigger_tests", []):
            rows.append((str(test_id).upper(), area_name))
    for test_id, area_name in sorted(rows):
        print(f"{test_id}: {area_name}")


def validate_map(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    commands = data.get("commands", {})
    areas = data.get("areas", {})
    if not areas:
        errors.append("No areas defined.")

    for area_name, area in areas.items():
        if not area.get("trigger_tests"):
            errors.append(f"{area_name}: trigger_tests is empty.")
        for command_id in area.get("run_commands", []):
            if command_id not in commands:
                errors.append(f"{area_name}: unknown command {command_id}.")
        for key in ("automated_reruns", "manual_reruns", "conditional_reruns", "jira_links"):
            if key not in area:
                errors.append(f"{area_name}: missing {key}.")
    return errors


def run_commands_with_results(data: dict[str, Any], command_ids: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command_id in command_ids:
        command = data["commands"].get(command_id)
        if not command:
            print(f"Missing command definition: {command_id}", file=sys.stderr)
            results.append(
                {
                    "command_id": command_id,
                    "description": "",
                    "command": "",
                    "returncode": 1,
                }
            )
            continue

        print(f"\nRunning {command_id}: {command.get('description', '')}")
        print(command["command"])
        completed = subprocess.run(command["command"], cwd=REPO_ROOT, shell=True)
        results.append(
            {
                "command_id": command_id,
                "description": command.get("description", ""),
                "command": command["command"],
                "returncode": completed.returncode,
            }
        )
        if completed.returncode != 0:
            print(f"Command failed: {command_id} ({completed.returncode})", file=sys.stderr)
    return results


def run_commands(data: dict[str, Any], command_ids: list[str]) -> int:
    results = run_commands_with_results(data, command_ids)
    exit_codes = [int(result["returncode"]) for result in results if int(result["returncode"]) != 0]
    return exit_codes[0] if exit_codes else 0


def automation_status_markdown(pack: dict[str, Any], results: list[dict[str, Any]]) -> str:
    passed = bool(results) and all(int(result["returncode"]) == 0 for result in results)
    status_icon = "✅" if passed else "❌"
    status_label = "PASS" if passed else "FAIL"

    lines = [
        f"## Automated Verification Status: `{pack['test_id']}`",
        "",
        f"Overall automated status: **{status_icon} {status_label}**",
        "",
        "### Automated Test Status",
    ]
    for item in pack["automated_reruns"] or ["None"]:
        lines.append(f"- {status_icon} `{item}`")

    lines.extend(["", "### Command Results"])
    for result in results:
        icon = "✅" if int(result["returncode"]) == 0 else "❌"
        lines.append(
            f"- {icon} `{result['command_id']}` "
            f"(exit {result['returncode']}): {result['description']}"
        )

    if not results:
        lines.append("- ❌ No automated commands were executed.")

    lines.extend(
        [
            "",
            "### Manual Items Still Require Human Evidence",
            "Automated status does not complete device, UAT, Play, legal, or release checks.",
        ]
    )
    for item in pack["manual_reruns"] or []:
        lines.append(f"- [ ] `{item}`")
    for item in pack["conditional_reruns"] or []:
        lines.append(f"- [ ] {item}")

    lines.append("")
    return "\n".join(lines)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show or run the regression pack for a failed FinSaathi test/story ID."
    )
    parser.add_argument("test_id", nargs="?", help="Failed test/story ID, for example SIT-D-011.")
    parser.add_argument("--map", default=str(DEFAULT_MAP), help="Path to regression-impact-map.yml.")
    parser.add_argument("--list", action="store_true", help="List known test IDs and their impact areas.")
    parser.add_argument("--validate", action="store_true", help="Validate the impact map structure.")
    parser.add_argument("--json", action="store_true", help="Print regression pack as JSON.")
    parser.add_argument("--markdown", action="store_true", help="Print regression pack as GitHub-flavored Markdown.")
    parser.add_argument("--run-auto", action="store_true", help="Run the runnable automated command pack.")
    parser.add_argument(
        "--status-markdown",
        help="Append automated execution status Markdown to this file when --run-auto is used.",
    )
    args = parser.parse_args(argv)

    data = load_map(Path(args.map))

    if args.validate:
        errors = validate_map(data)
        if errors:
            print("Regression impact map validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Regression impact map validation passed.")
        return 0

    if args.list:
        list_coverage(data)
        return 0

    if not args.test_id:
        parser.error("test_id is required unless --list or --validate is used")

    try:
        pack = build_pack(data, args.test_id)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.markdown:
        print(markdown_pack(data, pack))
    else:
        print_pack(data, pack, as_json=args.json)

    if args.run_auto:
        results = run_commands_with_results(data, pack["run_commands"])
        if args.status_markdown:
            status_path = Path(args.status_markdown)
            with status_path.open("a", encoding="utf-8") as handle:
                handle.write("\n")
                handle.write(automation_status_markdown(pack, results))
        exit_codes = [int(result["returncode"]) for result in results if int(result["returncode"]) != 0]
        return exit_codes[0] if exit_codes else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

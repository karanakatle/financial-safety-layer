#!/usr/bin/env python3
"""Suggest FinSaathi regression packs from changed files and PR text.

This is intentionally deterministic. It behaves like a small QA agent:
it reads the diff surface, maps it to known regression areas, and produces
test IDs that the existing regression runner can execute.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from run_regression_pack import DEFAULT_MAP, build_pack, load_map


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = REPO_ROOT / "qa" / "regression-impact-agent-rules.json"
TEST_ID_RE = re.compile(r"\b(?:DEV|INT|SIT-H|SIT-D|PLAY|UAT|QA)-\d{3}\b", re.IGNORECASE)


@dataclass(frozen=True)
class MatchedRule:
    name: str
    reason: str
    suggested_test_ids: tuple[str, ...]
    matched_files: tuple[str, ...]


def normalize_test_id(value: str) -> str:
    return value.strip().upper()


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_file_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    return normalized[2:] if normalized.startswith("./") else normalized


def extract_test_ids(text: str) -> list[str]:
    return unique([normalize_test_id(match) for match in TEST_ID_RE.findall(text or "")])


def load_rules(path: Path = DEFAULT_RULES) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Regression impact agent rules not found: {path}")
    with path.open(encoding="utf-8") as handle:
        rules = json.load(handle)
    rules.setdefault("path_rules", [])
    return rules


def files_from_git_diff(base: str | None, head: str | None) -> list[str]:
    if not base and not head:
        commands = [
            ["git", "diff", "--name-only", "--cached"],
            ["git", "diff", "--name-only"],
            ["git", "ls-files", "--others", "--exclude-standard"],
        ]
        files: list[str] = []
        for command in commands:
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
            files.extend(completed.stdout.splitlines())
        return unique([normalize_file_path(item) for item in files if item.strip()])

    if not base or not head:
        raise ValueError("--base and --head must be provided together.")

    completed = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return unique([normalize_file_path(item) for item in completed.stdout.splitlines() if item.strip()])


def files_from_file(path: Path) -> list[str]:
    return unique(
        [
            normalize_file_path(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    )


def rule_matches_file(pattern: str, file_path: str) -> bool:
    pattern = normalize_file_path(pattern)
    file_path = normalize_file_path(file_path)
    return fnmatch(file_path, pattern)


def match_rules(changed_files: list[str], rules: dict[str, Any]) -> list[MatchedRule]:
    matches: list[MatchedRule] = []
    for rule in rules.get("path_rules", []):
        patterns = [str(pattern) for pattern in rule.get("patterns", [])]
        matched_files = [
            file_path
            for file_path in changed_files
            if any(rule_matches_file(pattern, file_path) for pattern in patterns)
        ]
        if not matched_files:
            continue
        matches.append(
            MatchedRule(
                name=str(rule.get("name", "Unnamed rule")),
                reason=str(rule.get("reason", "")),
                suggested_test_ids=tuple(
                    normalize_test_id(str(item)) for item in rule.get("suggested_test_ids", [])
                ),
                matched_files=tuple(matched_files),
            )
        )
    return matches


def validate_suggestions(test_ids: list[str], map_path: Path = DEFAULT_MAP) -> list[str]:
    data = load_map(map_path)
    valid: list[str] = []
    for test_id in test_ids:
        build_pack(data, test_id)
        valid.append(test_id)
    return valid


def build_suggestion(
    changed_files: list[str],
    pr_text: str,
    rules_path: Path = DEFAULT_RULES,
    map_path: Path = DEFAULT_MAP,
) -> dict[str, Any]:
    rules = load_rules(rules_path)
    matched_rules = match_rules(changed_files, rules)
    mentioned_ids = extract_test_ids(pr_text)

    path_ids: list[str] = []
    for rule in matched_rules:
        path_ids.extend(rule.suggested_test_ids)

    suggested_ids = validate_suggestions(unique(mentioned_ids + path_ids), map_path)
    return {
        "changed_files": changed_files,
        "mentioned_test_ids": mentioned_ids,
        "path_suggested_test_ids": unique(path_ids),
        "suggested_test_ids": suggested_ids,
        "matched_rules": [
            {
                "name": rule.name,
                "reason": rule.reason,
                "suggested_test_ids": list(rule.suggested_test_ids),
                "matched_files": list(rule.matched_files),
            }
            for rule in matched_rules
        ],
    }


def suggestion_markdown(suggestion: dict[str, Any]) -> str:
    suggested_ids = suggestion["suggested_test_ids"]
    changed_files = suggestion["changed_files"]
    matched_rules = suggestion["matched_rules"]

    lines: list[str] = [
        "# Regression Impact Agent",
        "",
        "This deterministic QA agent inspected the PR/change surface and suggested regression packs.",
        "",
        f"Changed files inspected: **{len(changed_files)}**",
        "",
    ]

    if suggestion["mentioned_test_ids"]:
        lines.append("Explicit test IDs mentioned by human:")
        for test_id in suggestion["mentioned_test_ids"]:
            lines.append(f"- `{test_id}`")
        lines.append("")

    if suggested_ids:
        lines.append("Suggested regression IDs:")
        for test_id in suggested_ids:
            source = "human mention" if test_id in suggestion["mentioned_test_ids"] else "file impact"
            lines.append(f"- ✅ `{test_id}` ({source})")
    else:
        lines.append("Suggested regression IDs:")
        lines.append("- ⚠️ None. Add a test ID manually if this PR changes behavior.")

    lines.extend(["", "Matched impact rules:"])
    if not matched_rules:
        lines.append("- None")
    for rule in matched_rules:
        ids = ", ".join(f"`{item}`" for item in rule["suggested_test_ids"])
        lines.append(f"- **{rule['name']}** -> {ids}")
        lines.append(f"  - Reason: {rule['reason']}")
        sample_files = rule["matched_files"][:5]
        for file_path in sample_files:
            lines.append(f"  - `{file_path}`")
        remaining = len(rule["matched_files"]) - len(sample_files)
        if remaining > 0:
            lines.append(f"  - ...and {remaining} more file(s)")

    lines.extend(
        [
            "",
            "Next step:",
            "- CI uses these IDs to run automated reruns.",
            "- Manual and conditional verification still need human evidence after device/user testing.",
            "",
        ]
    )
    return "\n".join(lines)


def write_github_output(path: Path, suggestion: dict[str, Any]) -> None:
    suggested_ids = ",".join(suggestion["suggested_test_ids"])
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"suggested_ids={suggested_ids}\n")
        handle.write(f"has_suggestions={'true' if suggested_ids else 'false'}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Suggest regression packs from changed files and PR text.")
    parser.add_argument("--base", help="Base git ref/SHA for diff.")
    parser.add_argument("--head", help="Head git ref/SHA for diff.")
    parser.add_argument("--changed-file", action="append", default=[], help="Changed file path. Repeatable.")
    parser.add_argument("--changed-files-file", help="File containing changed file paths, one per line.")
    parser.add_argument("--pr-text", default="", help="PR title/body or other human context to inspect for test IDs.")
    parser.add_argument("--rules", default=str(DEFAULT_RULES), help="Path to regression-impact-agent-rules.json.")
    parser.add_argument("--map", default=str(DEFAULT_MAP), help="Path to regression-impact-map.yml.")
    parser.add_argument("--json", action="store_true", help="Print suggestion as JSON.")
    parser.add_argument("--markdown", action="store_true", help="Print suggestion as Markdown.")
    parser.add_argument("--summary-markdown", help="Append suggestion Markdown to this file.")
    parser.add_argument("--github-output", help="Append suggested_ids outputs to this GitHub output file.")
    args = parser.parse_args(argv)

    changed_files: list[str] = []
    if args.changed_files_file:
        changed_files.extend(files_from_file(Path(args.changed_files_file)))
    if args.changed_file:
        changed_files.extend(normalize_file_path(item) for item in args.changed_file)
    if not changed_files:
        changed_files.extend(files_from_git_diff(args.base, args.head))
    changed_files = unique([item for item in changed_files if item])

    try:
        suggestion = build_suggestion(
            changed_files=changed_files,
            pr_text=args.pr_text,
            rules_path=Path(args.rules),
            map_path=Path(args.map),
        )
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Regression Impact Agent failed: {exc}", file=sys.stderr)
        return 2

    if args.github_output:
        write_github_output(Path(args.github_output), suggestion)
    if args.summary_markdown:
        with Path(args.summary_markdown).open("a", encoding="utf-8") as handle:
            handle.write("\n")
            handle.write(suggestion_markdown(suggestion))
    if args.json:
        print(json.dumps(suggestion, indent=2))
    else:
        print(suggestion_markdown(suggestion) if args.markdown else ",".join(suggestion["suggested_test_ids"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

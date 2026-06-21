from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from suggest_regression_pack import build_suggestion  # noqa: E402


def test_agent_suggests_android_parser_pack_for_detector_change():
    suggestion = build_suggestion(
        changed_files=[
            "ArthamantriAndroid/app/src/main/java/com/finsaathi/android/core/FinancialRiskMessageDetector.kt"
        ],
        pr_text="",
    )

    assert suggestion["suggested_test_ids"] == ["SIT-D-011"]
    assert suggestion["matched_rules"][0]["name"] == "Android parser and financial-risk detector"


def test_agent_keeps_human_mentioned_test_id_first():
    suggestion = build_suggestion(
        changed_files=["backend/literacy/policy.py"],
        pr_text="Regression pack: UAT-004",
    )

    assert suggestion["suggested_test_ids"][0] == "UAT-004"
    assert "INT-005" in suggestion["suggested_test_ids"]


def test_agent_suggests_traceability_pack_for_workflow_change():
    suggestion = build_suggestion(
        changed_files=[".github/workflows/regression-pack.yml"],
        pr_text="",
    )

    assert suggestion["suggested_test_ids"] == ["QA-011"]
    assert suggestion["matched_rules"][0]["matched_files"] == [
        ".github/workflows/regression-pack.yml"
    ]

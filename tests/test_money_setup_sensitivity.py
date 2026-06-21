import importlib
import sys
from dataclasses import dataclass

from fastapi.testclient import TestClient

from backend.literacy.policy import policy_details_for_participant, policy_for_participant


@dataclass(frozen=True)
class DummyPolicy:
    daily_safe_limit: float = 1200.0
    warning_ratio: float = 0.9


class FakeStorage:
    def __init__(self, profile=None, policy=None):
        self.profile = profile
        self.policy = policy

    def get_participant_policy(self, participant_id):
        return self.policy

    def get_essential_goal_profile(self, participant_id):
        return self.profile


def _client_with_temp_db(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_research.db"))
    monkeypatch.setenv("VOICE_PROVIDER", "bhashini")
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")
    return TestClient(module.app)


def test_policy_defaults_when_money_setup_is_missing_or_skipped():
    default_limit, default_ratio = policy_for_participant(
        participant_id="missing_setup",
        pilot_storage=FakeStorage(profile=None),
        literacy_policy=DummyPolicy(),
    )
    skipped_limit, skipped_ratio = policy_for_participant(
        participant_id="skipped_setup",
        pilot_storage=FakeStorage(
            profile={
                "cohort": "daily_cashflow_worker",
                "affordability_bucket_id": "below_250",
                "active_priority_essentials": ["ration", "rent"],
                "setup_skipped": True,
            },
        ),
        literacy_policy=DummyPolicy(),
    )

    assert (default_limit, default_ratio) == (1200.0, 0.9)
    assert (skipped_limit, skipped_ratio) == (1200.0, 0.9)


def test_low_daily_cashflow_setup_makes_threshold_more_cautious_without_exact_bank_data():
    limit, ratio = policy_for_participant(
        participant_id="daily_low_bucket",
        pilot_storage=FakeStorage(
            profile={
                "cohort": "daily_cashflow_worker",
                "affordability_bucket_id": "below_250",
                "active_priority_essentials": ["ration", "rent", "medicine"],
                "setup_skipped": False,
            },
        ),
        literacy_policy=DummyPolicy(),
    )

    assert limit == 1200.0
    assert ratio < 0.9
    assert ratio >= 0.82


def test_low_women_led_household_setup_makes_threshold_more_cautious():
    _, ratio = policy_for_participant(
        participant_id="household_low_bucket",
        pilot_storage=FakeStorage(
            profile={
                "cohort": "women_led_household",
                "affordability_bucket_id": "below_6000",
                "active_priority_essentials": ["ration", "school", "medicine"],
                "setup_skipped": False,
            },
        ),
        literacy_policy=DummyPolicy(),
    )

    assert ratio < 0.9
    assert ratio >= 0.82


def test_money_setup_does_not_weaken_stricter_custom_warning_ratio():
    details = policy_details_for_participant(
        participant_id="custom_strict_ratio",
        pilot_storage=FakeStorage(
            policy={"daily_safe_limit": 1200.0, "warning_ratio": 0.8},
            profile={
                "cohort": "daily_cashflow_worker",
                "affordability_bucket_id": "below_250",
                "active_priority_essentials": ["ration", "rent", "medicine"],
                "setup_skipped": False,
            },
        ),
        literacy_policy=DummyPolicy(),
    )

    assert details["warning_ratio"] == 0.8
    assert details["source"] == "custom"
    assert details["money_setup_sensitivity"]["applied"] is False


def test_unsupported_cohort_does_not_tune_threshold_from_essentials_only():
    _, ratio = policy_for_participant(
        participant_id="malformed_cohort",
        pilot_storage=FakeStorage(
            profile={
                "cohort": "unexpected_profile",
                "affordability_bucket_id": "below_250",
                "active_priority_essentials": ["ration", "rent", "medicine"],
                "setup_skipped": False,
            },
        ),
        literacy_policy=DummyPolicy(),
    )

    assert ratio == 0.9


def test_money_setup_sensitivity_is_visible_through_policy_endpoint(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "policy_setup_p1"

    before = client.get("/api/literacy/policy", params={"participant_id": participant_id})
    assert before.status_code == 200
    assert before.json()["warning_ratio"] == 0.9

    setup = client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": participant_id,
            "cohort": "daily_cashflow_worker",
            "essential_goals": ["ration", "medicine"],
            "active_priority_essentials": ["ration", "medicine"],
            "affordability_bucket_id": "below_250",
            "language": "en",
            "setup_skipped": False,
        },
    )
    assert setup.status_code == 200

    after = client.get("/api/literacy/policy", params={"participant_id": participant_id})
    assert after.status_code == 200
    payload = after.json()
    assert payload["daily_safe_limit"] == 1200.0
    assert payload["warning_ratio"] < 0.9
    assert payload["source"] == "default+money_setup_lite"
    assert payload["money_setup_sensitivity"] == {
        "applied": True,
        "context": "rough_money_setup_context",
        "direction": "more_cautious",
        "applies_to": "cashflow_yellow_red_thresholds_only",
    }
    assert "reason_codes" not in payload["money_setup_sensitivity"]
    assert "below_250" not in str(payload["money_setup_sensitivity"])


def test_policy_upsert_returns_sanitized_sensitivity_metadata(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "policy_post_setup_p1"

    setup = client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": participant_id,
            "cohort": "daily_cashflow_worker",
            "essential_goals": ["ration", "medicine"],
            "active_priority_essentials": ["ration", "medicine"],
            "affordability_bucket_id": "below_250",
            "language": "en",
            "setup_skipped": False,
        },
    )
    assert setup.status_code == 200

    response = client.post(
        "/api/literacy/policy",
        json={
            "participant_id": participant_id,
            "daily_safe_limit": 1400.0,
            "warning_ratio": 0.9,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "custom+money_setup_lite"
    assert payload["warning_ratio"] < 0.9
    assert payload["money_setup_sensitivity"]["applied"] is True
    assert "reason_codes" not in payload["money_setup_sensitivity"]

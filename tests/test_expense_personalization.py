import importlib
import sys
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend.literacy.decisioning import personalized_guidance_copy
from backend.literacy.expense_personalization import (
    PERSONALIZATION_CONTRACT_VERSION,
    build_expense_personalization,
)


def _load_main_with_temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_research.db"))
    monkeypatch.setenv("VOICE_PROVIDER", "bhashini")
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")
    return module, TestClient(module.app)


def _client_with_temp_db(tmp_path, monkeypatch) -> TestClient:
    _, client = _load_main_with_temp_db(tmp_path, monkeypatch)
    return client


def test_expense_personalization_returns_bounded_contract_for_safer_limit_case():
    contract = build_expense_personalization(
        amount=120.0,
        projected_spend=260.0,
        daily_safe_limit=1400.0,
        envelope={
            "cohort": "daily_cashflow_worker",
            "essential_goals": ["ration", "medicine"],
            "protected_limit": 1100.0,
        },
        essential_profile={
            "cohort": "daily_cashflow_worker",
            "active_priority_essentials": ["ration", "medicine"],
            "affordability_bucket_id": "2000_plus",
        },
        financial_context={
            "income_count": 1,
            "expense_count": 1,
            "latest_income_amount": 2200.0,
            "latest_expense_amount": 110.0,
        },
        upi_open_flag=False,
        current_balance_amount=2200.0,
        current_balance_source="observed_balance",
        recent_amounts=[90.0, 110.0, 130.0],
        event_timestamp="2026-03-16T10:00:00",
        first_event_date="2026-03-01T09:00:00",
    )

    assert contract["contract_version"] == PERSONALIZATION_CONTRACT_VERSION
    assert contract["pressure_state"] == "within_safer_limit"
    assert contract["bounded_confidence"]["label"].startswith("bounded_")
    assert contract["inputs"]["cohort"] == "daily_cashflow_worker"
    assert contract["inputs"]["current_balance_source"] == "observed_balance"
    assert contract["inputs"]["income_bucket"] == "2000_plus"
    assert contract["inputs"]["essential_items"] == ["ration", "medicine"]
    assert contract["inputs"]["recent_observed_expense_pattern"]["median_recent_expense_amount"] == 110.0
    assert contract["explainability"]["output_vocabulary"] == [
        "within_safer_limit",
        "watch_this_expense",
        "this_adds_burden",
        "high_pressure_expense",
    ]
    assert contract["learning_period"]["status"] == "learning_complete"
    assert contract["delivery"]["surface"] == "notification"
    assert contract["future_extensions"]["preserve_deterministic_baseline"] is True
    assert contract["traceability"]["baseline_contract_version"] == PERSONALIZATION_CONTRACT_VERSION


def test_expense_personalization_escalates_to_high_pressure_for_open_plus_limit_breach():
    contract = build_expense_personalization(
        amount=1600.0,
        projected_spend=2200.0,
        daily_safe_limit=1200.0,
        envelope={
            "cohort": "women_led_household",
            "essential_goals": ["ration", "school", "rent"],
            "protected_limit": 780.0,
        },
        essential_profile={
            "cohort": "women_led_household",
            "active_priority_essentials": ["ration", "school", "rent"],
            "affordability_bucket_id": "below_6000",
        },
        financial_context={
            "income_count": 0,
            "expense_count": 3,
            "latest_income_amount": None,
            "latest_expense_amount": 900.0,
        },
        upi_open_flag=True,
        current_balance_amount=350.0,
        current_balance_source="observed_balance",
        recent_amounts=[300.0, 400.0, 700.0],
        event_timestamp="2026-03-20T08:00:00",
        first_event_date="2026-03-01T08:00:00",
    )

    assert contract["pressure_state"] == "high_pressure_expense"
    assert contract["pressure_score"] >= 0.72
    assert contract["inputs"]["income_bucket_source"] == "affordability_proxy_bucket"
    assert contract["inputs"]["essential_item_weights"][0]["rank"] == 1
    assert contract["explainability"]["top_factors"]
    assert contract["delivery"]["surface"] == "overlay"
    assert contract["delivery"]["overlay_eligible"] is True


def test_expense_personalization_keeps_high_pressure_in_notification_during_learning():
    contract = build_expense_personalization(
        amount=1600.0,
        projected_spend=2200.0,
        daily_safe_limit=1200.0,
        envelope={
            "cohort": "women_led_household",
            "essential_goals": ["ration", "school", "rent"],
            "protected_limit": 780.0,
        },
        essential_profile={
            "cohort": "women_led_household",
            "active_priority_essentials": ["ration", "school", "rent"],
            "affordability_bucket_id": "below_6000",
        },
        financial_context={
            "income_count": 0,
            "expense_count": 2,
            "latest_income_amount": None,
            "latest_expense_amount": 900.0,
        },
        upi_open_flag=True,
        current_balance_amount=350.0,
        current_balance_source="observed_balance",
        recent_amounts=[300.0, 400.0, 700.0],
        event_timestamp="2026-03-05T08:00:00",
        first_event_date="2026-03-01T08:00:00",
    )

    assert contract["pressure_state"] == "high_pressure_expense"
    assert contract["learning_period"]["status"] == "still_learning"
    assert contract["delivery"]["surface"] == "notification"
    assert contract["delivery"]["overlay_blocked_by_learning"] is True


def test_personalized_copy_softens_when_confidence_is_low():
    contract = build_expense_personalization(
        amount=850.0,
        projected_spend=1300.0,
        daily_safe_limit=1200.0,
        envelope={
            "cohort": "daily_cashflow_worker",
            "essential_goals": [],
            "protected_limit": 900.0,
        },
        essential_profile={
            "cohort": "daily_cashflow_worker",
            "active_priority_essentials": [],
            "affordability_bucket_id": None,
        },
        financial_context={
            "income_count": 0,
            "expense_count": 0,
            "latest_income_amount": None,
            "latest_expense_amount": None,
        },
        upi_open_flag=False,
        current_balance_amount=None,
        current_balance_source=None,
        recent_amounts=[],
        event_timestamp="2026-03-03T08:00:00",
        first_event_date="2026-03-02T08:00:00",
    )

    copy = personalized_guidance_copy(
        language="en",
        reason="daily_threshold_near_exceeded",
        risk_level="medium",
        projected_spend=1300.0,
        daily_safe_limit=1200.0,
        envelope={"essential_goals": []},
        financial_context={"income_count": 0, "expense_count": 0},
        spend_ratio=1.08,
        txn_anomaly_score=0.2,
        upi_open_flag=False,
        personalization=contract,
    )

    assert contract["bounded_confidence"]["label"] == "bounded_low"
    assert "soft pause" in copy["message"].lower()
    assert copy["delivery_surface"] == "notification"


def test_sms_ingest_alert_includes_pg11_expense_personalization_contract(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "pg11_contract_p1"

    client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": participant_id,
            "cohort": "women_led_household",
            "essential_goals": ["ration", "mobile_recharge"],
            "all_selected_essentials": ["ration", "mobile_recharge"],
            "active_priority_essentials": ["ration", "mobile_recharge"],
            "selection_source": "user_selected",
            "affordability_bucket_id": "25000_plus",
            "language": "en",
            "setup_skipped": False,
        },
    )

    res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "amount": 1800,
            "category": "upi",
            "note": "merchant payment",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["literacy_alerts"]
    alert = payload["literacy_alerts"][0]
    contract = alert["expense_personalization"]

    assert contract["contract_version"] == PERSONALIZATION_CONTRACT_VERSION
    assert contract["pressure_state"] in {
        "within_safer_limit",
        "watch_this_expense",
        "this_adds_burden",
        "high_pressure_expense",
    }
    assert contract["inputs"]["cohort"] == "women_led_household"
    assert contract["inputs"]["current_balance_source"] == "observed_balance"
    assert contract["inputs"]["income_bucket"] == "25000_plus"
    assert contract["inputs"]["income_bucket_source"] == "affordability_proxy_bucket"
    assert contract["inputs"]["essential_items"] == ["ration", "mobile_recharge"]
    assert "recent_observed_expense_pattern" in contract["inputs"]
    assert alert["pressure_state"] == contract["pressure_state"]
    assert alert["pressure_score"] == contract["pressure_score"]
    assert alert["delivery_surface"] == "notification"
    assert alert["message_family"].startswith("personalized_learning_notification_")
    assert alert["learning_period"]["status"] == "still_learning"
    assert "still learning your pattern" in alert["message"].lower()
    assert alert["future_extension_hooks"]["baseline_fallback_required"] is True


def test_upi_open_alert_includes_pg11_expense_personalization_contract(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "pg11_upi_open_p1"

    client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": participant_id,
            "cohort": "daily_cashflow_worker",
            "essential_goals": ["ration", "medicine"],
            "all_selected_essentials": ["ration", "medicine"],
            "active_priority_essentials": ["ration", "medicine"],
            "selection_source": "user_selected",
            "affordability_bucket_id": "500_749",
            "language": "en",
            "setup_skipped": False,
        },
    )

    expense_res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "amount": 1100,
            "category": "upi",
            "note": "merchant payment",
        },
    )
    assert expense_res.status_code == 200

    upi_open_res = client.post(
        "/api/literacy/upi-open",
        json={
            "participant_id": participant_id,
            "language": "en",
            "app_name": "PhonePe",
            "intent_amount": 250,
        },
    )

    assert upi_open_res.status_code == 200
    payload = upi_open_res.json()
    assert payload["alert"] is not None
    contract = payload["alert"]["expense_personalization"]
    assert contract["contract_version"] == PERSONALIZATION_CONTRACT_VERSION
    assert contract["inputs"]["current_balance_source"] == "observed_balance"
    assert payload["alert"]["pressure_state"] == contract["pressure_state"]
    assert payload["alert"]["delivery_surface"] == "notification"
    assert payload["alert"]["overlay_eligible"] is False


def test_upi_open_promotes_high_pressure_to_overlay_after_learning(tmp_path, monkeypatch):
    module, client = _load_main_with_temp_db(tmp_path, monkeypatch)
    participant_id = "pg11_upi_overlay_ready"

    client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": participant_id,
            "cohort": "women_led_household",
            "essential_goals": ["ration", "school", "rent"],
            "all_selected_essentials": ["ration", "school", "rent"],
            "active_priority_essentials": ["ration", "school", "rent"],
            "selection_source": "user_selected",
            "affordability_bucket_id": "below_6000",
            "language": "en",
            "setup_skipped": False,
        },
    )

    old_start = (datetime.utcnow() - timedelta(days=16)).date().isoformat()
    module.pilot_storage.upsert_literacy_state(
        participant_id=participant_id,
        current_date=old_start,
        daily_spend=0.0,
        threshold_risk_active=False,
        stage1_sent=False,
        stage2_sent=False,
        notifications_count=0,
        first_event_date=old_start,
        warmup_active=False,
        adaptive_daily_safe_limit=None,
        updated_at=datetime.utcnow().isoformat(),
    )

    expense_res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "amount": 1600,
            "category": "upi",
            "note": "merchant payment",
        },
    )
    assert expense_res.status_code == 200

    upi_open_res = client.post(
        "/api/literacy/upi-open",
        json={
            "participant_id": participant_id,
            "language": "en",
            "app_name": "PhonePe",
            "intent_amount": 800,
        },
    )

    assert upi_open_res.status_code == 200
    payload = upi_open_res.json()
    assert payload["alert"] is not None
    assert payload["alert"]["delivery_surface"] == "overlay"
    assert payload["alert"]["overlay_eligible"] is True
    assert payload["alert"]["pressure_state"] == "high_pressure_expense"
    assert payload["alert"]["learning_period"]["status"] == "learning_complete"
    assert payload["alert"]["message_family"] == "personalized_high_pressure_overlay"

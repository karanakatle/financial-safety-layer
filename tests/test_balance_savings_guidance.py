import importlib
import sys

from fastapi.testclient import TestClient


def _client_with_temp_db(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_balance_savings.db"))
    monkeypatch.setenv("VOICE_PROVIDER", "bhashini")
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")
    return TestClient(module.app)


def test_current_balance_endpoint_coarsens_self_reported_balance(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/literacy/current-balance",
        json={
            "participant_id": "bs_balance_p1",
            "amount": 1800,
            "source": "self_reported",
            "timestamp": "2026-04-04T08:15:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["current_balance"]["amount"] == 1000.0
    assert payload["current_balance"]["balance_band_id"] == "1000_2999"
    assert payload["current_balance"]["balance_band"]["label"] == "Rs 1,000-2,999"
    assert payload["current_balance"]["amount_precision"] == "coarse_band"
    assert payload["current_balance"]["amount_is_exact"] is False
    assert payload["current_balance"]["storage_policy"] == "exact_balance_not_stored"
    assert payload["current_balance"]["source"] == "self_reported"
    assert payload["current_balance"]["captured_at"] == "2026-04-04T08:15:00"
    assert "1800" not in str(payload)
    assert "verified" in payload["supported_sources"]


def test_current_balance_endpoint_accepts_band_without_exact_amount(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/literacy/current-balance",
        json={
            "participant_id": "bs_balance_band_p1",
            "balance_band_id": "3000_6999",
            "source": "self_reported",
            "timestamp": "2026-04-04T08:15:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_balance"]["amount"] == 3000.0
    assert payload["current_balance"]["balance_band_id"] == "3000_6999"
    assert payload["current_balance"]["amount_is_exact"] is False


def test_current_balance_history_does_not_expose_exact_legacy_amount(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "bs_balance_history_p1"

    first = client.post(
        "/api/literacy/current-balance",
        json={
            "participant_id": participant_id,
            "amount": 1800,
            "source": "self_reported",
            "timestamp": "2026-04-04T08:15:00",
        },
    )
    second = client.post(
        "/api/literacy/current-balance",
        json={
            "participant_id": participant_id,
            "amount": 6400,
            "source": "self_reported",
            "timestamp": "2026-04-04T11:15:00",
        },
    )
    current = client.get("/api/literacy/current-balance", params={"participant_id": participant_id})

    assert first.status_code == 200
    assert second.status_code == 200
    assert current.status_code == 200
    payload_text = str(current.json())
    assert "1800" not in payload_text
    assert "6400" not in payload_text
    assert current.json()["current_balance"]["balance_band_id"] == "3000_6999"
    assert current.json()["history"][0]["balance_band_id"] == "1000_2999"


def test_eod_savings_preview_stays_silent_without_balance_baseline(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/literacy/eod-savings-preview",
        json={
            "participant_id": "bs_no_balance",
            "language": "en",
            "channel": "notification",
            "timestamp": "2026-04-04T20:30:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_balance"] is None
    assert payload["nudge"]["decision_state"] == "missing_balance_baseline"
    assert payload["nudge"]["should_notify"] is False


def test_eod_savings_preview_suggests_small_savings_for_positive_day(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "bs_positive_day"

    client.post(
        "/api/literacy/current-balance",
        json={
            "participant_id": participant_id,
            "amount": 1000,
            "source": "self_reported",
            "timestamp": "2026-04-04T08:00:00",
        },
    )
    client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "signal_type": "income",
            "signal_confidence": "confirmed",
            "amount": 600,
            "category": "bank_sms",
            "note": "salary credited",
            "timestamp": "2026-04-04T11:00:00",
        },
    )
    client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "signal_type": "expense",
            "signal_confidence": "confirmed",
            "amount": 200,
            "category": "upi",
            "note": "merchant payment",
            "timestamp": "2026-04-04T14:00:00",
        },
    )

    response = client.post(
        "/api/literacy/eod-savings-preview",
        json={
            "participant_id": participant_id,
            "language": "en",
            "channel": "notification",
            "timestamp": "2026-04-04T20:30:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["estimate"]["opening_balance_for_day"] == 1000.0
    assert payload["estimate"]["observed_credits_today"] == 600.0
    assert payload["estimate"]["observed_debits_today"] == 200.0
    assert payload["estimate"]["positive_day_surplus"] == 400.0
    assert payload["nudge"]["decision_state"] == "suggest_save"
    assert payload["nudge"]["suggested_amount"] == 50.0
    assert payload["nudge"]["delivery"]["surface"] == "notification_only"
    assert payload["future_extension_hooks"]["history_compatible"] is True


def test_eod_savings_preview_stays_calm_for_flat_or_negative_day(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "bs_negative_day"

    client.post(
        "/api/literacy/current-balance",
        json={
            "participant_id": participant_id,
            "amount": 900,
            "source": "self_reported",
            "timestamp": "2026-04-04T08:00:00",
        },
    )
    client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "signal_type": "expense",
            "signal_confidence": "confirmed",
            "amount": 350,
            "category": "upi",
            "note": "merchant payment",
            "timestamp": "2026-04-04T12:00:00",
        },
    )

    response = client.post(
        "/api/literacy/eod-savings-preview",
        json={
            "participant_id": participant_id,
            "language": "en",
            "channel": "notification",
            "timestamp": "2026-04-04T20:30:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["estimate"]["positive_day_surplus"] == 0.0
    assert payload["nudge"]["decision_state"] == "flat_or_negative"
    assert payload["nudge"]["suggested_amount"] == 0.0
    assert "no savings ask" in payload["nudge"]["message"].lower()


def test_eod_savings_preview_softens_copy_when_visibility_is_partial(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "bs_partial_day"

    client.post(
        "/api/literacy/current-balance",
        json={
            "participant_id": participant_id,
            "amount": 1200,
            "source": "self_reported",
            "timestamp": "2026-04-04T08:00:00",
        },
    )
    client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "signal_type": "income",
            "signal_confidence": "confirmed",
            "amount": 500,
            "category": "bank_sms",
            "note": "cashback credit",
            "timestamp": "2026-04-04T15:00:00",
        },
    )

    response = client.post(
        "/api/literacy/eod-savings-preview",
        json={
            "participant_id": participant_id,
            "language": "en",
            "channel": "notification",
            "timestamp": "2026-04-04T20:30:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["estimate"]["visibility_state"] == "one_sided_observed"
    assert payload["nudge"]["decision_state"] == "suggest_save"
    assert "may have left a little room" in payload["nudge"]["message"].lower()


def test_eod_savings_preview_uses_same_phase1_logic_across_cohorts(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    for participant_id, cohort in (
        ("bs_daily_worker", "daily_cashflow_worker"),
        ("bs_women_household", "women_led_household"),
    ):
        client.post(
            "/api/literacy/essential-goals",
            json={
                "participant_id": participant_id,
                "cohort": cohort,
                "essential_goals": ["ration"],
                "all_selected_essentials": ["ration"],
                "active_priority_essentials": ["ration"],
                "selection_source": "user_selected",
                "language": "en",
                "setup_skipped": False,
            },
        )
        client.post(
            "/api/literacy/current-balance",
            json={
                "participant_id": participant_id,
                "amount": 1000,
                "source": "self_reported",
                "timestamp": "2026-04-04T08:00:00",
            },
        )
        client.post(
            "/api/literacy/sms-ingest",
            json={
                "participant_id": participant_id,
                "language": "en",
                "signal_type": "income",
                "signal_confidence": "confirmed",
                "amount": 250,
                "category": "bank_sms",
                "note": "income",
                "timestamp": "2026-04-04T12:00:00",
            },
        )

    worker = client.post(
        "/api/literacy/eod-savings-preview",
        json={
            "participant_id": "bs_daily_worker",
            "language": "en",
            "timestamp": "2026-04-04T20:30:00",
        },
    ).json()
    household = client.post(
        "/api/literacy/eod-savings-preview",
        json={
            "participant_id": "bs_women_household",
            "language": "en",
            "timestamp": "2026-04-04T20:30:00",
        },
    ).json()

    assert worker["nudge"]["suggested_amount"] == 20.0
    assert household["nudge"]["suggested_amount"] == 20.0
    assert worker["nudge"]["shared_phase_1_logic"] is True
    assert household["nudge"]["shared_phase_1_logic"] is True


def test_borrowing_pressure_check_labels_low_medium_high_without_advice():
    from backend.literacy.balance_savings import build_borrowing_pressure_check

    low = build_borrowing_pressure_check(
        repayment_amount=1200,
        rough_income_amount=24000,
        essential_expense_amount=9000,
        essential_expenses=["ration", "rent"],
        language="en",
    )
    medium = build_borrowing_pressure_check(
        repayment_amount=4500,
        rough_income_amount=24000,
        essential_expense_amount=12000,
        essential_expenses=["ration", "rent", "school"],
        language="en",
    )
    high = build_borrowing_pressure_check(
        repayment_amount=9000,
        rough_income_amount=24000,
        essential_expense_amount=13500,
        essential_expenses=["ration", "rent", "medicine", "school"],
        language="en",
    )

    assert low["pressure_level"] == "low"
    assert medium["pressure_level"] == "medium"
    assert high["pressure_level"] == "high"
    assert high["suggested_next_step"] == "verify_with_trusted_official_source"
    assert "official source" in high["next_best_action"].lower()
    for result in (low, medium, high):
        assert result["non_advisory_guardrail"]["is_loan_approval"] is False
        assert result["non_advisory_guardrail"]["is_financial_advice"] is False
        assert "not loan approval" in result["disclaimer"].lower()
        assert "financial advice" in result["disclaimer"].lower()
        assert "lender" not in result["next_best_action"].lower()


def test_borrowing_pressure_check_handles_missing_income_without_exact_inference():
    from backend.literacy.balance_savings import build_borrowing_pressure_check

    result = build_borrowing_pressure_check(
        repayment_amount=2500,
        rough_income_amount=None,
        essential_expense_amount=None,
        essential_expenses=["ration", "rent"],
        language="en",
    )

    assert result["pressure_level"] == "insufficient_information"
    assert result["decision_state"] == "missing_rough_income"
    assert result["confidence"]["label"] == "bounded_low"
    assert result["repayment_to_income_ratio"] is None
    assert "rough income" in result["why_this_check"].lower()
    assert result["non_advisory_guardrail"]["uses_rough_user_inputs_only"] is True


def test_borrowing_pressure_check_does_not_call_missing_essentials_low_pressure():
    from backend.literacy.balance_savings import build_borrowing_pressure_check

    result = build_borrowing_pressure_check(
        repayment_amount=1200,
        rough_income_amount=24000,
        essential_expense_amount=None,
        essential_expenses=[],
        language="en",
    )

    assert result["pressure_level"] == "medium"
    assert result["decision_state"] == "repayment_pressure_checked_limited"
    assert result["confidence"]["label"] == "bounded_medium"
    assert "essential-expense amount was not provided" in result["why_this_check"].lower()


def test_borrowing_pressure_check_zero_essentials_with_selected_goals_is_limited_confidence():
    from backend.literacy.balance_savings import build_borrowing_pressure_check

    result = build_borrowing_pressure_check(
        repayment_amount=1200,
        rough_income_amount=24000,
        essential_expense_amount=0,
        essential_expenses=["ration", "rent"],
        language="en",
    )

    assert result["essential_expense_amount"] is None
    assert result["pressure_level"] == "medium"
    assert result["confidence"]["label"] == "bounded_medium"


def test_borrowing_pressure_check_rejects_invalid_repayment_without_low_label():
    from backend.literacy.balance_savings import build_borrowing_pressure_check

    result = build_borrowing_pressure_check(
        repayment_amount=-100,
        rough_income_amount=24000,
        essential_expense_amount=9000,
        essential_expenses=["ration"],
        language="en",
    )

    assert result["pressure_level"] == "insufficient_information"
    assert result["decision_state"] == "missing_repayment_amount"
    assert result["repayment_amount"] is None


def test_borrowing_pressure_check_accepts_hindi_language_variants():
    from backend.literacy.balance_savings import build_borrowing_pressure_check

    result = build_borrowing_pressure_check(
        repayment_amount=9000,
        rough_income_amount=24000,
        essential_expense_amount=13500,
        essential_expenses=["ration", "rent", "medicine", "school"],
        language="hi-IN",
    )

    assert result["pressure_level"] == "high"
    assert "आधिकारिक" in result["next_best_action"]


def test_borrowing_pressure_check_normalizes_mixed_periods_to_monthly():
    from backend.literacy.balance_savings import build_borrowing_pressure_check

    result = build_borrowing_pressure_check(
        repayment_amount=2500,
        repayment_period="weekly",
        rough_income_amount=24000,
        income_period="monthly",
        essential_expense_amount=6000,
        essential_expense_period="monthly",
        essential_expenses=["ration", "rent"],
        language="en",
    )

    assert result["period_assumptions"]["repayment_period"] == "weekly"
    assert result["period_assumptions"]["income_period"] == "monthly"
    assert result["period_assumptions"]["normalized_to"] == "monthly"
    assert result["monthly_repayment_amount"] == 10833.33
    assert result["monthly_rough_income_amount"] == 24000.0
    assert result["repayment_to_income_ratio"] == 0.4514
    assert result["pressure_level"] == "high"


def test_borrowing_pressure_check_maps_localized_free_text_essentials():
    from backend.literacy.balance_savings import build_borrowing_pressure_check

    result = build_borrowing_pressure_check(
        repayment_amount=3500,
        rough_income_amount=24000,
        essential_expense_amount=12000,
        essential_expenses=[
            "Food / ration",
            "ghar kiraya",
            "medical",
            "school fees",
            "petrol",
            "EMI / debt",
            "dudh aur bhaji",
        ],
        language="hi-IN",
    )

    assert result["essential_expenses"] == [
        "ration",
        "rent",
        "medicine",
        "school",
        "transport",
        "loan_repayment",
    ]
    assert result["pressure_level"] == "medium"


def test_borrowing_pressure_api_rejects_non_finite_amounts(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/literacy/borrowing-pressure-preview",
        json={
            "participant_id": "bs_borrowing_bad_amount",
            "language": "en",
            "repayment_amount": "Infinity",
            "rough_income_amount": 24000,
            "essential_expense_amount": 9000,
        },
    )

    assert response.status_code == 422


def test_borrowing_pressure_api_accepts_explicit_periods_and_localized_essentials(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/literacy/borrowing-pressure-preview",
        json={
            "participant_id": "bs_borrowing_periods",
            "language": "hi-IN",
            "repayment_amount": 2500,
            "repayment_period": "weekly",
            "rough_income_amount": 24000,
            "income_period": "monthly",
            "essential_expense_amount": 6000,
            "essential_expense_period": "monthly",
            "essential_expenses": ["kirana", "ghar kiraya", "medical", "school fees", "petrol"],
        },
    )

    assert response.status_code == 200
    check = response.json()["pressure_check"]
    assert check["period_assumptions"]["repayment_period"] == "weekly"
    assert check["monthly_repayment_amount"] == 10833.33
    assert check["essential_expenses"] == ["ration", "rent", "medicine", "school", "transport"]
    assert check["pressure_level"] == "high"


def test_borrowing_pressure_api_accepts_rough_inputs_and_returns_high_pressure(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/literacy/borrowing-pressure-preview",
        json={
            "participant_id": "bs_borrowing_high",
            "language": "en",
            "repayment_amount": 9000,
            "rough_income_amount": 24000,
            "essential_expense_amount": 13500,
            "essential_expenses": ["ration", "rent", "medicine", "school"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    check = payload["pressure_check"]
    assert payload["participant_id"] == "bs_borrowing_high"
    assert check["pressure_level"] == "high"
    assert check["repayment_amount"] == 9000.0
    assert check["rough_income_amount"] == 24000.0
    assert check["suggested_next_step"] == "verify_with_trusted_official_source"
    assert check["non_advisory_guardrail"]["does_not_recommend_products"] is True

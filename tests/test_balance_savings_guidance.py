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


def test_current_balance_endpoint_stores_self_reported_contract(tmp_path, monkeypatch):
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
    assert payload["current_balance"]["amount"] == 1800.0
    assert payload["current_balance"]["source"] == "self_reported"
    assert payload["current_balance"]["captured_at"] == "2026-04-04T08:15:00"
    assert "verified" in payload["supported_sources"]


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

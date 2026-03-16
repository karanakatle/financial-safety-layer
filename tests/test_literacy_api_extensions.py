import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _client_with_temp_db(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_research.db"))
    monkeypatch.setenv("VOICE_PROVIDER", "bhashini")
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")
    return TestClient(module.app)


def _admin_headers() -> dict[str, str]:
    return {"x-pilot-admin-key": "pilot-admin-local"}


def test_essential_goals_upsert_and_get(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    payload = {
        "participant_id": "p1",
        "cohort": "daily_cashflow_worker",
        "essential_goals": ["fuel", "medicine"],
        "language": "en",
        "setup_skipped": False,
    }
    write_res = client.post("/api/literacy/essential-goals", json=payload)
    assert write_res.status_code == 200
    write_json = write_res.json()
    assert write_json["ok"] is True
    assert write_json["profile"]["essential_goals"] == ["fuel", "medicine"]

    read_res = client.get("/api/literacy/essential-goals", params={"participant_id": "p1"})
    assert read_res.status_code == 200
    read_json = read_res.json()
    assert read_json["profile"]["cohort"] == "daily_cashflow_worker"
    assert read_json["envelope"]["reserve_ratio"] > 0


def test_pilot_meta_localizes_disclaimer(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    english = client.get("/api/pilot/meta", params={"language": "en"})
    hindi = client.get("/api/pilot/meta", params={"language": "hi"})

    assert english.status_code == 200
    assert hindi.status_code == 200
    assert "research prototype" in english.json()["disclaimer"]
    assert "शोध प्रोटोटाइप" in hindi.json()["disclaimer"]


def test_sms_ingest_returns_explainability_fields(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": "p2",
            "cohort": "women_led_household",
            "essential_goals": ["ration", "school"],
            "language": "en",
            "setup_skipped": False,
        },
    )
    res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "p2",
            "language": "en",
            "amount": 6000,
            "category": "upi",
            "note": "test",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["experiment_variant"] in {"adaptive", "static_baseline"}
    assert payload["literacy_alerts"]
    alert = payload["literacy_alerts"][0]
    assert alert["risk_level"] in {"low", "medium", "high", "critical"}
    assert alert["severity"] in {"soft", "medium", "hard"}
    assert isinstance(alert.get("why_this_alert"), str) and alert["why_this_alert"]
    assert isinstance(alert.get("next_best_action"), str) and alert["next_best_action"]


def test_sms_ingest_localizes_hindi_alert_message(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "p2_hi",
            "language": "hi",
            "amount": 6000,
            "category": "upi",
            "note": "test",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["literacy_alerts"]
    alert = payload["literacy_alerts"][0]
    assert "सुरक्षित खर्च" in alert["message"] or "जरूरी जरूरतों" in alert["message"]
    assert "आज का खर्च" in alert["why_this_alert"] or "पैसा अलग" in alert["why_this_alert"]
    assert "जरूरी" in alert["next_best_action"] or "अलग रखें" in alert["next_best_action"]


def test_cashflow_guidance_explains_essential_pressure_with_goal_names(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": "cashflow_goals_p1",
            "cohort": "women_led_household",
            "essential_goals": ["ration", "school"],
            "language": "en",
            "setup_skipped": False,
        },
    )
    res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "cashflow_goals_p1",
            "language": "en",
            "amount": 1100,
            "category": "upi",
            "note": "grocery transfer",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["literacy_alerts"]
    alert = payload["literacy_alerts"][0]
    assert "money needed for essentials" in alert["message"].lower()
    assert "keeping aside money for ration, school fees" in alert["why_this_alert"].lower()
    assert "keep money aside for ration, school fees first" in alert["next_best_action"].lower()
    assert "ration, school fees" in alert["essential_goal_impact"].lower()


def test_cashflow_guidance_uses_recent_income_context_in_next_action(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    income_res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "cashflow_income_p1",
            "language": "en",
            "signal_type": "income",
            "signal_confidence": "confirmed",
            "amount": 4000,
            "category": "bank_sms",
            "note": "salary credited",
        },
    )
    assert income_res.status_code == 200

    expense_res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "cashflow_income_p1",
            "language": "en",
            "amount": 1100,
            "category": "upi",
            "note": "merchant payment",
        },
    )

    assert expense_res.status_code == 200
    payload = expense_res.json()
    assert payload["literacy_alerts"]
    alert = payload["literacy_alerts"][0]
    assert "recent money-in message" in alert["why_this_alert"].lower()
    assert "recent money received" in alert["next_best_action"].lower()


def test_reset_hard_clears_recent_income_context_and_cached_agent(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "reset_hard_income_p1"

    income_res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "signal_type": "income",
            "signal_confidence": "confirmed",
            "amount": 4000,
            "category": "bank_sms",
            "note": "salary credited",
        },
    )
    assert income_res.status_code == 200

    reset_res = client.post(
        "/api/literacy/reset-hard",
        params={"participant_id": participant_id},
        headers=_admin_headers(),
    )
    assert reset_res.status_code == 200

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
    payload = expense_res.json()
    assert payload["literacy_alerts"]
    alert = payload["literacy_alerts"][0]
    assert "recent money-in message" not in alert["why_this_alert"].lower()
    assert "recent money received" not in alert["next_best_action"].lower()


def test_sms_ingest_deduplicates_cross_source_duplicate_within_time_window(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "cross_source_dedupe_p1"

    first = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "amount": 4000,
            "category": "upi",
            "note": "SMS from +919999999999",
            "timestamp": "2026-03-16T04:16:28.952152Z",
        },
    )
    assert first.status_code == 200
    assert first.json()["deduplicated"] is False

    second = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": participant_id,
            "language": "en",
            "amount": 4000,
            "category": "upi",
            "note": "Notification from com.google.android.apps.messaging",
            "timestamp": "2026-03-16T04:16:30.138184Z",
        },
    )
    assert second.status_code == 200
    second_json = second.json()
    assert second_json["deduplicated"] is True
    assert second_json["literacy_alerts"] == []

    trace = client.get(
        "/api/literacy/debug-trace",
        params={"participant_id": participant_id, "limit": 20},
        headers=_admin_headers(),
    )
    assert trace.status_code == 200
    trace_json = trace.json()

    ingest_events = [
        event for event in trace_json["recent_literacy_events"]
        if event["event_type"] == "sms_ingest_event"
    ]
    assert len(ingest_events) == 1
    assert ingest_events[0]["note"] == "SMS from +919999999999"


def test_cashflow_guidance_localizes_goal_aware_copy_in_hindi(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": "cashflow_hi_goals",
            "cohort": "women_led_household",
            "essential_goals": ["ration", "school"],
            "language": "hi",
            "setup_skipped": False,
        },
    )
    res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "cashflow_hi_goals",
            "language": "hi",
            "amount": 1100,
            "category": "upi",
            "note": "merchant payment",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["literacy_alerts"]
    alert = payload["literacy_alerts"][0]
    assert "जरूरी जरूरतों" in alert["message"]
    assert "राशन" in alert["why_this_alert"] or "स्कूल फीस" in alert["why_this_alert"]
    assert "पहले अलग रखें" in alert["next_best_action"]
    assert "राशन" in alert["essential_goal_impact"] or "स्कूल फीस" in alert["essential_goal_impact"]


def test_sms_income_ingest_updates_context_without_expense_alert_path(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "income_p1",
            "language": "en",
            "signal_type": "income",
            "signal_confidence": "confirmed",
            "amount": 2500,
            "category": "bank_sms",
            "note": "salary credited",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["literacy_alerts"] == []
    assert payload["literacy_state"]["daily_spend"] == 0
    assert payload["transaction_result"]["balance"] == 4500

    trace = client.get(
        "/api/literacy/debug-trace",
        params={"participant_id": "income_p1", "limit": 10},
        headers=_admin_headers(),
    )
    assert trace.status_code == 200
    trace_json = trace.json()
    assert trace_json["recent_literacy_events"][0]["signal_type"] == "income"
    assert trace_json["recent_financial_context"]["income_count"] == 1
    assert trace_json["recent_financial_context"]["latest_income_amount"] == 2500.0


def test_sms_partial_ingest_preserves_safe_context_without_forcing_certainty(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "partial_p1",
            "language": "en",
            "signal_type": "partial",
            "signal_confidence": "partial",
            "amount": 5000,
            "category": "bank_sms",
            "note": "transaction alert, direction unclear",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["literacy_alerts"] == []
    assert payload["literacy_state"]["daily_spend"] == 0
    assert payload["transaction_result"] is None

    trace = client.get(
        "/api/literacy/debug-trace",
        params={"participant_id": "partial_p1", "limit": 10},
        headers=_admin_headers(),
    )
    assert trace.status_code == 200
    trace_json = trace.json()
    assert trace_json["recent_literacy_events"][0]["event_type"] == "sms_partial_context"
    assert trace_json["recent_literacy_events"][0]["signal_type"] == "partial"
    assert trace_json["recent_literacy_events"][0]["signal_confidence"] == "partial"
    assert trace_json["recent_financial_context"]["partial_count"] == 1


def test_goal_confidence_gate_keeps_low_confidence_unknown(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": "p3",
            "cohort": "daily_cashflow_worker",
            "essential_goals": ["fuel", "ration"],
            "language": "en",
            "setup_skipped": False,
        },
    )
    res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "p3",
            "language": "en",
            "amount": 4200,
            "category": "upi",
            "note": "paid to merchant xyz",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["literacy_alerts"]
    alert = payload["literacy_alerts"][0]
    assert alert["txn_goal_inferred"] == "unknown"
    assert alert["txn_goal_confidence_gate_passed"] is False


def test_essential_feedback_endpoint_updates_learning_trace(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": "p4",
            "cohort": "daily_cashflow_worker",
            "essential_goals": ["fuel", "ration"],
            "language": "en",
            "setup_skipped": False,
        },
    )
    sms_res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "p4",
            "language": "en",
            "amount": 6500,
            "category": "upi",
            "note": "beer and liquor shop payment",
        },
    )
    assert sms_res.status_code == 200
    sms_json = sms_res.json()
    assert sms_json["literacy_alerts"]
    alert = sms_json["literacy_alerts"][0]
    assert alert["txn_goal_inferred"] == "non_essential"
    assert alert["txn_goal_confidence_gate_passed"] is True

    feedback_res = client.post(
        "/api/literacy/essential-feedback",
        json={
            "alert_id": alert["alert_id"],
            "participant_id": "p4",
            "is_essential": False,
            "selected_goal": "non_essential",
        },
    )
    assert feedback_res.status_code == 200
    feedback_json = feedback_res.json()
    assert feedback_json["ok"] is True
    assert feedback_json["learned"]["selected_goal"] == "non_essential"

    trace = client.get(
        "/api/literacy/debug-trace",
        params={"participant_id": "p4", "limit": 10},
        headers=_admin_headers(),
    )
    assert trace.status_code == 200
    trace_json = trace.json()
    assert trace_json["recent_goal_feedback"]
    assert trace_json["recent_goal_feedback"][0]["selected_goal"] == "non_essential"


def test_legacy_agent_state_is_isolated_per_participant(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    tx_payload = {
        "participant_id": "web_p1",
        "type": "expense",
        "amount": 250,
        "category": "general",
        "note": "tea stall",
    }
    res = client.post("/api/transaction", json=tx_payload)
    assert res.status_code == 200

    p1_state = client.get("/api/state", params={"participant_id": "web_p1"})
    p2_state = client.get("/api/state", params={"participant_id": "web_p2"})
    p1_alerts = client.get("/api/alerts", params={"participant_id": "web_p1"})
    p2_alerts = client.get("/api/alerts", params={"participant_id": "web_p2"})

    assert p1_state.status_code == 200
    assert p2_state.status_code == 200
    assert p1_state.json()["transaction_count"] == 1
    assert p2_state.json()["transaction_count"] == 0
    assert len(p1_alerts.json()) > 0
    assert p2_alerts.json() == []


def test_frontend_mount_path_is_absolute(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    module = sys.modules["backend.main"]

    assert module.FRONTEND_DIR.is_absolute()
    assert module.FRONTEND_DIR == Path(module.FRONTEND_DIR)
    assert module.FRONTEND_DIR.exists()
    assert client.get("/").status_code == 200


def test_storage_health_reports_absolute_db_path(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.get("/api/literacy/storage-health", headers=_admin_headers())
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert Path(payload["db_path"]).is_absolute()
    assert payload["db_exists"] is True


def test_cashflow_review_is_protected_and_exposes_unified_telemetry(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.get("/api/pilot/summary")
    assert res.status_code == 401
    assert res.json() == {"detail": "unauthorized"}

    sms_res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "cashflow_review_p1",
            "language": "en",
            "amount": 6000,
            "category": "upi",
            "note": "merchant payment",
        },
    )
    assert sms_res.status_code == 200
    alert = sms_res.json()["literacy_alerts"][0]

    feedback_res = client.post(
        "/api/literacy/alert-feedback",
        json={
            "alert_id": alert["alert_id"],
            "participant_id": "cashflow_review_p1",
            "action": "dismissed",
            "channel": "overlay",
            "title": "Close",
            "message": "dismissed from overlay",
        },
    )
    assert feedback_res.status_code == 200

    review = client.get(
        "/api/pilot/review",
        params={"participant_id": "cashflow_review_p1", "limit": 10},
        headers=_admin_headers(),
    )
    assert review.status_code == 200
    review_json = review.json()
    assert review_json["telemetry_comparison"]["cashflow"]["generated_count"] >= 1
    assert review_json["telemetry_comparison"]["cashflow"]["action_count"] >= 1
    assert any(
        record["record_type"] == "generated" and record["telemetry_family"] == "cashflow"
        for record in review_json["recent_unified_telemetry"]
    )


def test_alert_feedback_event_replay_is_deduplicated(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    sms_res = client.post(
        "/api/literacy/sms-ingest",
        json={
            "participant_id": "dedupe_feedback_p1",
            "language": "en",
            "amount": 6000,
            "category": "upi",
            "note": "merchant payment",
        },
    )
    assert sms_res.status_code == 200
    alert_id = sms_res.json()["literacy_alerts"][0]["alert_id"]

    payload = {
        "event_id": "feedback-event-1",
        "alert_id": alert_id,
        "participant_id": "dedupe_feedback_p1",
        "action": "not_useful",
        "channel": "overlay",
        "title": "Not useful",
        "message": "not useful",
    }
    first = client.post("/api/literacy/alert-feedback", json=payload)
    second = client.post("/api/literacy/alert-feedback", json=payload)

    assert first.status_code == 200
    assert first.json()["deduplicated"] is False
    assert second.status_code == 200
    assert second.json()["deduplicated"] is True

    review = client.get(
        "/api/pilot/review",
        params={"participant_id": "dedupe_feedback_p1", "limit": 20},
        headers=_admin_headers(),
    )
    assert review.status_code == 200
    review_json = review.json()
    assert len(review_json["recent_alert_feedback"]) == 1
    assert review_json["telemetry_comparison"]["cashflow"]["not_useful_count"] == 1


def test_analysis_routes_expose_language_and_cohort_slices(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    consent_res = client.post(
        "/api/pilot/consent",
        json={
            "participant_id": "analysis_hi_p1",
            "accepted": True,
            "language": "hi",
        },
    )
    assert consent_res.status_code == 200

    goals_res = client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": "analysis_hi_p1",
            "cohort": "women_led_household",
            "essential_goals": ["ration"],
            "language": "hi",
            "setup_skipped": False,
        },
    )
    assert goals_res.status_code == 200

    inspect_res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "analysis_hi_p1",
            "language": "hi",
            "app_name": "PhonePe",
            "request_kind": "collect",
            "amount": 1800,
            "payee_label": "Reward Desk",
            "payee_handle": "reward@upi",
            "raw_text": "Approve collect request of Rs 1800",
            "source": "notification",
        },
    )
    assert inspect_res.status_code == 200

    analytics = client.get(
        "/api/pilot/analytics",
        params={"participant_id": "analysis_hi_p1", "limit": 20},
        headers=_admin_headers(),
    )
    assert analytics.status_code == 200
    comparison = analytics.json()["telemetry_comparison"]
    assert comparison["language_slices"]["hi"]["family_breakdown"]["payment_warning"] >= 1
    assert comparison["cohort_slices"]["women_led_household"]["family_breakdown"]["payment_warning"] >= 1
    assert comparison["payment_warning"]["trace_sample"][0]["event_id"] is None


def test_operator_sensitive_experiment_routes_require_admin(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    assignment_payload = {"participant_id": "exp_p1"}
    event_payload = {
        "participant_id": "exp_p1",
        "variant": "adaptive",
        "event_type": "warned",
    }

    unauthorized_assignment = client.post("/api/research/assignment", json=assignment_payload)
    unauthorized_event = client.post("/api/research/event", json=event_payload)
    assert unauthorized_assignment.status_code == 401
    assert unauthorized_event.status_code == 401

    authorized_assignment = client.post(
        "/api/research/assignment",
        json=assignment_payload,
        headers=_admin_headers(),
    )
    authorized_event = client.post(
        "/api/research/event",
        json=event_payload,
        headers=_admin_headers(),
    )
    assert authorized_assignment.status_code == 200
    assert authorized_event.status_code == 200


def test_client_fallback_app_logs_replay_idempotently_into_unified_telemetry(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    payload = {
        "event_id": "app-log-event-1",
        "participant_id": "fallback_log_p1",
        "level": "warn",
        "message": "payment_fallback_shown:alert-local-1:collect:2500:Merchant Desk:merchant@upi",
        "language": "en",
    }

    first = client.post("/api/pilot/app-log", json=payload)
    second = client.post("/api/pilot/app-log", json=payload)

    assert first.status_code == 200
    assert first.json()["deduplicated"] is False
    assert first.json()["telemetry_recorded"] is True
    assert second.status_code == 200
    assert second.json()["deduplicated"] is True
    assert second.json()["telemetry_recorded"] is False

    review = client.get(
        "/api/pilot/review",
        params={"participant_id": "fallback_log_p1", "limit": 20},
        headers=_admin_headers(),
    )
    assert review.status_code == 200
    review_json = review.json()
    assert review_json["telemetry_comparison"]["payment_warning"]["fallback_count"] == 1
    assert review_json["recent_unified_telemetry"][0]["event_name"] == "payment_fallback_shown"


def test_cors_origins_can_be_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_research.db"))
    monkeypatch.setenv("VOICE_PROVIDER", "bhashini")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com, https://research.example.com")
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")

    assert module.cors_allowed_origins == ["https://app.example.com", "https://research.example.com"]
    assert module.cors_allow_credentials is True

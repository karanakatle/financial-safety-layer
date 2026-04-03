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
        "all_selected_essentials": ["fuel", "medicine", "rent"],
        "active_priority_essentials": ["fuel", "medicine"],
        "selection_source": "user_selected",
        "goal_source_map": {"fuel": "user_selected", "medicine": "user_selected", "rent": "user_selected"},
        "affordability_bucket_id": "1000_1499",
        "language": "en",
        "setup_skipped": False,
    }
    write_res = client.post("/api/literacy/essential-goals", json=payload)
    assert write_res.status_code == 200
    write_json = write_res.json()
    assert write_json["ok"] is True
    assert write_json["profile"]["essential_goals"] == ["cooking_fuel", "medicine"]
    assert write_json["profile"]["all_selected_essentials"] == ["cooking_fuel", "medicine", "rent"]
    assert write_json["profile"]["active_priority_essentials"] == ["cooking_fuel", "medicine"]
    assert write_json["profile"]["selection_source"] == "user_selected"
    assert write_json["profile"]["affordability_bucket_id"] == "1000_1499"
    assert write_json["setup_config_version"] == "essential_goal_setup_v1"

    read_res = client.get("/api/literacy/essential-goals", params={"participant_id": "p1"})
    assert read_res.status_code == 200
    read_json = read_res.json()
    assert read_json["profile"]["cohort"] == "daily_cashflow_worker"
    assert read_json["profile"]["affordability_question_key"] == "daily_earnings_range"
    assert read_json["envelope"]["reserve_ratio"] > 0
    assert read_json["setup_config"]["active_priority_limit"] == 6


def test_essential_goals_auto_seed_when_selection_is_blank(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": "seeded_p1",
            "cohort": "women_led_household",
            "essential_goals": [],
            "language": "en",
            "setup_skipped": False,
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["profile"]["selection_source"] == "system_auto_seeded"
    assert payload["profile"]["active_priority_essentials"] == [
        "ration",
        "school",
        "rent",
        "medicine",
        "cooking_fuel",
        "electricity",
    ]


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


def test_context_events_can_be_ingested_and_filtered_for_review(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    notification_payload = {
        "event_id": "context-event-1",
        "participant_id": "context_p1",
        "level": "info",
        "message": "context_event:notification_observed:com.phonepe.app",
        "language": "en",
        "context_event": {
            "event_type": "notification_observed",
            "source_app": "com.phonepe.app",
            "target_app": "PhonePe",
            "correlation_id": "corr-123",
            "classification": "suppressed",
            "setup_state": "unknown",
            "suppression_reason": "setup_registration",
            "message_family": "setup_registration",
            "has_otp": False,
            "has_upi_handle": False,
            "has_upi_deeplink": False,
            "has_url": False,
            "link_clicked": False,
            "metadata": {"source": "notification"},
        },
    }
    payment_candidate_payload = {
        "event_id": "context-event-2",
        "participant_id": "context_p1",
        "level": "info",
        "message": "context_event:payment_candidate:com.phonepe.app",
        "language": "en",
        "context_event": {
            "event_type": "payment_candidate",
            "source_app": "com.phonepe.app",
            "target_app": "PhonePe",
            "correlation_id": "corr-123",
            "classification": "payment_candidate",
            "setup_state": "unknown",
            "message_family": "payment_signal",
            "amount": 2500,
            "has_otp": False,
            "has_upi_handle": True,
            "has_upi_deeplink": False,
            "has_url": False,
            "link_clicked": False,
            "metadata": {"request_kind": "collect_request"},
        },
    }

    first = client.post("/api/pilot/app-log", json=notification_payload)
    second = client.post("/api/pilot/app-log", json=payment_candidate_payload)
    assert first.status_code == 200
    assert second.status_code == 200

    context_events = client.get(
        "/api/pilot/context-events",
        params={
            "participant_id": "context_p1",
            "event_type": "payment_candidate",
            "correlation_id": "corr-123",
            "limit": 10,
        },
        headers=_admin_headers(),
    )
    assert context_events.status_code == 200
    events_json = context_events.json()
    assert events_json["count"] == 1
    assert events_json["events"][0]["event_type"] == "payment_candidate"
    assert events_json["events"][0]["correlation_id"] == "corr-123"
    assert events_json["events"][0]["metadata"]["request_kind"] == "collect_request"
    assert events_json["events"][0]["has_upi_handle"] is True
    assert events_json["breakdown"]["by_event_type"][0]["count"] >= 1

    review = client.get(
        "/api/pilot/review",
        params={"participant_id": "context_p1", "correlation_id": "corr-123", "limit": 10},
        headers=_admin_headers(),
    )
    assert review.status_code == 200
    review_json = review.json()
    assert len(review_json["recent_context_events"]) == 2
    assert {record["event_type"] for record in review_json["recent_context_events"]} == {
        "notification_observed",
        "payment_candidate",
    }


def test_pilot_analytics_exposes_context_event_breakdown(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    payload = {
        "event_id": "context-event-breakdown-1",
        "participant_id": "context_breakdown_p1",
        "level": "info",
        "message": "context_event:account_access_candidate:VM-IDFCFB",
        "language": "en",
        "context_event": {
            "event_type": "account_access_candidate",
            "source_app": "VM-IDFCFB",
            "correlation_id": "corr-breakdown-1",
            "classification": "account_access_candidate",
            "setup_state": "unknown",
            "message_family": "sensitive_access_signal",
            "has_otp": True,
            "has_upi_handle": False,
            "has_upi_deeplink": False,
            "has_url": True,
            "metadata": {"source": "sms"},
        },
    }
    created = client.post("/api/pilot/app-log", json=payload)
    assert created.status_code == 200

    analytics = client.get(
        "/api/pilot/analytics",
        params={"participant_id": "context_breakdown_p1", "limit": 10},
        headers=_admin_headers(),
    )
    assert analytics.status_code == 200
    analytics_json = analytics.json()
    assert analytics_json["recent_context_events"][0]["event_type"] == "account_access_candidate"
    assert analytics_json["context_event_breakdown"]["by_event_type"][0]["event_type"] == "account_access_candidate"
    assert analytics_json["context_event_breakdown"]["by_classification"][0]["classification"] == "account_access_candidate"


def test_context_events_store_domain_fields_and_backend_classification(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    payload = {
        "event_id": "context-event-domain-1",
        "participant_id": "context_domain_p1",
        "level": "info",
        "message": "context_event:link_click:whatsapp",
        "language": "en",
        "context_event": {
            "event_type": "link_click",
            "source_app": "com.whatsapp",
            "correlation_id": "corr-domain-1",
            "classification": "observed",
            "setup_state": "unknown",
            "message_family": "clicked_link",
            "has_url": True,
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": "secure-login.paytm-help.top",
            "resolved_domain": "paytm-help.top",
            "metadata": {"raw_url": "https://secure-login.paytm-help.top/login"},
        },
    }
    created = client.post("/api/pilot/app-log", json=payload)
    assert created.status_code == 200

    events = client.get(
        "/api/pilot/context-events",
        params={"participant_id": "context_domain_p1", "event_type": "link_click"},
        headers=_admin_headers(),
    )
    assert events.status_code == 200
    event = events.json()["events"][0]
    assert event["link_clicked"] is True
    assert event["url_host"] == "secure-login.paytm-help.top"
    assert event["resolved_domain"] == "paytm-help.top"
    assert event["domain_class"] == "suspicious"


def test_entity_registry_seeds_official_domain_from_context_event(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    payload = {
        "event_id": "entity-official-1",
        "participant_id": "entity_p1",
        "level": "info",
        "message": "context_event:link_click:browser",
        "language": "en",
        "context_event": {
            "event_type": "link_click",
            "source_app": "browser",
            "classification": "observed",
            "message_family": "clicked_link",
            "has_url": True,
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": "secure.icicibank.com",
            "resolved_domain": "icicibank.com",
            "metadata": {"raw_url": "https://secure.icicibank.com/login"},
        },
    }
    created = client.post("/api/pilot/app-log", json=payload)
    assert created.status_code == 200

    entities = client.get(
        "/api/pilot/entities",
        params={"trust_state": "official_verified"},
        headers=_admin_headers(),
    )
    assert entities.status_code == 200
    assert entities.json()["entities"][0]["entity_key"] == "icicibank.com"
    assert entities.json()["entities"][0]["trust_state"] == "official_verified"


def test_entity_registry_promotes_repeated_bank_like_domain_to_trusted_by_observation(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    for index, day in enumerate(("2026-03-20T08:00:00", "2026-03-21T08:00:00")):
        payload = {
            "event_id": f"entity-banklike-{index}",
            "participant_id": "entity_banklike_p1",
            "level": "info",
            "message": "context_event:notification_observed:bank",
            "language": "en",
            "timestamp": day,
            "context_event": {
                "event_type": "notification_observed",
                "source_app": "VM-GBANK",
                "classification": "observed",
                "message_family": "statement_or_report",
                "has_url": True,
                "link_clicked": False,
                "link_scheme": "https",
                "url_host": "secure.graminbank-example.co.in",
                "resolved_domain": "graminbank-example.co.in",
                "metadata": {"raw_url": "https://secure.graminbank-example.co.in/statement"},
            },
        }
        created = client.post("/api/pilot/app-log", json=payload)
        assert created.status_code == 200

    entities = client.get(
        "/api/pilot/entities",
        params={"trust_state": "trusted_by_observation"},
        headers=_admin_headers(),
    )
    assert entities.status_code == 200
    entity = entities.json()["entities"][0]
    assert entity["entity_key"] == "graminbank-example.co.in"
    assert entity["entity_type"] == "bank"
    assert entity["trust_state"] == "trusted_by_observation"
    assert entity["benign_count"] >= 2
    assert entity["evidence"]["distinct_benign_days"] == 2


def test_entity_registry_does_not_promote_same_day_benign_burst_without_additional_signals(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    for index in range(5):
        payload = {
            "event_id": f"entity-sameday-{index}",
            "participant_id": "entity_same_day_p1",
            "level": "info",
            "message": "context_event:notification_observed:bank",
            "language": "en",
            "timestamp": f"2026-03-20T0{index}:00:00",
            "context_event": {
                "event_type": "notification_observed",
                "source_app": f"VM-GBANK-{index}",
                "classification": "observed",
                "message_family": "statement_or_report",
                "has_url": True,
                "link_clicked": False,
                "link_scheme": "https",
                "url_host": "secure.graminbank-burst.co.in",
                "resolved_domain": "graminbank-burst.co.in",
                "metadata": {"raw_url": "https://secure.graminbank-burst.co.in/statement"},
            },
        }
        created = client.post("/api/pilot/app-log", json=payload)
        assert created.status_code == 200

    entities = client.get(
        "/api/pilot/entities",
        params={"entity_kind": "domain"},
        headers=_admin_headers(),
    )
    assert entities.status_code == 200
    entity = next(item for item in entities.json()["entities"] if item["entity_key"] == "graminbank-burst.co.in")
    assert entity["trust_state"] == "financial_unknown"
    assert entity["benign_count"] >= 5
    assert entity["evidence"]["distinct_benign_days"] == 1


def test_entity_registry_rewards_sender_domain_app_consistency(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "entity_consistency_p1"
    for index in range(2):
        payload = {
            "event_id": f"entity-consistency-{index}",
            "participant_id": participant_id,
            "level": "info",
            "message": "context_event:notification_observed:bank",
            "language": "en",
            "context_event": {
                "event_type": "notification_observed",
                "source_app": "VM-GBANK",
                "target_app": "Gramin Bank",
                "classification": "observed",
                "message_family": "statement_or_report",
                "has_url": True,
                "link_clicked": False,
                "link_scheme": "https",
                "url_host": "secure.graminbank-consistent.co.in",
                "resolved_domain": "graminbank-consistent.co.in",
                "metadata": {"raw_url": "https://secure.graminbank-consistent.co.in/statement"},
            },
        }
        created = client.post("/api/pilot/app-log", json=payload)
        assert created.status_code == 200

    entities = client.get(
        "/api/pilot/entities",
        params={"trust_state": "trusted_by_observation"},
        headers=_admin_headers(),
    )
    assert entities.status_code == 200
    entity = next(item for item in entities.json()["entities"] if item["entity_key"] == "graminbank-consistent.co.in")
    assert entity["trust_score"] >= 30.0
    assert entity["evidence"]["canonical_source_app"] == "vm-gbank"
    assert entity["evidence"]["canonical_target_app"] == "gramin bank"
    assert entity["evidence"]["source_consistency_count"] == 2
    assert entity["evidence"]["target_consistency_count"] == 2


def test_entity_registry_marks_clicked_suspicious_access_domain_as_suspicious(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    payload = {
        "event_id": "entity-suspicious-1",
        "participant_id": "entity_suspicious_p1",
        "level": "info",
        "message": "context_event:account_access_candidate:browser",
        "language": "en",
        "context_event": {
            "event_type": "account_access_candidate",
            "source_app": "browser",
            "classification": "account_access_candidate",
            "message_family": "otp_verification",
            "has_otp": True,
            "has_url": True,
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": "secure-login-paytm-help.top",
            "resolved_domain": "paytm-help.top",
            "metadata": {"raw_url": "https://secure-login-paytm-help.top/login"},
        },
    }
    created = client.post("/api/pilot/app-log", json=payload)
    assert created.status_code == 200

    entities = client.get(
        "/api/pilot/entities",
        params={"trust_state": "suspicious"},
        headers=_admin_headers(),
    )
    assert entities.status_code == 200
    entity = entities.json()["entities"][0]
    assert entity["entity_key"] == "paytm-help.top"
    assert entity["trust_state"] == "suspicious"
    assert entity["account_access_risk_count"] >= 1


def test_review_exposes_grouped_sequence_traces(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "sequence_review_p1"
    events = [
        {
            "event_id": "sequence-review-chat",
            "timestamp": "2026-03-22T09:00:00Z",
            "context_event": {
                "event_type": "chat_context",
                "source_app": "WhatsApp",
                "classification": "observed",
                "message_family": "chat_pressure",
            },
        },
        {
            "event_id": "sequence-review-link",
            "timestamp": "2026-03-22T09:00:30Z",
            "context_event": {
                "event_type": "link_click",
                "source_app": "browser",
                "classification": "observed",
                "message_family": "clicked_link",
                "link_clicked": True,
                "link_scheme": "https",
                "url_host": "secure.fakebank.top",
                "resolved_domain": "fakebank.top",
                "domain_class": "suspicious",
            },
        },
        {
            "event_id": "sequence-review-otp",
            "timestamp": "2026-03-22T09:01:00Z",
            "context_event": {
                "event_type": "sms_observed",
                "source_app": "VM-BANK",
                "classification": "observed",
                "message_family": "otp_verification",
                "has_otp": True,
            },
        },
    ]
    for event in events:
        res = client.post(
            "/api/pilot/app-log",
            json={
                "participant_id": participant_id,
                "level": "info",
                "message": event["event_id"],
                "language": "en",
                "timestamp": event["timestamp"],
                "context_event": event["context_event"],
            },
        )
        assert res.status_code == 200

    review = client.get(
        "/api/pilot/review",
        params={"participant_id": participant_id},
        headers=_admin_headers(),
    )
    assert review.status_code == 200
    payload = review.json()
    assert payload["recent_sequence_traces"]
    trace = payload["recent_sequence_traces"][0]
    assert trace["event_count"] >= 3
    assert trace["window"] == "0-120s"
    assert "chat_context" in trace["event_types"]
    assert "link_click" in trace["event_types"]


def test_entity_reputation_aggregates_across_participants_and_is_queryable(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    domain = "graminbank-risk.co.in"
    for participant_id in ("rep_p1", "rep_p2"):
        res = client.post(
            "/api/pilot/app-log",
            json={
                "participant_id": participant_id,
                "level": "info",
                "message": f"cross_user_signal:{participant_id}",
                "language": "en",
                "timestamp": "2026-03-22T11:00:00Z",
                "context_event": {
                    "event_type": "account_access_candidate",
                    "source_app": "browser",
                    "classification": "account_access_candidate",
                    "message_family": "otp_verification",
                    "has_otp": True,
                    "has_url": True,
                    "link_clicked": True,
                    "link_scheme": "https",
                    "url_host": f"secure.{domain}",
                    "resolved_domain": domain,
                    "domain_class": "bank",
                },
            },
        )
        assert res.status_code == 200

    reputations = client.get(
        "/api/pilot/entity-reputations",
        headers=_admin_headers(),
    )
    assert reputations.status_code == 200
    record = next(item for item in reputations.json()["entity_reputations"] if item["entity_key"] == domain)
    assert record["unique_participant_count"] == 2
    assert record["account_access_risk_count"] >= 2
    assert record["reputation_score"] >= 3.0

    review = client.get(
        "/api/pilot/review",
        params={"participant_id": "rep_p1"},
        headers=_admin_headers(),
    )
    assert review.status_code == 200
    assert any(item["entity_key"] == domain for item in review.json()["recent_entity_reputations"])


def test_entity_cohort_reputation_segments_by_cohort(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    domain = "graminbank-cohort.co.in"
    cohort_assignments = {
        "cohort_a_p1": "women_led_household",
        "cohort_a_p2": "women_led_household",
        "cohort_b_p1": "daily_cashflow_worker",
    }
    for participant_id, cohort in cohort_assignments.items():
        profile_res = client.post(
            "/api/literacy/essential-goals",
            json={
                "participant_id": participant_id,
                "cohort": cohort,
                "essential_goals": ["ration"],
                "language": "en",
                "setup_skipped": False,
            },
        )
        assert profile_res.status_code == 200

    for participant_id in cohort_assignments:
        res = client.post(
            "/api/pilot/app-log",
            json={
                "participant_id": participant_id,
                "level": "info",
                "message": f"cohort_signal:{participant_id}",
                "language": "en",
                "timestamp": "2026-03-22T12:00:00Z",
                "context_event": {
                    "event_type": "account_access_candidate",
                    "source_app": "browser",
                    "classification": "account_access_candidate",
                    "message_family": "otp_verification",
                    "has_otp": True,
                    "has_url": True,
                    "link_clicked": True,
                    "link_scheme": "https",
                    "url_host": f"secure.{domain}",
                    "resolved_domain": domain,
                    "domain_class": "bank",
                },
            },
        )
        assert res.status_code == 200

    reputations = client.get(
        "/api/pilot/entity-cohort-reputations",
        params={"cohort": "women_led_household"},
        headers=_admin_headers(),
    )
    assert reputations.status_code == 200
    record = next(item for item in reputations.json()["entity_cohort_reputations"] if item["entity_key"] == domain)
    assert record["cohort"] == "women_led_household"
    assert record["unique_participant_count"] == 2

    other_reputations = client.get(
        "/api/pilot/entity-cohort-reputations",
        params={"cohort": "daily_cashflow_worker"},
        headers=_admin_headers(),
    )
    assert other_reputations.status_code == 200
    other_record = next(item for item in other_reputations.json()["entity_cohort_reputations"] if item["entity_key"] == domain)
    assert other_record["cohort"] == "daily_cashflow_worker"
    assert other_record["unique_participant_count"] == 1

    review = client.get(
        "/api/pilot/review",
        params={"participant_id": "cohort_a_p1"},
        headers=_admin_headers(),
    )
    assert review.status_code == 200
    assert any(item["entity_key"] == domain for item in review.json()["recent_entity_cohort_reputations"])


def test_reviewer_override_pins_entity_trust_state(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    seed_payload = {
        "event_id": "entity-review-seed-1",
        "participant_id": "entity_review_p1",
        "level": "info",
        "message": "context_event:link_click:browser",
        "language": "en",
        "context_event": {
            "event_type": "link_click",
            "source_app": "browser",
            "target_app": "Unknown Bank",
            "classification": "observed",
            "message_family": "clicked_link",
            "has_url": True,
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": "secure.graminbank-review.co.in",
            "resolved_domain": "graminbank-review.co.in",
            "metadata": {"raw_url": "https://secure.graminbank-review.co.in/login"},
        },
    }
    created = client.post("/api/pilot/app-log", json=seed_payload)
    assert created.status_code == 200

    review_res = client.post(
        "/api/pilot/entities/review",
        headers=_admin_headers(),
        json={
            "entity_key": "graminbank-review.co.in",
            "entity_kind": "domain",
            "trust_state": "blocked",
            "review_status": "manual_override",
            "note": "confirmed phishing infrastructure",
        },
    )
    assert review_res.status_code == 200
    assert review_res.json()["entity"]["trust_state"] == "blocked"
    assert review_res.json()["entity"]["review_status"] == "manual_override"

    followup_payload = {
        "event_id": "entity-review-seed-2",
        "participant_id": "entity_review_p1",
        "level": "info",
        "message": "context_event:notification_observed:bank",
        "language": "en",
        "context_event": {
            "event_type": "notification_observed",
            "source_app": "VM-GBANK",
            "target_app": "Unknown Bank",
            "classification": "observed",
            "message_family": "statement_or_report",
            "has_url": True,
            "link_clicked": False,
            "link_scheme": "https",
            "url_host": "secure.graminbank-review.co.in",
            "resolved_domain": "graminbank-review.co.in",
        },
    }
    second = client.post("/api/pilot/app-log", json=followup_payload)
    assert second.status_code == 200

    entities = client.get(
        "/api/pilot/entities",
        params={"review_status": "manual_override"},
        headers=_admin_headers(),
    )
    assert entities.status_code == 200
    entity = next(item for item in entities.json()["entities"] if item["entity_key"] == "graminbank-review.co.in")
    assert entity["trust_state"] == "blocked"
    assert entity["review_status"] == "manual_override"
    assert entity["evidence"]["last_review_note"] == "confirmed phishing infrastructure"


def test_review_samples_can_be_labeled_and_exported_with_gold_filters(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "review_sample_live_p1"
    correlation_id = "review-sample-corr-1"

    profile_res = client.post(
        "/api/literacy/essential-goals",
        json={
            "participant_id": participant_id,
            "cohort": "women_led_household",
            "essential_goals": ["ration", "school"],
            "language": "en",
            "setup_skipped": False,
        },
    )
    assert profile_res.status_code == 200

    first_event = client.post(
        "/api/pilot/app-log",
        json={
            "event_id": "review-sample-event-1",
            "participant_id": participant_id,
            "level": "info",
            "message": "context_event:link_click:browser",
            "language": "en",
            "timestamp": "2026-03-22T10:00:00Z",
            "context_event": {
                "event_type": "link_click",
                "source_app": "browser",
                "target_app": "Gramin Bank",
                "correlation_id": correlation_id,
                "classification": "observed",
                "message_family": "clicked_link",
                "has_url": True,
                "link_clicked": True,
                "link_scheme": "https",
                "url_host": "secure.graminbank-live.co.in",
                "resolved_domain": "graminbank-live.co.in",
                "domain_class": "bank",
                "metadata": {"raw_url": "https://secure.graminbank-live.co.in/login"},
            },
        },
    )
    assert first_event.status_code == 200

    second_event = client.post(
        "/api/pilot/app-log",
        json={
            "event_id": "review-sample-event-2",
            "participant_id": participant_id,
            "level": "info",
            "message": "context_event:account_access_candidate",
            "language": "en",
            "timestamp": "2026-03-22T10:01:00Z",
            "context_event": {
                "event_type": "account_access_candidate",
                "source_app": "browser",
                "target_app": "Gramin Bank",
                "correlation_id": correlation_id,
                "classification": "account_access_candidate",
                "message_family": "otp_verification",
                "has_otp": True,
                "has_url": True,
                "link_clicked": True,
                "link_scheme": "https",
                "url_host": "secure.graminbank-live.co.in",
                "resolved_domain": "graminbank-live.co.in",
                "domain_class": "bank",
            },
        },
    )
    assert second_event.status_code == 200

    created = client.post(
        "/api/pilot/review-samples",
        headers=_admin_headers(),
        json={
            "sample_id": "review-live-1",
            "participant_id": participant_id,
            "correlation_id": correlation_id,
            "source_tier": "live_reviewed_ground_truth",
            "source_origin": "participant_trace",
            "review_status": "queued",
            "reviewer_id": "analyst_a",
        },
    )
    assert created.status_code == 200
    created_json = created.json()["sample"]
    assert created_json["sample_id"] == "review-live-1"
    assert created_json["review_status"] == "queued"
    assert len(created_json["event_trace"]) >= 2
    assert created_json["entity_context"]["entity_key"] == "graminbank-live.co.in"

    approved = client.post(
        "/api/pilot/review-samples",
        headers=_admin_headers(),
        json={
            "sample_id": "review-live-1",
            "participant_id": participant_id,
            "correlation_id": correlation_id,
            "source_tier": "live_reviewed_ground_truth",
            "source_origin": "participant_trace",
            "label": "account_access_risk",
            "review_status": "approved_ground_truth",
            "reviewer_id": "analyst_a",
            "note": "confirmed access-risk sequence",
        },
    )
    assert approved.status_code == 200
    approved_json = approved.json()["sample"]
    assert approved_json["review_status"] == "approved_ground_truth"
    assert approved_json["label"] == "account_access_risk"
    assert approved_json["cohort"] == "women_led_household"
    assert approved_json["language"] == "en"

    bootstrap = client.post(
        "/api/pilot/review-samples",
        headers=_admin_headers(),
        json={
            "sample_id": "review-bootstrap-1",
            "source_tier": "bootstrap_public",
            "source_origin": "website",
            "label": "account_access_risk",
            "review_status": "bootstrap_only",
            "reviewer_id": "analyst_b",
            "event_trace": [{"text": "public scam example"}],
            "sequence_trace": [{"signal": "clicked_link"}],
            "entity_context": {"resolved_domain": "example-phish.test"},
            "language": "en",
            "cohort": "unknown",
        },
    )
    assert bootstrap.status_code == 200

    uncertain = client.post(
        "/api/pilot/review-samples",
        headers=_admin_headers(),
        json={
            "sample_id": "review-live-uncertain",
            "participant_id": participant_id,
            "correlation_id": correlation_id,
            "source_tier": "live_reviewed_ground_truth",
            "source_origin": "participant_trace",
            "label": "uncertain",
            "review_status": "approved_ground_truth",
            "reviewer_id": "analyst_c",
        },
    )
    assert uncertain.status_code == 200

    review_samples = client.get(
        "/api/pilot/review-samples",
        headers=_admin_headers(),
        params={"participant_id": participant_id},
    )
    assert review_samples.status_code == 200
    review_samples_json = review_samples.json()
    assert review_samples_json["count"] >= 2
    assert any(item["sample_id"] == "review-live-1" for item in review_samples_json["review_samples"])
    assert review_samples_json["breakdown"]["by_source_tier"]

    review = client.get(
        "/api/pilot/review",
        headers=_admin_headers(),
        params={"participant_id": participant_id, "correlation_id": correlation_id},
    )
    assert review.status_code == 200
    review_json = review.json()
    assert any(item["sample_id"] == "review-live-1" for item in review_json["recent_review_samples"])
    assert review_json["review_sample_breakdown"]["by_review_status"]

    all_reviewed_export = client.get(
        "/api/pilot/review-exports",
        headers=_admin_headers(),
        params={"mode": "all_reviewed_samples"},
    )
    assert all_reviewed_export.status_code == 200
    all_records = all_reviewed_export.json()["records"]
    assert any(item["sample_id"] == "review-live-1" for item in all_records)
    assert any(item["sample_id"] == "review-bootstrap-1" for item in all_records)
    assert all(item["export_version"] == all_reviewed_export.json()["export_version"] for item in all_records)

    gold_export = client.get(
        "/api/pilot/review-exports",
        headers=_admin_headers(),
        params={"mode": "gold_ground_truth_only"},
    )
    assert gold_export.status_code == 200
    gold_records = gold_export.json()["records"]
    assert [item["sample_id"] for item in gold_records] == ["review-live-1"]

    gold_with_uncertain = client.get(
        "/api/pilot/review-exports",
        headers=_admin_headers(),
        params={"mode": "gold_ground_truth_only", "include_uncertain": "true"},
    )
    assert gold_with_uncertain.status_code == 200
    gold_with_uncertain_ids = {item["sample_id"] for item in gold_with_uncertain.json()["records"]}
    assert "review-live-1" in gold_with_uncertain_ids
    assert "review-live-uncertain" in gold_with_uncertain_ids


def test_cors_origins_can_be_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_research.db"))
    monkeypatch.setenv("VOICE_PROVIDER", "bhashini")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com, https://research.example.com")
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")

    assert module.cors_allowed_origins == ["https://app.example.com", "https://research.example.com"]
    assert module.cors_allow_credentials is True

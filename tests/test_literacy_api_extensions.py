import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _client_with_temp_db(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_research.db"))
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")
    return TestClient(module.app)


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
    assert isinstance(alert.get("why_this_alert"), str) and alert["why_this_alert"]
    assert isinstance(alert.get("next_best_action"), str) and alert["next_best_action"]


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

    trace = client.get("/api/literacy/debug-trace", params={"participant_id": "p4", "limit": 10})
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

    res = client.get("/api/literacy/storage-health")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert Path(payload["db_path"]).is_absolute()
    assert payload["db_exists"] is True


def test_cors_origins_can_be_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_research.db"))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com, https://research.example.com")
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")

    assert module.cors_allowed_origins == ["https://app.example.com", "https://research.example.com"]
    assert module.cors_allow_credentials is True

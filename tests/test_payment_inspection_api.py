import importlib
import sys

from fastapi.testclient import TestClient


def _client_with_temp_db(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PILOT_DB_PATH", str(tmp_path / "pilot_research.db"))
    monkeypatch.setenv("VOICE_PROVIDER", "bhashini")
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
    module = importlib.import_module("backend.main")
    return TestClient(module.app)


def test_upi_request_inspect_returns_structured_contract(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_1",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "collect",
            "amount": 2500,
            "payee_label": "Test Merchant",
            "payee_handle": "merchant@upi",
            "raw_text": "Approve collect request of Rs 2500",
            "source": "notification",
            "timestamp": "2026-03-14T10:00:00Z",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["scenario"] == "unknown"
    assert payload["risk_level"] == "medium"
    assert isinstance(payload["message"], str) and payload["message"]
    assert isinstance(payload["why_this_alert"], str) and payload["why_this_alert"]
    assert isinstance(payload["next_best_action"], str) and payload["next_best_action"]
    assert payload["actions"] == ["pause", "decline", "proceed"]
    assert isinstance(payload["alert_id"], str) and payload["alert_id"]


def test_upi_request_inspect_falls_back_safely_for_partial_payload(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "",
            "language": "hi",
            "raw_text": "",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["scenario"] == "unknown"
    assert payload["risk_level"] == "medium"
    assert "रुक" in payload["message"] or "जांच" in payload["message"]
    assert "भरोसे" in payload["why_this_alert"] or "सावधानी" in payload["why_this_alert"]
    assert "पुष्टि" in payload["next_best_action"] or "जांच" in payload["next_best_action"]
    assert payload["actions"] == ["pause", "decline", "proceed"]
    assert isinstance(payload["alert_id"], str) and payload["alert_id"]

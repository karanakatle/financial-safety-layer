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
    assert payload["scenario"] == "collect_request_confusion"
    assert payload["risk_level"] == "high"
    assert "send money" in payload["message"].lower()
    assert "collect" in payload["why_this_alert"].lower() or "approval" in payload["why_this_alert"].lower()
    assert "pause" in payload["next_best_action"].lower() or "verify" in payload["next_best_action"].lower()
    assert payload["actions"] == ["pause", "decline", "proceed"]
    assert isinstance(payload["alert_id"], str) and payload["alert_id"]


def test_upi_request_inspect_classifies_refund_reward_kyc_scam_in_hindi(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_2",
            "language": "hi",
            "app_name": "PhonePe",
            "request_kind": "collect_request",
            "amount": 1999,
            "payee_label": "Reward Desk",
            "payee_handle": "rewarddesk@upi",
            "raw_text": "Reward cashback claim ke liye collect request approve karein",
            "source": "notification",
            "timestamp": "2026-03-14T10:05:00Z",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["scenario"] == "refund_reward_kyc_scam"
    assert payload["risk_level"] == "high"
    assert "रिफंड" in payload["message"] or "इनाम" in payload["message"] or "KYC" in payload["message"]
    assert "ठगी" in payload["why_this_alert"] or "कलेक्ट" in payload["why_this_alert"]
    assert "आधिकारिक" in payload["next_best_action"] or "जांच" in payload["next_best_action"]
    assert payload["actions"] == ["pause", "decline", "proceed"]
    assert isinstance(payload["alert_id"], str) and payload["alert_id"]


def test_upi_request_inspect_classifies_unknown_payee_or_unusual_amount(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_3",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "unknown_request",
            "amount": 8500,
            "payee_label": "",
            "payee_handle": "",
            "raw_text": "Approve payment request of Rs 8500",
            "source": "notification",
            "timestamp": "2026-03-14T10:10:00Z",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["scenario"] == "unknown_payee_or_unusual_amount"
    assert payload["risk_level"] == "medium"
    assert "unfamiliar payee" in payload["message"].lower() or "unusual" in payload["message"].lower()
    assert "manual verification" in payload["why_this_alert"].lower() or "payee" in payload["why_this_alert"].lower()
    assert "verify the payee" in payload["next_best_action"].lower() or "decline" in payload["next_best_action"].lower()
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

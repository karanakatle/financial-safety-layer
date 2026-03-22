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


def _admin_headers() -> dict[str, str]:
    return {"x-pilot-admin-key": "pilot-admin-local"}


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
    assert payload["scenario"] == "ignore_benign"
    assert payload["classification"] == "ignore_benign"
    assert payload["should_warn"] is False
    assert payload["risk_level"] == "low"
    assert payload["message"] == ""
    assert payload["why_this_alert"] == ""
    assert payload["next_best_action"] == ""
    assert payload["actions"] == ["pause", "decline", "proceed"]
    assert isinstance(payload["alert_id"], str) and payload["alert_id"]


def test_upi_request_inspect_ignores_registration_success_notifications(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_ignore_setup",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "unknown_request",
            "raw_text": "Use PhonePe on your current device! You have successfully registered your PhonePe account.",
            "source": "notification",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "ignore_benign"
    assert payload["should_warn"] is False
    assert payload["message"] == ""


def test_upi_request_inspect_ignores_call_metadata_from_whatsapp(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_ignore_call",
            "language": "en",
            "app_name": "WhatsApp",
            "request_kind": "unknown_request",
            "payee_label": "Rajendra Gopani",
            "raw_text": "Rajendra Gopani Incoming voice call",
            "source": "notification",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "ignore_benign"
    assert payload["should_warn"] is False


def test_upi_request_inspect_stores_otp_access_signals_without_warning(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_store_only",
            "language": "en",
            "app_name": "ICICI Bank",
            "request_kind": "unknown_request",
            "raw_text": "Dear Customer, 489647 is the OTP for your request initiated through ICICI Bank Mobile Banking.",
            "source": "notification",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "store_only_account_access"
    assert payload["should_warn"] is False


def test_upi_request_inspect_persists_unified_payment_telemetry(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    inspect_res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_review",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "collect",
            "amount": 3200,
            "payee_label": "Merchant Desk",
            "payee_handle": "merchant@upi",
            "raw_text": "Approve collect request of Rs 3200",
            "source": "notification",
            "timestamp": "2026-03-14T10:20:00Z",
        },
    )
    assert inspect_res.status_code == 200
    alert_id = inspect_res.json()["alert_id"]

    feedback_res = client.post(
        "/api/literacy/alert-feedback",
        json={
            "alert_id": alert_id,
            "participant_id": "p_payment_review",
            "action": "declined",
            "channel": "notification",
            "title": "Declined",
            "message": "participant declined the request",
            "timestamp": "2026-03-14T10:21:00Z",
        },
    )
    assert feedback_res.status_code == 200

    summary_res = client.get(
        "/api/pilot/summary",
        params={"participant_id": "p_payment_review", "limit": 10},
        headers=_admin_headers(),
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["telemetry_comparison"]["payment_warning"]["generated_count"] >= 1
    assert summary["telemetry_comparison"]["payment_warning"]["action_count"] >= 1
    assert summary["recent_unified_telemetry"][0]["telemetry_family"] == "payment_warning"


def test_upi_request_inspect_does_not_persist_ignored_payment_warning_telemetry(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    inspect_res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_ignore_telemetry",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "unknown_request",
            "raw_text": "Use PhonePe on your current device! You have successfully registered your PhonePe account.",
            "source": "notification",
            "timestamp": "2026-03-22T06:48:54Z",
        },
    )
    assert inspect_res.status_code == 200
    assert inspect_res.json()["should_warn"] is False

    summary_res = client.get(
        "/api/pilot/summary",
        params={"participant_id": "p_payment_ignore_telemetry", "limit": 10},
        headers=_admin_headers(),
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["telemetry_comparison"]["payment_warning"]["generated_count"] == 0

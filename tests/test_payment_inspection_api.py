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


def _onboarding_apps() -> list[tuple[str, str]]:
    return [
        ("PhonePe", "com.phonepe.app"),
        ("Google Pay", "com.google.android.apps.nbu.paisa.user"),
        ("Paytm", "net.one97.paytm"),
    ]


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
    assert payload["alert_family"] == "payment"
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
    assert payload["alert_family"] == "payment"
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
    assert payload["alert_family"] == "payment"
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
    assert payload["alert_family"] == "payment"
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


def test_upi_request_inspect_suppresses_ambiguous_setup_context_when_setup_state_is_active(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_setup_active",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "unknown_request",
            "payee_handle": "helper@upi",
            "raw_text": "Complete verification to continue setup",
            "source": "notification",
            "setup_state": "phone_verification",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "ignore_benign"
    assert payload["should_warn"] is False


def test_upi_request_inspect_keeps_explicit_collect_visible_during_setup(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_setup_collect",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "collect_request",
            "amount": 2500,
            "payee_label": "Merchant Desk",
            "payee_handle": "merchant@upi",
            "raw_text": "Approve collect request of Rs 2500",
            "source": "notification",
            "setup_state": "phone_verification",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "payment_outflow_risk"
    assert payload["should_warn"] is True


def test_upi_request_inspect_promotes_clicked_suspicious_link_otp_to_visible_access_alert(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_suspicious_link_otp",
            "language": "en",
            "app_name": "Browser",
            "request_kind": "unknown_request",
            "raw_text": "OTP for your mobile banking login is 489647",
            "source": "notification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": "secure-login-paytm-help.top",
            "resolved_domain": "paytm-help.top",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "account_access_risk"
    assert payload["alert_family"] == "account_access"
    assert payload["should_warn"] is True
    assert payload["actions"] == ["pause", "protect", "proceed"]


def test_upi_request_inspect_keeps_official_setup_otp_silent_even_with_clicked_link(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_official_setup_otp",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "unknown_request",
            "raw_text": "Verify mobile number to continue setup. Your verification code is 456789.",
            "source": "notification",
            "setup_state": "phone_verification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": "secure.icicibank.com",
            "resolved_domain": "icicibank.com",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "ignore_benign"
    assert payload["should_warn"] is False


def test_upi_request_inspect_downgrades_bank_like_access_flow_after_trusted_observation(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "p_payment_trusted_bank_access"
    domain = "grameenbank.co.in"

    for index, day in enumerate(
        (
            "2026-03-20T08:00:00",
            "2026-03-21T08:00:00",
            "2026-03-21T12:00:00",
            "2026-03-22T08:00:00",
            "2026-03-22T12:00:00",
        )
    ):
        res = client.post(
            "/api/pilot/app-log",
            json={
                "participant_id": participant_id,
                "level": "info",
                "message": f"trusted_bank_seed_{index}",
                "language": "en",
                "timestamp": day,
                "context_event": {
                    "event_type": "notification_observed",
                    "classification": "observed",
                    "message_family": "statement_or_report",
                    "link_clicked": False,
                    "link_scheme": "https",
                    "url_host": f"secure.{domain}",
                    "resolved_domain": domain,
                    "domain_class": "bank",
                },
            },
        )
        assert res.status_code == 200

    inspect_res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": participant_id,
            "language": "en",
            "app_name": "Browser",
            "request_kind": "unknown_request",
            "raw_text": "OTP for your mobile banking login is 489647",
            "source": "notification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": f"secure.{domain}",
            "resolved_domain": domain,
            "domain_class": "bank",
        },
    )

    assert inspect_res.status_code == 200
    payload = inspect_res.json()
    assert payload["classification"] == "store_only_account_access"
    assert payload["should_warn"] is False


def test_upi_request_inspect_promotes_trusted_bank_access_when_strong_sequence_exists(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "p_payment_trusted_bank_sequence"
    domain = "grameenbank-sequence.co.in"

    for index, day in enumerate(
        (
            "2026-03-20T08:00:00Z",
            "2026-03-21T08:00:00Z",
            "2026-03-22T08:00:00Z",
        )
    ):
        res = client.post(
            "/api/pilot/app-log",
            json={
                "participant_id": participant_id,
                "level": "info",
                "message": f"trusted_bank_seed_{index}",
                "language": "en",
                "timestamp": day,
                "context_event": {
                    "event_type": "notification_observed",
                    "classification": "observed",
                    "message_family": "statement_or_report",
                    "link_clicked": False,
                    "link_scheme": "https",
                    "url_host": f"secure.{domain}",
                    "resolved_domain": domain,
                    "domain_class": "bank",
                },
            },
        )
        assert res.status_code == 200

    context_events = [
        {
            "event_id": "seq-chat-1",
            "timestamp": "2026-03-22T10:00:00Z",
            "context_event": {
                "event_type": "chat_context",
                "source_app": "WhatsApp",
                "classification": "observed",
                "message_family": "chat_pressure",
            },
        },
        {
            "event_id": "seq-link-1",
            "timestamp": "2026-03-22T10:00:40Z",
            "context_event": {
                "event_type": "link_click",
                "source_app": "browser",
                "classification": "observed",
                "message_family": "clicked_link",
                "link_clicked": True,
                "link_scheme": "https",
                "url_host": f"secure.{domain}",
                "resolved_domain": domain,
                "domain_class": "bank",
            },
        },
        {
            "event_id": "seq-otp-1",
            "timestamp": "2026-03-22T10:01:10Z",
            "context_event": {
                "event_type": "sms_observed",
                "source_app": "VM-GBANK",
                "classification": "observed",
                "message_family": "otp_verification",
                "has_otp": True,
                "link_clicked": False,
                "link_scheme": "https",
                "url_host": f"secure.{domain}",
                "resolved_domain": domain,
                "domain_class": "bank",
            },
        },
    ]
    for event in context_events:
        res = client.post(
            "/api/pilot/app-log",
            json={
                "participant_id": participant_id,
                "level": "info",
                "message": f"context_event:{event['event_id']}",
                "language": "en",
                "timestamp": event["timestamp"],
                "context_event": event["context_event"],
            },
        )
        assert res.status_code == 200

    inspect_res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": participant_id,
            "language": "en",
            "app_name": "Browser",
            "request_kind": "unknown_request",
            "raw_text": "OTP for your mobile banking login is 489647",
            "source": "notification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": f"secure.{domain}",
            "resolved_domain": domain,
            "domain_class": "bank",
            "timestamp": "2026-03-22T10:01:30Z",
        },
    )

    assert inspect_res.status_code == 200
    payload = inspect_res.json()
    assert payload["classification"] == "account_access_risk"
    assert payload["should_warn"] is True
    assert payload["sequence_window"] == "0-120s"
    assert payload["sequence_trace"]

    review = client.get(
        "/api/pilot/review",
        params={"participant_id": participant_id},
        headers=_admin_headers(),
    )
    assert review.status_code == 200
    review_json = review.json()
    assert review_json["recent_sequence_traces"]
    assert review_json["recent_sequence_traces"][0]["window"] in {"0-120s", "2-10m"}


def test_upi_request_inspect_uses_cross_user_reputation_to_escalate_trusted_bank_access(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "p_payment_trusted_bank_reputation"
    domain = "grameenbank-reputation.co.in"

    for index, day in enumerate(
        (
            "2026-03-20T08:00:00Z",
            "2026-03-21T08:00:00Z",
            "2026-03-22T08:00:00Z",
        )
    ):
        res = client.post(
            "/api/pilot/app-log",
            json={
                "participant_id": participant_id,
                "level": "info",
                "message": f"trusted_bank_seed_{index}",
                "language": "en",
                "timestamp": day,
                "context_event": {
                    "event_type": "notification_observed",
                    "classification": "observed",
                    "message_family": "statement_or_report",
                    "link_clicked": False,
                    "link_scheme": "https",
                    "url_host": f"secure.{domain}",
                    "resolved_domain": domain,
                    "domain_class": "bank",
                },
            },
        )
        assert res.status_code == 200

    for external_participant in ("other_p1", "other_p2"):
        res = client.post(
            "/api/pilot/app-log",
            json={
                "participant_id": external_participant,
                "level": "info",
                "message": f"cross_user_signal:{external_participant}",
                "language": "en",
                "timestamp": "2026-03-22T11:30:00Z",
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

    inspect_res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": participant_id,
            "language": "en",
            "app_name": "Browser",
            "request_kind": "unknown_request",
            "raw_text": "OTP for your mobile banking login is 489647",
            "source": "notification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": f"secure.{domain}",
            "resolved_domain": domain,
            "domain_class": "bank",
            "timestamp": "2026-03-22T11:31:00Z",
        },
    )

    assert inspect_res.status_code == 200
    payload = inspect_res.json()
    assert payload["classification"] == "account_access_risk"
    assert payload["should_warn"] is True
    assert "across participants" in payload["why_this_alert"].lower()


def test_upi_request_inspect_keeps_no_click_statement_link_benign(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_benign_statement_link",
            "language": "en",
            "app_name": "Bank",
            "request_kind": "unknown_request",
            "raw_text": "Please view your statement of account at https://secure.icicibank.com/statement",
            "source": "notification",
            "link_clicked": False,
            "link_scheme": "https",
            "url_host": "secure.icicibank.com",
            "resolved_domain": "icicibank.com",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "ignore_benign"
    assert payload["should_warn"] is False


def test_upi_request_inspect_mentions_risky_link_context_for_payment_warning(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_payment_link_context",
            "language": "en",
            "app_name": "PhonePe",
            "request_kind": "collect_request",
            "amount": 1999,
            "payee_label": "Reward Desk",
            "payee_handle": "rewarddesk@upi",
            "raw_text": "Reward cashback claim ke liye collect request approve karein",
            "source": "notification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": "verify-reward.top",
            "resolved_domain": "reward.top",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["classification"] == "payment_outflow_risk"
    assert payload["alert_family"] == "payment"
    assert payload["should_warn"] is True
    assert "risky link click" in payload["why_this_alert"].lower()


def test_upi_request_inspect_suppresses_setup_fixtures_for_phonepe_gpay_and_paytm(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    fixtures = [
        ("registration_success", "Use {app} on your current device! You have successfully registered your {app} account."),
        ("phone_verification", "Verify mobile number to continue setup. Your verification code is 456789."),
        ("bank_account_fetch", "Link bank account to continue. Bank account fetch in progress for {app}."),
        ("upi_pin_setup", "Set UPI PIN to complete setup for {app}."),
    ]

    for app_name, _package_name in _onboarding_apps():
        for setup_state, template in fixtures:
            res = client.post(
                "/api/literacy/upi-request-inspect",
                json={
                    "participant_id": f"setup_fixture_{app_name}_{setup_state}".replace(" ", "_").lower(),
                    "language": "en",
                    "app_name": app_name,
                    "request_kind": "unknown_request",
                    "raw_text": template.format(app=app_name),
                    "source": "notification",
                    "setup_state": setup_state,
                },
            )

            assert res.status_code == 200
            payload = res.json()
            assert payload["classification"] == "ignore_benign", (app_name, setup_state, payload)
            assert payload["should_warn"] is False, (app_name, setup_state, payload)


def test_upi_request_inspect_keeps_explicit_collect_fixtures_visible_for_phonepe_gpay_and_paytm(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    for app_name, _package_name in _onboarding_apps():
        res = client.post(
            "/api/literacy/upi-request-inspect",
            json={
                "participant_id": f"setup_collect_{app_name}".replace(" ", "_").lower(),
                "language": "en",
                "app_name": app_name,
                "request_kind": "collect_request",
                "amount": 2500,
                "payee_label": "Merchant Desk",
                "payee_handle": "merchant@upi",
                "raw_text": "Approve collect request of Rs 2500",
                "source": "notification",
                "setup_state": "bank_account_fetch",
            },
        )

        assert res.status_code == 200
        payload = res.json()
        assert payload["classification"] == "payment_outflow_risk", (app_name, payload)
        assert payload["should_warn"] is True, (app_name, payload)


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


def test_upi_request_inspect_persists_account_access_warning_telemetry(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)

    inspect_res = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": "p_access_review",
            "language": "en",
            "app_name": "Browser",
            "request_kind": "unknown_request",
            "raw_text": "OTP for your mobile banking login is 489647",
            "source": "notification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": "secure-login-paytm-help.top",
            "resolved_domain": "paytm-help.top",
        },
    )
    assert inspect_res.status_code == 200
    inspect_payload = inspect_res.json()
    assert inspect_payload["alert_family"] == "account_access"
    assert inspect_payload["should_warn"] is True

    feedback_res = client.post(
        "/api/literacy/alert-feedback",
        json={
            "alert_id": inspect_payload["alert_id"],
            "participant_id": "p_access_review",
            "action": "declined",
            "channel": "notification",
            "title": "Protected account",
            "message": "participant backed out of suspicious access flow",
            "timestamp": "2026-03-22T07:15:00Z",
        },
    )
    assert feedback_res.status_code == 200

    summary_res = client.get(
        "/api/pilot/summary",
        params={"participant_id": "p_access_review", "limit": 10},
        headers=_admin_headers(),
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["telemetry_comparison"]["account_access_warning"]["generated_count"] >= 1
    assert summary["telemetry_comparison"]["account_access_warning"]["action_count"] >= 1
    assert summary["recent_unified_telemetry"][0]["telemetry_family"] == "account_access_warning"


def test_small_bank_like_domain_downgrades_after_benign_context_and_safe_feedback(tmp_path, monkeypatch):
    client = _client_with_temp_db(tmp_path, monkeypatch)
    participant_id = "p_small_bank_feedback"
    domain = "graminbank-example.co.in"

    observed_res = client.post(
        "/api/pilot/app-log",
        json={
            "participant_id": participant_id,
            "level": "info",
            "message": "observed_small_bank_statement",
            "language": "en",
            "context_event": {
                "event_type": "notification_observed",
                "classification": "observed",
                "message_family": "statement_or_report",
                "link_clicked": False,
                "link_scheme": "https",
                "url_host": f"secure.{domain}",
                "resolved_domain": domain,
                "domain_class": "bank",
            },
        },
    )
    assert observed_res.status_code == 200

    first_inspect = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": participant_id,
            "language": "en",
            "app_name": "Browser",
            "request_kind": "unknown_request",
            "raw_text": "OTP for your mobile banking login is 489647",
            "source": "notification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": f"secure.{domain}",
            "resolved_domain": domain,
            "domain_class": "bank",
        },
    )
    assert first_inspect.status_code == 200
    first_payload = first_inspect.json()
    assert first_payload["classification"] == "account_access_risk"
    assert first_payload["should_warn"] is True

    feedback_res = client.post(
        "/api/literacy/alert-feedback",
        json={
            "alert_id": first_payload["alert_id"],
            "participant_id": participant_id,
            "action": "proceed",
            "channel": "notification",
            "title": "Expected bank access",
            "message": "participant confirmed this was expected",
            "timestamp": "2026-03-22T07:35:00Z",
        },
    )
    assert feedback_res.status_code == 200

    entities = client.get(
        "/api/pilot/entities",
        params={"trust_state": "trusted_by_observation"},
        headers=_admin_headers(),
    )
    assert entities.status_code == 200
    assert any(entity["entity_key"] == domain for entity in entities.json()["entities"])

    second_inspect = client.post(
        "/api/literacy/upi-request-inspect",
        json={
            "participant_id": participant_id,
            "language": "en",
            "app_name": "Browser",
            "request_kind": "unknown_request",
            "raw_text": "OTP for your mobile banking login is 489647",
            "source": "notification",
            "link_clicked": True,
            "link_scheme": "https",
            "url_host": f"secure.{domain}",
            "resolved_domain": domain,
            "domain_class": "bank",
        },
    )
    assert second_inspect.status_code == 200
    second_payload = second_inspect.json()
    assert second_payload["classification"] == "store_only_account_access"
    assert second_payload["should_warn"] is False


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

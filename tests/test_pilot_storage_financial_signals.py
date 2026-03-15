from backend.pilot.storage import PilotStorage


def test_recent_spend_amounts_ignore_income_and_partial(tmp_path):
    storage = PilotStorage(str(tmp_path / "pilot_research.db"))
    participant_id = "storage_p1"

    storage.add_literacy_event(
        participant_id=participant_id,
        event_type="sms_ingest_event",
        source="bank_sms",
        signal_type="income",
        signal_confidence="confirmed",
        category="bank_sms",
        amount=2500,
        note="salary credited",
        timestamp="2026-03-15T10:00:00",
    )
    storage.add_literacy_event(
        participant_id=participant_id,
        event_type="sms_partial_context",
        source="bank_sms",
        signal_type="partial",
        signal_confidence="partial",
        category="bank_sms",
        amount=5000,
        note="transaction alert",
        timestamp="2026-03-15T10:05:00",
    )
    storage.add_literacy_event(
        participant_id=participant_id,
        event_type="sms_ingest_event",
        source="bank_sms",
        signal_type="expense",
        signal_confidence="confirmed",
        category="upi",
        amount=900,
        note="upi debit",
        timestamp="2026-03-15T10:10:00",
    )

    assert storage.recent_spend_amounts(participant_id) == [900.0]

    signals = storage.recent_financial_signals(participant_id, limit=5)
    assert [signal["signal_type"] for signal in signals] == ["expense", "partial", "income"]


def test_unified_telemetry_helpers_return_recent_records_and_comparison(tmp_path):
    storage = PilotStorage(str(tmp_path / "pilot_research.db"))
    storage.upsert_consent(
        participant_id="telemetry_p1",
        accepted=True,
        language="hi",
        timestamp="2026-03-15T10:55:00",
    )
    storage.upsert_essential_goal_profile(
        participant_id="telemetry_p1",
        cohort="women_led_household",
        essential_goals=["ration"],
        language="hi",
        setup_skipped=False,
        timestamp="2026-03-15T10:56:00",
    )
    storage.upsert_experiment_assignment(
        participant_id="telemetry_p1",
        experiment_name="adaptive_alerts_v1",
        variant="adaptive",
        assigned_at="2026-03-15T10:57:00",
    )

    storage.add_unified_telemetry(
        event_id="evt-payment-1",
        participant_id="telemetry_p1",
        telemetry_family="payment_warning",
        record_type="generated",
        event_name="upi_request_inspection",
        alert_id="alert-payment-1",
        source_route="/api/literacy/upi-request-inspect",
        source="notification",
        timestamp="2026-03-15T11:00:00",
        amount=2100,
        scenario="collect_request_confusion",
        risk_level="high",
        summary_text="Pause before approving the request.",
        context={"why_this_alert": "collect request"},
        extensions={"payee_handle": "merchant@upi", "trace_id": "trace-payment-1"},
    )
    storage.add_unified_telemetry(
        event_id="evt-cashflow-1",
        participant_id="telemetry_p1",
        telemetry_family="cashflow",
        record_type="usefulness",
        event_name="alert_feedback",
        alert_id="alert-cashflow-1",
        source_route="/api/literacy/alert-feedback",
        source="participant_feedback",
        timestamp="2026-03-15T11:05:00",
        action="dismissed",
        channel="overlay",
        risk_level="medium",
        summary_text="dismissed from overlay",
        context={"title": "Close"},
        extensions={"module_family": "cashflow"},
    )

    recent = storage.recent_unified_telemetry(participant_id="telemetry_p1", limit=10)
    assert recent[0]["event_id"] == "evt-cashflow-1"
    assert recent[0]["telemetry_family"] == "cashflow"
    assert recent[1]["context"]["why_this_alert"] == "collect request"
    assert recent[1]["extensions"]["payee_handle"] == "merchant@upi"
    assert recent[1]["extensions"]["trace_id"] == "trace-payment-1"

    comparison = storage.unified_telemetry_comparison(participant_id="telemetry_p1", limit=10)
    assert comparison["payment_warning"]["generated_count"] == 1
    assert comparison["cashflow"]["usefulness_count"] == 1
    assert comparison["cashflow"]["action_breakdown"]["dismissed"] == 1
    assert comparison["language_slices"]["hi"]["family_breakdown"]["cashflow"] == 1
    assert comparison["cohort_slices"]["women_led_household"]["family_breakdown"]["payment_warning"] == 1
    assert comparison["variant_slices"]["adaptive"]["family_breakdown"]["cashflow"] == 1
    assert comparison["payment_warning"]["trace_sample"][0]["event_id"] == "evt-payment-1"

    linked = storage.latest_unified_telemetry_for_alert("alert-payment-1", participant_id="telemetry_p1")
    assert linked is not None
    assert linked["event_id"] == "evt-payment-1"
    assert linked["telemetry_family"] == "payment_warning"


def test_unified_telemetry_event_id_is_idempotent_and_preserves_extension_metadata(tmp_path):
    storage = PilotStorage(str(tmp_path / "pilot_research.db"))

    inserted = storage.add_unified_telemetry(
        event_id="evt-extension-1",
        participant_id="extension_p1",
        telemetry_family="payment_warning",
        record_type="fallback",
        event_name="payment_fallback_shown",
        alert_id="alert-extension-1",
        source_route="/api/pilot/app-log",
        source="android_client",
        timestamp="2026-03-15T12:00:00",
        scenario="collect_request",
        summary_text="fallback shown",
        context={"request_kind": "collect_request"},
        extensions={
            "trace_id": "trace-extension-1",
            "module_family": "trusted_circle_candidate",
            "policy_variant": "deterministic_guardrails",
        },
    )
    duplicate = storage.add_unified_telemetry(
        event_id="evt-extension-1",
        participant_id="extension_p1",
        telemetry_family="payment_warning",
        record_type="fallback",
        event_name="payment_fallback_shown",
        alert_id="alert-extension-1",
        source_route="/api/pilot/app-log",
        source="android_client",
        timestamp="2026-03-15T12:01:00",
    )

    assert inserted is True
    assert duplicate is False

    recent = storage.recent_unified_telemetry(participant_id="extension_p1", limit=10)
    assert len(recent) == 1
    assert recent[0]["event_id"] == "evt-extension-1"
    assert recent[0]["extensions"]["trace_id"] == "trace-extension-1"
    assert recent[0]["extensions"]["module_family"] == "trusted_circle_candidate"

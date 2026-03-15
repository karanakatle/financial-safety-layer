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

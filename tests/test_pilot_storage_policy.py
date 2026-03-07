from backend.pilot.storage import PilotStorage


def test_participant_policy_upsert_and_get(tmp_path):
    db = tmp_path / "pilot_policy.db"
    storage = PilotStorage(str(db))

    assert storage.get_participant_policy("p1") is None

    storage.upsert_participant_policy(
        participant_id="p1",
        daily_safe_limit=1500.0,
        warning_ratio=0.82,
        is_auto=False,
        updated_at="2026-03-06T00:00:00",
    )

    policy = storage.get_participant_policy("p1")
    assert policy is not None
    assert policy["daily_safe_limit"] == 1500.0
    assert policy["warning_ratio"] == 0.82

    storage.upsert_participant_policy(
        participant_id="p1",
        daily_safe_limit=1700.0,
        warning_ratio=0.8,
        is_auto=False,
        updated_at="2026-03-06T01:00:00",
    )
    policy2 = storage.get_participant_policy("p1")
    assert policy2 is not None
    assert policy2["daily_safe_limit"] == 1700.0
    assert policy2["warning_ratio"] == 0.8


def test_auto_policy_does_not_override_manual_policy(tmp_path):
    db = tmp_path / "pilot_policy_auto.db"
    storage = PilotStorage(str(db))

    storage.upsert_participant_policy(
        participant_id="p1",
        daily_safe_limit=1600.0,
        warning_ratio=0.85,
        is_auto=False,
        updated_at="2026-03-06T00:00:00",
    )
    changed = storage.upsert_auto_participant_policy(
        participant_id="p1",
        daily_safe_limit=1200.0,
        warning_ratio=0.9,
        updated_at="2026-03-06T01:00:00",
    )
    assert changed is False
    policy = storage.get_participant_policy("p1")
    assert policy is not None
    assert policy["daily_safe_limit"] == 1600.0


def test_recent_alert_feature_summary(tmp_path):
    db = tmp_path / "pilot_alert_features.db"
    storage = PilotStorage(str(db))

    storage.add_alert_features(
        alert_id="a1",
        participant_id="p1",
        timestamp="2026-03-07T00:00:00",
        amount=1200.0,
        projected_spend=2200.0,
        daily_safe_limit=2000.0,
        spend_ratio=1.1,
        txn_anomaly_score=0.8,
        hour_of_day=11,
        rapid_txn_flag=True,
        upi_open_flag=False,
        recent_dismissals_24h=1,
        risk_score=0.78,
        confidence_score=0.72,
        tone_selected="firm",
        frequency_bucket="hard",
    )
    storage.add_alert_features(
        alert_id="a2",
        participant_id="p1",
        timestamp="2026-03-07T00:10:00",
        amount=300.0,
        projected_spend=2500.0,
        daily_safe_limit=2000.0,
        spend_ratio=1.25,
        txn_anomaly_score=0.4,
        hour_of_day=12,
        rapid_txn_flag=False,
        upi_open_flag=True,
        recent_dismissals_24h=2,
        risk_score=0.55,
        confidence_score=0.66,
        tone_selected="soft",
        frequency_bucket="suppressed",
    )

    summary = storage.recent_alert_feature_summary("p1", limit=50)
    assert summary["sample_size"] == 2
    assert summary["hard_count"] == 1
    assert summary["suppressed_count"] == 1

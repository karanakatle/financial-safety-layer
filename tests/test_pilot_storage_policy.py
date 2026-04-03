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


def test_essential_goal_profile_upsert_and_get(tmp_path):
    db = tmp_path / "pilot_goals.db"
    storage = PilotStorage(str(db))

    storage.upsert_essential_goal_profile(
        participant_id="p1",
        cohort="daily_cashflow_worker",
        essential_goals=["cooking_fuel", "ration"],
        all_selected_essentials=["cooking_fuel", "ration", "rent"],
        active_priority_essentials=["cooking_fuel", "ration"],
        selection_source="user_selected",
        goal_source_map={"cooking_fuel": "user_selected", "ration": "user_selected", "rent": "user_selected"},
        affordability_question_key="daily_earnings_range",
        affordability_bucket_id="500_749",
        ranking_metadata={"config_version": "essential_goal_setup_v1"},
        config_version="essential_goal_setup_v1",
        language="en",
        setup_skipped=False,
        timestamp="2026-03-08T00:00:00",
    )

    profile = storage.get_essential_goal_profile("p1")
    assert profile is not None
    assert profile["cohort"] == "daily_cashflow_worker"
    assert profile["essential_goals"] == ["cooking_fuel", "ration"]
    assert profile["all_selected_essentials"] == ["cooking_fuel", "ration", "rent"]
    assert profile["active_priority_essentials"] == ["cooking_fuel", "ration"]
    assert profile["selection_source"] == "user_selected"
    assert profile["affordability_bucket_id"] == "500_749"
    assert profile["setup_skipped"] is False


def test_current_balance_upsert_replaces_latest_and_retains_history(tmp_path):
    db = tmp_path / "pilot_balance.db"
    storage = PilotStorage(str(db))

    storage.upsert_current_balance(
        participant_id="p1",
        amount=1200.0,
        source="self_reported",
        captured_at="2026-03-08T08:00:00",
        updated_at="2026-03-08T08:00:00",
    )
    first = storage.get_current_balance("p1")
    assert first is not None
    assert first["amount"] == 1200.0
    assert first["source"] == "self_reported"

    storage.upsert_current_balance(
        participant_id="p1",
        amount=1500.0,
        source="self_reported",
        captured_at="2026-03-08T10:30:00",
        updated_at="2026-03-08T10:30:00",
    )

    latest = storage.get_current_balance("p1")
    history = storage.list_current_balance_history("p1", limit=10)
    assert latest is not None
    assert latest["amount"] == 1500.0
    assert latest["captured_at"] == "2026-03-08T10:30:00"
    assert len(history) == 1
    assert history[0]["amount"] == 1200.0
    assert history[0]["source"] == "self_reported"


def test_experiment_assignment_and_event_export(tmp_path):
    db = tmp_path / "pilot_research_events.db"
    storage = PilotStorage(str(db))

    storage.upsert_experiment_assignment(
        participant_id="p1",
        experiment_name="adaptive_alerts_v1",
        variant="adaptive",
        assigned_at="2026-03-08T00:00:00",
    )
    assignment = storage.get_experiment_assignment("p1", "adaptive_alerts_v1")
    assert assignment is not None
    assert assignment["variant"] == "adaptive"

    storage.add_experiment_event(
        participant_id="p1",
        experiment_name="adaptive_alerts_v1",
        variant="adaptive",
        event_type="sms_ingest",
        payload={"amount": 1200, "alerts_count": 1},
        timestamp="2026-03-08T00:01:00",
    )
    events = storage.list_experiment_events(participant_id="p1", experiment_name="adaptive_alerts_v1", limit=20)
    assert len(events) == 1
    assert events[0]["event_type"] == "sms_ingest"
    assert events[0]["payload"]["alerts_count"] == 1


def test_grievance_create_update_list(tmp_path):
    db = tmp_path / "pilot_grievance.db"
    storage = PilotStorage(str(db))

    grievance_id = storage.create_grievance(
        participant_id="p1",
        category="trust",
        details="Alert was unclear",
        timestamp="2026-03-08T01:00:00",
    )
    assert grievance_id > 0

    listed = storage.list_grievances(participant_id="p1", limit=20)
    assert len(listed) == 1
    assert listed[0]["status"] == "open"

    changed = storage.update_grievance_status(
        grievance_id=grievance_id,
        status="resolved",
        timestamp="2026-03-08T02:00:00",
    )
    assert changed is True
    listed_after = storage.list_grievances(participant_id="p1", limit=20)
    assert listed_after[0]["status"] == "resolved"


def test_goal_memory_and_feedback_storage(tmp_path):
    db = tmp_path / "pilot_goal_memory.db"
    storage = PilotStorage(str(db))

    storage.upsert_goal_memory(
        participant_id="p1",
        merchant_key="m1",
        goal="fuel",
        delta_positive=1,
        delta_negative=0,
        timestamp="2026-03-08T03:00:00",
    )
    rows = storage.goal_memory_rows("p1", "m1")
    assert len(rows) == 1
    assert rows[0]["goal"] == "fuel"
    assert rows[0]["positive_count"] == 1

    storage.upsert_alert_goal_context(
        alert_id="a1",
        participant_id="p1",
        merchant_key="m1",
        inferred_goal="fuel",
        confidence=0.8,
        gate_passed=True,
        source="keyword",
        timestamp="2026-03-08T03:05:00",
    )
    context = storage.get_alert_goal_context("a1", "p1")
    assert context is not None
    assert context["merchant_key"] == "m1"
    assert context["gate_passed"] is True

    storage.add_goal_feedback(
        participant_id="p1",
        alert_id="a1",
        merchant_key="m1",
        selected_goal="fuel",
        is_essential=True,
        source_confidence=0.8,
        timestamp="2026-03-08T03:06:00",
    )
    feedback = storage.recent_goal_feedback("p1", 10)
    assert len(feedback) == 1
    assert feedback[0]["selected_goal"] == "fuel"
    assert feedback[0]["is_essential"] is True

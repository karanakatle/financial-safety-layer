from backend.literacy.safety_monitor import FinancialLiteracySafetyMonitor


def test_stage1_warning_when_threshold_near_exceeded():
    monitor = FinancialLiteracySafetyMonitor(daily_safe_limit=1000, warning_ratio=0.9)

    first = monitor.ingest_expense(850, timestamp="2026-02-28T10:00:00")
    assert first == []

    second = monitor.ingest_expense(60, timestamp="2026-02-28T11:00:00")
    assert len(second) == 1
    assert second[0]["reason"] == "daily_threshold_near_exceeded"
    assert second[0]["stage"] == 1


def test_stage2_warning_triggers_once_after_upi_open():
    monitor = FinancialLiteracySafetyMonitor(daily_safe_limit=1000, warning_ratio=0.9)
    monitor.ingest_expense(920, timestamp="2026-02-28T09:00:00")

    first = monitor.on_upi_app_open(
        app_name="PhonePe", intent_amount=150, timestamp="2026-02-28T09:30:00"
    )
    second = monitor.on_upi_app_open(
        app_name="Google Pay", intent_amount=50, timestamp="2026-02-28T09:40:00"
    )

    assert first is not None
    assert first["reason"] == "upi_open_after_threshold_warning"
    assert first["stage"] == 2
    assert second is None


def test_daily_rollover_resets_nudge_state():
    monitor = FinancialLiteracySafetyMonitor(daily_safe_limit=1000, warning_ratio=0.9)
    monitor.ingest_expense(910, timestamp="2026-02-28T09:00:00")
    assert monitor.stage1_sent is True

    monitor.ingest_expense(100, timestamp="2026-03-01T09:00:00")
    status = monitor.status()

    assert status["date"] == "2026-03-01"
    assert status["daily_spend"] == 100
    assert status["stage1_sent"] is False
    assert status["stage2_sent"] is False


def test_warmup_suppresses_regular_stage1_but_allows_extreme_spike():
    monitor = FinancialLiteracySafetyMonitor(
        daily_safe_limit=1000,
        warning_ratio=0.9,
        warmup_days=3,
        warmup_seed_multiplier=1.2,
        warmup_extreme_spike_ratio=0.4,
    )

    # First expense enters warmup; no hard stage1 warning expected for normal spend.
    first = monitor.ingest_expense(300, timestamp="2026-03-01T10:00:00")
    assert first == []
    assert monitor.warmup_active is True

    # Extreme single expense during warmup should still trigger stage1.
    second = monitor.ingest_expense(500, timestamp="2026-03-01T12:00:00")
    assert len(second) == 1
    assert second[0]["stage"] == 1
    assert second[0]["warmup_active"] is True


def test_catastrophic_override_triggers_even_during_warmup():
    monitor = FinancialLiteracySafetyMonitor(
        daily_safe_limit=1200,
        warning_ratio=0.9,
        warmup_days=3,
        warmup_seed_multiplier=1.2,
        warmup_extreme_spike_ratio=0.95,
        catastrophic_absolute=4000,
        catastrophic_multiplier=3.0,
        catastrophic_projected_cap=2.0,
    )

    first = monitor.ingest_expense(4200, timestamp="2026-03-01T09:00:00")
    assert len(first) == 1
    assert first[0]["reason"] == "catastrophic_risk_override"
    assert first[0]["catastrophic_risk"] is True

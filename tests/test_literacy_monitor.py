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

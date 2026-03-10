from __future__ import annotations

from datetime import datetime

from backend.literacy.safety_monitor import FinancialLiteracySafetyMonitor


def build_literacy_monitor(
    *,
    participant_id: str,
    pilot_storage,
    literacy_policy,
    policy_for_participant,
) -> FinancialLiteracySafetyMonitor:
    record = pilot_storage.get_literacy_state(participant_id)
    daily_safe_limit, warning_ratio = policy_for_participant(participant_id)
    monitor = FinancialLiteracySafetyMonitor(
        daily_safe_limit=daily_safe_limit,
        warning_ratio=warning_ratio,
        stage1_message=literacy_policy.stage1_message,
        stage2_over_limit_template=literacy_policy.stage2_over_limit_template,
        stage2_close_limit_message=literacy_policy.stage2_close_limit_message,
        warmup_days=literacy_policy.warmup_days,
        warmup_seed_multiplier=literacy_policy.warmup_seed_multiplier,
        warmup_extreme_spike_ratio=literacy_policy.warmup_extreme_spike_ratio,
        catastrophic_absolute=literacy_policy.catastrophic_absolute,
        catastrophic_multiplier=literacy_policy.catastrophic_multiplier,
        catastrophic_projected_cap=literacy_policy.catastrophic_projected_cap,
    )
    if not record:
        return monitor

    monitor.current_date = record["current_date"]
    monitor.daily_spend = float(record["daily_spend"])
    monitor.threshold_risk_active = bool(record["threshold_risk_active"])
    monitor.stage1_sent = bool(record["stage1_sent"])
    monitor.stage2_sent = bool(record["stage2_sent"])
    monitor.first_event_date = record.get("first_event_date")
    monitor.warmup_active = bool(record.get("warmup_active", False))
    monitor.adaptive_daily_safe_limit = record.get("adaptive_daily_safe_limit")
    monitor.notifications = [dict() for _ in range(int(record["notifications_count"]))]
    return monitor


def persist_literacy_monitor(
    *,
    participant_id: str,
    monitor: FinancialLiteracySafetyMonitor,
    pilot_storage,
) -> None:
    now_iso = datetime.utcnow().isoformat()
    pilot_storage.upsert_literacy_state(
        participant_id=participant_id,
        current_date=monitor.current_date,
        daily_spend=monitor.daily_spend,
        threshold_risk_active=monitor.threshold_risk_active,
        stage1_sent=monitor.stage1_sent,
        stage2_sent=monitor.stage2_sent,
        notifications_count=len(monitor.notifications),
        first_event_date=monitor.first_event_date,
        warmup_active=monitor.warmup_active,
        adaptive_daily_safe_limit=monitor.adaptive_daily_safe_limit,
        updated_at=now_iso,
    )
    pilot_storage.upsert_daily_spend(
        participant_id=participant_id,
        spend_date=monitor.current_date,
        daily_spend=monitor.daily_spend,
        updated_at=now_iso,
    )

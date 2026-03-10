from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from backend.literacy.messages import (
    DEFAULT_STAGE1_MESSAGE,
    DEFAULT_STAGE2_CLOSE_LIMIT_MESSAGE,
    DEFAULT_STAGE2_OVER_LIMIT_TEMPLATE,
)


@dataclass
class FinancialLiteracySafetyMonitor:
    daily_safe_limit: float = 1000.0
    warning_ratio: float = 0.9
    stage1_message: str = DEFAULT_STAGE1_MESSAGE
    stage2_over_limit_template: str = DEFAULT_STAGE2_OVER_LIMIT_TEMPLATE
    stage2_close_limit_message: str = DEFAULT_STAGE2_CLOSE_LIMIT_MESSAGE
    warmup_days: int = 0
    warmup_seed_multiplier: float = 1.2
    warmup_extreme_spike_ratio: float = 0.4
    catastrophic_absolute: float = 5000.0
    catastrophic_multiplier: float = 2.5
    catastrophic_projected_cap: float = 1.8
    daily_spend: float = 0.0
    threshold_risk_active: bool = False
    stage1_sent: bool = False
    stage2_sent: bool = False
    current_date: str = field(default_factory=lambda: datetime.utcnow().date().isoformat())
    first_event_date: str | None = None
    warmup_active: bool = False
    adaptive_daily_safe_limit: float | None = None
    notifications: list[dict] = field(default_factory=list)

    def _coerce_dt(self, timestamp: str | None) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        # Accept both "...Z" and timezone-less ISO strings.
        value = timestamp.replace("Z", "+00:00")
        return datetime.fromisoformat(value)

    def _rollover_if_needed(self, timestamp: str | None) -> None:
        event_dt = self._coerce_dt(timestamp)
        event_date = event_dt.date().isoformat()
        if event_date == self.current_date:
            return

        self.current_date = event_date
        self.daily_spend = 0.0
        self.threshold_risk_active = False
        self.stage1_sent = False
        self.stage2_sent = False

    def _event_date(self, timestamp: str | None) -> date:
        return self._coerce_dt(timestamp).date()

    def _effective_daily_safe_limit(self) -> float:
        if self.warmup_active and self.adaptive_daily_safe_limit is not None:
            return max(self.daily_safe_limit, self.adaptive_daily_safe_limit)
        return self.daily_safe_limit

    def ingest_expense(
        self,
        amount: float,
        source: str = "bank_sms",
        timestamp: str | None = None,
    ) -> list[dict]:
        self._rollover_if_needed(timestamp)

        alerts: list[dict] = []
        amount_value = float(amount)
        projected_spend = self.daily_spend + amount_value
        event_date = self._event_date(timestamp)

        if self.first_event_date is None:
            self.first_event_date = event_date.isoformat()
            self.warmup_active = self.warmup_days > 0

        if self.warmup_active:
            seed_limit = max(self.daily_safe_limit, projected_spend * self.warmup_seed_multiplier)
            self.adaptive_daily_safe_limit = max(self.adaptive_daily_safe_limit or 0.0, seed_limit)

            first_date = date.fromisoformat(self.first_event_date)
            days_seen = (event_date - first_date).days + 1
            if days_seen > self.warmup_days:
                self.warmup_active = False
                self.daily_safe_limit = self._effective_daily_safe_limit()

        effective_limit = self._effective_daily_safe_limit()
        trigger_point = effective_limit * self.warning_ratio

        catastrophic_risk = (
            amount_value >= self.catastrophic_absolute
            or (effective_limit > 0 and amount_value >= (effective_limit * self.catastrophic_multiplier))
            or (effective_limit > 0 and projected_spend >= (effective_limit * self.catastrophic_projected_cap))
        )
        should_trigger_stage1 = projected_spend >= trigger_point
        if self.warmup_active:
            # During warmup, avoid frequent threshold warnings; allow only extreme spikes.
            should_trigger_stage1 = (
                amount_value >= (effective_limit * self.warmup_extreme_spike_ratio)
                or catastrophic_risk
            )

        if not self.stage1_sent and should_trigger_stage1:
            self.threshold_risk_active = True
            self.stage1_sent = True
            alert = {
                "type": "ussd_alert",
                "priority": "critical" if catastrophic_risk else "high",
                "reason": "catastrophic_risk_override" if catastrophic_risk else "daily_threshold_near_exceeded",
                "stage": 1,
                "source": source,
                "message": self.stage1_message,
                "projected_daily_spend": round(projected_spend, 2),
                "daily_safe_limit": round(effective_limit, 2),
                "warmup_active": self.warmup_active,
                "catastrophic_risk": catastrophic_risk,
            }
            alerts.append(alert)
            self.notifications.append(alert)

        self.daily_spend = round(projected_spend, 2)
        return alerts

    def on_upi_app_open(
        self,
        app_name: str,
        intent_amount: float = 0.0,
        timestamp: str | None = None,
    ) -> dict | None:
        self._rollover_if_needed(timestamp)

        if not self.threshold_risk_active or self.stage2_sent:
            return None

        projected_spend = self.daily_spend + float(intent_amount)
        effective_limit = self._effective_daily_safe_limit()
        daily_overage = max(projected_spend - effective_limit, 0.0)
        weekly_impact = round(daily_overage * 7, 2)
        self.stage2_sent = True

        if daily_overage > 0:
            try:
                message = self.stage2_over_limit_template.format(
                    daily_overage=round(daily_overage, 2),
                    weekly_impact=weekly_impact,
                )
            except (KeyError, ValueError):
                message = DEFAULT_STAGE2_OVER_LIMIT_TEMPLATE.format(
                    daily_overage=round(daily_overage, 2),
                    weekly_impact=weekly_impact,
                )
        else:
            message = self.stage2_close_limit_message

        alert = {
            "type": "ussd_alert",
            "priority": "high",
            "reason": "upi_open_after_threshold_warning",
            "stage": 2,
            "source": "upi_open",
            "app_name": app_name,
            "message": message,
            "projected_daily_spend": round(projected_spend, 2),
            "daily_safe_limit": round(effective_limit, 2),
        }
        self.notifications.append(alert)
        return alert

    def status(self) -> dict:
        return {
            "date": self.current_date,
            "daily_spend": round(self.daily_spend, 2),
            "daily_safe_limit": round(self._effective_daily_safe_limit(), 2),
            "warning_ratio": self.warning_ratio,
            "threshold_risk_active": self.threshold_risk_active,
            "stage1_sent": self.stage1_sent,
            "stage2_sent": self.stage2_sent,
            "warmup_active": self.warmup_active,
            "warmup_days": self.warmup_days,
            "notifications_count": len(self.notifications),
        }

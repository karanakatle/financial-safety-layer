from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FinancialLiteracySafetyMonitor:
    daily_safe_limit: float = 1000.0
    warning_ratio: float = 0.9
    daily_spend: float = 0.0
    threshold_risk_active: bool = False
    stage1_sent: bool = False
    stage2_sent: bool = False
    current_date: str = field(default_factory=lambda: datetime.utcnow().date().isoformat())
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

    def ingest_expense(
        self,
        amount: float,
        source: str = "bank_sms",
        timestamp: str | None = None,
    ) -> list[dict]:
        self._rollover_if_needed(timestamp)

        alerts: list[dict] = []
        projected_spend = self.daily_spend + float(amount)
        trigger_point = self.daily_safe_limit * self.warning_ratio

        if not self.stage1_sent and projected_spend >= trigger_point:
            self.threshold_risk_active = True
            self.stage1_sent = True
            alert = {
                "type": "ussd_alert",
                "priority": "high",
                "reason": "daily_threshold_near_exceeded",
                "stage": 1,
                "source": source,
                "message": (
                    "Daily safe spend is about to be exceeded. "
                    "Exceeding amount can disturb your financial planning."
                ),
                "projected_daily_spend": round(projected_spend, 2),
                "daily_safe_limit": round(self.daily_safe_limit, 2),
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
        daily_overage = max(projected_spend - self.daily_safe_limit, 0.0)
        weekly_impact = round(daily_overage * 7, 2)
        self.stage2_sent = True

        if daily_overage > 0:
            message = (
                f"Paying now may exceed your daily safe amount by Rs {round(daily_overage, 2)} "
                f"and disturb your weekly planning by around Rs {weekly_impact}."
            )
        else:
            message = (
                "You are close to your daily limit. Paying now can disturb your financial "
                "planning for today or the week."
            )

        alert = {
            "type": "ussd_alert",
            "priority": "high",
            "reason": "upi_open_after_threshold_warning",
            "stage": 2,
            "source": "upi_open",
            "app_name": app_name,
            "message": message,
            "projected_daily_spend": round(projected_spend, 2),
            "daily_safe_limit": round(self.daily_safe_limit, 2),
        }
        self.notifications.append(alert)
        return alert

    def status(self) -> dict:
        return {
            "date": self.current_date,
            "daily_spend": round(self.daily_spend, 2),
            "daily_safe_limit": round(self.daily_safe_limit, 2),
            "warning_ratio": self.warning_ratio,
            "threshold_risk_active": self.threshold_risk_active,
            "stage1_sent": self.stage1_sent,
            "stage2_sent": self.stage2_sent,
            "notifications_count": len(self.notifications),
        }

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParticipantSimulationSummary:
    participant_id: str
    variant: str
    active_days: int = 0
    alert_count: int = 0
    soft_alert_count: int = 0
    medium_alert_count: int = 0
    hard_alert_count: int = 0
    useful_feedback_count: int = 0
    dismissed_feedback_count: int = 0
    ignored_feedback_count: int = 0
    prevented_risk_count: int = 0
    risky_spend_events: int = 0
    uninstall_day: int | None = None
    trust_score_final: float = 0.0


@dataclass
class SimulationReport:
    summaries: list[ParticipantSimulationSummary] = field(default_factory=list)

    def aggregate(self) -> dict:
        participants = len(self.summaries)
        total_alerts = sum(item.alert_count for item in self.summaries)
        total_soft = sum(item.soft_alert_count for item in self.summaries)
        total_medium = sum(item.medium_alert_count for item in self.summaries)
        total_hard = sum(item.hard_alert_count for item in self.summaries)
        total_useful = sum(item.useful_feedback_count for item in self.summaries)
        total_dismissed = sum(item.dismissed_feedback_count for item in self.summaries)
        total_ignored = sum(item.ignored_feedback_count for item in self.summaries)
        total_prevented = sum(item.prevented_risk_count for item in self.summaries)
        total_risky = sum(item.risky_spend_events for item in self.summaries)
        retained = sum(1 for item in self.summaries if item.uninstall_day is None)

        feedback_total = total_useful + total_dismissed + total_ignored
        useful_rate = round(total_useful / feedback_total, 4) if feedback_total else 0.0
        dismiss_rate = round(total_dismissed / feedback_total, 4) if feedback_total else 0.0
        soft_alert_rate = round(total_soft / total_alerts, 4) if total_alerts else 0.0
        medium_alert_rate = round(total_medium / total_alerts, 4) if total_alerts else 0.0
        hard_alert_rate = round(total_hard / total_alerts, 4) if total_alerts else 0.0
        prevention_rate = round(total_prevented / total_risky, 4) if total_risky else 0.0
        retention_rate = round(retained / participants, 4) if participants else 0.0

        return {
            "participants": participants,
            "total_alerts": total_alerts,
            "total_soft_alerts": total_soft,
            "total_medium_alerts": total_medium,
            "total_hard_alerts": total_hard,
            "useful_rate": useful_rate,
            "dismiss_rate": dismiss_rate,
            "soft_alert_rate": soft_alert_rate,
            "medium_alert_rate": medium_alert_rate,
            "hard_alert_rate": hard_alert_rate,
            "prevention_rate": prevention_rate,
            "retention_rate": retention_rate,
        }

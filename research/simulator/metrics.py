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
    preventive_inconvenient_feedback_count: int = 0
    dismissed_feedback_count: int = 0
    ignored_feedback_count: int = 0
    prevented_risk_count: int = 0
    risky_spend_events: int = 0
    uninstall_day: int | None = None
    trust_score_final: float = 0.0

    def as_dict(self) -> dict:
        feedback_total = (
            self.useful_feedback_count
            + self.preventive_inconvenient_feedback_count
            + self.dismissed_feedback_count
            + self.ignored_feedback_count
        )
        useful_rate = round(self.useful_feedback_count / feedback_total, 4) if feedback_total else 0.0
        preventive_inconvenient_rate = (
            round(self.preventive_inconvenient_feedback_count / feedback_total, 4)
            if feedback_total
            else 0.0
        )
        dismiss_rate = round(self.dismissed_feedback_count / feedback_total, 4) if feedback_total else 0.0
        ignored_rate = round(self.ignored_feedback_count / feedback_total, 4) if feedback_total else 0.0
        beneficial_rate = (
            round(
                (self.useful_feedback_count + self.preventive_inconvenient_feedback_count) / feedback_total,
                4,
            )
            if feedback_total
            else 0.0
        )
        prevention_rate = (
            round(self.prevented_risk_count / self.risky_spend_events, 4)
            if self.risky_spend_events
            else 0.0
        )
        retention_value = 1.0 if self.uninstall_day is None else 0.0

        return {
            "participant_id": self.participant_id,
            "variant": self.variant,
            "active_days": self.active_days,
            "alert_count": self.alert_count,
            "soft_alert_count": self.soft_alert_count,
            "medium_alert_count": self.medium_alert_count,
            "hard_alert_count": self.hard_alert_count,
            "useful_feedback_count": self.useful_feedback_count,
            "preventive_inconvenient_feedback_count": self.preventive_inconvenient_feedback_count,
            "dismissed_feedback_count": self.dismissed_feedback_count,
            "ignored_feedback_count": self.ignored_feedback_count,
            "prevented_risk_count": self.prevented_risk_count,
            "risky_spend_events": self.risky_spend_events,
            "useful_rate": useful_rate,
            "preventive_inconvenient_rate": preventive_inconvenient_rate,
            "beneficial_rate": beneficial_rate,
            "dismiss_rate": dismiss_rate,
            "ignored_rate": ignored_rate,
            "prevention_rate": prevention_rate,
            "retained": self.uninstall_day is None,
            "retention_value": retention_value,
            "uninstall_day": self.uninstall_day,
            "trust_score_final": round(self.trust_score_final, 4),
        }


@dataclass
class SimulationReport:
    summaries: list[ParticipantSimulationSummary] = field(default_factory=list)

    def by_participant(self) -> list[dict]:
        return [summary.as_dict() for summary in self.summaries]

    def aggregate(self) -> dict:
        participants = len(self.summaries)
        total_alerts = sum(item.alert_count for item in self.summaries)
        total_soft = sum(item.soft_alert_count for item in self.summaries)
        total_medium = sum(item.medium_alert_count for item in self.summaries)
        total_hard = sum(item.hard_alert_count for item in self.summaries)
        total_useful = sum(item.useful_feedback_count for item in self.summaries)
        total_preventive_inconvenient = sum(
            item.preventive_inconvenient_feedback_count for item in self.summaries
        )
        total_dismissed = sum(item.dismissed_feedback_count for item in self.summaries)
        total_ignored = sum(item.ignored_feedback_count for item in self.summaries)
        total_prevented = sum(item.prevented_risk_count for item in self.summaries)
        total_risky = sum(item.risky_spend_events for item in self.summaries)
        retained = sum(1 for item in self.summaries if item.uninstall_day is None)

        feedback_total = total_useful + total_preventive_inconvenient + total_dismissed + total_ignored
        useful_rate = round(total_useful / feedback_total, 4) if feedback_total else 0.0
        preventive_inconvenient_rate = (
            round(total_preventive_inconvenient / feedback_total, 4) if feedback_total else 0.0
        )
        beneficial_rate = (
            round((total_useful + total_preventive_inconvenient) / feedback_total, 4)
            if feedback_total
            else 0.0
        )
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
            "preventive_inconvenient_rate": preventive_inconvenient_rate,
            "beneficial_rate": beneficial_rate,
            "dismiss_rate": dismiss_rate,
            "soft_alert_rate": soft_alert_rate,
            "medium_alert_rate": medium_alert_rate,
            "hard_alert_rate": hard_alert_rate,
            "prevention_rate": prevention_rate,
            "retention_rate": retention_rate,
        }

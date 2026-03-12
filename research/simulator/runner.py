from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from random import Random

from backend.literacy.safety_monitor import FinancialLiteracySafetyMonitor
from research.simulator.metrics import ParticipantSimulationSummary, SimulationReport
from research.simulator.personas import PersonaProfile
from research.simulator.scenarios import build_scenario_window


@dataclass(frozen=True)
class SimulationConfig:
    days: int = 30
    start_date: date = date(2026, 3, 1)
    seed: int = 11
    include_adverse_events: bool = True


def _monitor_for_variant(persona: PersonaProfile, variant: str) -> FinancialLiteracySafetyMonitor:
    if variant == "static_baseline":
        return FinancialLiteracySafetyMonitor(
            daily_safe_limit=max(900.0, round(persona.avg_daily_spend * 1.05, 2)),
            warning_ratio=0.9,
            warmup_days=0,
        )
    return FinancialLiteracySafetyMonitor(
        daily_safe_limit=max(900.0, round(persona.avg_daily_spend * 1.2, 2)),
        warning_ratio=0.88 if persona.daily_spend_volatility >= 0.35 else 0.9,
        warmup_days=3,
        warmup_seed_multiplier=1.2,
    )


def _feedback_outcome(persona: PersonaProfile, alert: dict, trust_score: float, rng: Random) -> str:
    severity = alert.get("severity", "medium")
    risk_bonus = 0.18 if severity == "hard" else 0.08 if severity == "medium" else 0.02
    heed_score = (persona.alert_sensitivity * 0.35) + (trust_score * 0.4) + (persona.digital_confidence * 0.15) + risk_bonus
    heed_score -= persona.impulsivity * 0.2
    if rng.random() < heed_score:
        return "useful"

    dismiss_score = (1.0 - trust_score) * 0.45 + persona.impulsivity * 0.2
    if severity == "hard":
        dismiss_score += 0.08
    elif severity == "soft":
        dismiss_score -= 0.08
    if rng.random() < dismiss_score:
        return "dismissed"
    return "ignored"


def _record_alert(summary: ParticipantSimulationSummary, alert: dict) -> None:
    summary.alert_count += 1
    severity = alert.get("severity", "medium")
    if severity == "soft":
        summary.soft_alert_count += 1
    elif severity == "medium":
        summary.medium_alert_count += 1
    else:
        summary.hard_alert_count += 1


def _projected_ratio(monitor: FinancialLiteracySafetyMonitor, amount: float) -> float:
    status = monitor.status()
    limit = max(float(status.get("daily_safe_limit") or 0.0), 1.0)
    projected = float(status.get("daily_spend") or 0.0) + float(amount)
    return projected / limit


def _severity_for_expense_alert(
    *,
    variant: str,
    monitor: FinancialLiteracySafetyMonitor,
    persona: PersonaProfile,
    amount: float,
    event_metadata: dict,
) -> str | None:
    ratio = _projected_ratio(monitor, amount)
    catastrophic = bool(event_metadata.get("catastrophic"))
    anomaly_ratio = amount / max(persona.avg_daily_spend, 1.0)

    if catastrophic or ratio >= 1.18 or anomaly_ratio >= 2.4:
        return "hard"
    if variant == "adaptive":
        if ratio >= 0.97 or anomaly_ratio >= 1.55:
            return "medium"
        if ratio >= 0.82 or (not event_metadata.get("essential") and anomaly_ratio >= 1.15):
            return "soft"
        return None

    if ratio >= 1.0 or anomaly_ratio >= 1.75:
        return "hard"
    if ratio >= 0.9:
        return "medium"
    return None


def _severity_for_upi_alert(
    *,
    variant: str,
    monitor: FinancialLiteracySafetyMonitor,
    persona: PersonaProfile,
    amount: float,
    event_metadata: dict,
) -> str | None:
    ratio = _projected_ratio(monitor, amount)
    fraud_like = bool(event_metadata.get("fraud_like"))
    if fraud_like and (ratio >= 1.0 or persona.fraud_susceptibility >= 0.6):
        return "hard"
    if variant == "adaptive":
        if ratio >= 0.96:
            return "medium"
        if fraud_like or ratio >= 0.82:
            return "soft"
        return None
    if fraud_like or ratio >= 0.9:
        return "medium"
    return None


def _synthetic_alert(severity: str, event_type: str, amount: float) -> dict:
    return {
        "type": "synthetic_alert",
        "severity": severity,
        "priority": "high" if severity == "hard" else "medium" if severity == "medium" else "low",
        "event_type": event_type,
        "amount": amount,
    }


def _normalize_monitor_alert(event_type: str, alert: dict) -> dict:
    normalized = dict(alert)
    if event_type == "upi_open":
        normalized["severity"] = "hard" if normalized.get("priority") in {"high", "critical"} else "medium"
    elif normalized.get("reason") == "catastrophic_risk_override":
        normalized["severity"] = "hard"
    else:
        normalized["severity"] = "medium"
    return normalized


class SimulationRunner:
    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()

    def run(self, personas: list[PersonaProfile], variant: str) -> SimulationReport:
        report = SimulationReport()
        for index, persona in enumerate(personas):
            rng = Random(self.config.seed + index)
            monitor = _monitor_for_variant(persona, variant)
            summary = ParticipantSimulationSummary(
                participant_id=persona.persona_id,
                variant=variant,
                trust_score_final=persona.trust_level,
            )
            trust_score = persona.trust_level
            timeline = build_scenario_window(
                persona,
                start_date=self.config.start_date,
                days=self.config.days,
                seed=self.config.seed + index,
                include_adverse_events=self.config.include_adverse_events,
            )

            active_days: set[str] = set()
            for event in timeline:
                if summary.uninstall_day is not None:
                    break
                active_days.add(event.timestamp.date().isoformat())

                if event.event_type == "expense_sms":
                    pre_alert = _severity_for_expense_alert(
                        variant=variant,
                        monitor=monitor,
                        persona=persona,
                        amount=event.amount,
                        event_metadata=event.metadata,
                    )
                    alerts = monitor.ingest_expense(amount=event.amount, timestamp=event.timestamp.isoformat())
                    if event.metadata.get("catastrophic"):
                        summary.risky_spend_events += 1
                    emitted_alerts = [_normalize_monitor_alert("expense_sms", alert) for alert in alerts]
                    if pre_alert and not emitted_alerts:
                        emitted_alerts = [_synthetic_alert(pre_alert, "expense_sms", event.amount)]
                    for alert in emitted_alerts:
                        _record_alert(summary, alert)
                        outcome = _feedback_outcome(persona, alert, trust_score, rng)
                        if outcome == "useful":
                            summary.useful_feedback_count += 1
                            trust_score = min(1.0, trust_score + 0.04)
                        elif outcome == "dismissed":
                            summary.dismissed_feedback_count += 1
                            trust_score = max(0.0, trust_score - 0.05)
                        else:
                            summary.ignored_feedback_count += 1
                            trust_score = max(0.0, trust_score - 0.02)

                elif event.event_type == "upi_open":
                    pre_alert = _severity_for_upi_alert(
                        variant=variant,
                        monitor=monitor,
                        persona=persona,
                        amount=event.amount,
                        event_metadata=event.metadata,
                    )
                    alert = monitor.on_upi_app_open(
                        app_name="SyntheticUPI",
                        intent_amount=event.amount,
                        timestamp=event.timestamp.isoformat(),
                    )
                    emitted_alert = _normalize_monitor_alert("upi_open", alert) if alert else None
                    if emitted_alert is None and pre_alert is not None:
                        emitted_alert = _synthetic_alert(pre_alert, "upi_open", event.amount)
                    if emitted_alert:
                        _record_alert(summary, emitted_alert)
                        outcome = _feedback_outcome(persona, emitted_alert, trust_score, rng)
                        if outcome == "useful":
                            summary.useful_feedback_count += 1
                            if emitted_alert.get("severity") in {"medium", "hard"}:
                                summary.prevented_risk_count += 1
                            trust_score = min(1.0, trust_score + 0.05)
                        elif outcome == "dismissed":
                            summary.dismissed_feedback_count += 1
                            summary.risky_spend_events += 1
                            trust_score = max(0.0, trust_score - 0.05)
                        else:
                            summary.ignored_feedback_count += 1
                            summary.risky_spend_events += 1
                            trust_score = max(0.0, trust_score - 0.03)

                elif event.event_type == "shared_phone_noise":
                    trust_score = max(0.0, trust_score - 0.015)

                if summary.hard_alert_count >= 4 and trust_score <= 0.25:
                    day_offset = (event.timestamp.date() - self.config.start_date).days + 1
                    summary.uninstall_day = day_offset

            summary.active_days = len(active_days)
            summary.trust_score_final = round(trust_score, 3)
            report.summaries.append(summary)

        return report

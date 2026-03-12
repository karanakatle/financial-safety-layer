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
    scenario: str = "default"


def _adaptive_policy_profile(persona: PersonaProfile, scenario: str) -> dict[str, float]:
    limit_factor = 1.2
    warning_ratio = 0.88 if persona.daily_spend_volatility >= 0.35 else 0.9
    warmup_seed_multiplier = 1.2

    # Cautious / high-sensitivity users need fewer premature warnings.
    if persona.alert_sensitivity >= 0.65 and persona.impulsivity <= 0.35:
        limit_factor += 0.05
        warning_ratio += 0.02
        warmup_seed_multiplier += 0.08

    # Shared-phone households are more exposed to noisy context; be slightly calmer.
    if persona.shared_phone_risk >= 0.5:
        limit_factor += 0.03
        warning_ratio += 0.01
        warmup_seed_multiplier += 0.04

    # Fraud-prone users need earlier intervention on risky flows.
    if persona.fraud_susceptibility >= 0.65:
        limit_factor -= 0.02
        warning_ratio -= 0.02

    if scenario in {"festival_spend", "medical_emergency"} and persona.cohort == "women_led_household":
        limit_factor += 0.04
        warning_ratio += 0.015
        warmup_seed_multiplier += 0.05

    if scenario in {"festival_spend", "medical_emergency"} and persona.shared_phone_risk >= 0.5:
        limit_factor += 0.03
        warning_ratio += 0.01
        warmup_seed_multiplier += 0.03

    if scenario == "festival_spend" and persona.shared_phone_risk >= 0.5:
        limit_factor += 0.05
        warning_ratio += 0.015
        warmup_seed_multiplier += 0.04

    if scenario == "shared_phone_noise_heavy" and persona.shared_phone_risk >= 0.5:
        limit_factor += 0.07
        warning_ratio += 0.02
        warmup_seed_multiplier += 0.05

    return {
        "limit_factor": max(1.1, round(limit_factor, 3)),
        "warning_ratio": min(0.93, max(0.84, round(warning_ratio, 3))),
        "warmup_seed_multiplier": max(1.12, round(warmup_seed_multiplier, 3)),
    }


def _adaptive_expense_thresholds(persona: PersonaProfile, event_metadata: dict, scenario: str) -> dict[str, float]:
    thresholds = {
        "soft_ratio": 0.82,
        "medium_ratio": 0.97,
        "hard_ratio": 1.18,
        "soft_anomaly": 1.15,
        "medium_anomaly": 1.55,
        "hard_anomaly": 2.4,
    }

    if persona.alert_sensitivity >= 0.65 and persona.impulsivity <= 0.35:
        thresholds["soft_ratio"] += 0.08
        thresholds["medium_ratio"] += 0.05
        thresholds["soft_anomaly"] += 0.1
        thresholds["medium_anomaly"] += 0.1

    if persona.shared_phone_risk >= 0.5:
        thresholds["soft_ratio"] += 0.04
        thresholds["medium_ratio"] += 0.03

    if event_metadata.get("essential"):
        thresholds["soft_ratio"] += 0.05
        thresholds["medium_ratio"] += 0.03
        thresholds["soft_anomaly"] += 0.08

    if persona.fraud_susceptibility >= 0.65 and not event_metadata.get("essential"):
        thresholds["soft_ratio"] -= 0.02
        thresholds["medium_ratio"] -= 0.01

    if scenario in {"festival_spend", "medical_emergency"} and event_metadata.get("essential"):
        thresholds["soft_ratio"] += 0.06
        thresholds["medium_ratio"] += 0.05
        thresholds["hard_ratio"] += 0.07
        thresholds["soft_anomaly"] += 0.12
        thresholds["medium_anomaly"] += 0.16
        thresholds["hard_anomaly"] += 0.2

    if scenario == "festival_spend" and persona.cohort == "women_led_household":
        thresholds["soft_ratio"] += 0.04
        thresholds["medium_ratio"] += 0.03

    if scenario in {"festival_spend", "medical_emergency"} and persona.shared_phone_risk >= 0.5:
        thresholds["soft_ratio"] += 0.04
        thresholds["medium_ratio"] += 0.03
        thresholds["soft_anomaly"] += 0.08

    if scenario == "festival_spend" and persona.shared_phone_risk >= 0.5:
        thresholds["soft_ratio"] += 0.05
        thresholds["medium_ratio"] += 0.04
        thresholds["hard_ratio"] += 0.06
        thresholds["soft_anomaly"] += 0.1
        thresholds["medium_anomaly"] += 0.12

    if scenario == "shared_phone_noise_heavy" and persona.shared_phone_risk >= 0.5:
        thresholds["soft_ratio"] += 0.08
        thresholds["medium_ratio"] += 0.06
        thresholds["hard_ratio"] += 0.08
        thresholds["soft_anomaly"] += 0.14
        thresholds["medium_anomaly"] += 0.18
        thresholds["hard_anomaly"] += 0.22

    thresholds["soft_ratio"] = min(thresholds["soft_ratio"], 0.96)
    thresholds["medium_ratio"] = min(
        max(thresholds["medium_ratio"], thresholds["soft_ratio"] + 0.04),
        thresholds["hard_ratio"] - 0.04,
    )
    thresholds["hard_ratio"] = min(max(thresholds["hard_ratio"], thresholds["medium_ratio"] + 0.05), 1.32)
    return thresholds


def _adaptive_upi_thresholds(persona: PersonaProfile, event_metadata: dict, scenario: str) -> dict[str, float]:
    thresholds = {
        "soft_ratio": 0.82,
        "medium_ratio": 0.96,
        "hard_ratio": 1.0,
    }

    if persona.alert_sensitivity >= 0.65 and persona.impulsivity <= 0.35 and not event_metadata.get("fraud_like"):
        thresholds["soft_ratio"] += 0.06
        thresholds["medium_ratio"] += 0.04

    if persona.shared_phone_risk >= 0.5 and not event_metadata.get("fraud_like"):
        thresholds["soft_ratio"] += 0.03
        thresholds["medium_ratio"] += 0.02

    if persona.fraud_susceptibility >= 0.65:
        thresholds["soft_ratio"] -= 0.05
        thresholds["medium_ratio"] -= 0.04
        thresholds["hard_ratio"] -= 0.02

    if scenario in {"festival_spend", "medical_emergency"} and not event_metadata.get("fraud_like"):
        thresholds["soft_ratio"] += 0.04
        thresholds["medium_ratio"] += 0.03

    if scenario in {"festival_spend", "medical_emergency"} and persona.shared_phone_risk >= 0.5 and not event_metadata.get("fraud_like"):
        thresholds["soft_ratio"] += 0.03
        thresholds["medium_ratio"] += 0.02

    if scenario == "festival_spend" and persona.shared_phone_risk >= 0.5 and not event_metadata.get("fraud_like"):
        thresholds["soft_ratio"] += 0.04
        thresholds["medium_ratio"] += 0.03

    if scenario == "shared_phone_noise_heavy" and persona.shared_phone_risk >= 0.5 and not event_metadata.get("fraud_like"):
        thresholds["soft_ratio"] += 0.06
        thresholds["medium_ratio"] += 0.05

    thresholds["soft_ratio"] = min(max(thresholds["soft_ratio"], 0.72), 0.93)
    thresholds["medium_ratio"] = min(
        max(thresholds["medium_ratio"], thresholds["soft_ratio"] + 0.04),
        thresholds["hard_ratio"] - 0.01,
    )
    thresholds["hard_ratio"] = min(max(thresholds["hard_ratio"], thresholds["medium_ratio"] + 0.01), 1.05)
    return thresholds


def _monitor_for_variant(persona: PersonaProfile, variant: str) -> FinancialLiteracySafetyMonitor:
    if variant == "static_baseline":
        return FinancialLiteracySafetyMonitor(
            daily_safe_limit=max(900.0, round(persona.avg_daily_spend * 1.05, 2)),
            warning_ratio=0.9,
            warmup_days=0,
        )
    profile = _adaptive_policy_profile(persona, "default")
    return FinancialLiteracySafetyMonitor(
        daily_safe_limit=max(900.0, round(persona.avg_daily_spend * profile["limit_factor"], 2)),
        warning_ratio=profile["warning_ratio"],
        warmup_days=3,
        warmup_seed_multiplier=profile["warmup_seed_multiplier"],
    )


def _feedback_outcome(persona: PersonaProfile, alert: dict, trust_score: float, rng: Random) -> str:
    severity = alert.get("severity", "medium")
    protective_context = bool(alert.get("essential_context")) or bool(alert.get("goal_protection"))
    risk_bonus = 0.18 if severity == "hard" else 0.08 if severity == "medium" else 0.02
    heed_score = (persona.alert_sensitivity * 0.35) + (trust_score * 0.4) + (persona.digital_confidence * 0.15) + risk_bonus
    heed_score -= persona.impulsivity * 0.2
    if protective_context:
        heed_score += 0.04
    if rng.random() < heed_score:
        inconvenience_score = 0.0
        if protective_context and severity in {"medium", "hard"}:
            inconvenience_score += 0.14 if severity == "medium" else 0.22
            inconvenience_score += max(0.0, 0.55 - persona.digital_confidence) * 0.25
            inconvenience_score += persona.shared_phone_risk * 0.12
            if alert.get("scenario") == "festival_spend":
                inconvenience_score += 0.08
        if rng.random() < min(inconvenience_score, 0.65):
            return "preventive_inconvenient"
        return "useful"

    dismiss_score = (1.0 - trust_score) * 0.45 + persona.impulsivity * 0.2
    if severity == "hard":
        dismiss_score += 0.08
    elif severity == "soft":
        dismiss_score -= 0.08
    if protective_context:
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
    scenario: str,
) -> str | None:
    ratio = _projected_ratio(monitor, amount)
    catastrophic = bool(event_metadata.get("catastrophic"))
    anomaly_ratio = amount / max(persona.avg_daily_spend, 1.0)

    if catastrophic:
        return "hard"
    if variant == "adaptive":
        thresholds = _adaptive_expense_thresholds(persona, event_metadata, scenario)
        if ratio >= thresholds["hard_ratio"] or anomaly_ratio >= thresholds["hard_anomaly"]:
            return "hard"
        if ratio >= thresholds["medium_ratio"] or anomaly_ratio >= thresholds["medium_anomaly"]:
            return "medium"
        if ratio >= thresholds["soft_ratio"] or (
            not event_metadata.get("essential") and anomaly_ratio >= thresholds["soft_anomaly"]
        ):
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
    scenario: str,
) -> str | None:
    ratio = _projected_ratio(monitor, amount)
    fraud_like = bool(event_metadata.get("fraud_like"))
    if variant == "adaptive":
        thresholds = _adaptive_upi_thresholds(persona, event_metadata, scenario)
        if fraud_like and (ratio >= thresholds["hard_ratio"] or persona.fraud_susceptibility >= 0.6):
            return "hard"
        if ratio >= thresholds["medium_ratio"]:
            return "medium"
        if fraud_like or ratio >= thresholds["soft_ratio"]:
            return "soft"
        return None
    if fraud_like and (ratio >= 1.0 or persona.fraud_susceptibility >= 0.6):
        return "hard"
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


def _decorate_alert(alert: dict, event_type: str, event_metadata: dict, scenario: str) -> dict:
    enriched = dict(alert)
    enriched["scenario"] = scenario
    enriched["essential_context"] = bool(event_metadata.get("essential"))
    enriched["goal_protection"] = bool(event_metadata.get("essential")) or bool(event_metadata.get("goal"))
    enriched["fraud_like"] = bool(event_metadata.get("fraud_like"))
    if event_type == "upi_open":
        enriched["goal_protection"] = enriched["goal_protection"] and not enriched["fraud_like"]
    return enriched


class SimulationRunner:
    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()

    def run(self, personas: list[PersonaProfile], variant: str) -> SimulationReport:
        report = SimulationReport()
        for index, persona in enumerate(personas):
            rng = Random(self.config.seed + index)
            if variant == "adaptive":
                profile = _adaptive_policy_profile(persona, self.config.scenario)
                monitor = FinancialLiteracySafetyMonitor(
                    daily_safe_limit=max(900.0, round(persona.avg_daily_spend * profile["limit_factor"], 2)),
                    warning_ratio=profile["warning_ratio"],
                    warmup_days=3,
                    warmup_seed_multiplier=profile["warmup_seed_multiplier"],
                )
            else:
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
                scenario=self.config.scenario,
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
                        scenario=self.config.scenario,
                    )
                    alerts = monitor.ingest_expense(amount=event.amount, timestamp=event.timestamp.isoformat())
                    if event.metadata.get("catastrophic"):
                        summary.risky_spend_events += 1
                    emitted_alerts = [_normalize_monitor_alert("expense_sms", alert) for alert in alerts]
                    if pre_alert and not emitted_alerts:
                        emitted_alerts = [_synthetic_alert(pre_alert, "expense_sms", event.amount)]
                    for alert in emitted_alerts:
                        alert = _decorate_alert(alert, "expense_sms", event.metadata, self.config.scenario)
                        _record_alert(summary, alert)
                        outcome = _feedback_outcome(persona, alert, trust_score, rng)
                        if outcome == "useful":
                            summary.useful_feedback_count += 1
                            trust_score = min(1.0, trust_score + 0.04)
                        elif outcome == "preventive_inconvenient":
                            summary.preventive_inconvenient_feedback_count += 1
                            trust_score = min(1.0, trust_score + 0.01)
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
                        scenario=self.config.scenario,
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
                        emitted_alert = _decorate_alert(
                            emitted_alert,
                            "upi_open",
                            event.metadata,
                            self.config.scenario,
                        )
                        _record_alert(summary, emitted_alert)
                        outcome = _feedback_outcome(persona, emitted_alert, trust_score, rng)
                        if outcome == "useful":
                            summary.useful_feedback_count += 1
                            if emitted_alert.get("severity") in {"medium", "hard"}:
                                summary.prevented_risk_count += 1
                            trust_score = min(1.0, trust_score + 0.05)
                        elif outcome == "preventive_inconvenient":
                            summary.preventive_inconvenient_feedback_count += 1
                            if emitted_alert.get("severity") in {"medium", "hard"}:
                                summary.prevented_risk_count += 1
                            trust_score = min(1.0, trust_score + 0.01)
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

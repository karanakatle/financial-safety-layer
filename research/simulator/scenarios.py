from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from random import Random

from research.simulator.personas import PersonaProfile


@dataclass(frozen=True)
class SimulationEvent:
    timestamp: datetime
    event_type: str
    amount: float = 0.0
    description: str = ""
    metadata: dict = field(default_factory=dict)


SCENARIO_PRESETS = {
    "default",
    "fraud_week",
    "festival_spend",
    "medical_emergency",
    "shared_phone_noise_heavy",
}


def _day_timestamp(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour=hour, minute=minute))


def _festival_day(offset: int, days: int) -> bool:
    if days <= 3:
        return offset == max(days - 1, 0)
    midpoint = days // 2
    return midpoint - 1 <= offset <= midpoint + 1


def _fraud_pressure_for_day(persona: PersonaProfile, offset: int, days: int) -> float:
    if days <= 7:
        return 1.0
    midpoint = days // 2
    return 1.0 if midpoint - 3 <= offset <= midpoint + 3 else 0.45 + persona.fraud_susceptibility * 0.2


def _medical_emergency_day(offset: int, days: int) -> bool:
    target = min(max(days // 3, 1), max(days - 2, 1))
    return offset == target


def _daily_profile(
    persona: PersonaProfile,
    *,
    offset: int,
    days: int,
    rng: Random,
    scenario: str,
) -> dict:
    volatility_multiplier = max(
        0.2,
        1.0 + rng.uniform(-persona.daily_spend_volatility, persona.daily_spend_volatility),
    )
    baseline_spend = max(80.0, persona.avg_daily_spend * volatility_multiplier)

    essential_share = 0.58 if persona.cohort == "women_led_household" else 0.46
    fraud_pressure = max(0.08, persona.fraud_susceptibility * 0.18)
    impulse_pressure = max(0.05, persona.impulsivity * 0.15)
    shared_noise_pressure = persona.shared_phone_risk * 0.1
    emergency_amount = 0.0

    if scenario == "festival_spend" and _festival_day(offset, days):
        baseline_spend *= 1.45
        essential_share = min(0.78, essential_share + 0.08)
        impulse_pressure += 0.06

    if scenario == "fraud_week":
        fraud_pressure = min(0.75, _fraud_pressure_for_day(persona, offset, days))
        impulse_pressure = max(impulse_pressure - 0.02, 0.02)

    if scenario == "medical_emergency" and _medical_emergency_day(offset, days):
        emergency_amount = round(max(persona.avg_daily_spend * 2.1, 1800.0), 2)
        essential_share = min(0.85, essential_share + 0.18)
        baseline_spend *= 1.25
        fraud_pressure *= 0.8

    if scenario == "shared_phone_noise_heavy":
        shared_noise_pressure = max(shared_noise_pressure, persona.shared_phone_risk * 0.45 + 0.08)
        if persona.shared_phone_risk >= 0.5:
            baseline_spend *= 1.08
            essential_share = min(0.72, essential_share + 0.04)

    return {
        "baseline_spend": baseline_spend,
        "essential_share": essential_share,
        "fraud_pressure": fraud_pressure,
        "impulse_pressure": impulse_pressure,
        "shared_noise_pressure": shared_noise_pressure,
        "emergency_amount": emergency_amount,
    }


def build_daily_scenario(
    persona: PersonaProfile,
    day: date,
    offset: int,
    days: int,
    rng: Random,
    include_adverse_events: bool = True,
    scenario: str = "default",
) -> list[SimulationEvent]:
    events: list[SimulationEvent] = []
    profile = _daily_profile(persona, offset=offset, days=days, rng=rng, scenario=scenario)
    baseline_spend = profile["baseline_spend"]
    essential_share = profile["essential_share"]
    essential_amount = round(baseline_spend * essential_share, 2)
    discretionary_amount = round(max(baseline_spend - essential_amount, 0.0), 2)

    events.append(
        SimulationEvent(
            timestamp=_day_timestamp(day, 9, 10),
            event_type="expense_sms",
            amount=essential_amount,
            description="essential daily spend",
            metadata={"essential": True},
        )
    )

    if profile["emergency_amount"] > 0:
        events.append(
            SimulationEvent(
                timestamp=_day_timestamp(day, 13, 40),
                event_type="expense_sms",
                amount=profile["emergency_amount"],
                description="medical emergency expense",
                metadata={"essential": True, "catastrophic": True, "goal": "medicine"},
            )
        )

    if discretionary_amount > 0:
        events.append(
            SimulationEvent(
                timestamp=_day_timestamp(day, 18, 25),
                event_type="expense_sms",
                amount=discretionary_amount,
                description="regular discretionary spend",
                metadata={"essential": False},
            )
        )

    if include_adverse_events and rng.random() < profile["fraud_pressure"]:
        amount = round(max(persona.avg_daily_spend * 1.1, 900.0), 2)
        events.append(
            SimulationEvent(
                timestamp=_day_timestamp(day, 20, 15),
                event_type="upi_open",
                amount=amount,
                description="suspicious upi attempt",
                metadata={"fraud_like": True},
            )
        )

    if include_adverse_events and rng.random() < profile["impulse_pressure"]:
        amount = round(max(persona.avg_daily_spend * 2.8, 2400.0), 2)
        events.append(
            SimulationEvent(
                timestamp=_day_timestamp(day, 21, 5),
                event_type="expense_sms",
                amount=amount,
                description="catastrophic impulse spend",
                metadata={"catastrophic": True, "essential": False},
            )
        )

    if persona.shared_phone_risk > 0 and rng.random() < profile["shared_noise_pressure"]:
        events.append(
            SimulationEvent(
                timestamp=_day_timestamp(day, 22, 10),
                event_type="shared_phone_noise",
                description="other household member created noisy app-open context",
            )
        )

    return sorted(events, key=lambda event: event.timestamp)


def build_scenario_window(
    persona: PersonaProfile,
    *,
    start_date: date,
    days: int,
    seed: int,
    include_adverse_events: bool = True,
    scenario: str = "default",
) -> list[SimulationEvent]:
    if scenario not in SCENARIO_PRESETS:
        raise ValueError(f"Unsupported scenario preset: {scenario}")
    rng = Random(seed)
    timeline: list[SimulationEvent] = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        timeline.extend(
            build_daily_scenario(
                persona,
                day,
                offset,
                days,
                rng,
                include_adverse_events=include_adverse_events,
                scenario=scenario,
            )
        )
    return timeline

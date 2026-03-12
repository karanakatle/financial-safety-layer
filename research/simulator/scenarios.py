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


def _day_timestamp(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour=hour, minute=minute))


def build_daily_scenario(
    persona: PersonaProfile,
    day: date,
    rng: Random,
    include_adverse_events: bool = True,
) -> list[SimulationEvent]:
    events: list[SimulationEvent] = []
    volatility_multiplier = max(0.2, 1.0 + rng.uniform(-persona.daily_spend_volatility, persona.daily_spend_volatility))
    baseline_spend = max(80.0, persona.avg_daily_spend * volatility_multiplier)

    essential_share = 0.58 if persona.cohort == "women_led_household" else 0.46
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

    if include_adverse_events and rng.random() < max(0.08, persona.fraud_susceptibility * 0.18):
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

    if include_adverse_events and rng.random() < max(0.05, persona.impulsivity * 0.15):
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

    if persona.shared_phone_risk > 0 and rng.random() < persona.shared_phone_risk * 0.1:
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
) -> list[SimulationEvent]:
    rng = Random(seed)
    timeline: list[SimulationEvent] = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        timeline.extend(build_daily_scenario(persona, day, rng, include_adverse_events=include_adverse_events))
    return timeline

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PersonaProfile:
    persona_id: str
    cohort: str
    language: str
    essential_goals: tuple[str, ...] = field(default_factory=tuple)
    avg_daily_spend: float = 700.0
    daily_spend_volatility: float = 0.2
    trust_level: float = 0.55
    digital_confidence: float = 0.5
    alert_sensitivity: float = 0.6
    fraud_susceptibility: float = 0.4
    impulsivity: float = 0.4
    shared_phone_risk: float = 0.0


def default_personas() -> list[PersonaProfile]:
    return [
        PersonaProfile(
            persona_id="women_household_cautious",
            cohort="women_led_household",
            language="hi",
            essential_goals=("ration", "school"),
            avg_daily_spend=650.0,
            daily_spend_volatility=0.18,
            trust_level=0.62,
            digital_confidence=0.45,
            alert_sensitivity=0.72,
            fraud_susceptibility=0.35,
            impulsivity=0.25,
        ),
        PersonaProfile(
            persona_id="vendor_volatile",
            cohort="daily_cashflow_worker",
            language="hi",
            essential_goals=("fuel", "medicine"),
            avg_daily_spend=950.0,
            daily_spend_volatility=0.42,
            trust_level=0.48,
            digital_confidence=0.55,
            alert_sensitivity=0.5,
            fraud_susceptibility=0.5,
            impulsivity=0.55,
        ),
        PersonaProfile(
            persona_id="driver_fraud_prone",
            cohort="daily_cashflow_worker",
            language="en",
            essential_goals=("fuel", "loan_repayment"),
            avg_daily_spend=900.0,
            daily_spend_volatility=0.33,
            trust_level=0.44,
            digital_confidence=0.42,
            alert_sensitivity=0.58,
            fraud_susceptibility=0.72,
            impulsivity=0.47,
        ),
        PersonaProfile(
            persona_id="shared_phone_household",
            cohort="women_led_household",
            language="hi",
            essential_goals=("ration", "medicine"),
            avg_daily_spend=720.0,
            daily_spend_volatility=0.26,
            trust_level=0.5,
            digital_confidence=0.35,
            alert_sensitivity=0.63,
            fraud_susceptibility=0.41,
            impulsivity=0.32,
            shared_phone_risk=0.6,
        ),
    ]

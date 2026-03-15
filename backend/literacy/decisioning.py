from __future__ import annotations

from backend.literacy.messages import (
    DEFAULT_STAGE2_OVER_LIMIT_TEMPLATE,
    literacy_message,
)


def effective_goal_profile(profile: dict | None) -> dict:
    if profile:
        return profile
    return {
        "cohort": "daily_cashflow_worker",
        "essential_goals": [],
        "language": "en",
        "setup_skipped": True,
    }


def essential_goal_envelope(profile: dict | None, daily_safe_limit: float, cohort_normalizer) -> dict:
    active = effective_goal_profile(profile)
    goals = list(active.get("essential_goals") or [])
    cohort = cohort_normalizer(active.get("cohort"))

    base_ratio = 0.18 if cohort == "women_led_household" else 0.22
    ratio = max(0.15, min(0.35, base_ratio + (0.05 * min(len(goals), 2))))
    reserve_amount = round(daily_safe_limit * ratio, 2)
    protected_limit = round(max(daily_safe_limit - reserve_amount, daily_safe_limit * 0.55), 2)
    return {
        "cohort": cohort,
        "essential_goals": goals,
        "reserve_ratio": round(ratio, 3),
        "reserve_amount": reserve_amount,
        "protected_limit": protected_limit,
    }


def risk_level_from_score(risk_score: float) -> str:
    if risk_score >= 0.85:
        return "critical"
    if risk_score >= 0.65:
        return "high"
    if risk_score >= 0.45:
        return "medium"
    return "low"


def alert_severity_from_context(
    *,
    frequency_bucket: str,
    risk_level: str,
    upi_open_flag: bool,
    pause_seconds: int,
) -> str:
    if frequency_bucket == "hard":
        if risk_level == "critical" or pause_seconds > 0:
            return "hard"
        return "medium"
    if upi_open_flag and risk_level in {"high", "critical"}:
        return "medium"
    if risk_level in {"high", "critical"}:
        return "medium"
    return "soft"


def localized_label(language: str, key: str) -> str:
    return literacy_message(language, f"labels.{key}")


def localized_stage1_message(language: str, stage1_message: str) -> str:
    if language == "hi":
        return literacy_message(language, "stage1_message")
    return stage1_message


def localized_stage2_message(
    language: str,
    projected: float,
    limit: float,
    stage2_over_limit_template: str,
    stage2_close_limit_message: str,
) -> str:
    daily_overage = max(projected - limit, 0.0)
    weekly_impact = round(daily_overage * 7, 2)
    if daily_overage > 0:
        if language == "hi":
            return literacy_message(
                language,
                "stage2_over_limit_template",
                daily_overage=round(daily_overage, 2),
                weekly_impact=weekly_impact,
            )
        try:
            return stage2_over_limit_template.format(
                daily_overage=round(daily_overage, 2),
                weekly_impact=weekly_impact,
            )
        except (KeyError, ValueError):
            return DEFAULT_STAGE2_OVER_LIMIT_TEMPLATE.format(
                daily_overage=round(daily_overage, 2),
                weekly_impact=weekly_impact,
            )
    if language == "hi":
        return literacy_message(language, "stage2_close_limit_message")
    return stage2_close_limit_message


def localize_alert(
    alert: dict,
    language: str,
    stage1_message: str,
    stage2_over_limit_template: str,
    stage2_close_limit_message: str,
) -> dict:
    if language == "en":
        return alert
    localized = dict(alert)
    reason = localized.get("reason")
    if reason in {"daily_threshold_near_exceeded", "catastrophic_risk_override"}:
        localized["message"] = localized_stage1_message(language, stage1_message)
    elif reason == "upi_open_after_threshold_warning":
        projected = float(localized.get("projected_daily_spend") or 0.0)
        limit = float(localized.get("daily_safe_limit") or 0.0)
        localized["message"] = localized_stage2_message(
            language,
            projected,
            limit,
            stage2_over_limit_template,
            stage2_close_limit_message,
        )
    return localized


def localized_goal_names(language: str, envelope: dict) -> str:
    goals = [str(goal or "").strip() for goal in list(envelope.get("essential_goals") or []) if str(goal or "").strip()]
    if not goals:
        return literacy_message(language, "daily_essentials")
    localized_goals = [
        literacy_message(language, f"goals.{goal}") if literacy_message(language, f"goals.{goal}") != f"goals.{goal}" else goal
        for goal in goals[:2]
    ]
    return ", ".join(localized_goals)


def goal_impact_text(language: str, envelope: dict, projected_spend: float) -> str:
    protected_limit = float(envelope.get("protected_limit") or 0.0)
    if protected_limit <= 0:
        return ""
    delta = round(projected_spend - protected_limit, 2)
    if delta <= 0:
        return ""
    goal_names = localized_goal_names(language, envelope)
    return literacy_message(language, "goal_impact_template", delta=delta, goal_names=goal_names)


def primary_cashflow_message(
    language: str,
    reason: str,
    projected_spend: float,
    daily_safe_limit: float,
    envelope: dict,
    upi_open_flag: bool,
) -> str:
    protected_limit = float(envelope.get("protected_limit") or 0.0)
    essential_pressure = protected_limit > 0 and projected_spend > protected_limit
    over_limit = daily_safe_limit > 0 and projected_spend > daily_safe_limit

    if essential_pressure and over_limit:
        return literacy_message(language, "cashflow_message_over_limit_essentials")
    if essential_pressure:
        return literacy_message(language, "cashflow_message_essential_pressure")
    if upi_open_flag or reason == "upi_open_after_threshold_warning":
        return literacy_message(language, "cashflow_message_upi_open")
    return literacy_message(language, "cashflow_message_close_limit")


def why_text(
    language: str,
    reason: str,
    risk_level: str,
    projected_spend: float,
    daily_safe_limit: float,
    envelope: dict,
    financial_context: dict | None,
    spend_ratio: float,
    txn_anomaly_score: float,
    upi_open_flag: bool,
) -> str:
    protected_limit = float(envelope.get("protected_limit") or 0.0)
    goal_names = localized_goal_names(language, envelope)
    essential_pressure = protected_limit > 0 and projected_spend > protected_limit
    income_count = int((financial_context or {}).get("income_count") or 0)
    expense_count = int((financial_context or {}).get("expense_count") or 0)

    if essential_pressure:
        base = literacy_message(
            language,
            "why_essential_pressure_template",
            goal_names=goal_names,
            protected_limit=round(protected_limit, 2),
        )
    else:
        base = literacy_message(
            language,
            "why_daily_limit_template",
            projected_spend=round(projected_spend, 2),
            daily_safe_limit=round(daily_safe_limit, 2),
        )

    extras: list[str] = []
    if income_count > 0:
        extras.append(literacy_message(language, "why_recent_income_seen"))
    if expense_count >= 2:
        extras.append(literacy_message(language, "why_multiple_expenses_seen"))
    if reason == "catastrophic_risk_override":
        extras.append(literacy_message(language, "why_suffix_catastrophic"))
    elif upi_open_flag:
        extras.append(literacy_message(language, "why_suffix_upi_open"))
    elif txn_anomaly_score >= 0.7:
        extras.append(literacy_message(language, "why_suffix_anomaly"))

    return " ".join([base, *extras]).strip()


def next_action_text(
    language: str,
    risk_level: str,
    reason: str,
    projected_spend: float,
    daily_safe_limit: float,
    envelope: dict,
    financial_context: dict | None,
    upi_open_flag: bool,
) -> str:
    protected_limit = float(envelope.get("protected_limit") or 0.0)
    goal_names = localized_goal_names(language, envelope)
    essential_pressure = protected_limit > 0 and projected_spend > protected_limit
    income_count = int((financial_context or {}).get("income_count") or 0)

    if essential_pressure and income_count > 0:
        return literacy_message(language, "next_essential_pressure_with_income", goal_names=goal_names)
    if essential_pressure:
        return literacy_message(language, "next_essential_pressure", goal_names=goal_names)
    if risk_level in {"high", "critical"}:
        return literacy_message(language, "next_high_risk")
    if upi_open_flag or reason == "upi_open_after_threshold_warning":
        return literacy_message(language, "next_upi_open")
    return literacy_message(language, "next_default")

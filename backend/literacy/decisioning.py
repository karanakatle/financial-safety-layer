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


def goal_impact_text(language: str, envelope: dict, projected_spend: float) -> str:
    protected_limit = float(envelope.get("protected_limit") or 0.0)
    if protected_limit <= 0:
        return ""
    delta = round(projected_spend - protected_limit, 2)
    if delta <= 0:
        return ""
    goals = list(envelope.get("essential_goals") or [])
    goal_names = ", ".join(goals) if goals else literacy_message(language, "daily_essentials")
    return literacy_message(language, "goal_impact_template", delta=delta, goal_names=goal_names)


def why_text(
    language: str,
    reason: str,
    risk_level: str,
    spend_ratio: float,
    txn_anomaly_score: float,
    upi_open_flag: bool,
) -> str:
    base = literacy_message(
        language,
        "why_base_template",
        spend_ratio=round(spend_ratio, 2),
        risk_level=localized_label(language, risk_level),
    )
    if reason == "catastrophic_risk_override":
        return f"{base} {literacy_message(language, 'why_suffix_catastrophic')}"
    if upi_open_flag:
        return f"{base} {literacy_message(language, 'why_suffix_upi_open')}"
    if txn_anomaly_score >= 0.7:
        return f"{base} {literacy_message(language, 'why_suffix_anomaly')}"
    return base


def next_action_text(language: str, risk_level: str, reason: str) -> str:
    if risk_level in {"high", "critical"}:
        return literacy_message(language, "next_high_risk")
    if reason == "upi_open_after_threshold_warning":
        return literacy_message(language, "next_upi_open")
    return literacy_message(language, "next_default")

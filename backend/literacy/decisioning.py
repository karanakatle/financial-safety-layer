from __future__ import annotations


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
    if language == "hi":
        labels = {
            "risk": "जोखिम स्तर",
            "why": "क्यों दिखा",
            "next": "अगला सुरक्षित कदम",
            "goal_impact": "आवश्यक लक्ष्य प्रभाव",
            "low": "कम",
            "medium": "मध्यम",
            "high": "उच्च",
            "critical": "अत्यधिक",
        }
        return labels.get(key, key)
    labels = {
        "risk": "Risk level",
        "why": "Why this alert",
        "next": "Next safe action",
        "goal_impact": "Essential-goal impact",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
    }
    return labels.get(key, key)


def localized_stage1_message(language: str, stage1_message: str) -> str:
    if language == "hi":
        return (
            "आपका दैनिक सुरक्षित खर्च सीमा के करीब है। "
            "सीमा पार करने से आपकी वित्तीय योजना प्रभावित हो सकती है।"
        )
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
            return (
                f"अभी भुगतान करने पर आपकी दैनिक सुरक्षित सीमा लगभग ₹{round(daily_overage, 2)} "
                f"से पार हो सकती है और साप्ताहिक योजना पर लगभग ₹{weekly_impact} का असर पड़ सकता है।"
            )
        try:
            return stage2_over_limit_template.format(
                daily_overage=round(daily_overage, 2),
                weekly_impact=weekly_impact,
            )
        except (KeyError, ValueError):
            return (
                f"Paying now may exceed your daily safe amount by Rs {round(daily_overage, 2)} "
                f"and disturb your weekly planning by around Rs {weekly_impact}."
            )
    if language == "hi":
        return "आप दैनिक सीमा के करीब हैं। अभी भुगतान करने से आज या सप्ताह की योजना प्रभावित हो सकती है।"
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
    goal_names = ", ".join(goals) if goals else ("daily essentials" if language == "en" else "दैनिक आवश्यकताएं")
    if language == "hi":
        return f"₹{delta} का अतिरिक्त खर्च आपके {goal_names} बजट पर दबाव डाल सकता है।"
    return f"An extra ₹{delta} spend can pressure your {goal_names} budget."


def why_text(
    language: str,
    reason: str,
    risk_level: str,
    spend_ratio: float,
    txn_anomaly_score: float,
    upi_open_flag: bool,
) -> str:
    if language == "hi":
        base = (
            f"खर्च अनुपात {round(spend_ratio, 2)} और जोखिम स्तर "
            f"{localized_label(language, risk_level)} पाया गया।"
        )
        if reason == "catastrophic_risk_override":
            return f"{base} भुगतान राशि असामान्य रूप से अधिक थी।"
        if upi_open_flag:
            return f"{base} UPI ऐप खुलने पर जोखिम सक्रिय मिला।"
        if txn_anomaly_score >= 0.7:
            return f"{base} लेन-देन सामान्य से बड़ा है।"
        return base

    base = f"Spend ratio {round(spend_ratio, 2)} with {localized_label(language, risk_level)} risk."
    if reason == "catastrophic_risk_override":
        return f"{base} Transaction amount is unusually high."
    if upi_open_flag:
        return f"{base} Risk remained active when UPI app opened."
    if txn_anomaly_score >= 0.7:
        return f"{base} This transaction is larger than recent pattern."
    return base


def next_action_text(language: str, risk_level: str, reason: str) -> str:
    if language == "hi":
        if risk_level in {"high", "critical"}:
            return "भुगतान से पहले 5 सेकंड रुकें, प्राप्तकर्ता सत्यापित करें और राशि कम करें।"
        if reason == "upi_open_after_threshold_warning":
            return "जरूरत होने पर ही भुगतान करें, अन्यथा इसे बाद में करें।"
        return "आज अनावश्यक खर्च रोकें और आवश्यक लक्ष्य खर्च सुरक्षित रखें।"
    if risk_level in {"high", "critical"}:
        return "Pause 5 seconds, verify recipient, and reduce amount before paying."
    if reason == "upi_open_after_threshold_warning":
        return "Proceed only if essential; otherwise defer this payment."
    return "Stop non-essential spending today and protect essential-goal budget."

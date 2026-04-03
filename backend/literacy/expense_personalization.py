from __future__ import annotations

from datetime import date, datetime
from statistics import median

from .context import clamp, compute_txn_anomaly_score


PERSONALIZATION_CONTRACT_VERSION = "expense_pressure_v1"
PERSONALIZATION_TRACE_VERSION = "expense_pressure_trace_v1"
PRESSURE_STATES = (
    "within_safer_limit",
    "watch_this_expense",
    "this_adds_burden",
    "high_pressure_expense",
)
PERSONALIZATION_LEARNING_MIN_DAYS = 7
PERSONALIZATION_LEARNING_MAX_DAYS = 14

_DAILY_BUCKET_SCORES = {
    "below_250": 0.92,
    "250_499": 0.84,
    "500_749": 0.73,
    "750_999": 0.62,
    "1000_1499": 0.48,
    "1500_1999": 0.36,
    "2000_plus": 0.26,
}

_HOUSEHOLD_BUCKET_SCORES = {
    "below_6000": 0.86,
    "6000_9999": 0.76,
    "10000_13999": 0.62,
    "14000_17999": 0.52,
    "18000_24999": 0.41,
    "25000_plus": 0.31,
}


def _goal_weights(profile: dict | None) -> list[dict]:
    active = [
        str(goal or "").strip()
        for goal in list((profile or {}).get("active_priority_essentials") or (profile or {}).get("essential_goals") or [])
        if str(goal or "").strip()
    ]
    weights: list[dict] = []
    for index, goal in enumerate(active):
        rank = index + 1
        weight = round(max(0.35, 1.0 - (index * 0.12)), 3)
        weights.append({"goal": goal, "rank": rank, "weight": weight})
    return weights


def _resolve_balance_input(
    *,
    current_balance_amount: float | None,
    current_balance_source: str | None,
    daily_safe_limit: float,
    projected_spend: float,
) -> tuple[float | None, str]:
    if current_balance_amount is not None:
        return round(max(float(current_balance_amount), 0.0), 2), str(current_balance_source or "observed_balance")

    if daily_safe_limit > 0:
        # This is not a bank balance; it is a bounded budget-headroom estimate from the current policy.
        estimated = round(max(float(daily_safe_limit) - float(projected_spend), 0.0), 2)
        return estimated, "policy_headroom_estimate"

    return None, "unknown"


def _balance_pressure_score(*, amount: float, current_balance_amount: float | None, current_balance_source: str) -> float:
    if current_balance_amount is None:
        return 0.35
    if current_balance_amount <= 0:
        return 1.0

    ratio = amount / max(current_balance_amount, 1.0)
    base = clamp((ratio - 0.12) / 0.88)
    if current_balance_source == "policy_headroom_estimate":
        base = clamp(base * 0.9)
    return round(base, 4)


def _income_bucket_input(*, cohort: str, affordability_bucket_id: str | None, latest_income_amount: float | None) -> tuple[str, str, float]:
    bucket = str(affordability_bucket_id or "").strip()
    if bucket:
        if cohort == "daily_cashflow_worker":
            return bucket, "self_reported_income_bucket", _DAILY_BUCKET_SCORES.get(bucket, 0.5)
        return bucket, "affordability_proxy_bucket", _HOUSEHOLD_BUCKET_SCORES.get(bucket, 0.5)

    if latest_income_amount is None:
        return "unknown", "unknown", 0.45

    observed = float(latest_income_amount)
    if observed < 500:
        return "observed_low", "recent_income_signal", 0.82
    if observed < 1500:
        return "observed_mid", "recent_income_signal", 0.56
    return "observed_high", "recent_income_signal", 0.3


def _essential_pressure_score(
    *,
    weights: list[dict],
    projected_spend: float,
    daily_safe_limit: float,
    protected_limit: float,
) -> float:
    if weights:
        total_weight = sum(float(item["weight"]) for item in weights)
        active_focus_weight = sum(float(item["weight"]) for item in weights[:4]) / max(total_weight, 1.0)
    else:
        active_focus_weight = 0.0

    protected_gap = max(projected_spend - protected_limit, 0.0) if protected_limit > 0 else 0.0
    protected_gap_ratio = clamp(protected_gap / max(daily_safe_limit * 0.45, 1.0)) if daily_safe_limit > 0 else 0.0
    baseline = 0.1 if not weights else (0.18 + (0.34 * active_focus_weight))
    return round(clamp(baseline + (0.48 * protected_gap_ratio)), 4)


def _recent_pattern_input(*, amount: float, financial_context: dict | None, recent_amounts: list[float]) -> tuple[dict, float]:
    recent_expense_count = int((financial_context or {}).get("expense_count") or 0)
    latest_expense_amount = (financial_context or {}).get("latest_expense_amount")
    valid_recent = [float(value) for value in recent_amounts if float(value) > 0]
    median_recent = round(median(valid_recent), 2) if valid_recent else None
    txn_anomaly_score = compute_txn_anomaly_score(amount, valid_recent)
    recurrence_score = clamp(recent_expense_count / 4.0)
    pattern_score = round(clamp((0.58 * txn_anomaly_score) + (0.42 * recurrence_score)), 4)

    pattern = {
        "recent_expense_count": recent_expense_count,
        "latest_expense_amount": round(float(latest_expense_amount), 2) if latest_expense_amount is not None else None,
        "median_recent_expense_amount": median_recent,
        "txn_anomaly_score": round(txn_anomaly_score, 4),
    }
    return pattern, pattern_score


def _cohort_pressure_score(cohort: str) -> float:
    if cohort == "women_led_household":
        return 0.28
    if cohort == "daily_cashflow_worker":
        return 0.24
    return 0.2


def _confidence_bound(
    *,
    current_balance_source: str,
    income_bucket_source: str,
    has_essentials: bool,
    recent_pattern: dict,
    daily_safe_limit: float,
) -> tuple[float, str]:
    recent_count = int(recent_pattern.get("recent_expense_count") or 0)
    score = clamp(
        0.3
        + (0.22 if current_balance_source == "observed_balance" else 0.14 if current_balance_source != "unknown" else 0.0)
        + (0.18 if income_bucket_source != "unknown" else 0.0)
        + (0.16 if has_essentials else 0.0)
        + (0.14 * clamp(recent_count / 4.0))
        + (0.1 if daily_safe_limit > 0 else 0.0)
    )
    if score >= 0.78:
        label = "bounded_high"
    elif score >= 0.55:
        label = "bounded_medium"
    else:
        label = "bounded_low"
    return round(score, 4), label


def _coerce_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _learning_period(
    *,
    event_timestamp: str | None,
    first_event_date: str | None,
    financial_context: dict | None,
    current_balance_source: str,
    income_bucket_source: str,
    has_essentials: bool,
) -> dict:
    event_date = _coerce_iso_date(event_timestamp) or date.today()
    started_date = _coerce_iso_date(first_event_date) or event_date
    days_observed = max(1, (event_date - started_date).days + 1)
    signals = financial_context or {}
    expense_count = int(signals.get("expense_count") or 0)
    income_count = int(signals.get("income_count") or 0)
    partial_count = int(signals.get("partial_count") or 0)

    core_signal_count = 0
    if current_balance_source != "unknown":
        core_signal_count += 1
    if income_bucket_source != "unknown":
        core_signal_count += 1
    if has_essentials:
        core_signal_count += 1

    minimum_window_met = days_observed >= PERSONALIZATION_LEARNING_MIN_DAYS
    pattern_ready = expense_count >= 4
    strong_realtime_allowed = days_observed >= PERSONALIZATION_LEARNING_MAX_DAYS or (
        minimum_window_met and pattern_ready and core_signal_count >= 2
    )

    if days_observed >= PERSONALIZATION_LEARNING_MAX_DAYS:
        completion_reason = "max_window_elapsed"
    elif strong_realtime_allowed:
        completion_reason = "minimum_window_and_signal_coverage_met"
    else:
        completion_reason = "still_collecting_pattern"

    return {
        "status": "learning_complete" if strong_realtime_allowed else "still_learning",
        "window_days": {
            "minimum": PERSONALIZATION_LEARNING_MIN_DAYS,
            "maximum": PERSONALIZATION_LEARNING_MAX_DAYS,
        },
        "days_observed": days_observed,
        "minimum_days_remaining": max(0, PERSONALIZATION_LEARNING_MIN_DAYS - days_observed),
        "force_complete_days_remaining": max(0, PERSONALIZATION_LEARNING_MAX_DAYS - days_observed),
        "completion_reason": completion_reason,
        "strong_realtime_allowed": strong_realtime_allowed,
        "routine_overlay_allowed": False,
        "data_being_learned": [
            "current_balance",
            "income_bucket_or_proxy",
            "essential_priority_weights",
            "recent_expense_pattern",
        ],
        "evidence_summary": {
            "expense_signals": expense_count,
            "income_signals": income_count,
            "partial_signals": partial_count,
            "has_observed_balance": current_balance_source == "observed_balance",
            "has_income_bucket_proxy": income_bucket_source != "unknown",
            "has_essential_priorities": has_essentials,
        },
    }


def _delivery_plan(
    *,
    pressure_state: str,
    confidence_label: str,
    learning_period: dict,
    upi_open_flag: bool,
    projected_spend: float,
    daily_safe_limit: float,
) -> dict:
    over_safe_limit = daily_safe_limit > 0 and projected_spend > daily_safe_limit
    overlay_candidate = pressure_state == "high_pressure_expense" and (upi_open_flag or over_safe_limit)
    overlay_allowed = bool(learning_period.get("strong_realtime_allowed")) and overlay_candidate

    if confidence_label == "bounded_low":
        message_family = "personalized_low_confidence_notification"
    elif overlay_allowed:
        message_family = "personalized_high_pressure_overlay"
    elif learning_period.get("status") == "still_learning":
        message_family = f"personalized_learning_notification_{pressure_state}"
    else:
        message_family = f"personalized_notification_{pressure_state}"

    if overlay_allowed:
        escalation_reason = "high_pressure_after_learning"
    elif overlay_candidate:
        escalation_reason = "held_to_notification_during_learning"
    else:
        escalation_reason = "notification_first_default"

    return {
        "surface": "overlay" if overlay_allowed else "notification",
        "default_surface": "notification",
        "overlay_candidate": overlay_candidate,
        "overlay_eligible": overlay_allowed,
        "overlay_blocked_by_learning": overlay_candidate and not overlay_allowed,
        "message_family": message_family,
        "confidence_mode": "softened_for_low_confidence" if confidence_label == "bounded_low" else "bounded_guidance",
        "escalation_reason": escalation_reason,
    }


def _future_extensions() -> dict:
    return {
        "eligible_signals": [
            "location_context",
            "environment_context",
            "market_inflation",
            "deeper_expense_pattern_discovery",
            "ml_or_llm_reasoning",
        ],
        "preserve_deterministic_baseline": True,
        "baseline_fallback_required": True,
        "traceability_requirements": [
            "keep deterministic pressure_score and pressure_state available",
            "record which future signals changed the recommendation",
            "retain user-context explanation fields for every intelligent recommendation",
        ],
    }


def pressure_state_from_score(
    *,
    pressure_score: float,
    projected_spend: float,
    daily_safe_limit: float,
    protected_limit: float,
    upi_open_flag: bool,
) -> str:
    over_safe_limit = daily_safe_limit > 0 and projected_spend > daily_safe_limit
    over_protected_limit = protected_limit > 0 and projected_spend > protected_limit
    close_to_limit = daily_safe_limit > 0 and projected_spend >= (daily_safe_limit * 0.78)

    if (over_safe_limit and pressure_score >= 0.72) or (upi_open_flag and pressure_score >= 0.82):
        return "high_pressure_expense"
    if over_protected_limit or pressure_score >= 0.56:
        return "this_adds_burden"
    if close_to_limit or pressure_score >= 0.33:
        return "watch_this_expense"
    return "within_safer_limit"


def build_expense_personalization(
    *,
    amount: float,
    projected_spend: float,
    daily_safe_limit: float,
    envelope: dict,
    essential_profile: dict | None,
    financial_context: dict | None,
    upi_open_flag: bool,
    current_balance_amount: float | None = None,
    current_balance_source: str | None = None,
    recent_amounts: list[float] | None = None,
    event_timestamp: str | None = None,
    first_event_date: str | None = None,
) -> dict:
    profile = essential_profile or {}
    cohort = str(profile.get("cohort") or envelope.get("cohort") or "daily_cashflow_worker").strip() or "daily_cashflow_worker"
    protected_limit = float(envelope.get("protected_limit") or 0.0)
    weights = _goal_weights(profile)

    resolved_balance_amount, resolved_balance_source = _resolve_balance_input(
        current_balance_amount=current_balance_amount,
        current_balance_source=current_balance_source,
        daily_safe_limit=daily_safe_limit,
        projected_spend=projected_spend,
    )
    balance_score = _balance_pressure_score(
        amount=amount,
        current_balance_amount=resolved_balance_amount,
        current_balance_source=resolved_balance_source,
    )

    income_bucket, income_bucket_source, income_bucket_score = _income_bucket_input(
        cohort=cohort,
        affordability_bucket_id=profile.get("affordability_bucket_id"),
        latest_income_amount=(financial_context or {}).get("latest_income_amount"),
    )
    recent_pattern, recent_pattern_score = _recent_pattern_input(
        amount=amount,
        financial_context=financial_context,
        recent_amounts=list(recent_amounts or []),
    )
    essential_score = _essential_pressure_score(
        weights=weights,
        projected_spend=projected_spend,
        daily_safe_limit=daily_safe_limit,
        protected_limit=protected_limit,
    )
    cohort_score = _cohort_pressure_score(cohort)
    upi_score = 1.0 if upi_open_flag else 0.0

    contributions = {
        "current_balance": round(0.26 * balance_score, 4),
        "income_bucket": round(0.16 * income_bucket_score, 4),
        "essential_items": round(0.24 * essential_score, 4),
        "recent_observed_expense_pattern": round(0.22 * recent_pattern_score, 4),
        "cohort": round(0.07 * cohort_score, 4),
        "upi_open_context": round(0.05 * upi_score, 4),
    }
    pressure_score = round(clamp(sum(contributions.values())), 4)
    pressure_state = pressure_state_from_score(
        pressure_score=pressure_score,
        projected_spend=projected_spend,
        daily_safe_limit=daily_safe_limit,
        protected_limit=protected_limit,
        upi_open_flag=upi_open_flag,
    )
    confidence_score, confidence_label = _confidence_bound(
        current_balance_source=resolved_balance_source,
        income_bucket_source=income_bucket_source,
        has_essentials=bool(weights),
        recent_pattern=recent_pattern,
        daily_safe_limit=daily_safe_limit,
    )
    learning_period = _learning_period(
        event_timestamp=event_timestamp,
        first_event_date=first_event_date,
        financial_context=financial_context,
        current_balance_source=resolved_balance_source,
        income_bucket_source=income_bucket_source,
        has_essentials=bool(weights),
    )
    delivery = _delivery_plan(
        pressure_state=pressure_state,
        confidence_label=confidence_label,
        learning_period=learning_period,
        upi_open_flag=upi_open_flag,
        projected_spend=projected_spend,
        daily_safe_limit=daily_safe_limit,
    )

    top_factors = [
        {"factor": name, "contribution": contribution}
        for name, contribution in sorted(contributions.items(), key=lambda item: item[1], reverse=True)
        if contribution > 0
    ][:3]

    return {
        "contract_version": PERSONALIZATION_CONTRACT_VERSION,
        "phase": "phase_1_deterministic",
        "deterministic_baseline": True,
        "trace_version": PERSONALIZATION_TRACE_VERSION,
        "pressure_score": pressure_score,
        "pressure_state": pressure_state,
        "bounded_confidence": {
            "score": confidence_score,
            "label": confidence_label,
        },
        "learning_period": learning_period,
        "delivery": delivery,
        "inputs": {
            "cohort": cohort,
            "current_balance_amount": resolved_balance_amount,
            "current_balance_source": resolved_balance_source,
            "income_bucket": income_bucket,
            "income_bucket_source": income_bucket_source,
            "essential_items": [item["goal"] for item in weights],
            "essential_item_weights": weights,
            "recent_observed_expense_pattern": recent_pattern,
            "estimate_confidence": {
                "score": confidence_score,
                "label": confidence_label,
            },
        },
        "future_extensions": _future_extensions(),
        "explainability": {
            "top_factors": top_factors,
            "output_vocabulary": list(PRESSURE_STATES),
            "rules": [
                "Phase 1 remains deterministic and inspectable.",
                "Routine personalized guidance stays notification-first, especially during the learning period.",
                "High-pressure overlays are reserved for stronger cases after the learning period is complete.",
                "Current balance may use a policy-headroom estimate when no observed balance exists.",
                "Income bucket may come from a self-reported bucket, an affordability proxy, or a recent income signal.",
                "User-facing pressure states are bounded-confidence guidance, not certainty claims.",
            ],
        },
        "traceability": {
            "baseline_contract_version": PERSONALIZATION_CONTRACT_VERSION,
            "baseline_fields": [
                "pressure_score",
                "pressure_state",
                "bounded_confidence",
                "inputs",
                "learning_period",
                "delivery",
            ],
            "explanation_anchor": "known_user_context",
        },
    }

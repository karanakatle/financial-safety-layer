from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def compute_txn_anomaly_score(amount: float, recent_amounts: list[float]) -> float:
    if amount <= 0:
        return 0.0
    if not recent_amounts:
        return 0.45

    baseline = median(recent_amounts)
    if baseline <= 0:
        return 0.45

    ratio = amount / baseline
    if ratio <= 1.0:
        return clamp(0.35 * ratio)
    if ratio >= 3.0:
        return 1.0
    return clamp(0.35 + ((ratio - 1.0) / 2.0) * 0.65)


def compute_contextual_scores(
    *,
    participant_id: str,
    amount: float,
    projected_spend: float,
    daily_safe_limit: float,
    timestamp: str,
    upi_open_flag: bool,
    warmup_active: bool,
    goal_protection_ratio: float,
    non_essential_confidence: float,
    pilot_storage,
) -> dict:
    now_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    since_10m = (now_dt - timedelta(minutes=10)).isoformat()
    since_24h = (now_dt - timedelta(hours=24)).isoformat()

    recent_amounts = pilot_storage.recent_spend_amounts(participant_id, limit=20)
    txn_anomaly_score = compute_txn_anomaly_score(amount, recent_amounts)
    rapid_txn_flag = pilot_storage.count_recent_spend_events(participant_id, since_10m) >= 2
    recent_dismissals_24h = pilot_storage.count_recent_dismissals(participant_id, since_24h)

    spend_ratio = (projected_spend / daily_safe_limit) if daily_safe_limit > 0 else 0.0
    protected_limit = daily_safe_limit * (1.0 - goal_protection_ratio) if daily_safe_limit > 0 else 0.0
    goal_pressure_score = 0.0
    if protected_limit > 0:
        goal_pressure_score = clamp((projected_spend - protected_limit) / max(daily_safe_limit * 0.35, 1.0))
    risk_score = clamp(
        (0.45 * clamp(spend_ratio / 1.6))
        + (0.25 * txn_anomaly_score)
        + (0.15 * (1.0 if rapid_txn_flag else 0.0))
        + (0.10 * clamp(recent_dismissals_24h / 4.0))
        + (0.05 * (1.0 if upi_open_flag else 0.0))
        + (0.10 * goal_pressure_score)
        + (0.10 * clamp(non_essential_confidence))
    )

    confidence_score = clamp(
        0.45
        + (0.3 * clamp(len(recent_amounts) / 12.0))
        + (0.15 if amount > 0 else 0.0)
        + (0.1 if daily_safe_limit > 0 else 0.0)
        - (0.15 if warmup_active else 0.0)
    )

    if risk_score >= 0.85:
        tone_selected = "hard"
    elif risk_score >= 0.55:
        tone_selected = "firm"
    else:
        tone_selected = "soft"

    if recent_dismissals_24h >= 4 and risk_score < 0.8:
        frequency_bucket = "suppressed"
    elif risk_score >= 0.72:
        frequency_bucket = "hard"
    else:
        frequency_bucket = "soft"

    pause_seconds = 5 if upi_open_flag and risk_score >= 0.9 else 0

    return {
        "spend_ratio": round(spend_ratio, 4),
        "txn_anomaly_score": round(txn_anomaly_score, 4),
        "hour_of_day": now_dt.hour,
        "rapid_txn_flag": rapid_txn_flag,
        "upi_open_flag": upi_open_flag,
        "recent_dismissals_24h": recent_dismissals_24h,
        "risk_score": round(risk_score, 4),
        "confidence_score": round(confidence_score, 4),
        "goal_pressure_score": round(goal_pressure_score, 4),
        "non_essential_confidence": round(non_essential_confidence, 4),
        "tone_selected": tone_selected,
        "frequency_bucket": frequency_bucket,
        "pause_seconds": pause_seconds,
    }


def recent_financial_context(*, participant_id: str, pilot_storage, limit: int = 10) -> dict:
    signals = pilot_storage.recent_financial_signals(participant_id, limit=limit)
    latest_income = next(
        (signal for signal in signals if signal.get("signal_type") == "income" and signal.get("amount") is not None),
        None,
    )
    latest_expense = next(
        (signal for signal in signals if signal.get("signal_type") == "expense" and signal.get("amount") is not None),
        None,
    )
    partial_count = sum(1 for signal in signals if signal.get("signal_type") == "partial")
    income_count = sum(1 for signal in signals if signal.get("signal_type") == "income")
    expense_count = sum(1 for signal in signals if signal.get("signal_type") == "expense")

    return {
        "signals": signals,
        "income_count": income_count,
        "expense_count": expense_count,
        "partial_count": partial_count,
        "latest_income_amount": float(latest_income["amount"]) if latest_income else None,
        "latest_expense_amount": float(latest_expense["amount"]) if latest_expense else None,
    }

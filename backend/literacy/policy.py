from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from statistics import median, pstdev

from backend.literacy.context import clamp


def policy_for_participant(*, participant_id: str, pilot_storage, literacy_policy) -> tuple[float, float]:
    policy = pilot_storage.get_participant_policy(participant_id)
    if not policy:
        return literacy_policy.daily_safe_limit, literacy_policy.warning_ratio
    return float(policy["daily_safe_limit"]), float(policy["warning_ratio"])


def resolve_experiment_variant(*, participant_id: str, experiment_name: str, pilot_storage) -> str:
    existing = pilot_storage.get_experiment_assignment(participant_id, experiment_name)
    if existing:
        return str(existing.get("variant") or "adaptive")

    digest = hashlib.sha256(f"{participant_id}:{experiment_name}".encode("utf-8")).hexdigest()
    variant = "adaptive" if int(digest[:8], 16) % 2 == 0 else "static_baseline"
    pilot_storage.upsert_experiment_assignment(
        participant_id=participant_id,
        experiment_name=experiment_name,
        variant=variant,
        assigned_at=datetime.utcnow().isoformat(),
    )
    return variant


def auto_recalibrate_policy(*, participant_id: str, pilot_storage, literacy_policy) -> bool:
    spends = pilot_storage.recent_daily_spends(participant_id, limit=7)
    if len(spends) < 5:
        return False

    base = median(spends)
    target_limit = max(800.0, min(10000.0, round(base * 1.15, 2)))
    mean = (sum(spends) / len(spends)) if spends else 0.0
    volatility = (pstdev(spends) / mean) if mean > 0 else 0.0
    target_warning_ratio = 0.92 if volatility <= 0.25 else 0.9 if volatility <= 0.5 else 0.87

    feature_summary = pilot_storage.recent_alert_feature_summary(participant_id, limit=50)
    if feature_summary["sample_size"] >= 5:
        avg_risk = feature_summary["avg_risk_score"]
        avg_conf = feature_summary["avg_confidence_score"]
        suppressed_rate = (
            feature_summary["suppressed_count"] / feature_summary["sample_size"]
            if feature_summary["sample_size"] > 0
            else 0.0
        )
        hard_rate = (
            feature_summary["hard_count"] / feature_summary["sample_size"]
            if feature_summary["sample_size"] > 0
            else 0.0
        )

        if avg_risk >= 0.75 and avg_conf >= 0.6:
            target_warning_ratio -= 0.03
        if suppressed_rate >= 0.35:
            target_warning_ratio += 0.02
        if hard_rate >= 0.3:
            target_warning_ratio -= 0.02

    since_7d = (datetime.utcnow() - timedelta(days=7)).isoformat()
    dismissals_7d = pilot_storage.count_recent_dismissals(participant_id, since_7d)
    if dismissals_7d >= 8:
        target_warning_ratio += 0.02
    elif dismissals_7d >= 4:
        target_warning_ratio += 0.01
    target_warning_ratio = clamp(target_warning_ratio, 0.82, 0.95)

    policy = pilot_storage.get_participant_policy(participant_id)
    if policy:
        current_limit = float(policy["daily_safe_limit"])
        warning_ratio = float(policy["warning_ratio"])
    else:
        current_limit = literacy_policy.daily_safe_limit
        warning_ratio = literacy_policy.warning_ratio

    smoothed_limit = round((0.7 * current_limit) + (0.3 * target_limit), 2)
    smoothed_warning_ratio = round((0.7 * warning_ratio) + (0.3 * target_warning_ratio), 3)
    return pilot_storage.upsert_auto_participant_policy(
        participant_id=participant_id,
        daily_safe_limit=smoothed_limit,
        warning_ratio=smoothed_warning_ratio,
        updated_at=datetime.utcnow().isoformat(),
    )

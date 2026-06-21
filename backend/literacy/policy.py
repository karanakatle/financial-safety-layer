from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from statistics import median, pstdev

from backend.literacy.context import clamp


_MONEY_SETUP_MIN_WARNING_RATIO = 0.82
_MONEY_SETUP_MAX_WARNING_RATIO = 0.95
_MAX_MONEY_SETUP_RATIO_DELTA = -0.065
_DAILY_CASHFLOW_BUCKET_RATIO_DELTAS = {
    "below_250": -0.055,
    "250_499": -0.045,
    "500_749": -0.035,
    "750_999": -0.02,
    "1000_1499": -0.01,
}
_WOMEN_LED_HOUSEHOLD_BUCKET_RATIO_DELTAS = {
    "below_6000": -0.045,
    "6000_9999": -0.03,
    "10000_13999": -0.015,
}
_HIGH_PRESSURE_ESSENTIALS = {
    "ration",
    "rent",
    "medicine",
    "school",
    "loan_repayment",
    "cooking_fuel",
    "family_care",
}
_SUPPORTED_MONEY_SETUP_COHORTS = {"daily_cashflow_worker", "women_led_household"}
_AI_EXPLANATION_POLICY_CONTRACT = {
    "stage": "future_guarded_ai_layer",
    "purpose": "plain_language_explanation_only",
    "requires_user_consent": True,
    "input_policy": "redacted_minimized_context_only",
    "output_policy": "safety_filtered_before_display",
    "uncertainty_policy": "verify_through_official_source",
    "prohibited_outputs": [
        "loan_recommendation",
        "investment_recommendation",
        "lender_recommendation",
        "card_recommendation",
        "product_recommendation",
        "guaranteed_return_claim",
        "regulated_financial_advice",
    ],
    "allowed_outputs": [
        "risk_explanation",
        "why_warning_appeared",
        "safe_next_step",
        "official_source_verification",
        "non_advisory_disclaimer",
    ],
}


def _no_money_setup_sensitivity_adjustment(*, applies_to: str = "cashflow_thresholds_only") -> dict:
    return {
        "applied": False,
        "warning_ratio_delta": 0.0,
        "reason_codes": [],
        "applies_to": applies_to,
    }


def ai_explanation_policy_contract() -> dict:
    """Policy contract for the future guarded AI explanation layer."""
    return {
        **_AI_EXPLANATION_POLICY_CONTRACT,
        "prohibited_outputs": list(_AI_EXPLANATION_POLICY_CONTRACT["prohibited_outputs"]),
        "allowed_outputs": list(_AI_EXPLANATION_POLICY_CONTRACT["allowed_outputs"]),
    }


def _is_setup_complete(profile: dict | None) -> bool:
    return bool(profile) and not bool((profile or {}).get("setup_skipped"))


def money_setup_sensitivity_adjustment(profile: dict | None) -> dict:
    """Return bounded threshold adjustment from rough Money Setup Lite context only."""
    if not _is_setup_complete(profile):
        return _no_money_setup_sensitivity_adjustment()

    cohort = str((profile or {}).get("cohort") or "").strip().lower()
    if cohort not in _SUPPORTED_MONEY_SETUP_COHORTS:
        return _no_money_setup_sensitivity_adjustment()

    bucket = str((profile or {}).get("affordability_bucket_id") or "").strip().lower()
    essentials = {
        str(goal or "").strip().lower()
        for goal in list((profile or {}).get("active_priority_essentials") or (profile or {}).get("essential_goals") or [])
        if str(goal or "").strip()
    }
    reason_codes: list[str] = []
    delta = 0.0

    if cohort == "daily_cashflow_worker":
        delta -= 0.005
        reason_codes.append("daily_cashflow_worker")
        bucket_delta = _DAILY_CASHFLOW_BUCKET_RATIO_DELTAS.get(bucket, 0.0)
        if bucket_delta:
            delta += bucket_delta
            reason_codes.append(f"daily_bucket:{bucket}")
    elif cohort == "women_led_household":
        delta -= 0.01
        reason_codes.append("women_led_household")
        bucket_delta = _WOMEN_LED_HOUSEHOLD_BUCKET_RATIO_DELTAS.get(bucket, 0.0)
        if bucket_delta:
            delta += bucket_delta
            reason_codes.append(f"household_bucket:{bucket}")

    pressure_essentials = essentials & _HIGH_PRESSURE_ESSENTIALS
    if pressure_essentials:
        delta -= min(0.015, 0.004 * len(pressure_essentials))
        reason_codes.append("high_pressure_essentials")

    bounded_delta = round(max(delta, _MAX_MONEY_SETUP_RATIO_DELTA), 3)
    return {
        "applied": bounded_delta < 0,
        "warning_ratio_delta": bounded_delta,
        "reason_codes": reason_codes if bounded_delta < 0 else [],
        "applies_to": "cashflow_yellow_red_thresholds_only",
    }


def policy_details_for_participant(*, participant_id: str, pilot_storage, literacy_policy) -> dict:
    policy = pilot_storage.get_participant_policy(participant_id)
    if policy:
        daily_safe_limit = float(policy["daily_safe_limit"])
        warning_ratio = float(policy["warning_ratio"])
        source = "custom"
    else:
        daily_safe_limit = float(literacy_policy.daily_safe_limit)
        warning_ratio = float(literacy_policy.warning_ratio)
        source = "default"

    profile = None
    if hasattr(pilot_storage, "get_essential_goal_profile"):
        profile = pilot_storage.get_essential_goal_profile(participant_id)
    adjustment = money_setup_sensitivity_adjustment(profile)
    if adjustment["applied"]:
        adjusted_warning_ratio = round(
            clamp(
                warning_ratio + float(adjustment["warning_ratio_delta"]),
                min(_MONEY_SETUP_MIN_WARNING_RATIO, warning_ratio),
                _MONEY_SETUP_MAX_WARNING_RATIO,
            ),
            3,
        )
        if adjusted_warning_ratio < warning_ratio:
            adjustment = {
                **adjustment,
                "warning_ratio_delta": round(adjusted_warning_ratio - warning_ratio, 3),
            }
            warning_ratio = adjusted_warning_ratio
            source = f"{source}+money_setup_lite"
        else:
            adjustment = _no_money_setup_sensitivity_adjustment(
                applies_to="cashflow_yellow_red_thresholds_only"
            )

    return {
        "daily_safe_limit": round(daily_safe_limit, 2),
        "warning_ratio": warning_ratio,
        "source": source,
        "money_setup_sensitivity": adjustment,
    }


def public_money_setup_sensitivity(adjustment: dict | None) -> dict:
    """Expose non-sensitive sensitivity metadata for client explanations."""
    applied = bool((adjustment or {}).get("applied"))
    applies_to = str((adjustment or {}).get("applies_to") or "cashflow_thresholds_only")
    return {
        "applied": applied,
        "context": "rough_money_setup_context" if applied else "none",
        "direction": "more_cautious" if applied else "none",
        "applies_to": applies_to,
    }


def policy_for_participant(*, participant_id: str, pilot_storage, literacy_policy) -> tuple[float, float]:
    details = policy_details_for_participant(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=literacy_policy,
    )
    return float(details["daily_safe_limit"]), float(details["warning_ratio"])


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

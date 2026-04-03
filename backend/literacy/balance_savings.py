from __future__ import annotations

from datetime import datetime, time, timedelta

from .context import clamp


BALANCE_SAVINGS_CONTRACT_VERSION = "balance_savings_v1"
BALANCE_SOURCE_SELF_REPORTED = "self_reported"
SUPPORTED_BALANCE_SOURCES = (
    BALANCE_SOURCE_SELF_REPORTED,
    "estimated",
    "verified",
)
SAVINGS_BUCKETS = (
    (100.0, 0.0, "below_100"),
    (300.0, 20.0, "100_299"),
    (700.0, 50.0, "300_699"),
    (1500.0, 100.0, "700_1499"),
    (3000.0, 150.0, "1500_2999"),
    (float("inf"), 200.0, "3000_plus"),
)


def _coerce_datetime(value: str | None) -> datetime:
    if value:
        normalized = str(value).strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            pass
    return datetime.utcnow()


def _day_start(at: datetime) -> datetime:
    return datetime.combine(at.date(), time.min, tzinfo=at.tzinfo)


def current_balance_contract(record: dict | None) -> dict | None:
    if not record:
        return None
    return {
        "amount": round(float(record.get("amount") or 0.0), 2),
        "source": str(record.get("source") or BALANCE_SOURCE_SELF_REPORTED),
        "captured_at": str(record.get("captured_at") or ""),
        "updated_at": str(record.get("updated_at") or ""),
        "source_semantics": {
            "self_reported": "user_entered_ground_truth_for_that_moment",
            "estimated": "system_estimated_from_observed_signals",
            "verified": "future_regulated_or_partner_verified_balance",
        },
    }


def estimate_end_of_day_balance(
    *,
    balance_record: dict | None,
    signals_since_baseline: list[dict],
    as_of_timestamp: str | None,
) -> dict:
    as_of = _coerce_datetime(as_of_timestamp)
    if not balance_record:
        return {
            "contract_version": BALANCE_SAVINGS_CONTRACT_VERSION,
            "as_of_timestamp": as_of.isoformat(),
            "opening_balance_for_day": None,
            "estimated_closing_balance": None,
            "observed_credits_today": 0.0,
            "observed_debits_today": 0.0,
            "observed_net_today": 0.0,
            "positive_day_surplus": 0.0,
            "confidence": {"score": 0.12, "label": "bounded_low"},
            "visibility_state": "no_balance_baseline",
            "signal_summary": {
                "confirmed_credit_count": 0,
                "confirmed_debit_count": 0,
                "partial_signal_count": 0,
                "signals_used": 0,
            },
            "explanation": "No self-reported balance baseline is available yet.",
        }

    baseline = current_balance_contract(balance_record)
    captured_at = _coerce_datetime(baseline["captured_at"])
    start_of_day = _day_start(as_of)

    credits_before_today = 0.0
    debits_before_today = 0.0
    credits_today = 0.0
    debits_today = 0.0
    confirmed_credit_count = 0
    confirmed_debit_count = 0
    partial_signal_count = 0

    for signal in signals_since_baseline:
        signal_type = str(signal.get("signal_type") or "")
        timestamp = _coerce_datetime(signal.get("timestamp"))
        amount = float(signal.get("amount") or 0.0)
        confidence = str(signal.get("signal_confidence") or "confirmed")
        if confidence == "partial" or signal_type == "partial":
            partial_signal_count += 1
            continue
        if signal_type == "income":
            if timestamp < start_of_day:
                credits_before_today += amount
            else:
                credits_today += amount
                confirmed_credit_count += 1
        elif signal_type == "expense":
            if timestamp < start_of_day:
                debits_before_today += amount
            else:
                debits_today += amount
                confirmed_debit_count += 1

    opening_balance_for_day = round(
        float(baseline["amount"]) + credits_before_today - debits_before_today,
        2,
    )
    estimated_closing_balance = round(opening_balance_for_day + credits_today - debits_today, 2)
    observed_net_today = round(credits_today - debits_today, 2)
    positive_day_surplus = round(max(observed_net_today, 0.0), 2)

    baseline_age_days = max(0, (as_of.date() - captured_at.date()).days)
    if confirmed_credit_count > 0 and confirmed_debit_count > 0 and partial_signal_count == 0:
        visibility_state = "balanced_observed"
        visibility_bonus = 0.24
    elif (confirmed_credit_count > 0 or confirmed_debit_count > 0) and partial_signal_count == 0:
        visibility_state = "one_sided_observed"
        visibility_bonus = 0.14
    elif partial_signal_count > 0 and (confirmed_credit_count > 0 or confirmed_debit_count > 0):
        visibility_state = "mixed_partial"
        visibility_bonus = 0.1
    elif partial_signal_count > 0:
        visibility_state = "partial_only"
        visibility_bonus = 0.05
    else:
        visibility_state = "quiet_day"
        visibility_bonus = 0.04

    recency_bonus = 0.22 if baseline_age_days == 0 else 0.14 if baseline_age_days <= 2 else 0.06 if baseline_age_days <= 7 else 0.0
    signal_bonus = 0.08 if (confirmed_credit_count + confirmed_debit_count) >= 2 else 0.04 if (confirmed_credit_count + confirmed_debit_count) == 1 else 0.0
    penalty = 0.12 if partial_signal_count > 0 else 0.0
    confidence_score = clamp(0.18 + 0.28 + recency_bonus + visibility_bonus + signal_bonus - penalty)
    confidence_label = "bounded_high" if confidence_score >= 0.72 else "bounded_medium" if confidence_score >= 0.52 else "bounded_low"

    if visibility_state == "balanced_observed":
        explanation = "Opening balance was adjusted with both observed credits and debits for the day."
    elif visibility_state == "one_sided_observed":
        explanation = "Only one side of today’s cashflow was observed, so the balance estimate stays soft."
    elif visibility_state in {"mixed_partial", "partial_only"}:
        explanation = "Some of today’s signals were partial, so the estimate is useful for guidance but not exact."
    else:
        explanation = "No same-day financial movement was observed after the latest reported balance."

    return {
        "contract_version": BALANCE_SAVINGS_CONTRACT_VERSION,
        "as_of_timestamp": as_of.isoformat(),
        "opening_balance_for_day": round(opening_balance_for_day, 2),
        "estimated_closing_balance": round(estimated_closing_balance, 2),
        "observed_credits_today": round(credits_today, 2),
        "observed_debits_today": round(debits_today, 2),
        "observed_net_today": observed_net_today,
        "positive_day_surplus": positive_day_surplus,
        "confidence": {
            "score": round(confidence_score, 4),
            "label": confidence_label,
        },
        "visibility_state": visibility_state,
        "signal_summary": {
            "confirmed_credit_count": confirmed_credit_count,
            "confirmed_debit_count": confirmed_debit_count,
            "partial_signal_count": partial_signal_count,
            "signals_used": confirmed_credit_count + confirmed_debit_count,
        },
        "explanation": explanation,
    }


def _suggested_savings_amount(positive_day_surplus: float) -> tuple[float, str]:
    for upper, amount, bucket_id in SAVINGS_BUCKETS:
        if positive_day_surplus < upper:
            return amount, bucket_id
    return 200.0, "3000_plus"


def build_savings_nudge(
    *,
    cohort: str,
    estimate: dict,
    language: str,
) -> dict:
    if estimate.get("opening_balance_for_day") is None:
        return {
            "contract_version": BALANCE_SAVINGS_CONTRACT_VERSION,
            "decision_state": "missing_balance_baseline",
            "suggested_amount": 0.0,
            "bucket_id": "none",
            "title": "Balance needed first" if language == "en" else "पहले बैलेंस चाहिए",
            "message": (
                "Add your current balance first to start receiving end-of-day savings nudges."
                if language == "en"
                else "दिन के अंत की बचत सलाह पाने के लिए पहले अपना वर्तमान बैलेंस जोड़ें।"
            ),
            "delivery": {
                "channel": "notification",
                "surface": "notification_only",
                "channel_agnostic": True,
                "future_channels": ["whatsapp"],
                "future_channels_opt_in_required": True,
            },
            "copy_tone": "calm",
            "shared_phase_1_logic": True,
            "cohort": cohort,
            "confidence_bound": dict(estimate.get("confidence") or {}),
            "why_this_nudge": estimate.get("explanation", ""),
            "next_best_action": (
                "Enter a self-reported balance when you are ready."
                if language == "en"
                else "जब तैयार हों, अपना स्वयं बताया बैलेंस दर्ज करें।"
            ),
            "extension_hooks": {
                "future_balance_sources": list(SUPPORTED_BALANCE_SOURCES),
                "future_tuning_factors": [
                    "inflation",
                    "location",
                    "recurring_patterns",
                    "household_context",
                    "user_history",
                ],
                "deterministic_table_preserved": True,
            },
            "should_notify": False,
        }

    positive_day_surplus = float(estimate.get("positive_day_surplus") or 0.0)
    confidence = dict(estimate.get("confidence") or {})
    confidence_label = str(confidence.get("label") or "bounded_low")
    visibility_state = str(estimate.get("visibility_state") or "quiet_day")
    suggested_amount, bucket_id = _suggested_savings_amount(positive_day_surplus)
    can_ask_to_save = positive_day_surplus >= 100.0 and confidence_label in {"bounded_medium", "bounded_high"}
    visibility_softened = visibility_state in {"one_sided_observed", "mixed_partial", "partial_only"}

    if can_ask_to_save and suggested_amount > 0:
        decision_state = "suggest_save"
        title = "Small savings nudge" if language == "en" else "छोटी बचत का सुझाव"
        if confidence_label == "bounded_high" and not visibility_softened:
            message = (
                f"Today looks a little positive. If it feels doable, move Rs {int(suggested_amount)} aside tonight."
                if language == "en"
                else f"आज का दिन थोड़ा सकारात्मक दिख रहा है। अगर संभव लगे तो रात तक ₹{int(suggested_amount)} अलग रख दें।"
            )
        else:
            message = (
                f"Today may have left a little room. If it feels manageable, try saving around Rs {int(suggested_amount)}."
                if language == "en"
                else f"आज थोड़ा पैसा बचा हो सकता है। अगर ठीक लगे तो लगभग ₹{int(suggested_amount)} बचाने की कोशिश करें।"
            )
    elif positive_day_surplus > 0:
        decision_state = "positive_no_ask"
        title = "Good day, no pressure" if language == "en" else "अच्छा दिन, बिना दबाव"
        message = (
            "Today looks a little better. No savings ask for now, but this is a good sign to build on."
            if language == "en"
            else "आज का दिन थोड़ा बेहतर दिख रहा है। अभी बचत का दबाव नहीं है, लेकिन यह एक अच्छा संकेत है।"
        )
    else:
        decision_state = "flat_or_negative"
        title = "Try again tomorrow" if language == "en" else "कल फिर कोशिश करें"
        message = (
            "Today looked tight. No savings ask tonight. Protect what you need first and try again tomorrow."
            if language == "en"
            else "आज का दिन तंग दिखा। आज बचत का कोई दबाव नहीं है। पहले जरूरी जरूरतें संभालें, फिर कल कोशिश करें।"
        )

    return {
        "contract_version": BALANCE_SAVINGS_CONTRACT_VERSION,
        "decision_state": decision_state,
        "suggested_amount": round(suggested_amount if can_ask_to_save else 0.0, 2),
        "bucket_id": bucket_id,
        "title": title,
        "message": message,
        "delivery": {
            "channel": "notification",
            "surface": "notification_only",
            "channel_agnostic": True,
            "future_channels": ["whatsapp"],
            "future_channels_opt_in_required": True,
        },
        "copy_tone": "calm",
        "shared_phase_1_logic": True,
        "cohort": cohort,
        "confidence_bound": confidence,
        "why_this_nudge": estimate.get("explanation", ""),
        "next_best_action": (
            "Keep the amount small and optional."
            if decision_state == "suggest_save" and language == "en"
            else "राशि छोटी और वैकल्पिक रखें।"
            if decision_state == "suggest_save"
            else "No pressure today. The app can check again tomorrow."
            if language == "en"
            else "आज कोई दबाव नहीं। ऐप कल फिर देख सकता है।"
        ),
        "extension_hooks": {
            "future_balance_sources": list(SUPPORTED_BALANCE_SOURCES),
            "future_tuning_factors": [
                "inflation",
                "location",
                "recurring_patterns",
                "household_context",
                "user_history",
            ],
            "deterministic_table_preserved": True,
        },
        "should_notify": True,
    }


def build_balance_savings_response(
    *,
    participant_id: str,
    cohort: str,
    language: str,
    current_balance: dict | None,
    signals_since_baseline: list[dict],
    as_of_timestamp: str | None,
) -> dict:
    balance = current_balance_contract(current_balance)
    estimate = estimate_end_of_day_balance(
        balance_record=current_balance,
        signals_since_baseline=signals_since_baseline,
        as_of_timestamp=as_of_timestamp,
    )
    nudge = build_savings_nudge(
        cohort=cohort,
        estimate=estimate,
        language=language,
    )
    return {
        "participant_id": participant_id,
        "language": language,
        "current_balance": balance,
        "estimate": estimate,
        "nudge": nudge,
        "future_extension_hooks": {
            "verified_balance_sources_supported": list(SUPPORTED_BALANCE_SOURCES),
            "delivery_channels_supported": ["notification", "whatsapp"],
            "history_compatible": True,
        },
    }

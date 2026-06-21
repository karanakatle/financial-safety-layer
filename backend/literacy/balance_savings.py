from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from math import isfinite

from .context import clamp


BALANCE_SAVINGS_CONTRACT_VERSION = "balance_savings_v1"
BORROWING_PRESSURE_CONTRACT_VERSION = "borrowing_pressure_v1"
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
HIGH_PRESSURE_ESSENTIALS = {
    "ration",
    "rent",
    "electricity",
    "water",
    "medicine",
    "school",
    "transport",
    "loan_repayment",
    "cooking_fuel",
    "family_care",
}
BORROWING_PERIOD_MONTH_FACTORS = {
    "daily": 30.0,
    "weekly": 52 / 12,
    "monthly": 1.0,
}
ESSENTIAL_CATEGORY_KEYWORDS = {
    "ration": {
        "ration",
        "food",
        "kirana",
        "grocery",
        "groceries",
        "bhaji",
        "sabzi",
        "vegetable",
        "vegetables",
        "rice",
        "dal",
        "atta",
        "milk",
        "dudh",
        "anna",
        "jevan",
        "khana",
        "khaana",
        "rashan",
        "राशन",
        "किराणा",
        "भाजी",
        "दूध",
        "अन्न",
        "जेवण",
        "खाना",
    },
    "rent": {
        "rent",
        "house",
        "house_rent",
        "room_rent",
        "ghar",
        "kiraya",
        "bhada",
        "घर",
        "किराया",
        "भाडे",
        "भाडं",
        "भाडा",
    },
    "electricity": {"electricity", "power", "bijli", "light_bill", "वीज", "बिजली"},
    "water": {"water", "pani", "jal", "पाणी", "पानी"},
    "cooking_fuel": {"cooking_fuel", "fuel", "gas", "cylinder", "lpg", "गॅस", "गैस", "सिलेंडर"},
    "mobile_recharge": {"mobile", "phone", "recharge", "data", "airtel", "jio", "vi", "मोबाइल", "रिचार्ज"},
    "medicine": {
        "medical",
        "medicine",
        "medicines",
        "doctor",
        "hospital",
        "clinic",
        "dawai",
        "dava",
        "health",
        "दवाई",
        "दवा",
        "औषध",
        "डॉक्टर",
        "हॉस्पिटल",
    },
    "school": {"school", "education", "fees", "school_fees", "tuition", "college", "books", "uniform", "शाळा", "स्कूल", "फीस", "शिक्षण"},
    "transport": {"transport", "travel", "bus", "train", "auto", "cab", "fare", "commute", "petrol", "diesel", "cng", "प्रवास", "बस", "पेट्रोल", "डिझेल"},
    "loan_repayment": {"loan_repayment", "emi", "loan", "debt", "repayment", "borrow", "borrowing", "kist", "kisth", "kishta", "karz", "udhar", "कर्ज", "उधार", "किस्त", "हप्ता"},
    "work_inputs": {"work_inputs", "tools", "stock", "material", "business", "shop", "inventory", "wholesale", "काम", "सामान", "माल"},
    "family_care": {"family_care", "family", "child", "children", "parents", "elder", "baby", "bachcha", "bacha", "parivar", "परिवार", "कुटुंब", "बच्चा"},
}


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


def _optional_nonnegative_amount(value: float | int | str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(amount) or amount < 0:
        return None
    return round(amount, 2)


def _required_positive_amount(value: float | int | str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(amount) or amount <= 0:
        return None
    return round(amount, 2)


def _normalized_borrowing_period(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in BORROWING_PERIOD_MONTH_FACTORS else "monthly"


def _monthly_amount(amount: float | None, period: str) -> float | None:
    if amount is None:
        return None
    return round(amount * BORROWING_PERIOD_MONTH_FACTORS[_normalized_borrowing_period(period)], 2)


def _normalized_essential_text(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _essential_fragments(value: str) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    fragments = [raw]
    fragments.extend(
        part
        for part in re.split(r"[,;/|+&]|\band\b|\baur\b|\bani\b|\bor\b|\bya\b|\n", raw, flags=re.IGNORECASE)
        if part.strip()
    )
    return fragments


def _canonical_essentials_from_value(value: str) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    for fragment in _essential_fragments(value):
        normalized = _normalized_essential_text(fragment)
        tokens = {token for token in re.split(r"[_\s]+", normalized) if token}
        for category, keywords in ESSENTIAL_CATEGORY_KEYWORDS.items():
            found = False
            for keyword in keywords | {category}:
                keyword_normalized = _normalized_essential_text(keyword)
                keyword_tokens = {token for token in re.split(r"[_\s]+", keyword_normalized) if token}
                if (
                    normalized == keyword_normalized
                    or keyword_normalized in tokens
                    or bool(keyword_tokens and keyword_tokens <= tokens)
                ):
                    found = True
                    break
            if found and category not in seen:
                matches.append(category)
                seen.add(category)
    return matches


def _normalized_essentials(essential_expenses: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in list(essential_expenses or []):
        for value in _canonical_essentials_from_value(str(item or "")):
            if value and value not in seen:
                normalized.append(value)
                seen.add(value)
    return normalized


def build_borrowing_pressure_check(
    *,
    repayment_amount: float,
    repayment_period: str = "monthly",
    rough_income_amount: float | None,
    income_period: str = "monthly",
    essential_expense_amount: float | None = None,
    essential_expense_period: str = "monthly",
    essential_expenses: list[str] | None = None,
    language: str = "en",
) -> dict:
    language = _normalized_borrowing_language(language)
    repayment = _required_positive_amount(repayment_amount)
    rough_income = _optional_nonnegative_amount(rough_income_amount)
    essentials_amount = _optional_nonnegative_amount(essential_expense_amount)
    normalized_repayment_period = _normalized_borrowing_period(repayment_period)
    normalized_income_period = _normalized_borrowing_period(income_period)
    normalized_essential_expense_period = _normalized_borrowing_period(essential_expense_period)
    monthly_repayment = _monthly_amount(repayment, normalized_repayment_period)
    monthly_rough_income = _monthly_amount(rough_income, normalized_income_period)
    monthly_essentials_amount = _monthly_amount(essentials_amount, normalized_essential_expense_period)
    essentials = _normalized_essentials(essential_expenses)
    if essentials and monthly_essentials_amount == 0:
        essentials_amount = None
        monthly_essentials_amount = None
    pressure_essentials = sorted(set(essentials) & HIGH_PRESSURE_ESSENTIALS)
    period_assumptions = _borrowing_period_assumptions(
        repayment_period=normalized_repayment_period,
        income_period=normalized_income_period,
        essential_expense_period=normalized_essential_expense_period,
    )

    if repayment is None or monthly_repayment is None:
        return _borrowing_pressure_insufficient_response(
            decision_state="missing_repayment_amount",
            repayment_amount=None,
            rough_income_amount=rough_income,
            monthly_repayment_amount=None,
            monthly_rough_income_amount=monthly_rough_income,
            essential_expense_amount=essentials_amount,
            monthly_essential_expense_amount=monthly_essentials_amount,
            essential_expenses=essentials,
            period_assumptions=period_assumptions,
            language=language,
            reason="repayment",
        )

    if not monthly_rough_income or monthly_rough_income <= 0:
        return _borrowing_pressure_insufficient_response(
            decision_state="missing_rough_income",
            repayment_amount=repayment,
            rough_income_amount=None,
            monthly_repayment_amount=monthly_repayment,
            monthly_rough_income_amount=None,
            essential_expense_amount=essentials_amount,
            monthly_essential_expense_amount=monthly_essentials_amount,
            essential_expenses=essentials,
            period_assumptions=period_assumptions,
            language=language,
            reason="rough_income",
        )

    repayment_ratio = monthly_repayment / monthly_rough_income if monthly_rough_income > 0 else None
    essential_ratio = (
        (monthly_essentials_amount / monthly_rough_income)
        if monthly_essentials_amount is not None and monthly_rough_income > 0
        else None
    )
    buffer_after_essentials = (
        round(monthly_rough_income - monthly_repayment - monthly_essentials_amount, 2)
        if monthly_essentials_amount is not None
        else None
    )
    essentials_pressure = len(pressure_essentials) >= 3

    if (
        repayment_ratio >= 0.35
        or (buffer_after_essentials is not None and buffer_after_essentials < 0)
        or (repayment_ratio >= 0.25 and essentials_pressure)
        or (essential_ratio is not None and essential_ratio >= 0.65 and repayment_ratio >= 0.25)
    ):
        pressure_level = "high"
    elif (
        repayment_ratio >= 0.15
        or essentials_pressure
        or (buffer_after_essentials is not None and buffer_after_essentials < monthly_rough_income * 0.15)
    ):
        pressure_level = "medium"
    else:
        pressure_level = "low"

    limited_by_missing_essentials = essentials_amount is None
    if limited_by_missing_essentials and pressure_level == "low":
        pressure_level = "medium"

    confidence_score = 0.72 if essentials_amount is not None else 0.58
    confidence_label = "bounded_high" if confidence_score >= 0.7 else "bounded_medium"
    return {
        "contract_version": BORROWING_PRESSURE_CONTRACT_VERSION,
        "decision_state": "repayment_pressure_checked_limited" if limited_by_missing_essentials else "repayment_pressure_checked",
        "pressure_level": pressure_level,
        "repayment_amount": repayment,
        "rough_income_amount": rough_income,
        "essential_expense_amount": essentials_amount,
        "monthly_repayment_amount": monthly_repayment,
        "monthly_rough_income_amount": monthly_rough_income,
        "monthly_essential_expense_amount": monthly_essentials_amount,
        "period_assumptions": period_assumptions,
        "essential_expenses": essentials,
        "repayment_to_income_ratio": round(repayment_ratio, 4),
        "essential_expense_ratio": round(essential_ratio, 4) if essential_ratio is not None else None,
        "post_repayment_essential_buffer": buffer_after_essentials,
        "confidence": {"score": confidence_score, "label": confidence_label},
        "title": _borrowing_pressure_title(pressure_level, language),
        "message": _borrowing_pressure_message(pressure_level, language),
        "why_this_check": _borrowing_pressure_why(
            pressure_level=pressure_level,
            repayment_ratio=repayment_ratio,
            essentials_amount=essentials_amount,
            buffer_after_essentials=buffer_after_essentials,
            language=language,
        ),
        "next_best_action": _borrowing_pressure_next_action(pressure_level, language),
        "suggested_next_step": (
            "verify_with_trusted_official_source"
            if pressure_level == "high"
            else "review_total_repayment_before_committing"
            if pressure_level == "medium"
            else "keep_checking_total_cost_and_due_dates"
        ),
        "disclaimer": _borrowing_pressure_disclaimer(language),
        "non_advisory_guardrail": _borrowing_pressure_guardrail(),
    }


def _normalized_borrowing_language(language: str) -> str:
    return "hi" if str(language or "").strip().lower().startswith("hi") else "en"


def _borrowing_period_assumptions(
    *,
    repayment_period: str,
    income_period: str,
    essential_expense_period: str,
) -> dict:
    return {
        "repayment_period": _normalized_borrowing_period(repayment_period),
        "income_period": _normalized_borrowing_period(income_period),
        "essential_expense_period": _normalized_borrowing_period(essential_expense_period),
        "normalized_to": "monthly",
        "daily_month_factor": BORROWING_PERIOD_MONTH_FACTORS["daily"],
        "weekly_month_factor": BORROWING_PERIOD_MONTH_FACTORS["weekly"],
    }


def _borrowing_pressure_insufficient_response(
    *,
    decision_state: str,
    repayment_amount: float | None,
    rough_income_amount: float | None,
    monthly_repayment_amount: float | None,
    monthly_rough_income_amount: float | None,
    essential_expense_amount: float | None,
    monthly_essential_expense_amount: float | None,
    essential_expenses: list[str],
    period_assumptions: dict,
    language: str,
    reason: str,
) -> dict:
    missing_repayment = reason == "repayment"
    title = (
        "Need repayment amount first"
        if missing_repayment and language == "en"
        else "पहले किस्त की राशि चाहिए"
        if missing_repayment
        else "Need rough income first"
        if language == "en"
        else "पहले मोटी आय चाहिए"
    )
    message = (
        "This check needs a valid repayment amount to avoid guessing repayment pressure."
        if missing_repayment and language == "en"
        else "किस्त का दबाव अनुमान लगाने से बचने के लिए सही किस्त राशि चाहिए।"
        if missing_repayment
        else "This check needs rough income to avoid guessing repayment pressure."
        if language == "en"
        else "किस्त का दबाव अनुमान लगाने से बचने के लिए मोटी आय चाहिए।"
    )
    why = (
        "Repayment amount is missing or invalid, so FinSaathi cannot estimate whether repayment is light or heavy."
        if missing_repayment and language == "en"
        else "किस्त की राशि नहीं है या गलत है, इसलिए FinSaathi यह नहीं बता सकता कि किस्त हल्की है या भारी।"
        if missing_repayment
        else "Rough income is missing, so FinSaathi cannot estimate whether repayment is light or heavy."
        if language == "en"
        else "मोटी आय नहीं है, इसलिए FinSaathi यह नहीं बता सकता कि किस्त हल्की है या भारी।"
    )
    next_best_action = (
        "Add a valid repayment amount, rough income, and essential expenses before deciding. If someone is pressuring you, verify through an official source first."
        if missing_repayment and language == "en"
        else "निर्णय से पहले सही किस्त राशि, मोटी आय और जरूरी खर्च जोड़ें। अगर कोई दबाव डाल रहा है, तो पहले आधिकारिक स्रोत से जांचें।"
        if missing_repayment
        else "Add rough income and essential expenses before deciding. If someone is pressuring you, verify through an official source first."
        if language == "en"
        else "निर्णय से पहले मोटी आय और जरूरी खर्च जोड़ें। अगर कोई दबाव डाल रहा है, तो पहले आधिकारिक स्रोत से जांचें।"
    )
    return {
        "contract_version": BORROWING_PRESSURE_CONTRACT_VERSION,
        "decision_state": decision_state,
        "pressure_level": "insufficient_information",
        "repayment_amount": repayment_amount,
        "rough_income_amount": rough_income_amount,
        "essential_expense_amount": essential_expense_amount,
        "monthly_repayment_amount": monthly_repayment_amount,
        "monthly_rough_income_amount": monthly_rough_income_amount,
        "monthly_essential_expense_amount": monthly_essential_expense_amount,
        "period_assumptions": period_assumptions,
        "essential_expenses": essential_expenses,
        "repayment_to_income_ratio": None,
        "essential_expense_ratio": None,
        "post_repayment_essential_buffer": None,
        "confidence": {"score": 0.24, "label": "bounded_low"},
        "title": title,
        "message": message,
        "why_this_check": why,
        "next_best_action": next_best_action,
        "suggested_next_step": "add_rough_inputs_before_committing",
        "disclaimer": _borrowing_pressure_disclaimer(language),
        "non_advisory_guardrail": _borrowing_pressure_guardrail(),
    }


def _borrowing_pressure_title(pressure_level: str, language: str) -> str:
    if language == "hi":
        return {
            "low": "किस्त हल्की लग रही है",
            "medium": "किस्त पर ध्यान दें",
            "high": "किस्त भारी लग रही है",
        }.get(pressure_level, "किस्त जांच")
    return {
        "low": "Repayment looks light",
        "medium": "Repayment needs attention",
        "high": "Repayment looks heavy",
    }.get(pressure_level, "Repayment check")


def _borrowing_pressure_message(pressure_level: str, language: str) -> str:
    if language == "hi":
        return {
            "low": "दी गई मोटी जानकारी के हिसाब से यह किस्त बहुत भारी नहीं दिखती।",
            "medium": "यह किस्त आपके महीने को तंग कर सकती है, इसलिए कुल भुगतान और तारीखें जांचें।",
            "high": "यह किस्त भारी दिखती है। प्रतिबद्ध होने से पहले रुककर आधिकारिक स्रोत से जांचें।",
        }.get(pressure_level, "यह केवल मोटी सुरक्षा जांच है।")
    return {
        "low": "Based on the rough inputs, this repayment does not look very heavy.",
        "medium": "This repayment could make the month tighter, so check total repayment and due dates.",
        "high": "This repayment looks heavy. Pause and verify through a trusted official source before committing.",
    }.get(pressure_level, "This is only a rough safety check.")


def _borrowing_pressure_why(
    *,
    pressure_level: str,
    repayment_ratio: float,
    essentials_amount: float | None,
    buffer_after_essentials: float | None,
    language: str,
) -> str:
    percent = int(round(repayment_ratio * 100))
    if language == "hi":
        if essentials_amount is None:
            return f"किस्त मोटी आय का लगभग {percent}% है। जरूरी खर्च की राशि नहीं दी गई, इसलिए जांच सीमित है।"
        if buffer_after_essentials is not None and buffer_after_essentials < 0:
            return f"किस्त और जरूरी खर्च मिलाकर मोटी आय से ज्यादा हो रहे हैं।"
        return f"किस्त मोटी आय का लगभग {percent}% है और जरूरी खर्च के बाद लगभग ₹{int(buffer_after_essentials or 0)} बचता है।"
    if essentials_amount is None:
        return f"Repayment is about {percent}% of rough income. Essential-expense amount was not provided, so this stays bounded."
    if buffer_after_essentials is not None and buffer_after_essentials < 0:
        return "Repayment plus essential expenses is higher than the rough income shared."
    return f"Repayment is about {percent}% of rough income, leaving about Rs {int(buffer_after_essentials or 0)} after essentials."


def _borrowing_pressure_next_action(pressure_level: str, language: str) -> str:
    if language == "hi":
        if pressure_level == "high":
            return "अभी प्रतिबद्ध न हों। कुल भुगतान, देरी शुल्क और शर्तें किसी भरोसेमंद आधिकारिक स्रोत से जांचें।"
        if pressure_level == "medium":
            return "निर्णय से पहले कुल भुगतान, देरी शुल्क, तारीख और जरूरी खर्च फिर से जांचें।"
        return "फिर भी कुल भुगतान, देरी शुल्क और due date साफ समझकर ही आगे बढ़ें।"
    if pressure_level == "high":
        return "Do not commit yet. Check total repayment, late fees, and terms with a trusted official source."
    if pressure_level == "medium":
        return "Before deciding, re-check total repayment, late fees, due date, and essential expenses."
    return "Still check total repayment, late fees, and due dates clearly before moving ahead."


def _borrowing_pressure_disclaimer(language: str) -> str:
    if language == "hi":
        return "यह केवल मोटी सुरक्षा जांच है। यह loan approval या financial advice नहीं है। FinSaathi loan, lender या product recommend नहीं करता।"
    return "This is a rough safety check, not loan approval or financial advice. FinSaathi does not recommend loans, lenders, or products."


def _borrowing_pressure_guardrail() -> dict:
    return {
        "is_loan_approval": False,
        "is_financial_advice": False,
        "does_not_recommend_products": True,
        "uses_rough_user_inputs_only": True,
    }

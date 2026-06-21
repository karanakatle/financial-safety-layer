from __future__ import annotations

import re

from backend.utils.normalize import normalize_text
from backend.utils.intent import detect_intent
from backend.literacy.messages import literacy_message
from backend.literacy.policy import ai_explanation_policy_contract
from backend.pilot.redaction import redact_sensitive_text


_AI_CONTEXT_ALLOWED_KEYS = {
    "risk_level",
    "category",
    "source_type",
    "reason_code",
    "alert_family",
    "language",
}
_AI_CONTEXT_SAFE_DETAIL_KEYS = {"safe_detail"}
_AI_RAW_TEXT_KEYS = {"raw_message", "message", "text", "notification_text", "sms_text"}
_AI_CONTEXT_BLOCKED_KEYS = {
    "aadhaar",
    "aadhar",
    "account",
    "bank_account",
    "bank_password",
    "card",
    "card_number",
    "exact_balance",
    "exact_salary",
    "mobile",
    "otp",
    "pan",
    "participant_id",
    "password",
    "phone",
    "upi_pin",
}
_UNCERTAINTY_MARKERS = {
    "not sure",
    "uncertain",
    "unclear",
    "cannot confirm",
    "not fully sure",
    "maybe",
    "could be",
}
_PROHIBITED_OUTPUT_MARKERS = {
    "loan_recommendation": (
        "take this loan",
        "apply for this loan",
        "use this loan",
        "choose this loan",
        "loan app",
        "best loan",
        "recommend loan",
        "suggest loan",
        "which loan",
        "kaunsa loan",
        "loan lena",
        "personal loan lena",
        "borrow from",
        "use this lender",
    ),
    "investment_recommendation": (
        "invest in",
        "buy this stock",
        "buy shares",
        "mutual fund for high returns",
        "best mutual fund",
        "guaranteed returns",
        "which mutual fund",
        "recommend mutual fund",
        "suggest mutual fund",
        "start sip",
        "sip in",
        "best sip",
        "sip recommend",
        "recommend sip",
        "kaunsa mutual fund",
        "mutual fund me invest",
        "stock should i buy",
        "best stock",
        "share kharid",
    ),
    "product_recommendation": (
        "use kreditbee",
        "use cred",
        "use this card",
        "open this account",
        "buy this policy",
        "which credit card",
        "best credit card",
        "recommend credit card",
        "suggest credit card",
        "credit card should i",
        "open account with",
        "buy lic policy",
        "insurance policy should i",
    ),
}
_PROHIBITED_OUTPUT_PATTERNS = {
    "loan_recommendation": (
        r"\b(?:which|best|recommend|suggest)\s+(?:\w+\s+){0,4}(?:loan|lender|loan app)\b",
        r"\b(?:take|apply|choose|use)\s+(?:\w+\s+){0,4}(?:loan|lender|loan app)\b",
    ),
    "investment_recommendation": (
        r"\b(?:which|best|recommend|suggest|buy|start)\s+(?:\w+\s+){0,4}(?:mutual fund|sip|stock|share|crypto)\b",
        r"\b(?:invest|nivesh)\s+(?:\w+\s+){0,4}(?:mutual fund|sip|stock|share|crypto)\b",
        r"\b(?:guaranteed|pakka)\s+(?:\w+\s+){0,3}returns?\b",
    ),
    "product_recommendation": (
        r"\b(?:which|best|recommend|suggest|use)\s+(?:\w+\s+){0,4}(?:credit card|card|account|policy|insurance)\b",
        r"\b(?:open|buy)\s+(?:\w+\s+){0,4}(?:account|policy|insurance)\b",
    ),
}


def process_text(text: str):
    normalized = normalize_text(text)

    intent, score = detect_intent(normalized)

    return {
        "original": text,
        "normalized": normalized,
        "intent": intent,
        "confidence": score
    }


def ai_policy_contract() -> dict:
    return ai_explanation_policy_contract()


def minimize_ai_explanation_context(context: dict | None, *, user_consented: bool) -> dict:
    if not user_consented:
        return {
            "ok_for_ai": False,
            "block_reason": "ai_consent_required",
            "provider_input": {},
            "removed_keys": [],
        }

    source = dict(context or {})
    provider_input: dict[str, object] = {}
    removed_keys: list[str] = []

    for key, value in source.items():
        normalized_key = str(key or "").strip().lower()
        if normalized_key in _AI_CONTEXT_BLOCKED_KEYS:
            removed_keys.append(normalized_key)
            continue
        if normalized_key in _AI_CONTEXT_ALLOWED_KEYS:
            if value is not None and str(value).strip():
                provider_input[normalized_key] = _safe_context_value(value)
            continue
        if normalized_key in _AI_CONTEXT_SAFE_DETAIL_KEYS:
            if value is not None and str(value).strip():
                provider_input[normalized_key] = _safe_context_label(value)
            continue
        if normalized_key in _AI_RAW_TEXT_KEYS:
            redacted = redact_sensitive_text(str(value or ""), max_length=220)
            if redacted:
                provider_input["redacted_message"] = redacted
            continue
        removed_keys.append(normalized_key)

    return {
        "ok_for_ai": True,
        "block_reason": None,
        "provider_input": provider_input,
        "removed_keys": sorted(set(removed_keys)),
    }


def filter_ai_explanation_output(candidate_text: str, *, language: str = "en", user_query: str = "") -> dict:
    normalized = normalize_text(" ".join([user_query or "", candidate_text or ""])).lower()
    for reason_code in _PROHIBITED_OUTPUT_MARKERS:
        markers = _PROHIBITED_OUTPUT_MARKERS[reason_code]
        patterns = _PROHIBITED_OUTPUT_PATTERNS.get(reason_code, ())
        if any(marker in normalized for marker in markers) or any(re.search(pattern, normalized) for pattern in patterns):
            return {
                "allowed": False,
                "reason_code": "regulated_product_recommendation",
                "matched_policy": reason_code,
                "safe_text": literacy_message(language, "ai_guardrail_refusal"),
            }

    return {
        "allowed": True,
        "reason_code": "safe_explanation",
        "matched_policy": None,
        "safe_text": _append_required_safety_suffixes(candidate_text or "", language=language),
    }


def build_guarded_ai_explanation(
    *,
    user_query: str,
    context: dict | None,
    provider_output: str,
    user_consented: bool,
    language: str = "en",
) -> dict:
    minimized = minimize_ai_explanation_context(context, user_consented=user_consented)
    if not minimized["ok_for_ai"]:
        return {
            "display_allowed": False,
            "display_text": literacy_message(language, "ai_guardrail_refusal"),
            "policy_result": {
                "allowed": False,
                "reason_code": minimized["block_reason"],
                "safe_text": literacy_message(language, "ai_guardrail_refusal"),
            },
            "provider_input": minimized["provider_input"],
            "contract": ai_policy_contract(),
        }

    policy_result = filter_ai_explanation_output(
        provider_output,
        language=language,
        user_query=user_query,
    )
    display_text = policy_result["safe_text"]
    if policy_result["allowed"] and _is_uncertain(provider_output, context):
        display_text = _append_sentence_once(
            display_text,
            literacy_message(language, "ai_uncertain_verify_suffix"),
        )

    return {
        "display_allowed": bool(policy_result["allowed"]),
        "display_text": display_text,
        "policy_result": {
            **policy_result,
            "safe_text": display_text,
        },
        "provider_input": minimized["provider_input"],
        "contract": ai_policy_contract(),
        "query_intent": process_text(user_query).get("intent"),
    }


def _safe_context_value(value: object) -> str:
    return redact_sensitive_text(str(value or ""), max_length=120)


def _safe_context_label(value: object) -> str:
    normalized = normalize_text(str(value or ""))
    if not normalized:
        return "additional_context_removed"
    if "why" in normalized and "warning" in normalized:
        return "user_asked_why_warning_appeared"
    if "safety" in normalized or "safe" in normalized or "check" in normalized:
        return "user_requested_safety_check"
    if "uncertain" in normalized or "not sure" in normalized or "confus" in normalized:
        return "user_reported_uncertainty"
    return "additional_context_removed"


def _is_uncertain(candidate_text: str, context: dict | None) -> bool:
    normalized_candidate = normalize_text(candidate_text or "").lower()
    if any(marker in normalized_candidate for marker in _UNCERTAINTY_MARKERS):
        return True
    normalized_category = str((context or {}).get("category") or "").strip().lower()
    normalized_reason = str((context or {}).get("reason_code") or "").strip().lower()
    return normalized_category.startswith("unknown") or "unknown" in normalized_reason


def _append_required_safety_suffixes(candidate_text: str, *, language: str) -> str:
    text = candidate_text.strip()
    if not text:
        text = literacy_message(language, "ai_uncertain_verify_suffix")
    text = _append_sentence_once(text, literacy_message(language, "ai_non_advisory_suffix"))
    return text


def _append_sentence_once(text: str, sentence: str) -> str:
    normalized_text = normalize_text(text).lower()
    normalized_sentence = normalize_text(sentence).lower()
    if normalized_sentence in normalized_text:
        return text.strip()
    separator = "" if text.rstrip().endswith((".", "!", "?", "।")) else "."
    return f"{text.strip()}{separator} {sentence}".strip()

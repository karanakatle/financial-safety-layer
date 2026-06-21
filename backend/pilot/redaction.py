from __future__ import annotations

import re
from typing import Any


RAW_TEXT_KEYS = {
    "body",
    "content",
    "event_trace",
    "message",
    "note",
    "raw_message",
    "raw_text",
    "review_note",
    "text",
    "summary_text",
}

SENSITIVE_VALUE_KEYS = {
    "raw_url",
    "otp",
    "upi_pin",
    "pin",
    "aadhaar",
    "aadhar",
    "pan",
    "card",
    "card_number",
    "cvv",
    "account",
    "account_number",
    "account_no",
    "bank_account",
    "bank_password",
    "phone",
    "phone_number",
    "mobile",
    "mobile_number",
    "ifsc",
    "password",
    "upi_id",
    "vpa",
}


def redact_sensitive_text(value: str, *, max_length: int = 160) -> str:
    redacted = str(value or "")
    redacted = re.sub(
        r"\b(otp|one\s*time\s*password|upi\s*pin|pin|password|passcode|cvv)\s*(?:is|=|:|-)?\s*(?:[A-Za-z0-9][A-Za-z0-9-]{3,31}|(?:\d[\s-]*){3,8})\b",
        r"\1 [redacted]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"\b(?:[A-Za-z]*\d[A-Za-z0-9-]{3,31}|(?:\d[\s-]*){4,8})\s*(?:is|=|:|-)?\s*(otp|one\s*time\s*password|upi\s*pin|pin|password|passcode|cvv)\b",
        r"[redacted] \1",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"\b(?:avl\.?\s*bal|available\s+balance|balance)\s*(?:is|=|:|-)?\s*(?:rs\.?|inr|₹)?\s*[\d,]+(?:\.\d{1,2})?\b",
        "[redacted_balance]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(r"\b[a-z]{5}\d{4}[a-z]\b", "[redacted_pan]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[redacted_aadhaar]", redacted)
    redacted = re.sub(r"\b(?:\d[ -]*?){13,19}\b", "[redacted_card]", redacted)
    redacted = re.sub(r"\b\d{9,18}\b", "[redacted_number]", redacted)
    redacted = re.sub(r"\b\d{4,8}\b", "[redacted_code]", redacted)
    redacted = re.sub(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", "[redacted_ifsc]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"\b[\w.-]+@[\w.-]+\b", "[redacted_handle]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"https?://\S+|www\.\S+", "[redacted_url]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"\s+", " ", redacted).strip()
    if len(redacted) > max_length:
        return f"{redacted[:max_length].rstrip()}..."
    return redacted


def safe_review_export_record(record: dict[str, Any]) -> dict[str, Any]:
    return _safe_export_value(record)


def _safe_export_value(value: Any, *, key: str | None = None) -> Any:
    normalized_key = (key or "").strip().lower()
    if isinstance(value, dict):
        return {
            item_key: _safe_export_value(item_value, key=item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_safe_export_value(item) for item in value]
    if not isinstance(value, str):
        return value
    if normalized_key in RAW_TEXT_KEYS:
        return "[redacted_text]"
    if normalized_key in SENSITIVE_VALUE_KEYS:
        return "[redacted]"
    return redact_sensitive_text(value, max_length=240)

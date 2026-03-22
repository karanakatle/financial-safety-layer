from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StructuredMessageSignals:
    normalized_text: str
    has_otp_code: bool
    has_upi_handle: bool
    has_upi_deeplink: bool
    has_url: bool
    is_call_metadata: bool
    is_setup_or_registration: bool
    is_otp_verification: bool
    is_receive_only: bool
    is_post_transaction_confirmation: bool
    is_statement_or_report: bool
    is_emi_status: bool
    is_portfolio_info: bool
    is_marketing_or_product_status: bool
    is_sensitive_access_signal: bool
    has_collect_signal: bool
    has_send_signal: bool
    has_strong_payment_signal: bool


_OTP_CODE_RE = re.compile(r"\b\d{4,8}\b")
_UPI_HANDLE_RE = re.compile(r"\b[a-z0-9.\-_]{2,}@[a-z]{2,}\b", re.IGNORECASE)
_UPI_DEEPLINK_RE = re.compile(r"upi://pay\b", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_MESSAGE_BUNDLE_RE = re.compile(r"\b\d+\s+messages?\s+from\s+\d+\s+chats?\b", re.IGNORECASE)


def extract_message_signals(text: str) -> StructuredMessageSignals:
    normalized = _normalize(text)
    has_otp_code = bool(_OTP_CODE_RE.search(text))
    has_upi_handle = bool(_UPI_HANDLE_RE.search(text))
    has_upi_deeplink = bool(_UPI_DEEPLINK_RE.search(text))
    has_url = bool(_URL_RE.search(text))

    has_collect_signal = (
        _has_any_word(normalized, "collect", "mandate", "autopay")
        or _has_phrase(normalized, "request money")
        or _has_phrase(normalized, "approve request")
        or _has_phrase(normalized, "approve collect")
    )
    has_send_signal = (
        _has_phrase(normalized, "send money")
        or _has_phrase(normalized, "approve payment")
        or _has_phrase(normalized, "payment request")
        or _has_phrase(normalized, "pay to")
        or _has_phrase(normalized, "payment to")
        or _has_phrase(normalized, "scan and pay")
    )

    is_call_metadata = (
        _has_phrase(normalized, "missed call")
        or _has_phrase(normalized, "voice call")
        or _has_phrase(normalized, "available for calls")
        or bool(_MESSAGE_BUNDLE_RE.search(normalized))
    )
    is_setup_or_registration = (
        (
            _has_any_word(normalized, "register", "registered", "registration", "verify", "verified", "verification")
            and _has_any_word(normalized, "device", "mobile", "phone", "account")
        )
        or _has_all_words(normalized, "set", "upi", "pin")
        or _has_all_words(normalized, "link", "bank", "account")
        or _has_all_words(normalized, "bank", "account", "fetch")
        or _has_all_words(normalized, "current", "device")
    )
    is_otp_verification = has_otp_code and (
        _has_word(normalized, "otp")
        or _has_all_words(normalized, "verification", "code")
        or _has_phrase(normalized, "one time password")
    )
    is_receive_only = (
        _has_any_word(normalized, "credited", "received")
        and not has_collect_signal
        and not has_send_signal
        and not has_upi_deeplink
    ) or _has_all_words(normalized, "payment", "received")
    is_post_transaction_confirmation = (
        _has_all_words(normalized, "payment", "successful")
        or _has_all_words(normalized, "updated", "balance")
        or (_has_word(normalized, "processed") and _has_any_word(normalized, "purchase", "request", "investment"))
        or _has_all_words(normalized, "units", "allotted")
        or _has_all_words(normalized, "unit", "allotment")
        or _has_all_words(normalized, "thank", "investment")
    )
    is_statement_or_report = (
        _has_word(normalized, "statement")
        and _has_any_word(normalized, "account", "folio", "transaction", "view")
    ) or (_has_word(normalized, "pan") and _has_word(normalized, "password"))
    is_emi_status = _has_word(normalized, "emi") and _has_any_word(
        normalized, "due", "deducted", "received", "repayment", "presentation"
    )
    is_portfolio_info = (
        _has_any_word(normalized, "passbook", "portfolio", "valuation", "securities")
        and _has_any_word(normalized, "balance", "bal", "value")
    ) or _has_all_words(normalized, "fund", "bal")
    is_marketing_or_product_status = _has_all_words(normalized, "card", "status", "updated") or (
        _has_word(normalized, "loan")
        and _has_any_word(normalized, "offer", "approved", "pre-approved", "preapproved", "exclusive")
    )
    is_sensitive_access_signal = (
        (_has_word(normalized, "pan") and _has_word(normalized, "password"))
        or _has_all_words(normalized, "data", "sharing")
        or _has_word(normalized, "aadhaar")
        or _has_word(normalized, "passport")
        or _has_all_words(normalized, "net", "banking", "login")
        or _has_all_words(normalized, "mobile", "banking")
        or (_has_word(normalized, "email") and _has_word(normalized, "changed"))
        or _has_word(normalized, "authorising")
        or _has_word(normalized, "authorizing")
    )

    return StructuredMessageSignals(
        normalized_text=normalized,
        has_otp_code=has_otp_code,
        has_upi_handle=has_upi_handle,
        has_upi_deeplink=has_upi_deeplink,
        has_url=has_url,
        is_call_metadata=is_call_metadata,
        is_setup_or_registration=is_setup_or_registration,
        is_otp_verification=is_otp_verification,
        is_receive_only=is_receive_only,
        is_post_transaction_confirmation=is_post_transaction_confirmation,
        is_statement_or_report=is_statement_or_report,
        is_emi_status=is_emi_status,
        is_portfolio_info=is_portfolio_info,
        is_marketing_or_product_status=is_marketing_or_product_status,
        is_sensitive_access_signal=is_sensitive_access_signal,
        has_collect_signal=has_collect_signal,
        has_send_signal=has_send_signal,
        has_strong_payment_signal=has_collect_signal or has_send_signal or has_upi_handle or has_upi_deeplink,
    )


def _normalize(text: str) -> str:
    return f" {' '.join((text or '').split()).lower()} "


def _has_phrase(text: str, phrase: str) -> bool:
    return f" {phrase.lower()} " in text


def _has_word(text: str, word: str) -> bool:
    return bool(re.search(rf"(^|[^\w]){re.escape(word.lower())}([^\w]|$)", text))


def _has_any_word(text: str, *words: str) -> bool:
    return any(_has_word(text, word) or _has_phrase(text, word) for word in words)


def _has_all_words(text: str, *words: str) -> bool:
    return all(_has_word(text, word) or _has_phrase(text, word) for word in words)

from __future__ import annotations

from dataclasses import dataclass

from backend.api_models import UPIRequestInspectIn
from backend.literacy.domain_intelligence import enrich_domain_context, is_high_risk_domain_class
from backend.literacy.messages import literacy_message
from backend.literacy.sequence_correlation import SequenceEvidence
from backend.literacy.structured_message_signals import extract_message_signals


@dataclass(frozen=True)
class PaymentScenarioDecision:
    scenario: str
    classification: str
    should_warn: bool
    alert_family: str
    risk_level: str
    message: str
    why_this_alert: str
    next_best_action: str


IGNORE_BENIGN_CLASSIFICATION = "ignore_benign"
STORE_ONLY_ACCOUNT_ACCESS_CLASSIFICATION = "store_only_account_access"
ACCOUNT_ACCESS_RISK_CLASSIFICATION = "account_access_risk"
PAYMENT_OUTFLOW_RISK_CLASSIFICATION = "payment_outflow_risk"
ALERT_FAMILY_PAYMENT = "payment"
ALERT_FAMILY_ACCOUNT_ACCESS = "account_access"
COLLECT_SCENARIO = "collect_request_confusion"
REFUND_SCENARIO = "refund_reward_kyc_scam"
UNKNOWN_PAYEE_SCENARIO = "unknown_payee_or_unusual_amount"
ACCOUNT_ACCESS_RISK_SCENARIO = "account_access_risk"
UNKNOWN_SCENARIO = "unknown"
IGNORE_BENIGN_SCENARIO = "ignore_benign"
STORE_ONLY_ACCOUNT_ACCESS_SCENARIO = "store_only_account_access"
_ACTIVE_SETUP_STATES = {
    "upi registration started",
    "phone verification",
    "bank account fetch",
    "upi pin setup",
    "registration success",
}

_GENERIC_PAYEE_MARKERS = {
    "",
    "unknown",
    "unknown payee",
    "merchant",
    "test merchant",
    "user",
    "payment request",
}
_UNUSUAL_AMOUNT_HIGH = 10000.0
_UNUSUAL_AMOUNT_MEDIUM = 5000.0
_REFUND_SCAM_KEYWORDS = ("refund", "cashback", "reward", "prize", "bonus", "kyc", "verify account", "update account")


def classify_payment_scenario(
    payload: UPIRequestInspectIn,
    *,
    language: str,
    entity_trust_state: str | None = None,
    entity_reputation_level: str | None = None,
    sequence_evidence: SequenceEvidence | None = None,
) -> PaymentScenarioDecision:
    raw_text = _normalize(payload.raw_text)
    signals = extract_message_signals(raw_text)
    app_name = _normalize(payload.app_name)
    payee_label = _normalize(payload.payee_label)
    payee_handle = _normalize(payload.payee_handle)
    request_kind = _normalize((payload.request_kind or "").replace("_", " ")).lower()
    setup_state = _normalize((payload.setup_state or "").replace("_", " ")).lower()
    domain_context = enrich_domain_context(
        link_scheme=payload.link_scheme,
        url_host=payload.url_host,
        resolved_domain=payload.resolved_domain,
        domain_class=payload.domain_class,
    )
    link_clicked = bool(payload.link_clicked)
    sequence_evidence = sequence_evidence or SequenceEvidence(sequence_trace=[])

    if _looks_like_visible_access_flow(
        raw_text=raw_text,
        signals=signals,
        link_clicked=link_clicked,
        setup_state=setup_state,
        domain_class=domain_context.domain_class,
        entity_trust_state=entity_trust_state,
        entity_reputation_level=entity_reputation_level,
        sequence_evidence=sequence_evidence,
    ):
        return _augment_sequence_context(
            _account_access_risk_decision(
                language=language,
                domain_class=domain_context.domain_class,
                entity_trust_state=entity_trust_state,
                entity_reputation_level=entity_reputation_level,
            ),
            language=language,
            sequence_evidence=sequence_evidence,
        )

    if _looks_like_clicked_access_flow(
        raw_text=raw_text,
        signals=signals,
        link_clicked=link_clicked,
        domain_class=domain_context.domain_class,
    ):
        if sequence_evidence.access_confidence in {"medium", "strong"}:
            return _augment_sequence_context(
                _account_access_risk_decision(
                    language=language,
                    domain_class=domain_context.domain_class,
                    entity_trust_state=entity_trust_state,
                    entity_reputation_level=entity_reputation_level,
                ),
                language=language,
                sequence_evidence=sequence_evidence,
            )
        return _store_only_account_access_decision(language)

    if signals.is_call_metadata:
        return _ignore_benign_decision(language)
    if signals.is_setup_or_registration:
        return _ignore_benign_decision(language)
    if signals.is_statement_or_report:
        return _ignore_benign_decision(language)
    if signals.is_post_transaction_confirmation:
        return _ignore_benign_decision(language)
    if signals.is_receive_only:
        return _ignore_benign_decision(language)
    if signals.is_emi_status:
        return _ignore_benign_decision(language)
    if signals.is_marketing_or_product_status or signals.is_portfolio_info:
        return _ignore_benign_decision(language)
    if signals.is_otp_verification:
        if signals.is_sensitive_access_signal:
            return _store_only_account_access_decision(language)
        return _ignore_benign_decision(language)
    if signals.is_sensitive_access_signal:
        return _store_only_account_access_decision(language)
    if _is_active_setup_state(setup_state) and not _has_explicit_payment_signal(
        raw_text=raw_text,
        request_kind=request_kind,
    ):
        return _ignore_benign_decision(language)
    if not _has_strong_payment_signal(
        raw_text=raw_text,
        request_kind=request_kind,
        payee_handle=payee_handle,
        signals=signals,
    ):
        return _ignore_benign_decision(language)

    if _looks_like_refund_reward_kyc_scam(raw_text, request_kind):
        return _augment_link_context(
            _refund_reward_kyc_decision(language),
            language=language,
            link_clicked=link_clicked,
            domain_class=domain_context.domain_class,
            sequence_evidence=sequence_evidence,
        )

    if _looks_like_collect_request(raw_text, request_kind):
        return _augment_link_context(
            _collect_request_decision(language),
            language=language,
            link_clicked=link_clicked,
            domain_class=domain_context.domain_class,
            sequence_evidence=sequence_evidence,
        )

    if _looks_like_unknown_payee_or_unusual_amount(
        raw_text=raw_text,
        app_name=app_name,
        payee_label=payee_label,
        payee_handle=payee_handle,
        amount=payload.amount,
        request_kind=request_kind,
        signals=signals,
    ):
        return _augment_link_context(
            _unknown_payee_or_unusual_amount_decision(
                language=language,
                amount=payload.amount,
                request_kind=request_kind,
            ),
            language=language,
            link_clicked=link_clicked,
            domain_class=domain_context.domain_class,
            sequence_evidence=sequence_evidence,
        )

    return _augment_link_context(
        _fallback_decision(
            language=language,
            has_context=bool(raw_text or app_name or payee_label or payee_handle or payload.amount not in (None, 0)),
            request_kind=request_kind,
        ),
        language=language,
        link_clicked=link_clicked,
        domain_class=domain_context.domain_class,
        sequence_evidence=sequence_evidence,
    )


def _looks_like_collect_request(raw_text: str, request_kind: str) -> bool:
    if request_kind in {"collect", "collect request"}:
        return True
    return (
        "request money" in raw_text
        or "approve request" in raw_text
        or "approve collect" in raw_text
        or "collect" in raw_text
        or "mandate" in raw_text
        or "autopay" in raw_text
    )


def _looks_like_refund_reward_kyc_scam(raw_text: str, request_kind: str) -> bool:
    if not any(keyword in raw_text for keyword in _REFUND_SCAM_KEYWORDS):
        return False
    if request_kind in {"collect", "collect request", "refund request", "unknown request"}:
        return True
    return _looks_like_collect_request(raw_text, request_kind) or "fee" in raw_text or "pay" in raw_text


def _looks_like_unknown_payee_or_unusual_amount(
    *,
    raw_text: str,
    app_name: str,
    payee_label: str,
    payee_handle: str,
    amount: float | None,
    request_kind: str,
    signals,
) -> bool:
    has_payment_signal = _has_strong_payment_signal(
        raw_text=raw_text,
        request_kind=request_kind,
        payee_handle=payee_handle,
        signals=signals,
    )
    if not has_payment_signal:
        return False

    unusual_amount = (amount or 0) >= _UNUSUAL_AMOUNT_MEDIUM
    missing_or_generic_payee = _is_missing_or_generic_payee(payee_label, payee_handle)
    return unusual_amount or missing_or_generic_payee


def _is_missing_or_generic_payee(payee_label: str, payee_handle: str) -> bool:
    normalized_label = payee_label.lower()
    normalized_handle = payee_handle.lower()
    if normalized_handle:
        return False
    return normalized_label in _GENERIC_PAYEE_MARKERS


def _is_active_setup_state(setup_state: str) -> bool:
    return setup_state in _ACTIVE_SETUP_STATES


def _looks_like_clicked_access_flow(
    *,
    raw_text: str,
    signals,
    link_clicked: bool,
    domain_class: str | None,
) -> bool:
    if not link_clicked or not is_high_risk_domain_class(domain_class):
        return False
    return signals.is_otp_verification or signals.is_sensitive_access_signal or any(
        phrase in raw_text for phrase in ("login", "verify account", "kyc", "update account", "net banking", "mobile banking")
    )


def _looks_like_visible_access_flow(
    *,
    raw_text: str,
    signals,
    link_clicked: bool,
    setup_state: str,
    domain_class: str | None,
    entity_trust_state: str | None,
    entity_reputation_level: str | None,
    sequence_evidence: SequenceEvidence,
) -> bool:
    if not link_clicked:
        return False

    normalized_domain_class = (domain_class or "").strip().lower()
    normalized_trust_state = (entity_trust_state or "").strip().lower()
    normalized_reputation_level = (entity_reputation_level or "").strip().lower()
    if _is_active_setup_state(setup_state) and normalized_domain_class == "official":
        return False
    if _is_active_setup_state(setup_state) and normalized_trust_state in {"official_verified", "trusted_by_observation"}:
        return False

    has_access_context = signals.is_otp_verification or signals.is_sensitive_access_signal or any(
        phrase in raw_text
        for phrase in (
            "login",
            "verify account",
            "update account",
            "mobile banking",
            "net banking",
            "customer id",
            "internet banking",
            "kyc",
        )
    )
    if not has_access_context:
        return False

    if normalized_trust_state in {"official_verified", "trusted_by_observation"}:
        if normalized_domain_class in {"suspicious", "loan", "card"}:
            return True
        return normalized_domain_class == "bank" and (
            sequence_evidence.access_confidence in {"medium", "strong"} or
            normalized_reputation_level in {"medium", "high"}
        )
    if normalized_domain_class in {"suspicious", "loan", "card"}:
        return True
    return normalized_domain_class == "bank" and any(
        phrase in raw_text
        for phrase in ("login", "verify account", "update account", "mobile banking", "net banking", "customer id", "kyc")
    )


def _has_explicit_payment_signal(*, raw_text: str, request_kind: str) -> bool:
    normalized_request_kind = request_kind.replace("_", " ").strip().lower()
    if normalized_request_kind in {"collect", "collect request", "refund", "refund request", "send money"}:
        return True
    return (
        "request money" in raw_text
        or "approve request" in raw_text
        or "approve collect" in raw_text
        or "collect" in raw_text
        or "mandate" in raw_text
        or "autopay" in raw_text
        or "send money" in raw_text
        or "approve payment" in raw_text
        or "payment request" in raw_text
        or "pay to" in raw_text
        or "payment to" in raw_text
        or "scan and pay" in raw_text
        or "upi://pay" in raw_text
    )


def _collect_request_decision(language: str) -> PaymentScenarioDecision:
    return PaymentScenarioDecision(
        scenario=COLLECT_SCENARIO,
        classification=PAYMENT_OUTFLOW_RISK_CLASSIFICATION,
        should_warn=True,
        alert_family=ALERT_FAMILY_PAYMENT,
        risk_level="high",
        message=literacy_message(language, "payment_inspection.collect_request_confusion.message"),
        why_this_alert=literacy_message(language, "payment_inspection.collect_request_confusion.why"),
        next_best_action=literacy_message(language, "payment_inspection.collect_request_confusion.next"),
    )


def _refund_reward_kyc_decision(language: str) -> PaymentScenarioDecision:
    return PaymentScenarioDecision(
        scenario=REFUND_SCENARIO,
        classification=PAYMENT_OUTFLOW_RISK_CLASSIFICATION,
        should_warn=True,
        alert_family=ALERT_FAMILY_PAYMENT,
        risk_level="high",
        message=literacy_message(language, "payment_inspection.refund_reward_kyc_scam.message"),
        why_this_alert=literacy_message(language, "payment_inspection.refund_reward_kyc_scam.why"),
        next_best_action=literacy_message(language, "payment_inspection.refund_reward_kyc_scam.next"),
    )


def _unknown_payee_or_unusual_amount_decision(
    *,
    language: str,
    amount: float | None,
    request_kind: str,
) -> PaymentScenarioDecision:
    risk_level = "high" if (amount or 0) >= _UNUSUAL_AMOUNT_HIGH else "medium"
    direction_line = _direction_line(language, request_kind)

    return PaymentScenarioDecision(
        scenario=UNKNOWN_PAYEE_SCENARIO,
        classification=PAYMENT_OUTFLOW_RISK_CLASSIFICATION,
        should_warn=True,
        alert_family=ALERT_FAMILY_PAYMENT,
        risk_level=risk_level,
        message=_compact_message(
            literacy_message(
                language,
                "payment_inspection.unknown_payee_or_unusual_amount.message_template",
                direction_line=direction_line,
            )
        ),
        why_this_alert=literacy_message(language, "payment_inspection.unknown_payee_or_unusual_amount.why"),
        next_best_action=literacy_message(language, "payment_inspection.unknown_payee_or_unusual_amount.next"),
    )


def _fallback_decision(language: str, *, has_context: bool, request_kind: str) -> PaymentScenarioDecision:
    direction_line = _direction_line(language, request_kind, fallback=True)

    message_key = (
        "payment_inspection.unknown.message_with_context_template"
        if has_context
        else "payment_inspection.unknown.message_without_context_template"
    )
    return PaymentScenarioDecision(
        scenario=UNKNOWN_SCENARIO,
        classification=PAYMENT_OUTFLOW_RISK_CLASSIFICATION,
        should_warn=True,
        alert_family=ALERT_FAMILY_PAYMENT,
        risk_level="medium",
        message=_compact_message(
            literacy_message(
                language,
                message_key,
                direction_line=direction_line,
            )
        ),
        why_this_alert=literacy_message(language, "payment_inspection.unknown.why"),
        next_best_action=literacy_message(language, "payment_inspection.unknown.next"),
    )


def _direction_line(language: str, request_kind: str, fallback: bool = False) -> str:
    outgoing_kinds = {"collect", "collect request", "send money", "refund request"}
    if request_kind in outgoing_kinds:
        return literacy_message(language, "payment_inspection.direction_line_outgoing")
    if fallback:
        return literacy_message(language, "payment_inspection.direction_line_fallback")
    return ""


def _normalize(value: str | None) -> str:
    return " ".join((value or "").split()).lower()


def _ignore_benign_decision(language: str) -> PaymentScenarioDecision:
    return PaymentScenarioDecision(
        scenario=IGNORE_BENIGN_SCENARIO,
        classification=IGNORE_BENIGN_CLASSIFICATION,
        should_warn=False,
        alert_family=ALERT_FAMILY_PAYMENT,
        risk_level="low",
        message="",
        why_this_alert="",
        next_best_action="",
    )


def _store_only_account_access_decision(language: str) -> PaymentScenarioDecision:
    return PaymentScenarioDecision(
        scenario=STORE_ONLY_ACCOUNT_ACCESS_SCENARIO,
        classification=STORE_ONLY_ACCOUNT_ACCESS_CLASSIFICATION,
        should_warn=False,
        alert_family=ALERT_FAMILY_ACCOUNT_ACCESS,
        risk_level="low",
        message="",
        why_this_alert="",
        next_best_action="",
    )


def _account_access_risk_decision(
    language: str,
    *,
    domain_class: str | None,
    entity_trust_state: str | None,
    entity_reputation_level: str | None = None,
) -> PaymentScenarioDecision:
    normalized_domain_class = (domain_class or "").strip().lower()
    normalized_trust_state = (entity_trust_state or "").strip().lower()
    normalized_reputation_level = (entity_reputation_level or "").strip().lower()
    why_this_alert = literacy_message(language, "payment_inspection.account_access_risk.why")
    if normalized_domain_class in {"suspicious", "loan", "card"}:
        why_this_alert = f"{why_this_alert} {literacy_message(language, 'payment_inspection.account_access_risk.why_suffix_risky_domain')}".strip()
    elif normalized_domain_class == "bank" and normalized_trust_state not in {"official_verified", "trusted_by_observation"}:
        why_this_alert = f"{why_this_alert} {literacy_message(language, 'payment_inspection.account_access_risk.why_suffix_new_bank_like_domain')}".strip()
    if normalized_reputation_level in {"medium", "high"}:
        why_this_alert = f"{why_this_alert} {literacy_message(language, 'payment_inspection.account_access_risk.why_suffix_cross_user_reputation')}".strip()

    return PaymentScenarioDecision(
        scenario=ACCOUNT_ACCESS_RISK_SCENARIO,
        classification=ACCOUNT_ACCESS_RISK_CLASSIFICATION,
        should_warn=True,
        alert_family=ALERT_FAMILY_ACCOUNT_ACCESS,
        risk_level="high",
        message=literacy_message(language, "payment_inspection.account_access_risk.message"),
        why_this_alert=why_this_alert,
        next_best_action=literacy_message(language, "payment_inspection.account_access_risk.next"),
    )


def _augment_link_context(
    decision: PaymentScenarioDecision,
    *,
    language: str,
    link_clicked: bool,
    domain_class: str | None,
    sequence_evidence: SequenceEvidence,
) -> PaymentScenarioDecision:
    combined_why = decision.why_this_alert
    if link_clicked and is_high_risk_domain_class(domain_class):
        extra_line = literacy_message(language, "payment_inspection.risky_link_suffix")
        if extra_line not in combined_why:
            combined_why = f"{combined_why} {extra_line}".strip()
    if sequence_evidence.sequence_trace:
        extra_line = literacy_message(
            language,
            "payment_inspection.sequence_suffix_strong"
            if sequence_evidence.sequence_window == "0-120s"
            else "payment_inspection.sequence_suffix_medium",
        )
        if extra_line not in combined_why:
            combined_why = f"{combined_why} {extra_line}".strip()
    return PaymentScenarioDecision(
        scenario=decision.scenario,
        classification=decision.classification,
        should_warn=decision.should_warn,
        alert_family=decision.alert_family,
        risk_level=decision.risk_level,
        message=decision.message,
        why_this_alert=combined_why,
        next_best_action=decision.next_best_action,
    )


def _augment_sequence_context(
    decision: PaymentScenarioDecision,
    *,
    language: str,
    sequence_evidence: SequenceEvidence,
) -> PaymentScenarioDecision:
    if not sequence_evidence.sequence_trace:
        return decision
    extra_line = literacy_message(
        language,
        "payment_inspection.sequence_suffix_strong"
        if sequence_evidence.sequence_window == "0-120s"
        else "payment_inspection.sequence_suffix_medium",
    )
    combined_why = decision.why_this_alert
    if extra_line not in combined_why:
        combined_why = f"{combined_why} {extra_line}".strip()
    return PaymentScenarioDecision(
        scenario=decision.scenario,
        classification=decision.classification,
        should_warn=decision.should_warn,
        alert_family=decision.alert_family,
        risk_level=decision.risk_level,
        message=decision.message,
        why_this_alert=combined_why,
        next_best_action=decision.next_best_action,
    )


def _has_strong_payment_signal(*, raw_text: str, request_kind: str, payee_handle: str, signals) -> bool:
    if request_kind in {"collect", "collect request", "send money", "refund request"}:
        return True
    if payee_handle:
        return True
    return signals.has_strong_payment_signal


def _compact_message(value: str) -> str:
    return " ".join(value.split())

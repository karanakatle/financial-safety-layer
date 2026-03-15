from __future__ import annotations

from dataclasses import dataclass

from backend.api_models import UPIRequestInspectIn


@dataclass(frozen=True)
class PaymentScenarioDecision:
    scenario: str
    risk_level: str
    message: str
    why_this_alert: str
    next_best_action: str


COLLECT_SCENARIO = "collect_request_confusion"
REFUND_SCENARIO = "refund_reward_kyc_scam"
UNKNOWN_PAYEE_SCENARIO = "unknown_payee_or_unusual_amount"
UNKNOWN_SCENARIO = "unknown"

_COLLECT_KEYWORDS = (
    "collect",
    "collect request",
    "request money",
    "approve request",
    "approve collect",
    "autopay",
    "mandate",
)
_REFUND_SCAM_KEYWORDS = (
    "refund",
    "cashback",
    "reward",
    "prize",
    "bonus",
    "kyc",
    "verify account",
    "update account",
)
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


def classify_payment_scenario(payload: UPIRequestInspectIn, *, language: str) -> PaymentScenarioDecision:
    raw_text = _normalize(payload.raw_text)
    app_name = _normalize(payload.app_name)
    payee_label = _normalize(payload.payee_label)
    payee_handle = _normalize(payload.payee_handle)
    request_kind = _normalize((payload.request_kind or "").replace("_", " ")).lower()

    if _looks_like_refund_reward_kyc_scam(raw_text, request_kind):
        return _refund_reward_kyc_decision(language)

    if _looks_like_collect_request(raw_text, request_kind):
        return _collect_request_decision(language)

    if _looks_like_unknown_payee_or_unusual_amount(
        raw_text=raw_text,
        app_name=app_name,
        payee_label=payee_label,
        payee_handle=payee_handle,
        amount=payload.amount,
        request_kind=request_kind,
    ):
        return _unknown_payee_or_unusual_amount_decision(
            language=language,
            amount=payload.amount,
            request_kind=request_kind,
        )

    return _fallback_decision(
        language=language,
        has_context=bool(raw_text or app_name or payee_label or payee_handle or payload.amount not in (None, 0)),
        request_kind=request_kind,
    )


def _looks_like_collect_request(raw_text: str, request_kind: str) -> bool:
    if request_kind in {"collect", "collect request"}:
        return True
    return any(keyword in raw_text for keyword in _COLLECT_KEYWORDS)


def _looks_like_refund_reward_kyc_scam(raw_text: str, request_kind: str) -> bool:
    if not any(keyword in raw_text for keyword in _REFUND_SCAM_KEYWORDS):
        return False
    if request_kind in {"collect", "collect request", "refund request", "unknown request"}:
        return True
    return any(keyword in raw_text for keyword in _COLLECT_KEYWORDS) or "fee" in raw_text or "pay" in raw_text


def _looks_like_unknown_payee_or_unusual_amount(
    *,
    raw_text: str,
    app_name: str,
    payee_label: str,
    payee_handle: str,
    amount: float | None,
    request_kind: str,
) -> bool:
    has_payment_signal = bool(raw_text or app_name or request_kind or amount not in (None, 0))
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


def _collect_request_decision(language: str) -> PaymentScenarioDecision:
    if language == "hi":
        return PaymentScenarioDecision(
            scenario=COLLECT_SCENARIO,
            risk_level="high",
            message="यह अनुरोध पैसा प्राप्त करने का नहीं है। इसे मंजूर करने पर आपके खाते से पैसा जा सकता है।",
            why_this_alert=(
                "कलेक्ट अनुरोध, ऑटोपे या मंजूरी वाले प्रॉम्प्ट कई बार आने वाले पैसे जैसे दिखते हैं,"
                " लेकिन इन्हें स्वीकार करने पर भुगतान बाहर जा सकता है।"
            ),
            next_best_action="रुकें और अलग से पुष्टि करें कि सामने वाला आपसे पैसा क्यों मांग रहा है।",
        )

    return PaymentScenarioDecision(
        scenario=COLLECT_SCENARIO,
        risk_level="high",
        message="This is not incoming money. Approving this request can send money from your account.",
        why_this_alert=(
            "Collect requests, approval prompts, and autopay mandates can look like money is coming in,"
            " but approval usually authorizes a payment out from your account."
        ),
        next_best_action="Pause and verify why this person or business is asking you to approve a payment.",
    )


def _refund_reward_kyc_decision(language: str) -> PaymentScenarioDecision:
    if language == "hi":
        return PaymentScenarioDecision(
            scenario=REFUND_SCENARIO,
            risk_level="high",
            message=(
                "असली रिफंड, इनाम या KYC अपडेट के लिए आपको पैसा भेजने की जरूरत नहीं होनी चाहिए।"
                " यह मंजूरी आपके खाते से पैसा भेज सकती है।"
            ),
            why_this_alert=(
                "ठगी में अक्सर रिफंड, कैशबैक, इनाम या KYC के नाम पर ऐसा अनुरोध भेजा जाता है"
                " जिससे आप कलेक्ट या फीस जैसा भुगतान मंजूर कर दें।"
            ),
            next_best_action="भुगतान ऐप के अंदर मंजूरी न दें। आधिकारिक ऐप या सपोर्ट से अलग से जांच करें।",
        )

    return PaymentScenarioDecision(
        scenario=REFUND_SCENARIO,
        risk_level="high",
        message=(
            "A real refund, reward, or KYC update should not require you to send money."
            " Approving this can send money from your account."
        ),
        why_this_alert=(
            "Scammers often use refund, cashback, reward, or KYC stories to make users approve"
            " a collect request or a fake verification fee."
        ),
        next_best_action="Do not approve inside the payment app. Check with the official app or support separately.",
    )


def _unknown_payee_or_unusual_amount_decision(
    *,
    language: str,
    amount: float | None,
    request_kind: str,
) -> PaymentScenarioDecision:
    risk_level = "high" if (amount or 0) >= _UNUSUAL_AMOUNT_HIGH else "medium"
    direction_line = _direction_line(language, request_kind)

    if language == "hi":
        return PaymentScenarioDecision(
            scenario=UNKNOWN_PAYEE_SCENARIO,
            risk_level=risk_level,
            message=(
                "यह अनुरोध किसी अनजान प्राप्तकर्ता या असामान्य राशि जैसा दिख रहा है। "
                f"{direction_line} मंजूरी देने से पहले रुककर जांच लें."
            ).strip(),
            why_this_alert=(
                "अर्थमंत्री को प्राप्तकर्ता की साफ पहचान नहीं मिली या राशि इतनी अलग दिखी कि"
                " हाथ से सत्यापन जरूरी हो गया।"
            ),
            next_best_action="प्राप्तकर्ता का नाम और राशि अलग से पुष्टि करें। कुछ भी अजीब लगे तो अस्वीकार करें।",
        )

    return PaymentScenarioDecision(
        scenario=UNKNOWN_PAYEE_SCENARIO,
        risk_level=risk_level,
        message=(
            "This request involves an unfamiliar payee or an amount that looks unusual. "
            f"{direction_line} Pause before you approve it."
        ).strip(),
        why_this_alert=(
            "Arthamantri could not match a clearly known payee, or the amount is large enough"
            " to deserve manual verification."
        ),
        next_best_action="Verify the payee name and amount on a separate channel. Decline if anything feels unexpected.",
    )


def _fallback_decision(language: str, *, has_context: bool, request_kind: str) -> PaymentScenarioDecision:
    direction_line = _direction_line(language, request_kind, fallback=True)

    if language == "hi":
        message = (
            "यह अनुरोध पूरी तरह साफ नहीं है। आगे बढ़ने से पहले रुककर जांच लें।"
            if has_context
            else "यह भुगतान अनुरोध साफ नहीं पढ़ा जा सका। आगे बढ़ने से पहले रुककर जांच लें।"
        )
        if direction_line:
            message = f"{message} {direction_line}"
        return PaymentScenarioDecision(
            scenario=UNKNOWN_SCENARIO,
            risk_level="medium",
            message=message,
            why_this_alert=(
                "ऐप इस भुगतान के मतलब को भरोसे के साथ तय नहीं कर सका, इसलिए यह सावधानी वाली चेतावनी दिखा रहा है।"
            ),
            next_best_action="रुकें और भेजने वाले या मांग करने वाले व्यक्ति से अलग से पुष्टि करें।",
        )

    message = (
        "This request is not fully clear yet. Pause and verify before you approve it."
        if has_context
        else "This payment request could not be read clearly. Pause and verify before you approve it."
    )
    if direction_line:
        message = f"{message} {direction_line}"
    return PaymentScenarioDecision(
        scenario=UNKNOWN_SCENARIO,
        risk_level="medium",
        message=message,
        why_this_alert=(
            "Arthamantri could not confidently interpret what this payment will do, so it is showing a cautious warning."
        ),
        next_best_action="Pause and verify the request source before continuing.",
    )


def _direction_line(language: str, request_kind: str, fallback: bool = False) -> str:
    outgoing_kinds = {"collect", "collect request", "send money", "refund request"}
    if request_kind in outgoing_kinds:
        return (
            "इस मंजूरी से आपके खाते से पैसा जा सकता है।"
            if language == "hi"
            else "If you approve, money can go out from your account."
        )
    if fallback:
        return (
            "ऐप अभी साफ नहीं बता पा रहा कि पैसा जाएगा या आएगा।"
            if language == "hi"
            else "Arthamantri still cannot confirm whether this will send money or receive money."
        )
    return ""


def _normalize(value: str | None) -> str:
    return " ".join((value or "").split()).lower()

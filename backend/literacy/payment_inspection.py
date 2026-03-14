from __future__ import annotations

from backend.api_models import UPIRequestInspectIn, UPIRequestInspectOut

DEFAULT_PAYMENT_INSPECTION_ACTIONS = ["pause", "decline", "proceed"]


def inspect_payment_request(
    payload: UPIRequestInspectIn,
    *,
    participant_id: str,
    language: str,
    alert_id: str,
) -> UPIRequestInspectOut:
    normalized_text = " ".join((payload.raw_text or "").split())
    app_name = " ".join((payload.app_name or "").split())
    payee_label = " ".join((payload.payee_label or "").split())
    payee_handle = " ".join((payload.payee_handle or "").split())
    request_kind = " ".join((payload.request_kind or "").split()).lower()

    context_bits = [bit for bit in [app_name, payee_label, payee_handle, request_kind] if bit]
    has_context = bool(context_bits or normalized_text or payload.amount not in (None, 0))

    if language == "hi":
        message = (
            "यह अनुरोध पूरी तरह साफ नहीं है। आगे बढ़ने से पहले रुककर जांच लें।"
            if has_context
            else "यह भुगतान अनुरोध साफ नहीं पढ़ा जा सका। आगे बढ़ने से पहले रुककर जांच लें।"
        )
        why_this_alert = (
            "ऐप इस भुगतान के मतलब को भरोसे के साथ तय नहीं कर सका, इसलिए यह सावधानी वाली चेतावनी दिखा रहा है।"
        )
        next_best_action = "रुकें और भेजने वाले या मांग करने वाले व्यक्ति से अलग से पुष्टि करें।"
    else:
        message = (
            "This request is not fully clear yet. Pause and verify before you approve it."
            if has_context
            else "This payment request could not be read clearly. Pause and verify before you approve it."
        )
        why_this_alert = (
            "Arthamantri could not confidently interpret what this payment will do, so it is showing a cautious warning."
        )
        next_best_action = "Pause and verify the request source before continuing."

    return UPIRequestInspectOut(
        scenario="unknown",
        risk_level="medium",
        message=message,
        why_this_alert=why_this_alert,
        next_best_action=next_best_action,
        actions=list(DEFAULT_PAYMENT_INSPECTION_ACTIONS),
        alert_id=alert_id,
    )

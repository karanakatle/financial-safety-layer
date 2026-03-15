from __future__ import annotations

from backend.api_models import UPIRequestInspectIn, UPIRequestInspectOut
from backend.literacy.payment_scenarios import classify_payment_scenario

DEFAULT_PAYMENT_INSPECTION_ACTIONS = ["pause", "decline", "proceed"]


def inspect_payment_request(
    payload: UPIRequestInspectIn,
    *,
    participant_id: str,
    language: str,
    alert_id: str,
) -> UPIRequestInspectOut:
    decision = classify_payment_scenario(payload, language=language)

    return UPIRequestInspectOut(
        scenario=decision.scenario,
        risk_level=decision.risk_level,
        message=decision.message,
        why_this_alert=decision.why_this_alert,
        next_best_action=decision.next_best_action,
        actions=list(DEFAULT_PAYMENT_INSPECTION_ACTIONS),
        alert_id=alert_id,
    )

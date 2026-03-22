from __future__ import annotations

from backend.api_models import UPIRequestInspectIn, UPIRequestInspectOut
from backend.literacy.messages import literacy_message
from backend.literacy.payment_scenarios import classify_payment_scenario
from backend.literacy.sequence_correlation import SequenceEvidence

DEFAULT_PAYMENT_INSPECTION_ACTIONS = ["pause", "decline", "proceed"]
DEFAULT_ACCOUNT_ACCESS_INSPECTION_ACTIONS = ["pause", "protect", "proceed"]


def inspect_payment_request(
    payload: UPIRequestInspectIn,
    *,
    participant_id: str,
    language: str,
    alert_id: str,
    entity_trust_state: str | None = None,
    entity_reputation_level: str | None = None,
    sequence_evidence: SequenceEvidence | None = None,
) -> UPIRequestInspectOut:
    decision = classify_payment_scenario(
        payload,
        language=language,
        entity_trust_state=entity_trust_state,
        entity_reputation_level=entity_reputation_level,
        sequence_evidence=sequence_evidence,
    )
    actions = (
        DEFAULT_ACCOUNT_ACCESS_INSPECTION_ACTIONS
        if decision.alert_family == "account_access"
        else DEFAULT_PAYMENT_INSPECTION_ACTIONS
    )
    title = _inspection_title(
        language=language,
        alert_family=decision.alert_family,
        scenario=decision.scenario,
    )
    primary_action_label = _inspection_primary_action_label(
        language=language,
        alert_family=decision.alert_family,
    )
    action_labels = _inspection_action_labels(
        language=language,
        alert_family=decision.alert_family,
    )
    proceed_confirmation_label = _inspection_proceed_confirmation_label(
        language=language,
        alert_family=decision.alert_family,
    )

    return UPIRequestInspectOut(
        scenario=decision.scenario,
        classification=decision.classification,
        should_warn=decision.should_warn,
        alert_family=decision.alert_family,
        title=title,
        risk_level=decision.risk_level,
        message=decision.message,
        why_this_alert=decision.why_this_alert,
        next_best_action=decision.next_best_action,
        primary_action_label=primary_action_label,
        actions=list(actions),
        action_labels=action_labels,
        proceed_confirmation_label=proceed_confirmation_label,
        sequence_score=(sequence_evidence.sequence_score if sequence_evidence else 0.0),
        sequence_window=(sequence_evidence.sequence_window if sequence_evidence else ""),
        sequence_summary=(sequence_evidence.sequence_summary if sequence_evidence else ""),
        sequence_trace=list(sequence_evidence.sequence_trace or []) if sequence_evidence else [],
        alert_id=alert_id,
    )


def _inspection_title(*, language: str, alert_family: str, scenario: str) -> str:
    if alert_family == "account_access":
        return literacy_message(language, "payment_inspection.ui.account_access_title")
    if scenario == "unknown":
        return literacy_message(language, "payment_inspection.ui.payment_uncertain_title")
    return literacy_message(language, "payment_inspection.ui.payment_risk_title")


def _inspection_primary_action_label(*, language: str, alert_family: str) -> str:
    if alert_family == "account_access":
        return literacy_message(language, "payment_inspection.ui.account_access_primary_action")
    return literacy_message(language, "payment_inspection.ui.payment_primary_action")


def _inspection_action_labels(*, language: str, alert_family: str) -> list[str]:
    prefix = "account_access" if alert_family == "account_access" else "payment"
    return [
        literacy_message(language, f"payment_inspection.ui.{prefix}_action_pause"),
        literacy_message(language, f"payment_inspection.ui.{prefix}_action_secondary"),
        literacy_message(language, f"payment_inspection.ui.{prefix}_action_tertiary"),
    ]


def _inspection_proceed_confirmation_label(*, language: str, alert_family: str) -> str:
    prefix = "account_access" if alert_family == "account_access" else "payment"
    return literacy_message(language, f"payment_inspection.ui.{prefix}_action_confirm")

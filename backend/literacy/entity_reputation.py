from __future__ import annotations


SUSPICIOUS_FEEDBACK_ACTIONS = {
    "decline",
    "pause",
    "trusted_person_requested",
    "trusted_person_launched",
    "support_requested",
    "support_opened",
}
SAFE_FEEDBACK_ACTIONS = {"proceed"}


def apply_reputation_observation(
    *,
    current_score: float,
    unique_participant_count: int,
    event_type: str | None,
    classification: str | None,
    link_clicked: bool,
    domain_class: str | None,
    is_new_participant: bool,
) -> tuple[float, dict[str, int]]:
    score = float(current_score)
    access_risk_delta = 0
    payment_risk_delta = 0

    normalized_event = (event_type or "").strip().lower()
    normalized_classification = (classification or "").strip().lower()
    normalized_domain_class = (domain_class or "").strip().lower()

    if is_new_participant:
        score += 0.25

    if normalized_event == "account_access_candidate":
        access_risk_delta += 1
        if link_clicked and normalized_domain_class in {"suspicious", "loan", "card"}:
            score += 2.5
        elif link_clicked and normalized_domain_class == "bank":
            score += 1.5
        else:
            score += 0.5
    elif normalized_event == "payment_candidate":
        payment_risk_delta += 1
        if link_clicked and normalized_domain_class in {"suspicious", "loan", "card"}:
            score += 2.0
        else:
            score += 0.5
    elif normalized_classification in {"account_access_candidate", "payment_candidate"}:
        score += 0.5

    return score, {
        "access_risk_delta": access_risk_delta,
        "payment_risk_delta": payment_risk_delta,
    }


def apply_reputation_feedback(
    *,
    current_score: float,
    action: str | None,
    telemetry_family: str | None,
) -> tuple[float, dict[str, int]]:
    score = float(current_score)
    suspicious_feedback_delta = 0
    safe_feedback_delta = 0

    normalized_action = (action or "").strip().lower()
    normalized_family = (telemetry_family or "").strip().lower()

    if normalized_action in SUSPICIOUS_FEEDBACK_ACTIONS:
        suspicious_feedback_delta += 1
        score += 2.0 if normalized_family == "account_access_warning" else 1.5
    elif normalized_action in SAFE_FEEDBACK_ACTIONS:
        safe_feedback_delta += 1
        score -= 1.0

    return score, {
        "suspicious_feedback_delta": suspicious_feedback_delta,
        "safe_feedback_delta": safe_feedback_delta,
    }


def apply_reputation_review(
    *,
    current_score: float,
    trust_state: str,
) -> tuple[float, dict[str, int]]:
    normalized = (trust_state or "").strip().lower()
    if normalized == "blocked":
        return float(current_score) + 6.0, {"manual_block_delta": 1, "manual_safe_delta": 0}
    if normalized in {"official_verified", "trusted_by_observation"}:
        return float(current_score) - 4.0, {"manual_block_delta": 0, "manual_safe_delta": 1}
    return float(current_score), {"manual_block_delta": 0, "manual_safe_delta": 0}


def reputation_risk_level(record: dict | None) -> str:
    if not record:
        return "none"
    manual_block_count = int(record.get("manual_block_count") or 0)
    if manual_block_count > 0:
        return "high"

    unique_participant_count = int(record.get("unique_participant_count") or 0)
    suspicious_feedback_count = int(record.get("suspicious_feedback_count") or 0)
    account_access_risk_count = int(record.get("account_access_risk_count") or 0)
    payment_risk_count = int(record.get("payment_risk_count") or 0)
    score = float(record.get("reputation_score") or 0.0)

    if unique_participant_count < 2:
        return "none"
    if score >= 6.0 and (account_access_risk_count >= 2 or suspicious_feedback_count >= 1):
        return "high"
    if score >= 3.0 and (account_access_risk_count >= 1 or payment_risk_count >= 2):
        return "medium"
    return "none"

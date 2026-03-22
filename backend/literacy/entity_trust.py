from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


TRUST_STATE_OFFICIAL_VERIFIED = "official_verified"
TRUST_STATE_TRUSTED_BY_OBSERVATION = "trusted_by_observation"
TRUST_STATE_FINANCIAL_UNKNOWN = "financial_unknown"
TRUST_STATE_UNDER_REVIEW = "under_review"
TRUST_STATE_SUSPICIOUS = "suspicious"
TRUST_STATE_BLOCKED = "blocked"

ENTITY_KIND_DOMAIN = "domain"

ENTITY_TYPE_BANK = "bank"
ENTITY_TYPE_NBFC = "nbfc"
ENTITY_TYPE_PAYMENT_GATEWAY = "payment_gateway"
ENTITY_TYPE_WALLET = "wallet"
ENTITY_TYPE_CARD = "card"
ENTITY_TYPE_UNKNOWN_FINANCIAL = "unknown_financial"
ENTITY_TYPE_UNKNOWN = "unknown"

SAFE_FEEDBACK_ACTIONS = {"proceed"}
SUSPICIOUS_FEEDBACK_ACTIONS = {
    "decline",
    "pause",
    "trusted_person_requested",
    "trusted_person_launched",
    "support_requested",
    "support_opened",
}

BENIGN_OBSERVATION_SCORE_DELTA = 10.0
USER_SAFE_FEEDBACK_SCORE_DELTA = 15.0
USER_SUSPICIOUS_FEEDBACK_SCORE_DELTA = 25.0
CONSISTENT_SOURCE_OBSERVATION_SCORE_DELTA = 5.0
CONSISTENT_TARGET_OBSERVATION_SCORE_DELTA = 5.0


@dataclass(frozen=True)
class EntityTrustSeed:
    entity_type: str
    trust_state: str
    trust_score: float


def seed_for_domain_class(domain_class: str | None) -> EntityTrustSeed:
    normalized = (domain_class or "").strip().lower()
    if normalized == "official":
        return EntityTrustSeed(ENTITY_TYPE_BANK, TRUST_STATE_OFFICIAL_VERIFIED, 100.0)
    if normalized == "bank":
        return EntityTrustSeed(ENTITY_TYPE_BANK, TRUST_STATE_FINANCIAL_UNKNOWN, 0.0)
    if normalized == "loan":
        return EntityTrustSeed(ENTITY_TYPE_NBFC, TRUST_STATE_FINANCIAL_UNKNOWN, 0.0)
    if normalized == "card":
        return EntityTrustSeed(ENTITY_TYPE_CARD, TRUST_STATE_FINANCIAL_UNKNOWN, 0.0)
    if normalized == "payment_link":
        return EntityTrustSeed(ENTITY_TYPE_PAYMENT_GATEWAY, TRUST_STATE_FINANCIAL_UNKNOWN, 0.0)
    if normalized == "suspicious":
        return EntityTrustSeed(ENTITY_TYPE_UNKNOWN_FINANCIAL, TRUST_STATE_SUSPICIOUS, -60.0)
    return EntityTrustSeed(ENTITY_TYPE_UNKNOWN, TRUST_STATE_FINANCIAL_UNKNOWN, 0.0)


def apply_observation(
    *,
    current_state: str,
    current_score: float,
    review_status: str,
    benign_count: int,
    suspicious_count: int,
    user_safe_feedback_count: int,
    user_suspicious_feedback_count: int,
    domain_class: str | None,
    event_type: str | None,
    classification: str | None,
    link_clicked: bool,
    source_app: str | None,
    target_app: str | None,
    timestamp: str | None,
    evidence: dict | None,
) -> tuple[str, float, dict[str, int], dict[str, object]]:
    score = float(current_score)
    benign_delta = 0
    suspicious_delta = 0
    payment_risk_delta = 0
    access_risk_delta = 0
    evidence_updates: dict[str, object] = {}

    normalized_event = (event_type or "").strip().lower()
    normalized_classification = (classification or "").strip().lower()
    normalized_domain_class = (domain_class or "").strip().lower()
    normalized_source_app = (source_app or "").strip().lower()
    normalized_target_app = (target_app or "").strip().lower()
    prior_evidence = evidence or {}
    benign_day_count = _benign_day_count(prior_evidence)
    strong_consistency_signal = _has_strong_consistency_signal(prior_evidence)

    if normalized_domain_class == "suspicious":
        score -= 20.0
        suspicious_delta += 1

    if normalized_event == "account_access_candidate" and link_clicked and normalized_domain_class in {"suspicious", "loan", "card"}:
        score -= 20.0
        suspicious_delta += 1
        access_risk_delta += 1
    elif normalized_event == "payment_candidate" and link_clicked and normalized_domain_class == "suspicious":
        score -= 30.0
        suspicious_delta += 1
        payment_risk_delta += 1
    elif normalized_classification in {"observed", "suppressed"} and normalized_domain_class in {"official", "bank", "payment_link", "loan", "card", "unknown"}:
        score += BENIGN_OBSERVATION_SCORE_DELTA
        benign_delta += 1
        benign_day_count = _apply_benign_time_evidence(
            evidence=prior_evidence,
            timestamp=timestamp,
            evidence_updates=evidence_updates,
        )

    score += _apply_consistency_bonus(
        evidence=prior_evidence,
        source_app=normalized_source_app,
        target_app=normalized_target_app,
        evidence_updates=evidence_updates,
    )
    strong_consistency_signal = _has_strong_consistency_signal(
        {
            **prior_evidence,
            **evidence_updates,
        }
    )

    next_state = derive_trust_state(
        current_state=current_state,
        review_status=review_status,
        score=score,
        benign_count=benign_count + benign_delta,
        benign_day_count=benign_day_count,
        suspicious_count=suspicious_count + suspicious_delta,
        user_safe_feedback_count=user_safe_feedback_count,
        user_suspicious_feedback_count=user_suspicious_feedback_count,
        strong_consistency_signal=strong_consistency_signal,
    )
    return next_state, score, {
        "benign_delta": benign_delta,
        "suspicious_delta": suspicious_delta,
        "payment_risk_delta": payment_risk_delta,
        "access_risk_delta": access_risk_delta,
    }, evidence_updates


def apply_feedback(
    *,
    current_state: str,
    current_score: float,
    review_status: str,
    benign_count: int,
    benign_day_count: int,
    suspicious_count: int,
    user_safe_feedback_count: int,
    user_suspicious_feedback_count: int,
    feedback_action: str | None,
    telemetry_family: str | None,
    strong_consistency_signal: bool,
) -> tuple[str, float, dict[str, int]]:
    score = float(current_score)
    safe_feedback_delta = 0
    suspicious_feedback_delta = 0
    suspicious_delta = 0
    payment_risk_delta = 0
    access_risk_delta = 0

    normalized_action = (feedback_action or "").strip().lower()
    normalized_telemetry_family = (telemetry_family or "").strip().lower()

    if normalized_action in SAFE_FEEDBACK_ACTIONS:
        score += USER_SAFE_FEEDBACK_SCORE_DELTA
        safe_feedback_delta += 1
    elif normalized_action in SUSPICIOUS_FEEDBACK_ACTIONS:
        score -= USER_SUSPICIOUS_FEEDBACK_SCORE_DELTA
        suspicious_feedback_delta += 1
        suspicious_delta += 1
        if normalized_telemetry_family == "account_access_warning":
            access_risk_delta += 1
        elif normalized_telemetry_family == "payment_warning":
            payment_risk_delta += 1

    next_state = derive_trust_state(
        current_state=current_state,
        review_status=review_status,
        score=score,
        benign_count=benign_count,
        benign_day_count=benign_day_count,
        suspicious_count=suspicious_count + suspicious_delta,
        user_safe_feedback_count=user_safe_feedback_count + safe_feedback_delta,
        user_suspicious_feedback_count=user_suspicious_feedback_count + suspicious_feedback_delta,
        strong_consistency_signal=strong_consistency_signal,
    )
    return next_state, score, {
        "user_safe_feedback_delta": safe_feedback_delta,
        "user_suspicious_feedback_delta": suspicious_feedback_delta,
        "suspicious_delta": suspicious_delta,
        "payment_risk_delta": payment_risk_delta,
        "access_risk_delta": access_risk_delta,
    }


def derive_trust_state(
    *,
    current_state: str,
    review_status: str,
    score: float,
    benign_count: int,
    benign_day_count: int,
    suspicious_count: int,
    user_safe_feedback_count: int,
    user_suspicious_feedback_count: int,
    strong_consistency_signal: bool,
) -> str:
    normalized = (current_state or "").strip().lower()
    normalized_review_status = (review_status or "").strip().lower()
    if normalized_review_status == "manual_override":
        return normalized
    if normalized in {TRUST_STATE_OFFICIAL_VERIFIED, TRUST_STATE_BLOCKED}:
        return normalized
    if normalized == TRUST_STATE_SUSPICIOUS and score < 25.0:
        return TRUST_STATE_SUSPICIOUS
    if score <= -40.0:
        return TRUST_STATE_SUSPICIOUS
    if normalized == TRUST_STATE_TRUSTED_BY_OBSERVATION and (suspicious_count > 0 or user_suspicious_feedback_count > 0):
        return TRUST_STATE_UNDER_REVIEW
    if normalized == TRUST_STATE_TRUSTED_BY_OBSERVATION:
        return TRUST_STATE_TRUSTED_BY_OBSERVATION
    if (
        suspicious_count == 0 and
        user_suspicious_feedback_count == 0 and
        score >= 20.0 and
        (
            benign_day_count >= 2 or
            (benign_day_count >= 1 and benign_count >= 1 and user_safe_feedback_count >= 1) or
            (strong_consistency_signal and benign_count >= 2 and score >= 30.0)
        )
    ):
        return TRUST_STATE_TRUSTED_BY_OBSERVATION
    if suspicious_count > 0:
        return TRUST_STATE_UNDER_REVIEW
    return TRUST_STATE_FINANCIAL_UNKNOWN


def manual_override_score(trust_state: str, current_score: float = 0.0) -> float:
    normalized = (trust_state or "").strip().lower()
    if normalized == TRUST_STATE_OFFICIAL_VERIFIED:
        return 100.0
    if normalized == TRUST_STATE_TRUSTED_BY_OBSERVATION:
        return 40.0
    if normalized == TRUST_STATE_FINANCIAL_UNKNOWN:
        return 0.0
    if normalized == TRUST_STATE_UNDER_REVIEW:
        return -10.0
    if normalized == TRUST_STATE_SUSPICIOUS:
        return -60.0
    if normalized == TRUST_STATE_BLOCKED:
        return -100.0
    return float(current_score)


def _apply_consistency_bonus(
    *,
    evidence: dict,
    source_app: str,
    target_app: str,
    evidence_updates: dict[str, object],
) -> float:
    bonus = 0.0

    previous_source = str(evidence.get("canonical_source_app") or "").strip().lower()
    previous_target = str(evidence.get("canonical_target_app") or "").strip().lower()
    source_consistency_count = int(evidence.get("source_consistency_count") or 0)
    target_consistency_count = int(evidence.get("target_consistency_count") or 0)
    source_mismatch_count = int(evidence.get("source_mismatch_count") or 0)
    target_mismatch_count = int(evidence.get("target_mismatch_count") or 0)

    if source_app:
        if not previous_source:
            evidence_updates["canonical_source_app"] = source_app
            evidence_updates["source_consistency_count"] = 1
        elif previous_source == source_app:
            next_count = source_consistency_count + 1
            evidence_updates["canonical_source_app"] = previous_source
            evidence_updates["source_consistency_count"] = next_count
            if source_consistency_count >= 1:
                bonus += CONSISTENT_SOURCE_OBSERVATION_SCORE_DELTA
        else:
            evidence_updates["source_mismatch_count"] = source_mismatch_count + 1

    if target_app:
        if not previous_target:
            evidence_updates["canonical_target_app"] = target_app
            evidence_updates["target_consistency_count"] = 1
        elif previous_target == target_app:
            next_count = target_consistency_count + 1
            evidence_updates["canonical_target_app"] = previous_target
            evidence_updates["target_consistency_count"] = next_count
            if target_consistency_count >= 1:
                bonus += CONSISTENT_TARGET_OBSERVATION_SCORE_DELTA
        else:
            evidence_updates["target_mismatch_count"] = target_mismatch_count + 1

    return bonus


def _apply_benign_time_evidence(
    *,
    evidence: dict,
    timestamp: str | None,
    evidence_updates: dict[str, object],
) -> int:
    benign_day = _coerce_day(timestamp)
    prior_days = [str(day) for day in evidence.get("benign_days", []) if str(day).strip()]
    prior_first = str(evidence.get("first_benign_at") or "").strip()
    prior_last = str(evidence.get("last_benign_at") or "").strip()

    if timestamp:
        if not prior_first:
            evidence_updates["first_benign_at"] = timestamp
        evidence_updates["last_benign_at"] = timestamp
    elif prior_first:
        evidence_updates["first_benign_at"] = prior_first
        evidence_updates["last_benign_at"] = prior_last or prior_first

    if benign_day and benign_day not in prior_days:
        prior_days = [*prior_days, benign_day]
    if prior_days:
        evidence_updates["benign_days"] = prior_days[-30:]
        evidence_updates["distinct_benign_days"] = len(prior_days[-30:])
        return len(prior_days[-30:])
    return int(evidence.get("distinct_benign_days") or 0)


def _benign_day_count(evidence: dict) -> int:
    explicit = int(evidence.get("distinct_benign_days") or 0)
    if explicit > 0:
        return explicit
    days = [str(day) for day in evidence.get("benign_days", []) if str(day).strip()]
    return len(days)


def _has_strong_consistency_signal(evidence: dict) -> bool:
    source_count = int(evidence.get("source_consistency_count") or 0)
    target_count = int(evidence.get("target_consistency_count") or 0)
    return (source_count >= 2 and target_count >= 2) or source_count >= 3 or target_count >= 3


def _coerce_day(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None

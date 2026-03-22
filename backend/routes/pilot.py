from __future__ import annotations

import os
from datetime import datetime
from typing import Callable, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from backend.api_models import (
    ExperimentAssignIn,
    ExperimentEventIn,
    PilotAppLogIn,
    PilotConsentIn,
    PilotEntityReviewIn,
    PilotFeedbackIn,
    PilotGrievanceIn,
    PilotGrievanceStatusIn,
    PilotReviewSampleUpsertIn,
)
from backend.literacy.domain_intelligence import enrich_domain_context
from backend.literacy.entity_trust import (
    ENTITY_KIND_DOMAIN,
    apply_observation,
    manual_override_score,
    seed_for_domain_class,
)
from backend.literacy.entity_reputation import (
    apply_reputation_observation,
    apply_reputation_review,
)
from backend.literacy.sequence_correlation import build_recent_sequence_groups
from backend.literacy.messages import literacy_message
from backend.pilot.telemetry import record_client_app_log_telemetry


def build_pilot_router(
    *,
    pilot_storage,
    resolve_experiment_variant: Callable[[str, str], str],
    require_admin: Callable[[Request], None],
) -> APIRouter:
    router = APIRouter()

    def _resolve_review_material(
        *,
        participant_id: str | None,
        correlation_id: str | None,
        source_tier: str,
        event_trace: list[dict],
        sequence_trace: list[dict],
        entity_context: dict,
        alert_family: str,
        heuristic_classification: str,
        language: str | None,
        cohort: str | None,
    ) -> dict:
        normalized_participant = (participant_id or "").strip()
        normalized_correlation = (correlation_id or "").strip()
        resolved_event_trace = list(event_trace or [])
        resolved_sequence_trace = list(sequence_trace or [])
        resolved_entity_context = dict(entity_context or {})
        resolved_alert_family = (alert_family or "").strip()
        resolved_heuristic_classification = (heuristic_classification or "").strip()
        resolved_language = (language or "").strip().lower()
        resolved_cohort = (cohort or "").strip()

        if source_tier != "live_reviewed_ground_truth" or not normalized_participant or not normalized_correlation:
            return {
                "event_trace": resolved_event_trace,
                "sequence_trace": resolved_sequence_trace,
                "entity_context": resolved_entity_context,
                "alert_family": resolved_alert_family,
                "heuristic_classification": resolved_heuristic_classification,
                "language": resolved_language or None,
                "cohort": resolved_cohort or None,
            }

        live_context_events = list(
            reversed(
                pilot_storage.recent_app_logs(
                    participant_id=normalized_participant,
                    correlation_id=normalized_correlation,
                    limit=120,
                    context_only=True,
                )
            )
        )
        if not resolved_event_trace:
            resolved_event_trace = live_context_events

        if not resolved_sequence_trace:
            matching_groups = [
                group
                for group in build_recent_sequence_groups(
                    pilot_storage=pilot_storage,
                    participant_id=normalized_participant,
                    limit=100,
                )
                if str(group.get("correlation_id") or "").strip() == normalized_correlation
            ]
            resolved_sequence_trace = matching_groups[0]["trace"] if matching_groups else []

        latest_event = live_context_events[-1] if live_context_events else {}
        profile = pilot_storage.get_essential_goal_profile(normalized_participant)
        resolved_language = (
            resolved_language
            or str(latest_event.get("language") or "").strip().lower()
            or str((profile or {}).get("language") or "").strip().lower()
            or "en"
        )
        resolved_cohort = (
            resolved_cohort
            or str((profile or {}).get("cohort") or "").strip()
            or "unknown"
        )
        resolved_alert_family = (
            resolved_alert_family
            or str(latest_event.get("classification") or "").strip()
        )
        resolved_heuristic_classification = (
            resolved_heuristic_classification
            or str(latest_event.get("classification") or "").strip()
        )

        if not resolved_entity_context:
            domain_event = next(
                (
                    record
                    for record in reversed(live_context_events)
                    if str(record.get("resolved_domain") or "").strip()
                ),
                None,
            )
            if domain_event:
                entity_key = str(domain_event.get("resolved_domain") or "").strip()
                entity_kind = ENTITY_KIND_DOMAIN
                entity_record = pilot_storage.get_entity(entity_key=entity_key, entity_kind=entity_kind)
                entity_reputation = pilot_storage.get_entity_reputation(entity_key=entity_key, entity_kind=entity_kind)
                cohort_reputation = pilot_storage.get_entity_cohort_reputation(
                    entity_key=entity_key,
                    entity_kind=entity_kind,
                    cohort=resolved_cohort,
                )
                resolved_entity_context = {
                    "entity_key": entity_key,
                    "entity_kind": entity_kind,
                    "url_host": domain_event.get("url_host"),
                    "resolved_domain": domain_event.get("resolved_domain"),
                    "domain_class": domain_event.get("domain_class"),
                    "source_app": domain_event.get("source_app"),
                    "target_app": domain_event.get("target_app"),
                    "trust_state": (entity_record or {}).get("trust_state"),
                    "trust_score": (entity_record or {}).get("trust_score"),
                    "entity_review_status": (entity_record or {}).get("review_status"),
                    "entity_reputation_score": (entity_reputation or {}).get("reputation_score"),
                    "cohort_reputation_score": (cohort_reputation or {}).get("reputation_score"),
                }

        return {
            "event_trace": resolved_event_trace,
            "sequence_trace": resolved_sequence_trace,
            "entity_context": resolved_entity_context,
            "alert_family": resolved_alert_family,
            "heuristic_classification": resolved_heuristic_classification,
            "language": resolved_language or None,
            "cohort": resolved_cohort or None,
        }

    @router.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @router.get("/api/pilot/meta")
    def pilot_meta(language: Optional[str] = None) -> dict:
        normalized_language = "hi" if (language or "").strip().lower().startswith("hi") else "en"
        return {
            "pilot_mode": True,
            "target_cohort_size": 60,
            "frozen_cohorts": ["women_led_household", "daily_cashflow_worker"],
            "frozen_use_cases": [
                "overspending_prevention",
                "fraud_prevention",
                "essential_goal_savings_behavior",
            ],
            "disclaimer": literacy_message(normalized_language, "pilot_disclaimer"),
            "alert_policy": {
                "income": "informational_only",
                "overspending": "stage1_near_threshold_once",
                "upi_open": "stage2_first_open_after_stage1_once",
                "lockscreen_alerts": False,
            },
        }

    @router.post("/api/pilot/consent")
    def pilot_consent(payload: PilotConsentIn) -> dict:
        event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
        record = {
            "participant_id": payload.participant_id,
            "accepted": payload.accepted,
            "language": payload.language,
            "timestamp": event_timestamp,
        }
        pilot_storage.upsert_consent(
            participant_id=payload.participant_id,
            accepted=payload.accepted,
            language=payload.language,
            timestamp=event_timestamp,
        )
        return {"ok": True, "consent": record}

    @router.post("/api/pilot/feedback")
    def pilot_feedback_submit(payload: PilotFeedbackIn) -> dict:
        event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
        pilot_storage.add_feedback(
            participant_id=payload.participant_id,
            rating=payload.rating,
            comment=payload.comment.strip(),
            language=payload.language,
            timestamp=event_timestamp,
        )
        return {"ok": True, "feedback_count": pilot_storage.summary()["feedback_count"]}

    @router.get("/api/pilot/summary")
    def pilot_summary(
        request: Request,
        participant_id: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 200))
        return {
            **pilot_storage.summary(),
            "participant_id": participant_id,
            "telemetry_comparison": pilot_storage.unified_telemetry_comparison(
                participant_id=participant_id,
                limit=safe_limit * 4,
            ),
            "recent_unified_telemetry": pilot_storage.recent_unified_telemetry(
                participant_id=participant_id,
                limit=safe_limit,
            ),
            "recent_sequence_traces": build_recent_sequence_groups(
                pilot_storage=pilot_storage,
                participant_id=participant_id,
                limit=safe_limit,
            ),
        }

    @router.get("/api/pilot/analytics")
    def pilot_analytics(
        request: Request,
        participant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 200))
        return {
            **pilot_storage.analytics(
                recent_limit=safe_limit,
                participant_id=participant_id,
                event_type=event_type,
                correlation_id=correlation_id,
            ),
            "participant_id": participant_id,
            "event_type": event_type,
            "correlation_id": correlation_id,
            "recent_entities": pilot_storage.recent_entities(limit=safe_limit),
            "entity_breakdown": pilot_storage.entity_breakdown(),
            "recent_entity_reputations": pilot_storage.recent_entity_reputations(limit=safe_limit),
            "entity_reputation_breakdown": pilot_storage.entity_reputation_breakdown(),
            "recent_entity_cohort_reputations": pilot_storage.recent_entity_cohort_reputations(limit=safe_limit),
            "entity_cohort_reputation_breakdown": pilot_storage.entity_cohort_reputation_breakdown(),
            "telemetry_comparison": pilot_storage.unified_telemetry_comparison(
                participant_id=participant_id,
                limit=safe_limit * 4,
            ),
            "recent_unified_telemetry": pilot_storage.recent_unified_telemetry(
                participant_id=participant_id,
                limit=safe_limit,
            ),
        }

    @router.get("/api/pilot/review")
    def pilot_review(
        request: Request,
        participant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 200))
        return {
            "participant_id": participant_id,
            "event_type": event_type,
            "correlation_id": correlation_id,
            "telemetry_comparison": pilot_storage.unified_telemetry_comparison(
                participant_id=participant_id,
                limit=safe_limit * 4,
            ),
            "recent_unified_telemetry": pilot_storage.recent_unified_telemetry(
                participant_id=participant_id,
                limit=safe_limit,
            ),
            "recent_literacy_events": (
                pilot_storage.recent_literacy_events(participant_id, safe_limit)
                if participant_id
                else []
            ),
            "recent_alert_features": (
                pilot_storage.recent_alert_features(participant_id, safe_limit)
                if participant_id
                else []
            ),
            "recent_alert_feedback": (
                pilot_storage.recent_alert_feedback(participant_id, safe_limit)
                if participant_id
                else []
            ),
            "recent_context_events": pilot_storage.recent_app_logs(
                participant_id=participant_id,
                limit=safe_limit,
                event_type=event_type,
                correlation_id=correlation_id,
                context_only=True,
            ),
            "recent_sequence_traces": build_recent_sequence_groups(
                pilot_storage=pilot_storage,
                participant_id=participant_id,
                limit=safe_limit,
            ),
            "context_event_breakdown": pilot_storage.context_event_breakdown(participant_id=participant_id),
            "recent_entities": pilot_storage.recent_entities(limit=safe_limit),
            "entity_breakdown": pilot_storage.entity_breakdown(),
            "recent_entity_reputations": pilot_storage.recent_entity_reputations(limit=safe_limit),
            "entity_reputation_breakdown": pilot_storage.entity_reputation_breakdown(),
            "recent_entity_cohort_reputations": pilot_storage.recent_entity_cohort_reputations(limit=safe_limit),
            "entity_cohort_reputation_breakdown": pilot_storage.entity_cohort_reputation_breakdown(),
            "recent_review_samples": pilot_storage.recent_review_samples(
                participant_id=participant_id,
                correlation_id=correlation_id,
                limit=safe_limit,
            ),
            "review_sample_breakdown": pilot_storage.review_sample_breakdown(),
        }

    @router.post("/api/pilot/review-samples")
    def pilot_review_sample_upsert(request: Request, payload: PilotReviewSampleUpsertIn) -> dict:
        require_admin(request)
        event_timestamp = payload.reviewed_at or datetime.utcnow().isoformat()
        sample_id = (payload.sample_id or "").strip() or f"review-sample-{uuid4().hex}"
        source_tier = (payload.source_tier or "").strip().lower()
        source_origin = (payload.source_origin or "").strip().lower() or (
            "participant_trace" if source_tier == "live_reviewed_ground_truth" else "website"
        )
        review_status = (payload.review_status or "").strip().lower() or "queued"
        participant_id = (payload.participant_id or "").strip() or None
        correlation_id = (payload.correlation_id or "").strip() or None

        if source_tier == "live_reviewed_ground_truth" and (not participant_id or not correlation_id):
            raise HTTPException(status_code=400, detail="live_reviewed_ground_truth requires participant_id and correlation_id")
        if source_tier == "bootstrap_public" and review_status == "approved_ground_truth":
            raise HTTPException(status_code=400, detail="bootstrap_public cannot be approved as ground truth")
        if review_status == "bootstrap_only" and source_tier != "bootstrap_public":
            raise HTTPException(status_code=400, detail="bootstrap_only is only valid for bootstrap_public samples")
        if review_status == "approved_ground_truth" and not payload.label:
            raise HTTPException(status_code=400, detail="approved_ground_truth requires a label")

        resolved = _resolve_review_material(
            participant_id=participant_id,
            correlation_id=correlation_id,
            source_tier=source_tier,
            event_trace=payload.event_trace,
            sequence_trace=payload.sequence_trace,
            entity_context=payload.entity_context,
            alert_family=payload.alert_family,
            heuristic_classification=payload.heuristic_classification,
            language=payload.language,
            cohort=payload.cohort,
        )
        pilot_storage.upsert_review_sample(
            sample_id=sample_id,
            participant_id=participant_id,
            correlation_id=correlation_id,
            source_tier=source_tier,
            source_origin=source_origin,
            label=payload.label,
            review_status=review_status,
            reviewer_id=(payload.reviewer_id or "").strip() or None,
            reviewed_at=event_timestamp,
            event_trace=resolved["event_trace"],
            sequence_trace=resolved["sequence_trace"],
            entity_context=resolved["entity_context"],
            alert_family=resolved["alert_family"],
            heuristic_classification=resolved["heuristic_classification"],
            language=resolved["language"],
            cohort=resolved["cohort"],
            note=payload.note,
            updated_at=event_timestamp,
        )
        stored = pilot_storage.recent_review_samples(limit=1, review_status=review_status, participant_id=participant_id, correlation_id=correlation_id)
        matching = next((item for item in stored if item["sample_id"] == sample_id), None)
        if not matching:
            matching = next(
                (
                    item
                    for item in pilot_storage.recent_review_samples(limit=200)
                    if item["sample_id"] == sample_id
                ),
                None,
            )
        return {"ok": True, "sample": matching}

    @router.get("/api/pilot/review-samples")
    def pilot_review_samples(
        request: Request,
        participant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        source_tier: Optional[str] = None,
        source_origin: Optional[str] = None,
        review_status: Optional[str] = None,
        label: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 500))
        records = pilot_storage.recent_review_samples(
            participant_id=participant_id,
            correlation_id=correlation_id,
            source_tier=(source_tier or None),
            source_origin=(source_origin or None),
            review_status=(review_status or None),
            label=(label or None),
            limit=safe_limit,
        )
        return {
            "participant_id": participant_id,
            "correlation_id": correlation_id,
            "source_tier": source_tier,
            "source_origin": source_origin,
            "review_status": review_status,
            "label": label,
            "count": len(records),
            "review_samples": records,
            "breakdown": pilot_storage.review_sample_breakdown(),
        }

    @router.get("/api/pilot/review-exports")
    def pilot_review_exports(
        request: Request,
        mode: str = "gold_ground_truth_only",
        include_uncertain: bool = False,
        limit: int = 500,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 5000))
        export_version = f"review-export-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
        records = [
            {
                **row,
                "export_version": export_version,
            }
            for row in pilot_storage.export_review_samples(
                mode=mode,
                include_uncertain=include_uncertain,
                limit=safe_limit,
            )
        ]
        return {
            "mode": mode,
            "include_uncertain": include_uncertain,
            "count": len(records),
            "export_version": export_version,
            "generated_at": datetime.utcnow().isoformat(),
            "records": records,
        }

    @router.get("/api/pilot/entities")
    def pilot_entities(
        request: Request,
        entity_kind: Optional[str] = None,
        trust_state: Optional[str] = None,
        review_status: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 500))
        records = pilot_storage.recent_entities(
            entity_kind=entity_kind,
            trust_state=trust_state,
            review_status=review_status,
            limit=safe_limit,
        )
        return {
            "entity_kind": entity_kind,
            "trust_state": trust_state,
            "review_status": review_status,
            "count": len(records),
            "entities": records,
            "breakdown": pilot_storage.entity_breakdown(),
        }

    @router.get("/api/pilot/entity-reputations")
    def pilot_entity_reputations(
        request: Request,
        entity_kind: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 500))
        records = pilot_storage.recent_entity_reputations(entity_kind=entity_kind, limit=safe_limit)
        return {
            "entity_kind": entity_kind,
            "count": len(records),
            "entity_reputations": records,
            "breakdown": pilot_storage.entity_reputation_breakdown(),
        }

    @router.get("/api/pilot/entity-cohort-reputations")
    def pilot_entity_cohort_reputations(
        request: Request,
        entity_kind: Optional[str] = None,
        cohort: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 500))
        records = pilot_storage.recent_entity_cohort_reputations(
            entity_kind=entity_kind,
            cohort=cohort,
            limit=safe_limit,
        )
        return {
            "entity_kind": entity_kind,
            "cohort": cohort,
            "count": len(records),
            "entity_cohort_reputations": records,
            "breakdown": pilot_storage.entity_cohort_reputation_breakdown(),
        }

    @router.post("/api/pilot/entities/review")
    def pilot_entity_review(request: Request, payload: PilotEntityReviewIn) -> dict:
        require_admin(request)
        event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
        existing = pilot_storage.get_entity(
            entity_key=payload.entity_key,
            entity_kind=payload.entity_kind,
        )
        reputation = pilot_storage.get_entity_reputation(
            entity_key=payload.entity_key,
            entity_kind=payload.entity_kind,
        )
        cohort_records = pilot_storage.recent_entity_cohort_reputations(
            entity_kind=payload.entity_kind,
            limit=500,
        )
        if not existing:
            return {"ok": False, "reason": "entity_not_found"}

        pilot_storage.upsert_entity(
            entity_key=payload.entity_key,
            entity_kind=payload.entity_kind,
            entity_type=str(existing.get("entity_type") or "unknown"),
            trust_state=payload.trust_state,
            trust_score=manual_override_score(payload.trust_state, float(existing.get("trust_score") or 0.0)),
            review_status=(payload.review_status or "manual_override").strip().lower() or "manual_override",
            timestamp=event_timestamp,
            benign_count=int(existing.get("benign_count") or 0),
            suspicious_count=int(existing.get("suspicious_count") or 0),
            user_safe_feedback_count=int(existing.get("user_safe_feedback_count") or 0),
            user_suspicious_feedback_count=int(existing.get("user_suspicious_feedback_count") or 0),
            account_access_risk_count=int(existing.get("account_access_risk_count") or 0),
            payment_risk_count=int(existing.get("payment_risk_count") or 0),
            evidence={
                **(existing.get("evidence") or {}),
                "last_review_note": payload.note.strip(),
                "last_reviewed_at": event_timestamp,
                "last_reviewed_state": payload.trust_state,
            },
        )
        next_reputation_score, reputation_deltas = apply_reputation_review(
            current_score=float((reputation or {}).get("reputation_score") or 0.0),
            trust_state=payload.trust_state,
        )
        pilot_storage.upsert_entity_reputation(
            entity_key=payload.entity_key,
            entity_kind=payload.entity_kind,
            reputation_score=next_reputation_score,
            unique_participant_count=int((reputation or {}).get("unique_participant_count") or 0),
            suspicious_feedback_count=int((reputation or {}).get("suspicious_feedback_count") or 0),
            safe_feedback_count=int((reputation or {}).get("safe_feedback_count") or 0),
            account_access_risk_count=int((reputation or {}).get("account_access_risk_count") or 0),
            payment_risk_count=int((reputation or {}).get("payment_risk_count") or 0),
            manual_block_count=int((reputation or {}).get("manual_block_count") or 0) + reputation_deltas["manual_block_delta"],
            manual_safe_count=int((reputation or {}).get("manual_safe_count") or 0) + reputation_deltas["manual_safe_delta"],
            timestamp=event_timestamp,
            evidence={
                **((reputation or {}).get("evidence") or {}),
                "last_review_note": payload.note.strip(),
                "last_reviewed_at": event_timestamp,
                "last_reviewed_state": payload.trust_state,
            },
        )
        for cohort_record in cohort_records:
            if cohort_record.get("entity_key") != payload.entity_key:
                continue
            next_cohort_reputation_score, cohort_reputation_deltas = apply_reputation_review(
                current_score=float(cohort_record.get("reputation_score") or 0.0),
                trust_state=payload.trust_state,
            )
            pilot_storage.upsert_entity_cohort_reputation(
                entity_key=payload.entity_key,
                entity_kind=payload.entity_kind,
                cohort=str(cohort_record.get("cohort") or "unknown"),
                reputation_score=next_cohort_reputation_score,
                unique_participant_count=int(cohort_record.get("unique_participant_count") or 0),
                suspicious_feedback_count=int(cohort_record.get("suspicious_feedback_count") or 0),
                safe_feedback_count=int(cohort_record.get("safe_feedback_count") or 0),
                account_access_risk_count=int(cohort_record.get("account_access_risk_count") or 0),
                payment_risk_count=int(cohort_record.get("payment_risk_count") or 0),
                manual_block_count=int(cohort_record.get("manual_block_count") or 0) + cohort_reputation_deltas["manual_block_delta"],
                manual_safe_count=int(cohort_record.get("manual_safe_count") or 0) + cohort_reputation_deltas["manual_safe_delta"],
                timestamp=event_timestamp,
                evidence={
                    **(cohort_record.get("evidence") or {}),
                    "last_review_note": payload.note.strip(),
                    "last_reviewed_at": event_timestamp,
                    "last_reviewed_state": payload.trust_state,
                },
            )
        updated = pilot_storage.get_entity(entity_key=payload.entity_key, entity_kind=payload.entity_kind)
        updated_reputation = pilot_storage.get_entity_reputation(entity_key=payload.entity_key, entity_kind=payload.entity_kind)
        updated_cohort_reputations = [
            record
            for record in pilot_storage.recent_entity_cohort_reputations(entity_kind=payload.entity_kind, limit=500)
            if record.get("entity_key") == payload.entity_key
        ]
        return {"ok": True, "entity": updated, "entity_reputation": updated_reputation, "entity_cohort_reputations": updated_cohort_reputations}

    @router.get("/api/pilot/context-events")
    def pilot_context_events(
        request: Request,
        participant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        classification: Optional[str] = None,
        domain_class: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 500))
        records = pilot_storage.recent_app_logs(
            participant_id=participant_id,
            limit=safe_limit,
            event_type=event_type,
            correlation_id=correlation_id,
            classification=classification,
            domain_class=domain_class,
            context_only=True,
        )
        return {
            "participant_id": participant_id,
            "event_type": event_type,
            "correlation_id": correlation_id,
            "classification": classification,
            "domain_class": domain_class,
            "count": len(records),
            "events": records,
            "breakdown": pilot_storage.context_event_breakdown(participant_id=participant_id),
        }

    @router.post("/api/pilot/app-log")
    def pilot_app_log(payload: PilotAppLogIn) -> dict:
        event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
        participant_id = payload.participant_id.strip() or "global_user"
        level = payload.level.lower().strip() or "info"
        language = payload.language.strip().lower() or "en"
        normalized_message = payload.message.strip()
        domain_context = enrich_domain_context(
            link_scheme=(payload.context_event.link_scheme if payload.context_event else None),
            url_host=(payload.context_event.url_host if payload.context_event else None),
            resolved_domain=(payload.context_event.resolved_domain if payload.context_event else None),
            raw_url=(payload.context_event.metadata.get("raw_url") if payload.context_event else None),
            domain_class=(payload.context_event.domain_class if payload.context_event else None),
        )
        inserted = pilot_storage.add_app_log(
            participant_id=participant_id,
            level=level,
            message=normalized_message,
            language=language,
            timestamp=event_timestamp,
            event_id=payload.event_id,
            event_type=(payload.context_event.event_type if payload.context_event else None),
            source_app=(payload.context_event.source_app if payload.context_event else None),
            target_app=(payload.context_event.target_app if payload.context_event else None),
            correlation_id=(payload.context_event.correlation_id if payload.context_event else None),
            classification=(payload.context_event.classification if payload.context_event else None),
            setup_state=(payload.context_event.setup_state if payload.context_event else None),
            suppression_reason=(payload.context_event.suppression_reason if payload.context_event else None),
            message_family=(payload.context_event.message_family if payload.context_event else None),
            amount=(payload.context_event.amount if payload.context_event else None),
            has_otp=(payload.context_event.has_otp if payload.context_event else None),
            has_upi_handle=(payload.context_event.has_upi_handle if payload.context_event else None),
            has_upi_deeplink=(payload.context_event.has_upi_deeplink if payload.context_event else None),
            has_url=(payload.context_event.has_url if payload.context_event else None),
            link_clicked=(payload.context_event.link_clicked if payload.context_event else None),
            link_scheme=domain_context.link_scheme,
            url_host=domain_context.url_host,
            resolved_domain=domain_context.resolved_domain,
            domain_class=domain_context.domain_class,
            metadata=(payload.context_event.metadata if payload.context_event else None),
        )
        telemetry_recorded = False
        if inserted:
            telemetry_recorded = record_client_app_log_telemetry(
                pilot_storage=pilot_storage,
                participant_id=participant_id,
                event_id=payload.event_id,
                level=level,
                message=normalized_message,
                language=language,
                timestamp=event_timestamp,
            )
            if domain_context.resolved_domain:
                profile = pilot_storage.get_essential_goal_profile(participant_id)
                cohort = str((profile or {}).get("cohort") or "unknown").strip() or "unknown"
                is_new_participant = pilot_storage.record_entity_reputation_participant(
                    entity_key=domain_context.resolved_domain,
                    entity_kind=ENTITY_KIND_DOMAIN,
                    participant_id=participant_id,
                    timestamp=event_timestamp,
                )
                is_new_cohort_participant = pilot_storage.record_entity_cohort_reputation_participant(
                    entity_key=domain_context.resolved_domain,
                    entity_kind=ENTITY_KIND_DOMAIN,
                    cohort=cohort,
                    participant_id=participant_id,
                    timestamp=event_timestamp,
                )
                existing = pilot_storage.get_entity(
                    entity_key=domain_context.resolved_domain,
                    entity_kind=ENTITY_KIND_DOMAIN,
                )
                reputation = pilot_storage.get_entity_reputation(
                    entity_key=domain_context.resolved_domain,
                    entity_kind=ENTITY_KIND_DOMAIN,
                )
                cohort_reputation = pilot_storage.get_entity_cohort_reputation(
                    entity_key=domain_context.resolved_domain,
                    entity_kind=ENTITY_KIND_DOMAIN,
                    cohort=cohort,
                )
                seed = seed_for_domain_class(domain_context.domain_class)
                next_state, next_score, deltas, evidence_updates = apply_observation(
                    current_state=(existing or {}).get("trust_state") or seed.trust_state,
                    current_score=float((existing or {}).get("trust_score") or seed.trust_score),
                    review_status=(existing or {}).get("review_status") or "none",
                    benign_count=int((existing or {}).get("benign_count") or 0),
                    suspicious_count=int((existing or {}).get("suspicious_count") or 0),
                    user_safe_feedback_count=int((existing or {}).get("user_safe_feedback_count") or 0),
                    user_suspicious_feedback_count=int((existing or {}).get("user_suspicious_feedback_count") or 0),
                    domain_class=domain_context.domain_class,
                    event_type=(payload.context_event.event_type if payload.context_event else None),
                    classification=(payload.context_event.classification if payload.context_event else None),
                    link_clicked=bool(payload.context_event.link_clicked if payload.context_event else False),
                    source_app=(payload.context_event.source_app if payload.context_event else None),
                    target_app=(payload.context_event.target_app if payload.context_event else None),
                    timestamp=event_timestamp,
                    evidence=(existing or {}).get("evidence") or {},
                )
                pilot_storage.upsert_entity(
                    entity_key=domain_context.resolved_domain,
                    entity_kind=ENTITY_KIND_DOMAIN,
                    entity_type=(existing or {}).get("entity_type") or seed.entity_type,
                    trust_state=next_state,
                    trust_score=next_score,
                    review_status=(existing or {}).get("review_status") or "none",
                    timestamp=event_timestamp,
                    benign_count=int((existing or {}).get("benign_count") or 0) + deltas["benign_delta"],
                    suspicious_count=int((existing or {}).get("suspicious_count") or 0) + deltas["suspicious_delta"],
                    user_safe_feedback_count=int((existing or {}).get("user_safe_feedback_count") or 0),
                    user_suspicious_feedback_count=int((existing or {}).get("user_suspicious_feedback_count") or 0),
                    account_access_risk_count=int((existing or {}).get("account_access_risk_count") or 0) + deltas["access_risk_delta"],
                    payment_risk_count=int((existing or {}).get("payment_risk_count") or 0) + deltas["payment_risk_delta"],
                    evidence={
                        **((existing or {}).get("evidence") or {}),
                        **evidence_updates,
                        "last_domain_class": domain_context.domain_class,
                        "last_event_type": payload.context_event.event_type if payload.context_event else None,
                        "last_classification": payload.context_event.classification if payload.context_event else None,
                        "last_link_clicked": bool(payload.context_event.link_clicked if payload.context_event else False),
                        "last_source_app": payload.context_event.source_app if payload.context_event else None,
                        "last_target_app": payload.context_event.target_app if payload.context_event else None,
                        "url_host": domain_context.url_host,
                    },
                )
                reputation_score, reputation_deltas = apply_reputation_observation(
                    current_score=float((reputation or {}).get("reputation_score") or 0.0),
                    unique_participant_count=int((reputation or {}).get("unique_participant_count") or 0) + (1 if is_new_participant else 0),
                    event_type=(payload.context_event.event_type if payload.context_event else None),
                    classification=(payload.context_event.classification if payload.context_event else None),
                    link_clicked=bool(payload.context_event.link_clicked if payload.context_event else False),
                    domain_class=domain_context.domain_class,
                    is_new_participant=is_new_participant,
                )
                pilot_storage.upsert_entity_reputation(
                    entity_key=domain_context.resolved_domain,
                    entity_kind=ENTITY_KIND_DOMAIN,
                    reputation_score=reputation_score,
                    unique_participant_count=int((reputation or {}).get("unique_participant_count") or 0) + (1 if is_new_participant else 0),
                    suspicious_feedback_count=int((reputation or {}).get("suspicious_feedback_count") or 0),
                    safe_feedback_count=int((reputation or {}).get("safe_feedback_count") or 0),
                    account_access_risk_count=int((reputation or {}).get("account_access_risk_count") or 0) + reputation_deltas["access_risk_delta"],
                    payment_risk_count=int((reputation or {}).get("payment_risk_count") or 0) + reputation_deltas["payment_risk_delta"],
                    manual_block_count=int((reputation or {}).get("manual_block_count") or 0),
                    manual_safe_count=int((reputation or {}).get("manual_safe_count") or 0),
                    timestamp=event_timestamp,
                    evidence={
                        **((reputation or {}).get("evidence") or {}),
                        "last_domain_class": domain_context.domain_class,
                        "last_event_type": payload.context_event.event_type if payload.context_event else None,
                        "last_participant_id": participant_id,
                    },
                )
                cohort_reputation_score, cohort_reputation_deltas = apply_reputation_observation(
                    current_score=float((cohort_reputation or {}).get("reputation_score") or 0.0),
                    unique_participant_count=int((cohort_reputation or {}).get("unique_participant_count") or 0) + (1 if is_new_cohort_participant else 0),
                    event_type=(payload.context_event.event_type if payload.context_event else None),
                    classification=(payload.context_event.classification if payload.context_event else None),
                    link_clicked=bool(payload.context_event.link_clicked if payload.context_event else False),
                    domain_class=domain_context.domain_class,
                    is_new_participant=is_new_cohort_participant,
                )
                pilot_storage.upsert_entity_cohort_reputation(
                    entity_key=domain_context.resolved_domain,
                    entity_kind=ENTITY_KIND_DOMAIN,
                    cohort=cohort,
                    reputation_score=cohort_reputation_score,
                    unique_participant_count=int((cohort_reputation or {}).get("unique_participant_count") or 0) + (1 if is_new_cohort_participant else 0),
                    suspicious_feedback_count=int((cohort_reputation or {}).get("suspicious_feedback_count") or 0),
                    safe_feedback_count=int((cohort_reputation or {}).get("safe_feedback_count") or 0),
                    account_access_risk_count=int((cohort_reputation or {}).get("account_access_risk_count") or 0) + cohort_reputation_deltas["access_risk_delta"],
                    payment_risk_count=int((cohort_reputation or {}).get("payment_risk_count") or 0) + cohort_reputation_deltas["payment_risk_delta"],
                    manual_block_count=int((cohort_reputation or {}).get("manual_block_count") or 0),
                    manual_safe_count=int((cohort_reputation or {}).get("manual_safe_count") or 0),
                    timestamp=event_timestamp,
                    evidence={
                        **((cohort_reputation or {}).get("evidence") or {}),
                        "last_domain_class": domain_context.domain_class,
                        "last_event_type": payload.context_event.event_type if payload.context_event else None,
                        "last_participant_id": participant_id,
                        "cohort": cohort,
                    },
                )
        return {"ok": True, "deduplicated": not inserted, "telemetry_recorded": telemetry_recorded}

    @router.post("/api/pilot/grievance")
    def pilot_grievance_create(payload: PilotGrievanceIn) -> dict:
        event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
        participant_id = payload.participant_id.strip() or "global_user"
        grievance_id = pilot_storage.create_grievance(
            participant_id=participant_id,
            category=(payload.category or "other").strip().lower(),
            details=payload.details.strip(),
            timestamp=event_timestamp,
        )
        return {"ok": True, "grievance_id": grievance_id}

    @router.get("/api/pilot/grievance")
    def pilot_grievance_list(
        request: Request,
        participant_id: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 500))
        records = pilot_storage.list_grievances(participant_id=participant_id, limit=safe_limit)
        return {"count": len(records), "grievances": records}

    @router.post("/api/pilot/grievance/status")
    def pilot_grievance_status(request: Request, payload: PilotGrievanceStatusIn) -> dict:
        require_admin(request)
        event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
        changed = pilot_storage.update_grievance_status(
            grievance_id=payload.grievance_id,
            status=payload.status,
            timestamp=event_timestamp,
        )
        return {"ok": changed}

    @router.post("/api/research/assignment")
    def research_assignment(request: Request, payload: ExperimentAssignIn) -> dict:
        require_admin(request)
        participant_id = payload.participant_id.strip() or "global_user"
        experiment_name = (payload.experiment_name or "adaptive_alerts_v1").strip() or "adaptive_alerts_v1"
        preferred = (payload.preferred_variant or "").strip().lower()
        if preferred in {"adaptive", "static_baseline"}:
            variant = preferred
            pilot_storage.upsert_experiment_assignment(
                participant_id=participant_id,
                experiment_name=experiment_name,
                variant=variant,
                assigned_at=datetime.utcnow().isoformat(),
            )
        else:
            variant = resolve_experiment_variant(participant_id, experiment_name)
        assignment = pilot_storage.get_experiment_assignment(participant_id, experiment_name)
        return {
            "ok": True,
            "participant_id": participant_id,
            "experiment_name": experiment_name,
            "variant": variant,
            "assignment": assignment,
        }

    @router.post("/api/research/event")
    def research_event(request: Request, payload: ExperimentEventIn) -> dict:
        require_admin(request)
        participant_id = payload.participant_id.strip() or "global_user"
        experiment_name = (payload.experiment_name or "adaptive_alerts_v1").strip() or "adaptive_alerts_v1"
        variant = (payload.variant or "adaptive").strip().lower()
        event_type = (payload.event_type or "unknown_event").strip().lower()
        event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
        pilot_storage.add_experiment_event(
            participant_id=participant_id,
            experiment_name=experiment_name,
            variant=variant,
            event_type=event_type,
            payload=payload.payload,
            timestamp=event_timestamp,
        )
        return {"ok": True}

    @router.get("/api/research/export/experiment-events")
    def research_export_experiment_events(
        request: Request,
        participant_id: Optional[str] = None,
        experiment_name: Optional[str] = None,
        limit: int = 200,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 5000))
        events = pilot_storage.list_experiment_events(
            participant_id=participant_id,
            experiment_name=experiment_name,
            limit=safe_limit,
        )
        return {
            "count": len(events),
            "limit": safe_limit,
            "participant_id": participant_id,
            "experiment_name": experiment_name,
            "events": events,
        }

    @router.get("/api/pilot/storage-health")
    def pilot_storage_health(request: Request) -> dict:
        require_admin(request)
        db_path = str(pilot_storage.db_path)
        return {
            "ok": True,
            "db_path": db_path,
            "db_exists": os.path.exists(db_path),
            "storage_mode": "file",
        }

    return router

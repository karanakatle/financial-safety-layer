from __future__ import annotations

import os
from datetime import datetime
from typing import Callable, Optional

from fastapi import APIRouter, Request

from backend.api_models import (
    ExperimentAssignIn,
    ExperimentEventIn,
    PilotAppLogIn,
    PilotConsentIn,
    PilotFeedbackIn,
    PilotGrievanceIn,
    PilotGrievanceStatusIn,
)
from backend.literacy.messages import literacy_message
from backend.pilot.telemetry import record_client_app_log_telemetry


def build_pilot_router(
    *,
    pilot_storage,
    resolve_experiment_variant: Callable[[str, str], str],
    require_admin: Callable[[Request], None],
) -> APIRouter:
    router = APIRouter()

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
        }

    @router.get("/api/pilot/analytics")
    def pilot_analytics(
        request: Request,
        participant_id: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 200))
        return {
            **pilot_storage.analytics(recent_limit=safe_limit),
            "participant_id": participant_id,
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
        limit: int = 25,
    ) -> dict:
        require_admin(request)
        safe_limit = max(1, min(limit, 200))
        return {
            "participant_id": participant_id,
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
        }

    @router.post("/api/pilot/app-log")
    def pilot_app_log(payload: PilotAppLogIn) -> dict:
        event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
        participant_id = payload.participant_id.strip() or "global_user"
        level = payload.level.lower().strip() or "info"
        language = payload.language.strip().lower() or "en"
        normalized_message = payload.message.strip()
        inserted = pilot_storage.add_app_log(
            participant_id=participant_id,
            level=level,
            message=normalized_message,
            language=language,
            timestamp=event_timestamp,
            event_id=payload.event_id,
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

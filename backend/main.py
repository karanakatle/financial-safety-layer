from dotenv import load_dotenv
import os
from pathlib import Path
from threading import Lock

load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from uuid import uuid4
from backend.utils.logger import logger

from backend.api_models import (
    EssentialGoalProfileUpsertIn,
    EssentialTxnFeedbackIn,
    LiteracyAlertFeedbackIn,
    LiteracyPolicyUpsertIn,
    SMSIngestIn,
    UPIRequestInspectIn,
    UPIOpenIn,
)
from rule_engine.engine import FinancialAgent
from backend.voice.factory import get_voice_provider
from backend.literacy import (
    apply_goal_feedback_learning,
    alert_severity_from_context,
    build_literacy_monitor,
    clamp,
    compute_contextual_scores,
    effective_goal_profile,
    essential_goal_envelope,
    infer_goal_context,
    goal_impact_text,
    localized_label,
    localize_alert,
    next_action_text,
    policy_for_participant,
    persist_literacy_monitor,
    recent_financial_context,
    auto_recalibrate_policy,
    resolve_experiment_variant,
    risk_level_from_score,
    why_text,
)
from backend.literacy.payment_inspection import inspect_payment_request
from backend.pilot import PilotStorage
from backend.config import load_literacy_policy
from backend.nlp.pipeline import process_text
from backend.interaction_manager import orchestrate_response
from backend.routes import build_legacy_router, build_pilot_router
from rule_engine.schemes import evaluate_schemes

LEGACY_AGENT_INITIAL_BALANCE = 2000.0
LEGACY_DEFAULT_PARTICIPANT_ID = "global_user"
_participant_agents: dict[str, FinancialAgent] = {}
_participant_agents_lock = Lock()
LITERACY_POLICY = load_literacy_policy()

voice = get_voice_provider()
pilot_storage = PilotStorage(os.getenv("PILOT_DB_PATH", "data/pilot_research.db"))

SUPPORTED_COHORTS = {"women_led_household", "daily_cashflow_worker"}
SUPPORTED_ESSENTIAL_GOALS = {
    "ration",
    "school",
    "fuel",
    "medicine",
    "rent",
    "mobile_recharge",
    "loan_repayment",
}
GOAL_NON_ESSENTIAL = "non_essential"
SUPPORTED_GOAL_FEEDBACK_VALUES = SUPPORTED_ESSENTIAL_GOALS | {GOAL_NON_ESSENTIAL}
GOAL_CONFIDENCE_GATE = 0.72
MERCHANT_KEYWORD_MAP = {
    "fuel": {"petrol", "diesel", "hpcl", "indianoil", "bharat", "bpcl", "ioc"},
    "ration": {"kirana", "grocery", "supermarket", "ration", "mart", "provision"},
    "school": {"school", "tuition", "fees", "education", "uniform", "books"},
    "medicine": {"medical", "pharmacy", "chemist", "hospital", "clinic", "med"},
    "rent": {"rent", "landlord", "house rent", "room rent"},
    "mobile_recharge": {"recharge", "topup", "prepaid", "postpaid", "airtel", "jio", "vi"},
    "loan_repayment": {"loan", "emi", "repayment", "nbfc", "finance"},
}
NON_ESSENTIAL_KEYWORDS = {
    "liquor",
    "alcohol",
    "beer",
    "wine",
    "cigarette",
    "tobacco",
    "smoke",
    "hookah",
    "junk",
    "snack",
    "gaming",
    "bet",
    "gamble",
}
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def _normalized_participant_id(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or LEGACY_DEFAULT_PARTICIPANT_ID


def _load_cors_settings() -> tuple[list[str], bool]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if origins:
        return origins, True
    return ["*"], False


def _agent_for_participant(participant_id: str | None) -> FinancialAgent:
    normalized = _normalized_participant_id(participant_id)
    agent = _participant_agents.get(normalized)
    if agent is not None:
        return agent
    with _participant_agents_lock:
        agent = _participant_agents.get(normalized)
        if agent is None:
            agent = FinancialAgent(initial_balance=LEGACY_AGENT_INITIAL_BALANCE)
            _participant_agents[normalized] = agent
        return agent


cors_allowed_origins, cors_allow_credentials = _load_cors_settings()

app = FastAPI(title="Arthamantri Prototype", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalized_language(language: str | None) -> str:
    value = (language or "en").strip().lower()
    return "hi" if value.startswith("hi") else "en"


def _normalized_cohort(cohort: str | None) -> str:
    value = (cohort or "").strip().lower().replace("-", "_").replace(" ", "_")
    if value in SUPPORTED_COHORTS:
        return value
    return "daily_cashflow_worker"


def _normalized_goals(goals: list[str] | None) -> list[str]:
    if not goals:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for goal in goals:
        value = (goal or "").strip().lower().replace("-", "_").replace(" ", "_")
        if value in SUPPORTED_ESSENTIAL_GOALS and value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized[:2]


def _normalized_goal_feedback_value(value: str | None) -> str:
    raw = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in SUPPORTED_GOAL_FEEDBACK_VALUES:
        return raw
    return "unknown"


def _infer_goal_context(
    participant_id: str,
    note: str,
    source: str,
    category: str,
    profile: dict | None,
) -> dict:
    return infer_goal_context(
        participant_id=participant_id,
        note=note,
        source=source,
        category=category,
        profile=profile,
        effective_goal_profile=effective_goal_profile,
        pilot_storage=pilot_storage,
        non_essential_keywords=NON_ESSENTIAL_KEYWORDS,
        merchant_keyword_map=MERCHANT_KEYWORD_MAP,
        supported_essential_goals=SUPPORTED_ESSENTIAL_GOALS,
        non_essential_goal=GOAL_NON_ESSENTIAL,
        goal_confidence_gate=GOAL_CONFIDENCE_GATE,
    )


def _apply_goal_feedback_learning(
    participant_id: str,
    alert_id: str,
    is_essential: bool,
    selected_goal: str | None,
    timestamp: str,
) -> dict:
    return apply_goal_feedback_learning(
        participant_id=participant_id,
        alert_id=alert_id,
        is_essential=is_essential,
        selected_goal=selected_goal,
        timestamp=timestamp,
        pilot_storage=pilot_storage,
        normalized_goal_feedback_value=_normalized_goal_feedback_value,
        supported_goal_feedback_values=SUPPORTED_GOAL_FEEDBACK_VALUES,
        supported_essential_goals=SUPPORTED_ESSENTIAL_GOALS,
        non_essential_goal=GOAL_NON_ESSENTIAL,
    )


def _apply_contextual_alert_intensity(
    participant_id: str,
    alert: dict,
    amount: float,
    note: str,
    source: str,
    category: str,
    timestamp: str,
    upi_open_flag: bool,
    warmup_active: bool,
    language: str,
    essential_profile: dict | None,
) -> dict | None:
    localized_alert = localize_alert(
        alert,
        language,
        LITERACY_POLICY.stage1_message,
        LITERACY_POLICY.stage2_over_limit_template,
        LITERACY_POLICY.stage2_close_limit_message,
    )
    projected_spend = float(localized_alert.get("projected_daily_spend") or 0.0)
    daily_safe_limit = float(localized_alert.get("daily_safe_limit") or 0.0)
    envelope = essential_goal_envelope(essential_profile, daily_safe_limit, _normalized_cohort)
    goal_context = _infer_goal_context(
        participant_id=participant_id,
        note=note,
        source=source,
        category=category,
        profile=essential_profile,
    )
    non_essential_confidence = (
        float(goal_context["confidence"])
        if goal_context["gated_goal"] == GOAL_NON_ESSENTIAL
        else 0.0
    )
    features = compute_contextual_scores(
        participant_id=participant_id,
        amount=float(amount),
        projected_spend=projected_spend,
        daily_safe_limit=daily_safe_limit,
        timestamp=timestamp,
        upi_open_flag=upi_open_flag,
        warmup_active=warmup_active,
        goal_protection_ratio=float(envelope.get("reserve_ratio") or 0.0),
        non_essential_confidence=non_essential_confidence,
        pilot_storage=pilot_storage,
    )

    alert_id = str(uuid4())
    pilot_storage.add_alert_features(
        alert_id=alert_id,
        participant_id=participant_id,
        timestamp=timestamp,
        amount=float(amount),
        projected_spend=projected_spend,
        daily_safe_limit=daily_safe_limit,
        spend_ratio=features["spend_ratio"],
        txn_anomaly_score=features["txn_anomaly_score"],
        hour_of_day=features["hour_of_day"],
        rapid_txn_flag=features["rapid_txn_flag"],
        upi_open_flag=features["upi_open_flag"],
        recent_dismissals_24h=features["recent_dismissals_24h"],
        risk_score=features["risk_score"],
        confidence_score=features["confidence_score"],
        tone_selected=features["tone_selected"],
        frequency_bucket=features["frequency_bucket"],
    )
    pilot_storage.upsert_alert_goal_context(
        alert_id=alert_id,
        participant_id=participant_id,
        merchant_key=goal_context["merchant_key"],
        inferred_goal=goal_context["gated_goal"],
        confidence=float(goal_context["confidence"]),
        gate_passed=bool(goal_context["gate_passed"]),
        source=goal_context["source"],
        timestamp=timestamp,
    )

    if features["frequency_bucket"] == "suppressed":
        return None

    risk_level = risk_level_from_score(float(features["risk_score"]))
    goal_impact = goal_impact_text(language, envelope, projected_spend)
    reason = str(localized_alert.get("reason") or "")
    why_this = why_text(
        language=language,
        reason=reason,
        risk_level=risk_level,
        spend_ratio=float(features["spend_ratio"]),
        txn_anomaly_score=float(features["txn_anomaly_score"]),
        upi_open_flag=upi_open_flag,
    )
    next_action = next_action_text(language=language, risk_level=risk_level, reason=reason)

    contextual_alert = dict(localized_alert)
    contextual_alert["alert_id"] = alert_id
    contextual_alert["risk_score"] = features["risk_score"]
    contextual_alert["confidence_score"] = features["confidence_score"]
    contextual_alert["risk_level"] = risk_level
    contextual_alert["tone_selected"] = features["tone_selected"]
    contextual_alert["frequency_bucket"] = features["frequency_bucket"]
    contextual_alert["pause_seconds"] = features["pause_seconds"]
    contextual_alert["severity"] = alert_severity_from_context(
        frequency_bucket=features["frequency_bucket"],
        risk_level=risk_level,
        upi_open_flag=upi_open_flag,
        pause_seconds=int(features["pause_seconds"]),
    )
    contextual_alert["why_this_alert"] = why_this
    contextual_alert["next_best_action"] = next_action
    contextual_alert["essential_goal_impact"] = goal_impact
    contextual_alert["essential_goals"] = envelope.get("essential_goals", [])
    contextual_alert["goal_reserve_ratio"] = envelope.get("reserve_ratio")
    contextual_alert["goal_protected_limit"] = envelope.get("protected_limit")
    contextual_alert["txn_goal_inferred"] = goal_context["gated_goal"]
    contextual_alert["txn_goal_confidence"] = goal_context["confidence"]
    contextual_alert["txn_goal_confidence_gate_passed"] = goal_context["gate_passed"]
    contextual_alert["txn_goal_inference_source"] = goal_context["source"]
    message = contextual_alert.get("message") or ""
    appended_lines = [
        f"{localized_label(language, 'risk')}: {localized_label(language, risk_level)}",
        f"{localized_label(language, 'why')}: {why_this}",
        f"{localized_label(language, 'next')}: {next_action}",
    ]
    if goal_impact:
        appended_lines.append(f"{localized_label(language, 'goal_impact')}: {goal_impact}")
    contextual_alert["message"] = "\n".join([message, *appended_lines]).strip()
    contextual_alert["priority"] = {
        "hard": "critical",
        "medium": "high",
        "soft": "default",
    }.get(contextual_alert["severity"], contextual_alert.get("priority", "high"))
    return contextual_alert


app.include_router(
    build_pilot_router(
        pilot_storage=pilot_storage,
        resolve_experiment_variant=lambda participant_id, experiment_name: resolve_experiment_variant(
            participant_id=participant_id,
            experiment_name=experiment_name,
            pilot_storage=pilot_storage,
        ),
    )
)
app.include_router(
    build_legacy_router(
        default_participant_id=LEGACY_DEFAULT_PARTICIPANT_ID,
        agent_for_participant=_agent_for_participant,
        normalized_participant_id=_normalized_participant_id,
        build_literacy_monitor=lambda participant_id: build_literacy_monitor(
            participant_id=participant_id,
            pilot_storage=pilot_storage,
            literacy_policy=LITERACY_POLICY,
            policy_for_participant=lambda participant_id: policy_for_participant(
                participant_id=participant_id,
                pilot_storage=pilot_storage,
                literacy_policy=LITERACY_POLICY,
            ),
        ),
        persist_literacy_monitor=lambda participant_id, monitor: persist_literacy_monitor(
            participant_id=participant_id,
            monitor=monitor,
            pilot_storage=pilot_storage,
        ),
        apply_contextual_alert_intensity=_apply_contextual_alert_intensity,
        process_text=process_text,
        evaluate_schemes=evaluate_schemes,
        orchestrate_response=orchestrate_response,
        pilot_storage=pilot_storage,
        voice=voice,
        logger=logger,
    )
)


@app.post("/api/literacy/sms-ingest")
def literacy_sms_ingest(payload: SMSIngestIn) -> dict:
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    participant_id = (payload.participant_id or "global_user").strip() or "global_user"
    language = _normalized_language(payload.language)
    signal_type = payload.signal_type
    signal_confidence = payload.signal_confidence
    amount = float(payload.amount) if payload.amount is not None else None
    if signal_type in {"expense", "income"} and amount is None:
        signal_type = "partial"
        signal_confidence = "partial"
    variant = resolve_experiment_variant(
        participant_id=participant_id,
        experiment_name="adaptive_alerts_v1",
        pilot_storage=pilot_storage,
    )
    participant_agent = _agent_for_participant(participant_id)
    transaction_result = None
    if signal_type in {"expense", "income"} and amount is not None:
        event = {
            "timestamp": event_timestamp,
            "type": signal_type,
            "amount": amount,
            "category": payload.category,
            "note": payload.note or f"Bank SMS detected {signal_type}",
        }
        transaction_result = participant_agent.process_event(event)

    monitor = build_literacy_monitor(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
        policy_for_participant=lambda participant_id: policy_for_participant(
            participant_id=participant_id,
            pilot_storage=pilot_storage,
            literacy_policy=LITERACY_POLICY,
        ),
    )
    profile = pilot_storage.get_essential_goal_profile(participant_id)
    current_daily_spend = monitor.daily_spend
    projected_daily_spend = current_daily_spend + amount if signal_type == "expense" and amount is not None else current_daily_spend
    event_type = "sms_ingest_event" if signal_type in {"expense", "income"} else "sms_partial_context"
    pilot_storage.add_literacy_event(
        participant_id=participant_id,
        event_type=event_type,
        source="bank_sms",
        signal_type=signal_type,
        signal_confidence=signal_confidence,
        category=payload.category,
        amount=amount,
        note=payload.note,
        reason=None,
        stage=None,
        daily_spend=projected_daily_spend,
        daily_safe_limit=monitor.status().get("daily_safe_limit"),
        timestamp=event_timestamp,
    )
    literacy_alerts: list[dict] = []
    if signal_type == "expense" and amount is not None:
        literacy_alerts = monitor.ingest_expense(
            amount=amount,
            source="bank_sms",
            timestamp=event_timestamp,
        )
        literacy_alerts = [
            contextual
            for alert in literacy_alerts
            if (
                contextual := _apply_contextual_alert_intensity(
                    participant_id=participant_id,
                    alert=alert,
                    amount=amount,
                    note=payload.note or "bank_sms",
                    source="bank_sms",
                    category=payload.category,
                    timestamp=event_timestamp,
                    upi_open_flag=False,
                    warmup_active=monitor.warmup_active,
                    language=language,
                    essential_profile=profile,
                )
            )
        ]
    persist_literacy_monitor(participant_id=participant_id, monitor=monitor, pilot_storage=pilot_storage)
    policy_recalibrated = auto_recalibrate_policy(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
    )
    pilot_storage.add_experiment_event(
        participant_id=participant_id,
        experiment_name="adaptive_alerts_v1",
        variant=variant,
        event_type="sms_ingest",
        payload={
            "amount": amount,
            "category": payload.category,
            "signal_type": signal_type,
            "signal_confidence": signal_confidence,
            "alerts_count": len(literacy_alerts),
            "warmup_active": monitor.warmup_active,
        },
        timestamp=event_timestamp,
    )
    participant_agent.alerts.extend(literacy_alerts)
    for alert in literacy_alerts:
        pilot_storage.add_literacy_event(
            participant_id=participant_id,
            event_type="sms_ingest_alert",
            source="bank_sms",
            signal_type="expense",
            signal_confidence="confirmed",
            category=payload.category,
            amount=amount,
            note=payload.note,
            reason=alert.get("reason"),
            stage=alert.get("stage"),
            daily_spend=alert.get("projected_daily_spend"),
            daily_safe_limit=alert.get("daily_safe_limit"),
            timestamp=event_timestamp,
        )

    return {
        "transaction_result": transaction_result,
        "literacy_alerts": literacy_alerts,
        "literacy_state": monitor.status(),
        "essential_goal_profile": effective_goal_profile(profile),
        "essential_goal_envelope": essential_goal_envelope(profile, monitor.status().get("daily_safe_limit", 0.0), _normalized_cohort),
        "participant_id": participant_id,
        "language": language,
        "experiment_variant": variant,
        "policy_recalibrated": policy_recalibrated,
    }


@app.post("/api/literacy/upi-open")
def literacy_upi_open(payload: UPIOpenIn) -> dict:
    participant_id = (payload.participant_id or "global_user").strip() or "global_user"
    participant_agent = _agent_for_participant(participant_id)
    language = _normalized_language(payload.language)
    variant = resolve_experiment_variant(
        participant_id=participant_id,
        experiment_name="adaptive_alerts_v1",
        pilot_storage=pilot_storage,
    )
    monitor = build_literacy_monitor(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
        policy_for_participant=lambda participant_id: policy_for_participant(
            participant_id=participant_id,
            pilot_storage=pilot_storage,
            literacy_policy=LITERACY_POLICY,
        ),
    )
    profile = pilot_storage.get_essential_goal_profile(participant_id)
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    pilot_storage.add_literacy_event(
        participant_id=participant_id,
        event_type="upi_open_event",
        source="upi_open",
        app_name=payload.app_name,
        amount=payload.intent_amount,
        reason=None,
        stage=None,
        daily_spend=monitor.daily_spend + payload.intent_amount,
        daily_safe_limit=monitor.status().get("daily_safe_limit"),
        timestamp=event_timestamp,
    )
    alert = monitor.on_upi_app_open(
        app_name=payload.app_name,
        intent_amount=payload.intent_amount,
        timestamp=event_timestamp,
    )
    if alert:
        alert = _apply_contextual_alert_intensity(
            participant_id=participant_id,
            alert=alert,
            amount=payload.intent_amount,
            note=payload.app_name,
            source="upi_open",
            category="upi_open",
            timestamp=event_timestamp,
            upi_open_flag=True,
            warmup_active=monitor.warmup_active,
            language=language,
            essential_profile=profile,
        )
    persist_literacy_monitor(participant_id=participant_id, monitor=monitor, pilot_storage=pilot_storage)
    if alert:
        participant_agent.alerts.append(alert)
        pilot_storage.add_literacy_event(
            participant_id=participant_id,
            event_type="upi_open_alert",
            source="upi_open",
            app_name=payload.app_name,
            amount=payload.intent_amount,
            reason=alert.get("reason"),
            stage=alert.get("stage"),
            daily_spend=alert.get("projected_daily_spend"),
            daily_safe_limit=alert.get("daily_safe_limit"),
            timestamp=event_timestamp,
        )
    pilot_storage.add_experiment_event(
        participant_id=participant_id,
        experiment_name="adaptive_alerts_v1",
        variant=variant,
        event_type="upi_open",
        payload={
            "app_name": payload.app_name,
            "intent_amount": payload.intent_amount,
            "alert_emitted": bool(alert),
            "pause_seconds": int((alert or {}).get("pause_seconds") or 0),
        },
        timestamp=event_timestamp,
    )

    return {
        "alert": alert,
        "literacy_state": monitor.status(),
        "essential_goal_profile": effective_goal_profile(profile),
        "essential_goal_envelope": essential_goal_envelope(profile, monitor.status().get("daily_safe_limit", 0.0), _normalized_cohort),
        "participant_id": participant_id,
        "language": language,
        "experiment_variant": variant,
    }


@app.post("/api/literacy/upi-request-inspect")
def literacy_upi_request_inspect(payload: UPIRequestInspectIn) -> dict:
    participant_id = _normalized_participant_id(payload.participant_id)
    language = _normalized_language(payload.language)
    inspection = inspect_payment_request(
        payload,
        participant_id=participant_id,
        language=language,
        alert_id=str(uuid4()),
    )
    return inspection.model_dump()


@app.get("/api/literacy/status")
def literacy_status(participant_id: str = "global_user") -> dict:
    monitor = build_literacy_monitor(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
        policy_for_participant=lambda participant_id: policy_for_participant(
            participant_id=participant_id,
            pilot_storage=pilot_storage,
            literacy_policy=LITERACY_POLICY,
        ),
    )
    return {"participant_id": participant_id, **monitor.status()}


@app.get("/api/literacy/policy")
def literacy_policy_get(participant_id: str = "global_user") -> dict:
    daily_safe_limit, warning_ratio = policy_for_participant(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
    )
    custom = pilot_storage.get_participant_policy(participant_id)
    return {
        "participant_id": participant_id,
        "daily_safe_limit": daily_safe_limit,
        "warning_ratio": warning_ratio,
        "source": "custom" if custom else "default",
    }


@app.post("/api/literacy/policy")
def literacy_policy_upsert(payload: LiteracyPolicyUpsertIn) -> dict:
    participant_id = payload.participant_id.strip() or "global_user"
    pilot_storage.upsert_participant_policy(
        participant_id=participant_id,
        daily_safe_limit=payload.daily_safe_limit,
        warning_ratio=payload.warning_ratio,
        is_auto=False,
        updated_at=datetime.utcnow().isoformat(),
    )
    daily_safe_limit, warning_ratio = policy_for_participant(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
    )
    return {
        "ok": True,
        "participant_id": participant_id,
        "daily_safe_limit": daily_safe_limit,
        "warning_ratio": warning_ratio,
        "source": "custom",
    }


@app.get("/api/literacy/essential-goals")
def literacy_essential_goals_get(participant_id: str = "global_user") -> dict:
    profile = pilot_storage.get_essential_goal_profile(participant_id)
    daily_safe_limit, _ = policy_for_participant(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
    )
    return {
        "participant_id": participant_id,
        "profile": effective_goal_profile(profile),
        "envelope": essential_goal_envelope(profile, daily_safe_limit, _normalized_cohort),
        "supported_cohorts": sorted(SUPPORTED_COHORTS),
        "supported_essential_goals": sorted(SUPPORTED_ESSENTIAL_GOALS),
    }


@app.post("/api/literacy/essential-goals")
def literacy_essential_goals_upsert(payload: EssentialGoalProfileUpsertIn) -> dict:
    participant_id = payload.participant_id.strip() or "global_user"
    language = _normalized_language(payload.language)
    cohort = _normalized_cohort(payload.cohort)
    goals = _normalized_goals(payload.essential_goals)
    setup_skipped = bool(payload.setup_skipped)
    now_iso = datetime.utcnow().isoformat()
    pilot_storage.upsert_essential_goal_profile(
        participant_id=participant_id,
        cohort=cohort,
        essential_goals=goals,
        language=language,
        setup_skipped=setup_skipped,
        timestamp=now_iso,
    )
    daily_safe_limit, _ = policy_for_participant(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
    )
    return {
        "ok": True,
        "participant_id": participant_id,
        "profile": effective_goal_profile(pilot_storage.get_essential_goal_profile(participant_id)),
        "envelope": essential_goal_envelope(
            pilot_storage.get_essential_goal_profile(participant_id),
            daily_safe_limit,
            _normalized_cohort,
        ),
    }


@app.get("/api/literacy/debug-trace")
def literacy_debug_trace(participant_id: str = "global_user", limit: int = 20) -> dict:
    safe_limit = max(1, min(limit, 200))
    profile = pilot_storage.get_essential_goal_profile(participant_id)
    policy = pilot_storage.get_participant_policy(participant_id)
    assignment = pilot_storage.get_experiment_assignment(participant_id, "adaptive_alerts_v1")
    return {
        "participant_id": participant_id,
        "status": literacy_status(participant_id),
        "policy": policy
        or {
            "participant_id": participant_id,
            "daily_safe_limit": LITERACY_POLICY.daily_safe_limit,
            "warning_ratio": LITERACY_POLICY.warning_ratio,
            "source": "default",
        },
        "essential_goal_profile": effective_goal_profile(profile),
        "essential_goal_envelope": essential_goal_envelope(
            profile,
            float((policy or {}).get("daily_safe_limit") or LITERACY_POLICY.daily_safe_limit),
            _normalized_cohort,
        ),
        "experiment_assignment": assignment,
        "recent_literacy_events": pilot_storage.recent_literacy_events(participant_id, safe_limit),
        "recent_financial_context": recent_financial_context(
            participant_id=participant_id,
            pilot_storage=pilot_storage,
            limit=safe_limit,
        ),
        "recent_alert_features": pilot_storage.recent_alert_features(participant_id, safe_limit),
        "recent_alert_feedback": pilot_storage.recent_alert_feedback(participant_id, safe_limit),
        "recent_goal_feedback": pilot_storage.recent_goal_feedback(participant_id, safe_limit),
    }


@app.get("/api/literacy/storage-health")
def literacy_storage_health() -> dict:
    db_path = str(pilot_storage.db_path)
    return {
        "ok": True,
        "db_path": db_path,
        "db_exists": os.path.exists(db_path),
        "storage_mode": "file",
    }


@app.post("/api/literacy/reset")
def literacy_reset(participant_id: str = "global_user") -> dict:
    pilot_storage.reset_literacy_state(participant_id)
    monitor = build_literacy_monitor(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
        policy_for_participant=lambda participant_id: policy_for_participant(
            participant_id=participant_id,
            pilot_storage=pilot_storage,
            literacy_policy=LITERACY_POLICY,
        ),
    )
    return {"ok": True, "participant_id": participant_id, "literacy_state": monitor.status()}


@app.post("/api/literacy/reset-hard")
def literacy_reset_hard(participant_id: str = "global_user") -> dict:
    pilot_storage.reset_literacy_profile(participant_id)
    monitor = build_literacy_monitor(
        participant_id=participant_id,
        pilot_storage=pilot_storage,
        literacy_policy=LITERACY_POLICY,
        policy_for_participant=lambda participant_id: policy_for_participant(
            participant_id=participant_id,
            pilot_storage=pilot_storage,
            literacy_policy=LITERACY_POLICY,
        ),
    )
    return {"ok": True, "participant_id": participant_id, "literacy_state": monitor.status(), "mode": "hard"}


@app.post("/api/literacy/alert-feedback")
def literacy_alert_feedback(payload: LiteracyAlertFeedbackIn) -> dict:
    participant_id = payload.participant_id.strip() or "global_user"
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    variant = resolve_experiment_variant(
        participant_id=participant_id,
        experiment_name="adaptive_alerts_v1",
        pilot_storage=pilot_storage,
    )
    pilot_storage.add_alert_feedback(
        alert_id=payload.alert_id.strip(),
        participant_id=participant_id,
        action=payload.action.strip().lower(),
        channel=payload.channel.strip().lower() or "overlay",
        title=payload.title.strip(),
        message=payload.message.strip(),
        timestamp=event_timestamp,
    )
    pilot_storage.add_experiment_event(
        participant_id=participant_id,
        experiment_name="adaptive_alerts_v1",
        variant=variant,
        event_type=f"alert_feedback_{payload.action.strip().lower()}",
        payload={
            "alert_id": payload.alert_id.strip(),
            "channel": payload.channel.strip().lower() or "overlay",
            "title": payload.title.strip(),
        },
        timestamp=event_timestamp,
    )
    return {"ok": True}


@app.post("/api/literacy/essential-feedback")
def literacy_essential_feedback(payload: EssentialTxnFeedbackIn) -> dict:
    participant_id = payload.participant_id.strip() or "global_user"
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    learned = _apply_goal_feedback_learning(
        participant_id=participant_id,
        alert_id=payload.alert_id.strip(),
        is_essential=payload.is_essential,
        selected_goal=payload.selected_goal,
        timestamp=event_timestamp,
    )
    return {"ok": True, "participant_id": participant_id, "learned": learned}

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

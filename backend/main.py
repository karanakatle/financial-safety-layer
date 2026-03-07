from dotenv import load_dotenv
import os

from backend.utils import intent
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime, timedelta
from statistics import median, pstdev
from uuid import uuid4
from backend.utils.logger import logger

from rule_engine.engine import FinancialAgent
from rule_engine.schemes import evaluate_schemes
from backend.voice.factory import get_voice_provider
from backend.interaction_manager import orchestrate_response
from backend.nlp.pipeline import process_text
from backend.literacy import FinancialLiteracySafetyMonitor
from backend.pilot import PilotStorage
from backend.config import load_literacy_policy



class TransactionIn(BaseModel):
    type: Literal["expense", "income"]
    amount: float = Field(gt=0)
    category: str = "general"
    note: str = ""


class VoiceQueryIn(BaseModel):
    query: str

class SchemeProfile(BaseModel):
    age: int
    income: int
    occupation: str
    gender: str
    rural: bool
    bank_account: bool
    farmer: bool = False
    business_owner: bool = False

class AudioRequest(BaseModel):
    audio: str

class ChatRequest(BaseModel):
    query: str
    language: Optional[str] = "hi"

class SavingsDecision(BaseModel):
    accept: bool


class SMSIngestIn(BaseModel):
    participant_id: str = "global_user"
    language: str = "en"
    amount: float = Field(gt=0)
    category: str = "bank_sms"
    note: str = ""
    timestamp: Optional[str] = None


class UPIOpenIn(BaseModel):
    participant_id: str = "global_user"
    language: str = "en"
    app_name: str
    intent_amount: float = Field(default=0.0, ge=0)
    timestamp: Optional[str] = None


class LiteracyPolicyUpsertIn(BaseModel):
    participant_id: str
    daily_safe_limit: float = Field(gt=0)
    warning_ratio: float = Field(gt=0, lt=1.0)


class LiteracyAlertFeedbackIn(BaseModel):
    alert_id: str
    participant_id: str
    action: str
    channel: str = "overlay"
    title: str = ""
    message: str = ""
    timestamp: Optional[str] = None


class PilotConsentIn(BaseModel):
    participant_id: str
    accepted: bool
    language: str = "en"
    timestamp: Optional[str] = None


class PilotFeedbackIn(BaseModel):
    participant_id: str
    rating: int = Field(ge=1, le=5)
    comment: str = ""
    language: str = "en"
    timestamp: Optional[str] = None


class PilotAppLogIn(BaseModel):
    participant_id: str
    level: str = "info"
    message: str
    language: str = "en"
    timestamp: Optional[str] = None

app = FastAPI(title="Arthamantri Prototype", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = FinancialAgent(initial_balance=2000.0)
LITERACY_POLICY = load_literacy_policy()

voice = get_voice_provider()
pilot_storage = PilotStorage()

PILOT_DISCLAIMER = (
    "Arthamantri is a research prototype for financial literacy and safety nudges. "
    "It is not investment advice, not a regulated advisory service, and may make mistakes. "
    "Use your judgement before making payments."
)


def _policy_for_participant(participant_id: str) -> tuple[float, float]:
    policy = pilot_storage.get_participant_policy(participant_id)
    if not policy:
        return LITERACY_POLICY.daily_safe_limit, LITERACY_POLICY.warning_ratio
    return float(policy["daily_safe_limit"]), float(policy["warning_ratio"])


def _normalized_language(language: str | None) -> str:
    value = (language or "en").strip().lower()
    return "hi" if value.startswith("hi") else "en"


def _localized_stage1_message(language: str) -> str:
    if language == "hi":
        return (
            "आपका दैनिक सुरक्षित खर्च सीमा के करीब है। "
            "सीमा पार करने से आपकी वित्तीय योजना प्रभावित हो सकती है।"
        )
    return LITERACY_POLICY.stage1_message


def _localized_stage2_message(language: str, projected: float, limit: float) -> str:
    daily_overage = max(projected - limit, 0.0)
    weekly_impact = round(daily_overage * 7, 2)
    if daily_overage > 0:
        if language == "hi":
            return (
                f"अभी भुगतान करने पर आपकी दैनिक सुरक्षित सीमा लगभग ₹{round(daily_overage, 2)} "
                f"से पार हो सकती है और साप्ताहिक योजना पर लगभग ₹{weekly_impact} का असर पड़ सकता है।"
            )
        try:
            return LITERACY_POLICY.stage2_over_limit_template.format(
                daily_overage=round(daily_overage, 2),
                weekly_impact=weekly_impact,
            )
        except (KeyError, ValueError):
            return (
                f"Paying now may exceed your daily safe amount by Rs {round(daily_overage, 2)} "
                f"and disturb your weekly planning by around Rs {weekly_impact}."
            )
    if language == "hi":
        return "आप दैनिक सीमा के करीब हैं। अभी भुगतान करने से आज या सप्ताह की योजना प्रभावित हो सकती है।"
    return LITERACY_POLICY.stage2_close_limit_message


def _localize_alert(alert: dict, language: str) -> dict:
    if language == "en":
        return alert
    localized = dict(alert)
    reason = localized.get("reason")
    if reason in {"daily_threshold_near_exceeded", "catastrophic_risk_override"}:
        localized["message"] = _localized_stage1_message(language)
    elif reason == "upi_open_after_threshold_warning":
        projected = float(localized.get("projected_daily_spend") or 0.0)
        limit = float(localized.get("daily_safe_limit") or 0.0)
        localized["message"] = _localized_stage2_message(language, projected, limit)
    return localized


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _compute_txn_anomaly_score(amount: float, recent_amounts: list[float]) -> float:
    if amount <= 0:
        return 0.0
    if not recent_amounts:
        return 0.45

    baseline = median(recent_amounts)
    if baseline <= 0:
        return 0.45

    ratio = amount / baseline
    if ratio <= 1.0:
        return _clamp(0.35 * ratio)
    if ratio >= 3.0:
        return 1.0
    return _clamp(0.35 + ((ratio - 1.0) / 2.0) * 0.65)


def _compute_contextual_scores(
    participant_id: str,
    amount: float,
    projected_spend: float,
    daily_safe_limit: float,
    timestamp: str,
    upi_open_flag: bool,
    warmup_active: bool,
) -> dict:
    now_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    since_10m = (now_dt - timedelta(minutes=10)).isoformat()
    since_24h = (now_dt - timedelta(hours=24)).isoformat()

    recent_amounts = pilot_storage.recent_spend_amounts(participant_id, limit=20)
    txn_anomaly_score = _compute_txn_anomaly_score(amount, recent_amounts)
    rapid_txn_flag = pilot_storage.count_recent_spend_events(participant_id, since_10m) >= 2
    recent_dismissals_24h = pilot_storage.count_recent_dismissals(participant_id, since_24h)

    spend_ratio = (projected_spend / daily_safe_limit) if daily_safe_limit > 0 else 0.0
    risk_score = _clamp(
        (0.45 * _clamp(spend_ratio / 1.6))
        + (0.25 * txn_anomaly_score)
        + (0.15 * (1.0 if rapid_txn_flag else 0.0))
        + (0.10 * _clamp(recent_dismissals_24h / 4.0))
        + (0.05 * (1.0 if upi_open_flag else 0.0))
    )

    confidence_score = _clamp(
        0.45
        + (0.3 * _clamp(len(recent_amounts) / 12.0))
        + (0.15 if amount > 0 else 0.0)
        + (0.1 if daily_safe_limit > 0 else 0.0)
        - (0.15 if warmup_active else 0.0)
    )

    if risk_score >= 0.85:
        tone_selected = "hard"
    elif risk_score >= 0.55:
        tone_selected = "firm"
    else:
        tone_selected = "soft"

    if recent_dismissals_24h >= 4 and risk_score < 0.8:
        frequency_bucket = "suppressed"
    elif risk_score >= 0.72:
        frequency_bucket = "hard"
    else:
        frequency_bucket = "soft"

    pause_seconds = 5 if upi_open_flag and risk_score >= 0.9 else 0

    return {
        "spend_ratio": round(spend_ratio, 4),
        "txn_anomaly_score": round(txn_anomaly_score, 4),
        "hour_of_day": now_dt.hour,
        "rapid_txn_flag": rapid_txn_flag,
        "upi_open_flag": upi_open_flag,
        "recent_dismissals_24h": recent_dismissals_24h,
        "risk_score": round(risk_score, 4),
        "confidence_score": round(confidence_score, 4),
        "tone_selected": tone_selected,
        "frequency_bucket": frequency_bucket,
        "pause_seconds": pause_seconds,
    }


def _apply_contextual_alert_intensity(
    participant_id: str,
    alert: dict,
    amount: float,
    timestamp: str,
    upi_open_flag: bool,
    warmup_active: bool,
) -> dict | None:
    projected_spend = float(alert.get("projected_daily_spend") or 0.0)
    daily_safe_limit = float(alert.get("daily_safe_limit") or 0.0)
    features = _compute_contextual_scores(
        participant_id=participant_id,
        amount=float(amount),
        projected_spend=projected_spend,
        daily_safe_limit=daily_safe_limit,
        timestamp=timestamp,
        upi_open_flag=upi_open_flag,
        warmup_active=warmup_active,
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

    if features["frequency_bucket"] == "suppressed":
        return None

    contextual_alert = dict(alert)
    contextual_alert["alert_id"] = alert_id
    contextual_alert["risk_score"] = features["risk_score"]
    contextual_alert["confidence_score"] = features["confidence_score"]
    contextual_alert["tone_selected"] = features["tone_selected"]
    contextual_alert["frequency_bucket"] = features["frequency_bucket"]
    contextual_alert["pause_seconds"] = features["pause_seconds"]
    contextual_alert["priority"] = (
        "critical" if features["frequency_bucket"] == "hard" else contextual_alert.get("priority", "high")
    )
    return contextual_alert


def _build_literacy_monitor(participant_id: str) -> FinancialLiteracySafetyMonitor:
    record = pilot_storage.get_literacy_state(participant_id)
    daily_safe_limit, warning_ratio = _policy_for_participant(participant_id)
    monitor = FinancialLiteracySafetyMonitor(
        daily_safe_limit=daily_safe_limit,
        warning_ratio=warning_ratio,
        stage1_message=LITERACY_POLICY.stage1_message,
        stage2_over_limit_template=LITERACY_POLICY.stage2_over_limit_template,
        stage2_close_limit_message=LITERACY_POLICY.stage2_close_limit_message,
        warmup_days=LITERACY_POLICY.warmup_days,
        warmup_seed_multiplier=LITERACY_POLICY.warmup_seed_multiplier,
        warmup_extreme_spike_ratio=LITERACY_POLICY.warmup_extreme_spike_ratio,
        catastrophic_absolute=LITERACY_POLICY.catastrophic_absolute,
        catastrophic_multiplier=LITERACY_POLICY.catastrophic_multiplier,
        catastrophic_projected_cap=LITERACY_POLICY.catastrophic_projected_cap,
    )
    if not record:
        return monitor

    monitor.current_date = record["current_date"]
    monitor.daily_spend = float(record["daily_spend"])
    monitor.threshold_risk_active = bool(record["threshold_risk_active"])
    monitor.stage1_sent = bool(record["stage1_sent"])
    monitor.stage2_sent = bool(record["stage2_sent"])
    monitor.first_event_date = record.get("first_event_date")
    monitor.warmup_active = bool(record.get("warmup_active", False))
    monitor.adaptive_daily_safe_limit = record.get("adaptive_daily_safe_limit")
    monitor.notifications = [dict() for _ in range(int(record["notifications_count"]))]
    return monitor


def _persist_literacy_monitor(participant_id: str, monitor: FinancialLiteracySafetyMonitor) -> None:
    now_iso = datetime.utcnow().isoformat()
    pilot_storage.upsert_literacy_state(
        participant_id=participant_id,
        current_date=monitor.current_date,
        daily_spend=monitor.daily_spend,
        threshold_risk_active=monitor.threshold_risk_active,
        stage1_sent=monitor.stage1_sent,
        stage2_sent=monitor.stage2_sent,
        notifications_count=len(monitor.notifications),
        first_event_date=monitor.first_event_date,
        warmup_active=monitor.warmup_active,
        adaptive_daily_safe_limit=monitor.adaptive_daily_safe_limit,
        updated_at=now_iso,
    )
    pilot_storage.upsert_daily_spend(
        participant_id=participant_id,
        spend_date=monitor.current_date,
        daily_spend=monitor.daily_spend,
        updated_at=now_iso,
    )


def _auto_recalibrate_policy(participant_id: str) -> bool:
    # Learn a stable user baseline from recent behavior and update only auto policies.
    spends = pilot_storage.recent_daily_spends(participant_id, limit=7)
    if len(spends) < 5:
        return False

    base = median(spends)
    target_limit = max(800.0, min(10000.0, round(base * 1.15, 2)))
    mean = (sum(spends) / len(spends)) if spends else 0.0
    volatility = (pstdev(spends) / mean) if mean > 0 else 0.0
    target_warning_ratio = 0.92 if volatility <= 0.25 else 0.9 if volatility <= 0.5 else 0.87

    # Contextual refinement: recent alert-quality signals tune strictness.
    # Lower ratio => earlier warnings; higher ratio => fewer warnings.
    feature_summary = pilot_storage.recent_alert_feature_summary(participant_id, limit=50)
    if feature_summary["sample_size"] >= 5:
        avg_risk = feature_summary["avg_risk_score"]
        avg_conf = feature_summary["avg_confidence_score"]
        suppressed_rate = (
            feature_summary["suppressed_count"] / feature_summary["sample_size"]
            if feature_summary["sample_size"] > 0
            else 0.0
        )
        hard_rate = (
            feature_summary["hard_count"] / feature_summary["sample_size"]
            if feature_summary["sample_size"] > 0
            else 0.0
        )

        # If risk is repeatedly high and model confidence is good -> warn earlier.
        if avg_risk >= 0.75 and avg_conf >= 0.6:
            target_warning_ratio -= 0.03
        # If user context leads to many suppressed alerts -> reduce alerting pressure.
        if suppressed_rate >= 0.35:
            target_warning_ratio += 0.02
        # If many hard alerts are still needed, nudge earlier.
        if hard_rate >= 0.3:
            target_warning_ratio -= 0.02

    # Dismissals are a direct proxy for alert fatigue.
    since_7d = (datetime.utcnow() - timedelta(days=7)).isoformat()
    dismissals_7d = pilot_storage.count_recent_dismissals(participant_id, since_7d)
    if dismissals_7d >= 8:
        target_warning_ratio += 0.02
    elif dismissals_7d >= 4:
        target_warning_ratio += 0.01
    target_warning_ratio = _clamp(target_warning_ratio, 0.82, 0.95)
    policy = pilot_storage.get_participant_policy(participant_id)
    if policy:
        current_limit = float(policy["daily_safe_limit"])
        warning_ratio = float(policy["warning_ratio"])
    else:
        current_limit = LITERACY_POLICY.daily_safe_limit
        warning_ratio = LITERACY_POLICY.warning_ratio

    # Smooth updates to avoid sudden jumps.
    smoothed_limit = round((0.7 * current_limit) + (0.3 * target_limit), 2)
    smoothed_warning_ratio = round((0.7 * warning_ratio) + (0.3 * target_warning_ratio), 3)
    return pilot_storage.upsert_auto_participant_policy(
        participant_id=participant_id,
        daily_safe_limit=smoothed_limit,
        warning_ratio=smoothed_warning_ratio,
        updated_at=datetime.utcnow().isoformat(),
    )

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/pilot/meta")
def pilot_meta() -> dict:
    return {
        "pilot_mode": True,
        "target_cohort_size": 60,
        "disclaimer": PILOT_DISCLAIMER,
        "alert_policy": {
            "income": "informational_only",
            "overspending": "stage1_near_threshold_once",
            "upi_open": "stage2_first_open_after_stage1_once",
            "lockscreen_alerts": False,
        },
    }


@app.post("/api/pilot/consent")
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


@app.post("/api/pilot/feedback")
def pilot_feedback_submit(payload: PilotFeedbackIn) -> dict:
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    record = {
        "participant_id": payload.participant_id,
        "rating": payload.rating,
        "comment": payload.comment.strip(),
        "language": payload.language,
        "timestamp": event_timestamp,
    }
    pilot_storage.add_feedback(
        participant_id=payload.participant_id,
        rating=payload.rating,
        comment=payload.comment.strip(),
        language=payload.language,
        timestamp=event_timestamp,
    )
    return {"ok": True, "feedback_count": pilot_storage.summary()["feedback_count"]}


@app.get("/api/pilot/summary")
def pilot_summary() -> dict:
    return pilot_storage.summary()


@app.get("/api/pilot/analytics")
def pilot_analytics() -> dict:
    return pilot_storage.analytics()


@app.post("/api/pilot/app-log")
def pilot_app_log(payload: PilotAppLogIn) -> dict:
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    pilot_storage.add_app_log(
        participant_id=payload.participant_id,
        level=payload.level.lower(),
        message=payload.message.strip(),
        language=payload.language,
        timestamp=event_timestamp,
    )
    return {"ok": True}


@app.get("/api/state")
def get_state() -> dict:
    return agent.state_snapshot()


@app.get("/api/alerts")
def get_alerts() -> list[dict]:
    return agent.alerts


@app.post("/api/transaction")
def add_transaction(payload: TransactionIn) -> dict:
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": payload.type,
        "amount": payload.amount,
        "category": payload.category,
        "note": payload.note,
    }
    result = agent.process_event(event)
    literacy_alerts = []
    if payload.type == "expense":
        monitor = _build_literacy_monitor("global_user")
        pilot_storage.add_literacy_event(
            participant_id="global_user",
            event_type="manual_txn_event",
            source="manual_ui",
            amount=payload.amount,
            reason=None,
            stage=None,
            daily_spend=monitor.daily_spend + payload.amount,
            daily_safe_limit=monitor.status().get("daily_safe_limit"),
            timestamp=event["timestamp"],
        )
        literacy_alerts = monitor.ingest_expense(
            amount=payload.amount,
            source="manual_ui",
            timestamp=event["timestamp"],
        )
        literacy_alerts = [
            contextual
            for alert in literacy_alerts
            if (
                contextual := _apply_contextual_alert_intensity(
                    participant_id="global_user",
                    alert=alert,
                    amount=payload.amount,
                    timestamp=event["timestamp"],
                    upi_open_flag=False,
                    warmup_active=monitor.warmup_active,
                )
            )
        ]
        _persist_literacy_monitor("global_user", monitor)
        agent.alerts.extend(literacy_alerts)
        result["literacy_alerts"] = literacy_alerts

    return result


@app.post("/api/literacy/sms-ingest")
def literacy_sms_ingest(payload: SMSIngestIn) -> dict:
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    participant_id = (payload.participant_id or "global_user").strip() or "global_user"
    language = _normalized_language(payload.language)
    event = {
        "timestamp": event_timestamp,
        "type": "expense",
        "amount": payload.amount,
        "category": payload.category,
        "note": payload.note or "Bank SMS detected expense",
    }
    transaction_result = agent.process_event(event)

    monitor = _build_literacy_monitor(participant_id)
    pilot_storage.add_literacy_event(
        participant_id=participant_id,
        event_type="sms_ingest_event",
        source="bank_sms",
        amount=payload.amount,
        reason=None,
        stage=None,
        daily_spend=monitor.daily_spend + payload.amount,
        daily_safe_limit=monitor.status().get("daily_safe_limit"),
        timestamp=event_timestamp,
    )
    literacy_alerts = monitor.ingest_expense(
        amount=payload.amount,
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
                amount=payload.amount,
                timestamp=event_timestamp,
                upi_open_flag=False,
                warmup_active=monitor.warmup_active,
            )
        )
    ]
    literacy_alerts = [_localize_alert(alert, language) for alert in literacy_alerts]
    _persist_literacy_monitor(participant_id, monitor)
    policy_recalibrated = _auto_recalibrate_policy(participant_id)
    agent.alerts.extend(literacy_alerts)
    for alert in literacy_alerts:
        pilot_storage.add_literacy_event(
            participant_id=participant_id,
            event_type="sms_ingest_alert",
            source="bank_sms",
            amount=payload.amount,
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
        "participant_id": participant_id,
        "language": language,
        "policy_recalibrated": policy_recalibrated,
    }


@app.post("/api/literacy/upi-open")
def literacy_upi_open(payload: UPIOpenIn) -> dict:
    participant_id = (payload.participant_id or "global_user").strip() or "global_user"
    language = _normalized_language(payload.language)
    monitor = _build_literacy_monitor(participant_id)
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
            timestamp=event_timestamp,
            upi_open_flag=True,
            warmup_active=monitor.warmup_active,
        )
    if alert:
        alert = _localize_alert(alert, language)
    _persist_literacy_monitor(participant_id, monitor)
    if alert:
        agent.alerts.append(alert)
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

    return {
        "alert": alert,
        "literacy_state": monitor.status(),
        "participant_id": participant_id,
        "language": language,
    }


@app.get("/api/literacy/status")
def literacy_status(participant_id: str = "global_user") -> dict:
    monitor = _build_literacy_monitor(participant_id)
    return {"participant_id": participant_id, **monitor.status()}


@app.get("/api/literacy/policy")
def literacy_policy_get(participant_id: str = "global_user") -> dict:
    daily_safe_limit, warning_ratio = _policy_for_participant(participant_id)
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
    daily_safe_limit, warning_ratio = _policy_for_participant(participant_id)
    return {
        "ok": True,
        "participant_id": participant_id,
        "daily_safe_limit": daily_safe_limit,
        "warning_ratio": warning_ratio,
        "source": "custom",
    }


@app.post("/api/literacy/reset")
def literacy_reset(participant_id: str = "global_user") -> dict:
    pilot_storage.reset_literacy_state(participant_id)
    monitor = _build_literacy_monitor(participant_id)
    return {"ok": True, "participant_id": participant_id, "literacy_state": monitor.status()}


@app.post("/api/literacy/reset-hard")
def literacy_reset_hard(participant_id: str = "global_user") -> dict:
    pilot_storage.reset_literacy_profile(participant_id)
    monitor = _build_literacy_monitor(participant_id)
    return {"ok": True, "participant_id": participant_id, "literacy_state": monitor.status(), "mode": "hard"}


@app.post("/api/literacy/alert-feedback")
def literacy_alert_feedback(payload: LiteracyAlertFeedbackIn) -> dict:
    participant_id = payload.participant_id.strip() or "global_user"
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    pilot_storage.add_alert_feedback(
        alert_id=payload.alert_id.strip(),
        participant_id=participant_id,
        action=payload.action.strip().lower(),
        channel=payload.channel.strip().lower() or "overlay",
        title=payload.title.strip(),
        message=payload.message.strip(),
        timestamp=event_timestamp,
    )
    return {"ok": True}


@app.post("/api/voice-query")
def voice_query(payload: VoiceQueryIn) -> dict:
    nlp = process_text(payload.query)
    intent = nlp["intent"]
    score = nlp["confidence"]

    logger.info(
    f"QUERY='{nlp['original']}' | "
    f"NORMALIZED='{nlp['normalized']}' | "
    f"INTENT={intent} | SCORE={score}"
    )
    response = agent.handle_intent(intent)
    return {"query": payload.query, "response": response}

@app.post("/api/schemes")
def get_schemes(profile: SchemeProfile):
    schemes = evaluate_schemes(profile.dict())
    reminding = {
            "count": len(schemes),
            "message": "Here are the government schemes you may benefit from."
        }

    return {
        "eligible_schemes": schemes,
        "summary": reminding
    }


@app.post("/api/voice-audio")
def voice_audio(req: AudioRequest):

    result = voice.speech_to_text(req.audio)

    text = result["text"]
    lang = result["language"]

    if text.lower() in ["haan", "yes", "save karo"]:
        result = agent.confirm_savings(True)

        return orchestrate_response(
            result["message"],
            mode="voice",
            language=lang,
            voice_provider=voice
        )
    # intent detection
    nlp = process_text(text)

    intent = nlp["intent"]
    score = nlp["confidence"]
    response_text = agent.handle_intent(intent)
    logger.info(
    f"QUERY='{nlp['original']}' | "
    f"NORMALIZED='{nlp['normalized']}' | "
    f"INTENT={intent} | SCORE={score}"
    )

    if "fraud_warning" in response_text.lower():
        response_text = "Yeh transaction risky lag raha hai. Kripya verify karein."
    else:
        response_text = response_text
    
    return orchestrate_response(
        message=response_text,
        mode="voice",
        language=lang,
        voice_provider=voice
    )

@app.post("/api/chat")
def chat(req: ChatRequest):

    q = req.query.lower()

    if "save" in q and ("yes" in q or "haan" in q):
        result = agent.confirm_savings(True)
        return orchestrate_response(
            result["message"],
            mode="chat",
            language=req.language
        )

    nlp = process_text(req.query)

    intent = nlp["intent"]
    score = nlp["confidence"]

    logger.info(
    f"QUERY='{nlp['original']}' | "
    f"NORMALIZED='{nlp['normalized']}' | "
    f"INTENT={intent} | SCORE={score}"
    )
    reply = agent.handle_intent(intent)

    return orchestrate_response(
        reply,
        mode="chat",
        language="hi"
    )

@app.post("/api/confirm-savings")
def confirm_savings(decision: SavingsDecision):

    result = agent.confirm_savings(decision.accept)

    return result

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

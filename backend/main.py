from dotenv import load_dotenv
import os
import hashlib
import re

from backend.utils import intent
load_dotenv()
from fastapi import FastAPI
from fastapi import HTTPException
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


class EssentialGoalProfileUpsertIn(BaseModel):
    participant_id: str
    cohort: str = "daily_cashflow_worker"
    essential_goals: list[str] = Field(default_factory=list)
    language: str = "en"
    setup_skipped: bool = False


class ExperimentAssignIn(BaseModel):
    participant_id: str
    experiment_name: str = "adaptive_alerts_v1"
    preferred_variant: Optional[str] = None


class ExperimentEventIn(BaseModel):
    participant_id: str
    experiment_name: str = "adaptive_alerts_v1"
    variant: str
    event_type: str
    payload: dict = Field(default_factory=dict)
    timestamp: Optional[str] = None


class PilotGrievanceIn(BaseModel):
    participant_id: str
    category: str = "other"
    details: str
    timestamp: Optional[str] = None


class PilotGrievanceStatusIn(BaseModel):
    grievance_id: int
    status: Literal["open", "in_review", "resolved", "rejected"]
    timestamp: Optional[str] = None


class EssentialTxnFeedbackIn(BaseModel):
    alert_id: str
    participant_id: str
    is_essential: bool
    selected_goal: Optional[str] = None
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
pilot_storage = PilotStorage(os.getenv("PILOT_DB_PATH", "data/pilot_research.db"))

PILOT_DISCLAIMER = (
    "Arthamantri is a research prototype for financial literacy and safety nudges. "
    "It is not investment advice, not a regulated advisory service, and may make mistakes. "
    "Use your judgement before making payments."
)

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


def _policy_for_participant(participant_id: str) -> tuple[float, float]:
    policy = pilot_storage.get_participant_policy(participant_id)
    if not policy:
        return LITERACY_POLICY.daily_safe_limit, LITERACY_POLICY.warning_ratio
    return float(policy["daily_safe_limit"]), float(policy["warning_ratio"])


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


def _merchant_key_from_note(note: str, source: str, category: str) -> str:
    base = f"{note} {source} {category}".lower()
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", base)
    cleaned = re.sub(r"\b\d{3,}\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = f"{source}:{category}"
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    return digest[:24]


def _goal_from_keywords(text: str) -> tuple[str, float, str]:
    lower = text.lower()
    if any(token in lower for token in NON_ESSENTIAL_KEYWORDS):
        return GOAL_NON_ESSENTIAL, 0.78, "keyword_non_essential"
    for goal, words in MERCHANT_KEYWORD_MAP.items():
        if any(word in lower for word in words):
            return goal, 0.58, "keyword_essential"
    return "unknown", 0.0, "none"


def _goal_from_memory(participant_id: str, merchant_key: str) -> tuple[str, float, str]:
    rows = pilot_storage.goal_memory_rows(participant_id, merchant_key)
    if not rows:
        return "unknown", 0.0, "none"

    best_goal = "unknown"
    best_score = 0.0
    best_count = 0
    for row in rows:
        pos = int(row.get("positive_count") or 0)
        neg = int(row.get("negative_count") or 0)
        total = pos + neg
        if total <= 0:
            continue
        # Bayesian-smoothed success estimate.
        score = (pos + 1.0) / (total + 2.0)
        if score > best_score:
            best_score = score
            best_goal = str(row.get("goal") or "unknown")
            best_count = total

    if best_goal == "unknown":
        return "unknown", 0.0, "none"

    memory_conf = min(0.55, 0.22 + (best_count * 0.06))
    return best_goal, memory_conf, "memory"


def _infer_goal_context(
    participant_id: str,
    note: str,
    source: str,
    category: str,
    profile: dict | None,
) -> dict:
    profile_goals = set((_effective_goal_profile(profile).get("essential_goals") or []))
    merchant_key = _merchant_key_from_note(note=note, source=source, category=category)
    keyword_goal, keyword_conf, keyword_source = _goal_from_keywords(note)
    memory_goal, memory_conf, _ = _goal_from_memory(participant_id, merchant_key)

    inferred_goal = "unknown"
    confidence = 0.0
    confidence_source = "none"

    if keyword_conf > 0 or memory_conf > 0:
        if keyword_goal == memory_goal and keyword_goal != "unknown":
            inferred_goal = keyword_goal
            confidence = min(0.95, keyword_conf + memory_conf + 0.12)
            confidence_source = "keyword+memory"
        elif memory_conf >= keyword_conf and memory_goal != "unknown":
            inferred_goal = memory_goal
            confidence = memory_conf
            confidence_source = "memory"
        elif keyword_goal != "unknown":
            inferred_goal = keyword_goal
            confidence = keyword_conf
            confidence_source = keyword_source

    # Bias guard: low-evidence memory cannot force essential classification.
    if inferred_goal in SUPPORTED_ESSENTIAL_GOALS and confidence_source == "memory":
        confidence = min(confidence, 0.7)

    # Confidence gate: only accept essential goal when confidence is high and goal matches profile.
    gate_passed = (
        confidence >= GOAL_CONFIDENCE_GATE
        and (
            inferred_goal == GOAL_NON_ESSENTIAL
            or inferred_goal in profile_goals
        )
    )
    gated_goal = inferred_goal if gate_passed else "unknown"

    return {
        "merchant_key": merchant_key,
        "raw_goal": inferred_goal,
        "gated_goal": gated_goal,
        "confidence": round(confidence, 4),
        "gate_passed": gate_passed,
        "source": confidence_source,
        "profile_goals": sorted(profile_goals),
    }


def _effective_goal_profile(profile: dict | None) -> dict:
    if profile:
        return profile
    return {
        "cohort": "daily_cashflow_worker",
        "essential_goals": [],
        "language": "en",
        "setup_skipped": True,
    }


def _essential_goal_envelope(profile: dict | None, daily_safe_limit: float) -> dict:
    active = _effective_goal_profile(profile)
    goals = list(active.get("essential_goals") or [])
    cohort = _normalized_cohort(active.get("cohort"))

    base_ratio = 0.18 if cohort == "women_led_household" else 0.22
    ratio = _clamp(base_ratio + (0.05 * min(len(goals), 2)), 0.15, 0.35)
    reserve_amount = round(daily_safe_limit * ratio, 2)
    protected_limit = round(max(daily_safe_limit - reserve_amount, daily_safe_limit * 0.55), 2)
    return {
        "cohort": cohort,
        "essential_goals": goals,
        "reserve_ratio": round(ratio, 3),
        "reserve_amount": reserve_amount,
        "protected_limit": protected_limit,
    }


def _risk_level_from_score(risk_score: float) -> str:
    if risk_score >= 0.85:
        return "critical"
    if risk_score >= 0.65:
        return "high"
    if risk_score >= 0.45:
        return "medium"
    return "low"


def _localized_label(language: str, key: str) -> str:
    if language == "hi":
        labels = {
            "risk": "जोखिम स्तर",
            "why": "क्यों दिखा",
            "next": "अगला सुरक्षित कदम",
            "goal_impact": "आवश्यक लक्ष्य प्रभाव",
            "low": "कम",
            "medium": "मध्यम",
            "high": "उच्च",
            "critical": "अत्यधिक",
        }
        return labels.get(key, key)
    labels = {
        "risk": "Risk level",
        "why": "Why this alert",
        "next": "Next safe action",
        "goal_impact": "Essential-goal impact",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
    }
    return labels.get(key, key)


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


def _goal_impact_text(language: str, envelope: dict, projected_spend: float) -> str:
    protected_limit = float(envelope.get("protected_limit") or 0.0)
    if protected_limit <= 0:
        return ""
    delta = round(projected_spend - protected_limit, 2)
    if delta <= 0:
        return ""
    goals = list(envelope.get("essential_goals") or [])
    goal_names = ", ".join(goals) if goals else ("daily essentials" if language == "en" else "दैनिक आवश्यकताएं")
    if language == "hi":
        return f"₹{delta} का अतिरिक्त खर्च आपके {goal_names} बजट पर दबाव डाल सकता है।"
    return f"An extra ₹{delta} spend can pressure your {goal_names} budget."


def _why_text(
    language: str,
    reason: str,
    risk_level: str,
    spend_ratio: float,
    txn_anomaly_score: float,
    upi_open_flag: bool,
) -> str:
    if language == "hi":
        base = (
            f"खर्च अनुपात {round(spend_ratio, 2)} और जोखिम स्तर "
            f"{_localized_label(language, risk_level)} पाया गया।"
        )
        if reason == "catastrophic_risk_override":
            return f"{base} भुगतान राशि असामान्य रूप से अधिक थी।"
        if upi_open_flag:
            return f"{base} UPI ऐप खुलने पर जोखिम सक्रिय मिला।"
        if txn_anomaly_score >= 0.7:
            return f"{base} लेन-देन सामान्य से बड़ा है।"
        return base

    base = f"Spend ratio {round(spend_ratio, 2)} with {_localized_label(language, risk_level)} risk."
    if reason == "catastrophic_risk_override":
        return f"{base} Transaction amount is unusually high."
    if upi_open_flag:
        return f"{base} Risk remained active when UPI app opened."
    if txn_anomaly_score >= 0.7:
        return f"{base} This transaction is larger than recent pattern."
    return base


def _next_action_text(language: str, risk_level: str, reason: str) -> str:
    if language == "hi":
        if risk_level in {"high", "critical"}:
            return "भुगतान से पहले 5 सेकंड रुकें, प्राप्तकर्ता सत्यापित करें और राशि कम करें।"
        if reason == "upi_open_after_threshold_warning":
            return "जरूरत होने पर ही भुगतान करें, अन्यथा इसे बाद में करें।"
        return "आज अनावश्यक खर्च रोकें और आवश्यक लक्ष्य खर्च सुरक्षित रखें।"
    if risk_level in {"high", "critical"}:
        return "Pause 5 seconds, verify recipient, and reduce amount before paying."
    if reason == "upi_open_after_threshold_warning":
        return "Proceed only if essential; otherwise defer this payment."
    return "Stop non-essential spending today and protect essential-goal budget."


def _resolve_experiment_variant(participant_id: str, experiment_name: str) -> str:
    existing = pilot_storage.get_experiment_assignment(participant_id, experiment_name)
    if existing:
        return str(existing.get("variant") or "adaptive")

    digest = hashlib.sha256(f"{participant_id}:{experiment_name}".encode("utf-8")).hexdigest()
    variant = "adaptive" if int(digest[:8], 16) % 2 == 0 else "static_baseline"
    pilot_storage.upsert_experiment_assignment(
        participant_id=participant_id,
        experiment_name=experiment_name,
        variant=variant,
        assigned_at=datetime.utcnow().isoformat(),
    )
    return variant


def _apply_goal_feedback_learning(
    participant_id: str,
    alert_id: str,
    is_essential: bool,
    selected_goal: str | None,
    timestamp: str,
) -> dict:
    context = pilot_storage.get_alert_goal_context(alert_id, participant_id)
    if not context:
        raise HTTPException(status_code=404, detail="Alert context not found for participant")

    chosen = _normalized_goal_feedback_value(selected_goal)
    if chosen == "unknown":
        inferred_goal = str(context.get("inferred_goal") or "unknown")
        chosen = inferred_goal if inferred_goal in SUPPORTED_GOAL_FEEDBACK_VALUES else GOAL_NON_ESSENTIAL

    source_confidence = float(context.get("confidence") or 0.0)
    merchant_key = str(context.get("merchant_key") or "")
    if not merchant_key:
        raise HTTPException(status_code=400, detail="Invalid merchant context")

    # Bias guard: user essential feedback updates are lighter than non-essential feedback.
    if is_essential:
        if chosen not in SUPPORTED_ESSENTIAL_GOALS:
            raise HTTPException(status_code=400, detail="Essential feedback requires a supported essential goal")
        positive_delta = 1
        negative_delta = 0
    else:
        positive_delta = 1 if chosen == GOAL_NON_ESSENTIAL else 0
        negative_delta = 1 if chosen in SUPPORTED_ESSENTIAL_GOALS else 0

    pilot_storage.upsert_goal_memory(
        participant_id=participant_id,
        merchant_key=merchant_key,
        goal=chosen,
        delta_positive=positive_delta,
        delta_negative=negative_delta,
        timestamp=timestamp,
    )
    pilot_storage.add_goal_feedback(
        participant_id=participant_id,
        alert_id=alert_id,
        merchant_key=merchant_key,
        selected_goal=chosen,
        is_essential=is_essential,
        source_confidence=source_confidence,
        timestamp=timestamp,
    )
    return {
        "merchant_key": merchant_key,
        "selected_goal": chosen,
        "is_essential": is_essential,
        "source_confidence": source_confidence,
    }


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
    goal_protection_ratio: float = 0.0,
    non_essential_confidence: float = 0.0,
) -> dict:
    now_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    since_10m = (now_dt - timedelta(minutes=10)).isoformat()
    since_24h = (now_dt - timedelta(hours=24)).isoformat()

    recent_amounts = pilot_storage.recent_spend_amounts(participant_id, limit=20)
    txn_anomaly_score = _compute_txn_anomaly_score(amount, recent_amounts)
    rapid_txn_flag = pilot_storage.count_recent_spend_events(participant_id, since_10m) >= 2
    recent_dismissals_24h = pilot_storage.count_recent_dismissals(participant_id, since_24h)

    spend_ratio = (projected_spend / daily_safe_limit) if daily_safe_limit > 0 else 0.0
    protected_limit = daily_safe_limit * (1.0 - goal_protection_ratio) if daily_safe_limit > 0 else 0.0
    goal_pressure_score = 0.0
    if protected_limit > 0:
        goal_pressure_score = _clamp((projected_spend - protected_limit) / max(daily_safe_limit * 0.35, 1.0))
    risk_score = _clamp(
        (0.45 * _clamp(spend_ratio / 1.6))
        + (0.25 * txn_anomaly_score)
        + (0.15 * (1.0 if rapid_txn_flag else 0.0))
        + (0.10 * _clamp(recent_dismissals_24h / 4.0))
        + (0.05 * (1.0 if upi_open_flag else 0.0))
        + (0.10 * goal_pressure_score)
        + (0.10 * _clamp(non_essential_confidence))
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
        "goal_pressure_score": round(goal_pressure_score, 4),
        "non_essential_confidence": round(non_essential_confidence, 4),
        "tone_selected": tone_selected,
        "frequency_bucket": frequency_bucket,
        "pause_seconds": pause_seconds,
    }


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
    localized_alert = _localize_alert(alert, language)
    projected_spend = float(localized_alert.get("projected_daily_spend") or 0.0)
    daily_safe_limit = float(localized_alert.get("daily_safe_limit") or 0.0)
    envelope = _essential_goal_envelope(essential_profile, daily_safe_limit)
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
    features = _compute_contextual_scores(
        participant_id=participant_id,
        amount=float(amount),
        projected_spend=projected_spend,
        daily_safe_limit=daily_safe_limit,
        timestamp=timestamp,
        upi_open_flag=upi_open_flag,
        warmup_active=warmup_active,
        goal_protection_ratio=float(envelope.get("reserve_ratio") or 0.0),
        non_essential_confidence=non_essential_confidence,
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

    risk_level = _risk_level_from_score(float(features["risk_score"]))
    goal_impact = _goal_impact_text(language, envelope, projected_spend)
    reason = str(localized_alert.get("reason") or "")
    why_this = _why_text(
        language=language,
        reason=reason,
        risk_level=risk_level,
        spend_ratio=float(features["spend_ratio"]),
        txn_anomaly_score=float(features["txn_anomaly_score"]),
        upi_open_flag=upi_open_flag,
    )
    next_action = _next_action_text(language=language, risk_level=risk_level, reason=reason)

    contextual_alert = dict(localized_alert)
    contextual_alert["alert_id"] = alert_id
    contextual_alert["risk_score"] = features["risk_score"]
    contextual_alert["confidence_score"] = features["confidence_score"]
    contextual_alert["risk_level"] = risk_level
    contextual_alert["tone_selected"] = features["tone_selected"]
    contextual_alert["frequency_bucket"] = features["frequency_bucket"]
    contextual_alert["pause_seconds"] = features["pause_seconds"]
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
        f"{_localized_label(language, 'risk')}: {_localized_label(language, risk_level)}",
        f"{_localized_label(language, 'why')}: {why_this}",
        f"{_localized_label(language, 'next')}: {next_action}",
    ]
    if goal_impact:
        appended_lines.append(f"{_localized_label(language, 'goal_impact')}: {goal_impact}")
    contextual_alert["message"] = "\n".join([message, *appended_lines]).strip()
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
        "frozen_cohorts": ["women_led_household", "daily_cashflow_worker"],
        "frozen_use_cases": [
            "overspending_prevention",
            "fraud_prevention",
            "essential_goal_savings_behavior",
        ],
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


@app.post("/api/pilot/grievance")
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


@app.get("/api/pilot/grievance")
def pilot_grievance_list(participant_id: Optional[str] = None, limit: int = 100) -> dict:
    safe_limit = max(1, min(limit, 500))
    records = pilot_storage.list_grievances(participant_id=participant_id, limit=safe_limit)
    return {"count": len(records), "grievances": records}


@app.post("/api/pilot/grievance/status")
def pilot_grievance_status(payload: PilotGrievanceStatusIn) -> dict:
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    changed = pilot_storage.update_grievance_status(
        grievance_id=payload.grievance_id,
        status=payload.status,
        timestamp=event_timestamp,
    )
    return {"ok": changed}


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
        language = "en"
        monitor = _build_literacy_monitor("global_user")
        profile = pilot_storage.get_essential_goal_profile("global_user")
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
                    note=payload.note,
                    source="manual_ui",
                    category=payload.category,
                    timestamp=event["timestamp"],
                    upi_open_flag=False,
                    warmup_active=monitor.warmup_active,
                    language=language,
                    essential_profile=profile,
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
    variant = _resolve_experiment_variant(participant_id, "adaptive_alerts_v1")
    event = {
        "timestamp": event_timestamp,
        "type": "expense",
        "amount": payload.amount,
        "category": payload.category,
        "note": payload.note or "Bank SMS detected expense",
    }
    transaction_result = agent.process_event(event)

    monitor = _build_literacy_monitor(participant_id)
    profile = pilot_storage.get_essential_goal_profile(participant_id)
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
    _persist_literacy_monitor(participant_id, monitor)
    policy_recalibrated = _auto_recalibrate_policy(participant_id)
    pilot_storage.add_experiment_event(
        participant_id=participant_id,
        experiment_name="adaptive_alerts_v1",
        variant=variant,
        event_type="sms_ingest",
        payload={
            "amount": payload.amount,
            "category": payload.category,
            "alerts_count": len(literacy_alerts),
            "warmup_active": monitor.warmup_active,
        },
        timestamp=event_timestamp,
    )
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
        "essential_goal_profile": _effective_goal_profile(profile),
        "essential_goal_envelope": _essential_goal_envelope(profile, monitor.status().get("daily_safe_limit", 0.0)),
        "participant_id": participant_id,
        "language": language,
        "experiment_variant": variant,
        "policy_recalibrated": policy_recalibrated,
    }


@app.post("/api/literacy/upi-open")
def literacy_upi_open(payload: UPIOpenIn) -> dict:
    participant_id = (payload.participant_id or "global_user").strip() or "global_user"
    language = _normalized_language(payload.language)
    variant = _resolve_experiment_variant(participant_id, "adaptive_alerts_v1")
    monitor = _build_literacy_monitor(participant_id)
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
        "essential_goal_profile": _effective_goal_profile(profile),
        "essential_goal_envelope": _essential_goal_envelope(profile, monitor.status().get("daily_safe_limit", 0.0)),
        "participant_id": participant_id,
        "language": language,
        "experiment_variant": variant,
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


@app.get("/api/literacy/essential-goals")
def literacy_essential_goals_get(participant_id: str = "global_user") -> dict:
    profile = pilot_storage.get_essential_goal_profile(participant_id)
    daily_safe_limit, _ = _policy_for_participant(participant_id)
    return {
        "participant_id": participant_id,
        "profile": _effective_goal_profile(profile),
        "envelope": _essential_goal_envelope(profile, daily_safe_limit),
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
    daily_safe_limit, _ = _policy_for_participant(participant_id)
    return {
        "ok": True,
        "participant_id": participant_id,
        "profile": _effective_goal_profile(pilot_storage.get_essential_goal_profile(participant_id)),
        "envelope": _essential_goal_envelope(
            pilot_storage.get_essential_goal_profile(participant_id),
            daily_safe_limit,
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
        "essential_goal_profile": _effective_goal_profile(profile),
        "essential_goal_envelope": _essential_goal_envelope(
            profile,
            float((policy or {}).get("daily_safe_limit") or LITERACY_POLICY.daily_safe_limit),
        ),
        "experiment_assignment": assignment,
        "recent_literacy_events": pilot_storage.recent_literacy_events(participant_id, safe_limit),
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
    variant = _resolve_experiment_variant(participant_id, "adaptive_alerts_v1")
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


@app.post("/api/research/assignment")
def research_assignment(payload: ExperimentAssignIn) -> dict:
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
        variant = _resolve_experiment_variant(participant_id, experiment_name)
    assignment = pilot_storage.get_experiment_assignment(participant_id, experiment_name)
    return {
        "ok": True,
        "participant_id": participant_id,
        "experiment_name": experiment_name,
        "variant": variant,
        "assignment": assignment,
    }


@app.post("/api/research/event")
def research_event(payload: ExperimentEventIn) -> dict:
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


@app.get("/api/research/export/experiment-events")
def research_export_experiment_events(
    participant_id: Optional[str] = None,
    experiment_name: Optional[str] = None,
    limit: int = 200,
) -> dict:
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

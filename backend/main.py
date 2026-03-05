from dotenv import load_dotenv
import os

from backend.utils import intent
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from backend.utils.logger import logger

from rule_engine.engine import FinancialAgent
from rule_engine.schemes import evaluate_schemes
from backend.voice.factory import get_voice_provider
from backend.interaction_manager import orchestrate_response
from backend.nlp.pipeline import process_text
from backend.literacy import FinancialLiteracySafetyMonitor
from backend.pilot import PilotStorage



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
    amount: float = Field(gt=0)
    category: str = "bank_sms"
    note: str = ""
    timestamp: Optional[str] = None


class UPIOpenIn(BaseModel):
    app_name: str
    intent_amount: float = Field(default=0.0, ge=0)
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
literacy_monitor = FinancialLiteracySafetyMonitor(daily_safe_limit=1200.0, warning_ratio=0.9)

voice = get_voice_provider()
pilot_storage = PilotStorage()

PILOT_DISCLAIMER = (
    "Arthamantri is a research prototype for financial literacy and safety nudges. "
    "It is not investment advice, not a regulated advisory service, and may make mistakes. "
    "Use your judgement before making payments."
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
        literacy_alerts = literacy_monitor.ingest_expense(
            amount=payload.amount,
            source="manual_ui",
            timestamp=event["timestamp"],
        )
        agent.alerts.extend(literacy_alerts)
        result["literacy_alerts"] = literacy_alerts

    return result


@app.post("/api/literacy/sms-ingest")
def literacy_sms_ingest(payload: SMSIngestIn) -> dict:
    event_timestamp = payload.timestamp or datetime.utcnow().isoformat()
    event = {
        "timestamp": event_timestamp,
        "type": "expense",
        "amount": payload.amount,
        "category": payload.category,
        "note": payload.note or "Bank SMS detected expense",
    }
    transaction_result = agent.process_event(event)

    literacy_alerts = literacy_monitor.ingest_expense(
        amount=payload.amount,
        source="bank_sms",
        timestamp=event_timestamp,
    )
    agent.alerts.extend(literacy_alerts)
    for alert in literacy_alerts:
        pilot_storage.add_literacy_event(
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
        "literacy_state": literacy_monitor.status(),
    }


@app.post("/api/literacy/upi-open")
def literacy_upi_open(payload: UPIOpenIn) -> dict:
    alert = literacy_monitor.on_upi_app_open(
        app_name=payload.app_name,
        intent_amount=payload.intent_amount,
        timestamp=payload.timestamp,
    )
    if alert:
        agent.alerts.append(alert)
        pilot_storage.add_literacy_event(
            event_type="upi_open_alert",
            source="upi_open",
            app_name=payload.app_name,
            amount=payload.intent_amount,
            reason=alert.get("reason"),
            stage=alert.get("stage"),
            daily_spend=alert.get("projected_daily_spend"),
            daily_safe_limit=alert.get("daily_safe_limit"),
            timestamp=payload.timestamp or datetime.utcnow().isoformat(),
        )

    return {"alert": alert, "literacy_state": literacy_monitor.status()}


@app.get("/api/literacy/status")
def literacy_status() -> dict:
    return literacy_monitor.status()


@app.post("/api/literacy/reset")
def literacy_reset() -> dict:
    literacy_monitor.daily_spend = 0.0
    literacy_monitor.threshold_risk_active = False
    literacy_monitor.stage1_sent = False
    literacy_monitor.stage2_sent = False
    literacy_monitor.notifications.clear()
    literacy_monitor.current_date = datetime.utcnow().date().isoformat()
    return {"ok": True, "literacy_state": literacy_monitor.status()}


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

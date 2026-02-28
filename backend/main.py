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

app = FastAPI(title="Arthamantri Prototype", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = FinancialAgent(initial_balance=2000.0)

voice = get_voice_provider()

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


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
    return result


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

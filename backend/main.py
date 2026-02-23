from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

from rule_engine.engine import FinancialAgent


class TransactionIn(BaseModel):
    type: Literal["expense", "income"]
    amount: float = Field(gt=0)
    category: str = "general"
    note: str = ""


class VoiceQueryIn(BaseModel):
    query: str


app = FastAPI(title="Arthamantri Prototype", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = FinancialAgent(initial_balance=2000.0)


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
    response = agent.answer_query(payload.query)
    return {"query": payload.query, "response": response}


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

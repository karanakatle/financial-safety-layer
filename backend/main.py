from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
from backend.db import init_db
from backend.db import get_session
from backend.models.savings_log import SavingsLog
from backend.models.transaction import Transaction
from backend.models.user import User
from sqlmodel import select
from backend.agent.signals import generate_financial_signals
from backend.agent.risk import classify_risk
from backend.agent.guidance import generate_guidance, add_empathy_prefix
from backend.i18n.messages import get_message
from backend.agent.savings import get_savings_progress
from backend.models.commitment import Commitment
from rule_engine.engine import FinancialAgent
from backend.agent.pending_actions import (
    get_pending_action,
    clear_pending_action
)
from backend.agent.intent import detect_affirmation, detect_intent


class TransactionIn(BaseModel):
    user_id: int
    type: Literal["expense", "income"]
    amount: float = Field(gt=0)
    category: str = "general"
    note: str = ""


class VoiceQueryIn(BaseModel):
    query: str
    user_id: int = 1

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # runs when app starts
    yield       # app runs here

app = FastAPI(title="Arthamantri Prototype", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = FinancialAgent(initial_balance=2000.0)

def get_user_transactions(user_id: int):
    with get_session() as session:
        statement = select(Transaction).where(Transaction.user_id == user_id)
        results = session.exec(statement)
        return results.all()
    
def calculate_total_spent(transactions):
    return sum(tx.amount for tx in transactions if tx.amount < 0)

def calculate_balance(transactions):
    return sum(tx.amount for tx in transactions)

def calculate_daily_spend(transactions):
    if not transactions:
        return 0

    days = len(set(tx.timestamp.date() for tx in transactions))
    total_spent = sum(abs(tx.amount) for tx in transactions if tx.amount < 0)

    return total_spent / days if days else 0

def get_user_language(user_id):
    with get_session() as session:
        user = session.get(User, user_id)
        return user.language if user else "en"

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
        "user_id": payload.user_id
    }
    result = agent.process_event(event, payload.user_id)
    return result


@app.post("/api/voice-query")
def voice_query(payload: VoiceQueryIn) -> dict:
    pending = get_pending_action(payload.user_id)
    response = agent.answer_query(payload.query)

    # if user responding to suggestion
    if pending:
        if detect_affirmation(payload.query):
            amount = pending["data"]["amount"]

            commit_saving(payload.user_id, amount)
            clear_pending_action(payload.user_id)

            return {
                "message": f"Bahut badhiya! Roz ₹{amount} bachane se aapka future secure hoga 💛"
            }

        else:
            clear_pending_action(payload.user_id)
            return {"message": "Theek hai, jab aap ready hon tab shuru kar sakte hain."}

    # fallback logic
    intent = detect_intent(payload.query)

    if intent == "BALANCE":
        return {"message": "..."}

    return {"message": "Main aapki madad ke liye yahan hoon."}

    return {"query": payload.query, "response": response}

@app.post("/transaction")
def add_transaction(tx: Transaction):
    with get_session() as session:
        session.add(tx)
        session.commit()
    return {"status": "transaction saved"}

@app.post("/commit-saving")
def commit_saving(user_id: int, amount: float):
    with get_session() as session:
        record = Commitment(user_id=user_id, amount=amount)
        session.add(record)
        session.commit()

    lang = get_user_language(user_id)

    message = get_message("commit_success", lang, amount=amount)

    return {"message": message}

@app.get("/summary/{user_id}")
def financial_summary(user_id: int):
    transactions = get_user_transactions(user_id)

    balance = calculate_balance(transactions)
    daily_spend = calculate_daily_spend(transactions)
    total_spent = calculate_total_spent(transactions)

    monthly_income = 10000  # temporary
    signals = generate_financial_signals(
        balance,
        daily_spend,
        monthly_income
    )

    risks = classify_risk(signals)

    lang = get_user_language(user_id)

    guidance = generate_guidance(risks, signals, lang)
    guidance = add_empathy_prefix(guidance, lang)

    return {
        "balance": balance,
        "daily_spend": daily_spend,
        "signals": signals,
        "risks": risks,
        "guidance": guidance
    }

@app.post("/log-saving")
def log_saving(user_id: int, amount: float):
    with get_session() as session:
        entry = SavingsLog(user_id=user_id, amount=amount)
        session.add(entry)
        session.commit()

    return {"status": "saved"}

@app.get("/savings-progress/{user_id}")
def savings_progress(user_id: int):
    total, days = get_savings_progress(user_id)
    lang = get_user_language(user_id)

    if total >= 500:
        msg = get_message("milestone", lang, total=total)
    else:
        msg = get_message("encourage", lang, total=total)

    return {
        "total_saved": total,
        "days": days,
        "message": msg
    }

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

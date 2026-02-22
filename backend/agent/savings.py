from sqlmodel import select
from backend.db import get_session
from backend.models.savings_log import SavingsLog

def get_savings_progress(user_id):
    with get_session() as session:
        logs = session.exec(
            select(SavingsLog).where(SavingsLog.user_id == user_id)
        ).all()

    total = sum(l.amount for l in logs)
    days = len(logs)

    return total, days
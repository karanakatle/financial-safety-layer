from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class SavingsLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    amount: float
    date: datetime = Field(default_factory=datetime.utcnow)
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    amount: float
    category: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
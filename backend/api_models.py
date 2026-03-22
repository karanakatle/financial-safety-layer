from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class TransactionIn(BaseModel):
    participant_id: str = "global_user"
    type: Literal["expense", "income"]
    amount: float = Field(gt=0)
    category: str = "general"
    note: str = ""


class VoiceQueryIn(BaseModel):
    query: str
    participant_id: str = "global_user"


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
    participant_id: str = "global_user"


class ChatRequest(BaseModel):
    query: str
    language: Optional[str] = "hi"
    participant_id: str = "global_user"


class SavingsDecision(BaseModel):
    accept: bool
    participant_id: str = "global_user"


class SMSIngestIn(BaseModel):
    participant_id: str = "global_user"
    language: str = "en"
    amount: Optional[float] = Field(default=None, ge=0)
    signal_type: Literal["expense", "income", "partial"] = "expense"
    signal_confidence: Literal["confirmed", "partial"] = "confirmed"
    category: str = "bank_sms"
    note: str = ""
    timestamp: Optional[str] = None


class UPIOpenIn(BaseModel):
    participant_id: str = "global_user"
    language: str = "en"
    app_name: str
    intent_amount: float = Field(default=0.0, ge=0)
    timestamp: Optional[str] = None


class UPIRequestInspectIn(BaseModel):
    participant_id: str = "global_user"
    language: str = "en"
    app_name: str = ""
    request_kind: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    payee_label: str = ""
    payee_handle: str = ""
    raw_text: str = ""
    source: str = "android"
    timestamp: Optional[str] = None


class UPIRequestInspectOut(BaseModel):
    scenario: str
    classification: str = "payment_outflow_risk"
    should_warn: bool = True
    risk_level: Literal["low", "medium", "high", "critical"]
    message: str
    why_this_alert: str
    next_best_action: str
    actions: list[str] = Field(default_factory=list)
    alert_id: str


class LiteracyPolicyUpsertIn(BaseModel):
    participant_id: str
    daily_safe_limit: float = Field(gt=0)
    warning_ratio: float = Field(gt=0, lt=1.0)


class LiteracyAlertFeedbackIn(BaseModel):
    event_id: Optional[str] = None
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
    event_id: Optional[str] = None
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

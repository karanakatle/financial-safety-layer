from __future__ import annotations

from datetime import datetime
from typing import Callable

from fastapi import APIRouter

from backend.api_models import AudioRequest, ChatRequest, SavingsDecision, SchemeProfile, TransactionIn, VoiceQueryIn


def build_legacy_router(
    *,
    default_participant_id: str,
    agent_for_participant: Callable[[str | None], object],
    normalized_participant_id: Callable[[str | None], str],
    build_literacy_monitor: Callable[[str], object],
    persist_literacy_monitor: Callable[[str, object], None],
    apply_contextual_alert_intensity: Callable[..., dict | None],
    process_text: Callable[[str], dict],
    evaluate_schemes: Callable[[dict], list],
    orchestrate_response: Callable[..., dict],
    pilot_storage,
    voice,
    logger,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/state")
    def get_state(participant_id: str = default_participant_id) -> dict:
        return agent_for_participant(participant_id).state_snapshot()

    @router.get("/api/alerts")
    def get_alerts(participant_id: str = default_participant_id) -> list[dict]:
        return agent_for_participant(participant_id).alerts

    @router.post("/api/transaction")
    def add_transaction(payload: TransactionIn) -> dict:
        participant_id = normalized_participant_id(payload.participant_id)
        participant_agent = agent_for_participant(participant_id)
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": payload.type,
            "amount": payload.amount,
            "category": payload.category,
            "note": payload.note,
        }
        result = participant_agent.process_event(event)
        literacy_alerts = []
        if payload.type == "expense":
            language = "en"
            monitor = build_literacy_monitor(participant_id)
            profile = pilot_storage.get_essential_goal_profile(participant_id)
            pilot_storage.add_literacy_event(
                participant_id=participant_id,
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
                    contextual := apply_contextual_alert_intensity(
                        participant_id=participant_id,
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
            persist_literacy_monitor(participant_id, monitor)
            participant_agent.alerts.extend(literacy_alerts)
            result["literacy_alerts"] = literacy_alerts

        return result

    @router.post("/api/voice-query")
    def voice_query(payload: VoiceQueryIn) -> dict:
        participant_agent = agent_for_participant(payload.participant_id)
        nlp = process_text(payload.query)
        intent = nlp["intent"]
        score = nlp["confidence"]

        logger.info(
            f"QUERY='{nlp['original']}' | "
            f"NORMALIZED='{nlp['normalized']}' | "
            f"INTENT={intent} | SCORE={score}"
        )
        response = participant_agent.handle_intent(intent)
        return {"query": payload.query, "response": response}

    @router.post("/api/schemes")
    def get_schemes(profile: SchemeProfile) -> dict:
        schemes = evaluate_schemes(profile.dict())
        return {
            "eligible_schemes": schemes,
            "summary": {
                "count": len(schemes),
                "message": "Here are the government schemes you may benefit from.",
            },
        }

    @router.post("/api/voice-audio")
    def voice_audio(req: AudioRequest) -> dict:
        participant_agent = agent_for_participant(req.participant_id)

        result = voice.speech_to_text(req.audio)
        text = result["text"]
        lang = result["language"]

        if text.lower() in ["haan", "yes", "save karo"]:
            confirmation = participant_agent.confirm_savings(True)
            return orchestrate_response(
                confirmation["message"],
                mode="voice",
                language=lang,
                voice_provider=voice,
            )

        nlp = process_text(text)
        intent = nlp["intent"]
        score = nlp["confidence"]
        response_text = participant_agent.handle_intent(intent)
        logger.info(
            f"QUERY='{nlp['original']}' | "
            f"NORMALIZED='{nlp['normalized']}' | "
            f"INTENT={intent} | SCORE={score}"
        )

        if "fraud_warning" in response_text.lower():
            response_text = "Yeh transaction risky lag raha hai. Kripya verify karein."

        return orchestrate_response(
            message=response_text,
            mode="voice",
            language=lang,
            voice_provider=voice,
        )

    @router.post("/api/chat")
    def chat(req: ChatRequest) -> dict:
        participant_agent = agent_for_participant(req.participant_id)
        q = req.query.lower()

        if "save" in q and ("yes" in q or "haan" in q):
            confirmation = participant_agent.confirm_savings(True)
            return orchestrate_response(
                confirmation["message"],
                mode="chat",
                language=req.language,
            )

        nlp = process_text(req.query)
        intent = nlp["intent"]
        score = nlp["confidence"]

        logger.info(
            f"QUERY='{nlp['original']}' | "
            f"NORMALIZED='{nlp['normalized']}' | "
            f"INTENT={intent} | SCORE={score}"
        )
        reply = participant_agent.handle_intent(intent)

        return orchestrate_response(
            reply,
            mode="chat",
            language="hi",
        )

    @router.post("/api/confirm-savings")
    def confirm_savings(decision: SavingsDecision) -> dict:
        return agent_for_participant(decision.participant_id).confirm_savings(decision.accept)

    return router

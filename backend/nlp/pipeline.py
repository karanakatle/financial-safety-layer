from backend.utils.normalize import normalize_text
from backend.utils.intent import detect_intent


def process_text(text: str):
    normalized = normalize_text(text)

    intent, score = detect_intent(normalized)

    return {
        "original": text,
        "normalized": normalized,
        "intent": intent,
        "confidence": score
    }
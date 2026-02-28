from rapidfuzz import fuzz

INTENTS = {
    "balance": [
        "kitna paisa bacha",
        "balance",
        "money left",
        "kitna paisa hai",
        "mera balance",
    ],
    "safe_spend": [
        "kitna kharch kar sakta",
        "safe spend",
        "aaj kharch",
        "spending limit",
    ],
    "schemes": [
        "yojana",
        "scheme",
        "sarkari madad",
        "benefit",
        "government help",
    ],
}


def detect_intent(text):
    text = text.lower()

    best_intent = "unknown"
    best_score = 0

    for intent, phrases in INTENTS.items():
        for phrase in phrases:
            score = fuzz.partial_ratio(text, phrase)

            if score > best_score:
                best_score = score
                best_intent = intent

    if best_score < 60:
        best_intent = "unknown"

    return best_intent, best_score
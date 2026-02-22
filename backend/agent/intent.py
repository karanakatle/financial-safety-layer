def detect_affirmation(text):
    affirmations = [
        "yes", "haan", "ha", "ok", "okay",
        "theek hai", "sure", "haan karunga"
    ]

    text = text.lower()

    return any(word in text for word in affirmations)

def detect_intent(text: str):
    text = text.lower()

    if "balance" in text or "kitna paisa" in text:
        return "BALANCE"

    if "kharcha" in text or "spending" in text:
        return "SPENDING"

    if "bacha sakta" in text or "safe spend" in text:
        return "SAFE_SPEND"

    return "UNKNOWN"
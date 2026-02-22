from backend.i18n.messages import get_message

def generate_guidance(risks, signals, lang="en"):
    guidance = []

    if "RUNWAY_LOW" in risks:
        guidance.append(
            get_message("runway_alert", lang, days=int(signals["runway_days"]))
        )

    if "OVERSPENDING" in risks:
        guidance.append(
            get_message("overspending", lang)
        )

    if "LOW_BALANCE" in risks:
        guidance.append(
            get_message("low_balance", lang)
        )

    if "STABLE" in risks:
        guidance.append(
            get_message("healthy", lang)
        )

    return guidance

def add_empathy_prefix(messages, lang):
    prefix = {
        "en": "💛 We are looking out for you:",
        "hi": "💛 हम आपका ध्यान रख रहे हैं:",
        "te": "💛 మేము మీ గురించి జాగ్రత్తగా ఉన్నాము:",
        "mr": "💛 आम्ही तुमची काळजी घेत आहोत:"
    }

    return [prefix.get(lang, prefix["en"])] + messages
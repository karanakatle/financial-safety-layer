from __future__ import annotations


LITERACY_MESSAGE_CATALOG = {
    "en": {
        "pilot_disclaimer": (
            "Arthamantri is a research prototype for financial literacy and safety nudges. "
            "It is not investment advice, not a regulated advisory service, and may make mistakes. "
            "Use your judgement before making payments."
        ),
        "labels": {
            "risk": "Risk level",
            "why": "Why this alert",
            "next": "Next safe action",
            "goal_impact": "Essential-goal impact",
            "low": "Low",
            "medium": "Medium",
            "high": "High",
            "critical": "Critical",
        },
        "stage1_message": (
            "Daily safe spend is about to be exceeded. "
            "Exceeding amount can disturb your financial planning."
        ),
        "stage2_over_limit_template": (
            "Paying now may exceed your daily safe amount by Rs {daily_overage} "
            "and disturb your weekly planning by around Rs {weekly_impact}."
        ),
        "stage2_close_limit_message": (
            "You are close to your daily limit. Paying now can disturb your financial "
            "planning for today or the week."
        ),
        "daily_essentials": "daily essentials",
        "goal_impact_template": "An extra ₹{delta} spend can pressure your {goal_names} budget.",
        "why_base_template": "Spend ratio {spend_ratio} with {risk_level} risk.",
        "why_suffix_catastrophic": "Transaction amount is unusually high.",
        "why_suffix_upi_open": "Risk remained active when UPI app opened.",
        "why_suffix_anomaly": "This transaction is larger than recent pattern.",
        "next_high_risk": "Pause 5 seconds, verify recipient, and reduce amount before paying.",
        "next_upi_open": "Proceed only if essential; otherwise defer this payment.",
        "next_default": "Stop non-essential spending today and protect essential-goal budget.",
    },
    "hi": {
        "pilot_disclaimer": (
            "अर्थमंत्री वित्तीय साक्षरता और सुरक्षा संकेतों के लिए एक शोध प्रोटोटाइप है। "
            "यह निवेश सलाह नहीं है, कोई विनियमित सलाह सेवा नहीं है, और इसमें त्रुटि हो सकती है। "
            "भुगतान करने से पहले अपना विवेक जरूर लगाएं।"
        ),
        "labels": {
            "risk": "जोखिम स्तर",
            "why": "क्यों दिखा",
            "next": "अगला सुरक्षित कदम",
            "goal_impact": "आवश्यक लक्ष्य प्रभाव",
            "low": "कम",
            "medium": "मध्यम",
            "high": "उच्च",
            "critical": "अत्यधिक",
        },
        "stage1_message": (
            "आपका दैनिक सुरक्षित खर्च सीमा के करीब है। "
            "सीमा पार करने से आपकी वित्तीय योजना प्रभावित हो सकती है।"
        ),
        "stage2_over_limit_template": (
            "अभी भुगतान करने पर आपकी दैनिक सुरक्षित सीमा लगभग ₹{daily_overage} "
            "से पार हो सकती है और साप्ताहिक योजना पर लगभग ₹{weekly_impact} का असर पड़ सकता है।"
        ),
        "stage2_close_limit_message": (
            "आप दैनिक सीमा के करीब हैं। अभी भुगतान करने से आज या सप्ताह की योजना प्रभावित हो सकती है।"
        ),
        "daily_essentials": "दैनिक आवश्यकताएं",
        "goal_impact_template": "₹{delta} का अतिरिक्त खर्च आपके {goal_names} बजट पर दबाव डाल सकता है।",
        "why_base_template": "खर्च अनुपात {spend_ratio} और जोखिम स्तर {risk_level} पाया गया।",
        "why_suffix_catastrophic": "भुगतान राशि असामान्य रूप से अधिक थी।",
        "why_suffix_upi_open": "UPI ऐप खुलने पर जोखिम सक्रिय मिला।",
        "why_suffix_anomaly": "लेन-देन सामान्य से बड़ा है।",
        "next_high_risk": "भुगतान से पहले 5 सेकंड रुकें, प्राप्तकर्ता सत्यापित करें और राशि कम करें।",
        "next_upi_open": "जरूरत होने पर ही भुगतान करें, अन्यथा इसे बाद में करें।",
        "next_default": "आज अनावश्यक खर्च रोकें और आवश्यक लक्ष्य खर्च सुरक्षित रखें।",
    },
}


def _resolve_catalog_value(language: str, key: str):
    active_language = "hi" if language == "hi" else "en"
    current = LITERACY_MESSAGE_CATALOG.get(active_language, LITERACY_MESSAGE_CATALOG["en"])
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            current = None
            break
        current = current[part]
    if current is not None:
        return current

    fallback = LITERACY_MESSAGE_CATALOG["en"]
    for part in key.split("."):
        if not isinstance(fallback, dict) or part not in fallback:
            return None
        fallback = fallback[part]
    return fallback


def literacy_message(language: str, key: str, **kwargs) -> str:
    value = _resolve_catalog_value(language, key)
    if not isinstance(value, str):
        return key
    if not kwargs:
        return value
    try:
        return value.format(**kwargs)
    except (KeyError, ValueError):
        return value


DEFAULT_PILOT_DISCLAIMER = literacy_message("en", "pilot_disclaimer")
DEFAULT_STAGE1_MESSAGE = literacy_message("en", "stage1_message")
DEFAULT_STAGE2_OVER_LIMIT_TEMPLATE = literacy_message("en", "stage2_over_limit_template")
DEFAULT_STAGE2_CLOSE_LIMIT_MESSAGE = literacy_message("en", "stage2_close_limit_message")

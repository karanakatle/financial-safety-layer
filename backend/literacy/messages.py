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
        "goals": {
            "ration": "ration",
            "school": "school fees",
            "fuel": "fuel",
            "medicine": "medicine",
            "rent": "rent",
            "mobile_recharge": "mobile recharge",
            "loan_repayment": "loan repayment",
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
        "cashflow_message_close_limit": "You are close to the safer spending amount for today.",
        "cashflow_message_essential_pressure": "Today's spending is starting to press on money needed for essentials.",
        "cashflow_message_over_limit_essentials": "Today's spending can reduce money needed for essentials.",
        "cashflow_message_upi_open": "Paying now can disturb the money kept aside for today.",
        "why_daily_limit_template": (
            "Today's spending is about Rs {projected_spend} against a safer amount of about Rs {daily_safe_limit}."
        ),
        "why_essential_pressure_template": (
            "After keeping aside money for {goal_names}, only about Rs {protected_limit} remains safer to spend today."
        ),
        "why_recent_income_seen": "A recent money-in message was also seen, so it is safer to keep part of that amount aside.",
        "why_multiple_expenses_seen": "Recent messages also show money going out again today.",
        "why_suffix_catastrophic": "This amount is much higher than usual for the day.",
        "why_suffix_upi_open": "The warning stayed active when the payment app was opened.",
        "why_suffix_anomaly": "This amount looks higher than recent spending messages.",
        "next_high_risk": "Pause here, verify what still must be paid today, and reduce the amount if you can.",
        "next_upi_open": "Pay only if it cannot wait today. Otherwise stop here and do it later.",
        "next_default": "Pause non-essential spending today and review what still must be paid.",
        "next_essential_pressure": "Keep money aside for {goal_names} first. Delay other spending today.",
        "next_essential_pressure_with_income": (
            "Keep part of the recent money received aside for {goal_names} first. Spend more only if it cannot wait."
        ),
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
        "goals": {
            "ration": "राशन",
            "school": "स्कूल फीस",
            "fuel": "ईंधन",
            "medicine": "दवा",
            "rent": "किराया",
            "mobile_recharge": "मोबाइल रिचार्ज",
            "loan_repayment": "कर्ज की किस्त",
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
        "cashflow_message_close_limit": "आप आज के सुरक्षित खर्च के करीब हैं।",
        "cashflow_message_essential_pressure": "आज का खर्च जरूरी जरूरतों के लिए रखे पैसे पर दबाव डालने लगा है।",
        "cashflow_message_over_limit_essentials": "आज का खर्च जरूरी जरूरतों के पैसे को कम कर सकता है।",
        "cashflow_message_upi_open": "अभी भुगतान करने से आज के लिए अलग रखा पैसा बिगड़ सकता है।",
        "why_daily_limit_template": "आज का खर्च लगभग ₹{projected_spend} है और आज का सुरक्षित खर्च लगभग ₹{daily_safe_limit} है।",
        "why_essential_pressure_template": (
            "{goal_names} के लिए पैसा अलग रखने के बाद आज खर्च के लिए लगभग ₹{protected_limit} ही सुरक्षित बचता है।"
        ),
        "why_recent_income_seen": "हाल की एक पैसे आने वाली सूचना भी दिखी थी, इसलिए उसका कुछ हिस्सा अलग रखना ज्यादा सुरक्षित है।",
        "why_multiple_expenses_seen": "हाल की सूचनाएं यह भी दिखा रही हैं कि आज पैसे कई बार निकल रहे हैं।",
        "why_suffix_catastrophic": "यह राशि आज के हिसाब से काफी बड़ी है।",
        "why_suffix_upi_open": "भुगतान ऐप खुलने पर भी यह चेतावनी बनी रही।",
        "why_suffix_anomaly": "यह राशि हाल के खर्च की तुलना में ज्यादा लग रही है।",
        "next_high_risk": "यहीं रुकें, आज क्या जरूरी है उसे जांचें, और हो सके तो राशि कम करें।",
        "next_upi_open": "भुगतान केवल तभी करें जब यह आज ही जरूरी हो। नहीं तो इसे बाद में करें।",
        "next_default": "आज अनावश्यक खर्च रोकें और पहले देखें कि क्या सच में जरूरी है।",
        "next_essential_pressure": "{goal_names} के लिए पैसा पहले अलग रखें। बाकी खर्च आज टाल दें।",
        "next_essential_pressure_with_income": (
            "हाल में मिले पैसे का कुछ हिस्सा {goal_names} के लिए पहले अलग रखें। ज्यादा खर्च तभी करें जब बहुत जरूरी हो।"
        ),
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

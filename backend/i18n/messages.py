MESSAGES = {
    "low_balance": {
        "en": "Your money may run out in a few days.",
        "hi": "आपके पैसे कुछ दिनों में खत्म हो सकते हैं।",
        "te": "మీ డబ్బు కొన్ని రోజుల్లో అయిపోవచ్చు.",
        "mr": "तुमचे पैसे काही दिवसांत संपतील."
    },
    "overspending": {
        "en": "You are spending faster than your income.",
        "hi": "आप अपनी आय से ज़्यादा तेजी से खर्च कर रहे हैं।",
        "te": "మీరు మీ ఆదాయం కంటే వేగంగా ఖర్చు చేస్తున్నారు.",
        "mr": "तुम्ही तुमच्या उत्पन्नापेक्षा जास्त खर्च करत आहात."
    },
    "runway_alert": {
        "en": "Money may last only {days} days.",
        "hi": "पैसे केवल {days} दिन चल सकते हैं।",
        "te": "డబ్బు కేవలం {days} రోజులు మాత్రమే సరిపోతుంది.",
        "mr": "पैसे फक्त {days} दिवस पुरतील."
    },
    "healthy": {
        "en": "Your spending is under control.",
        "hi": "आपका खर्च नियंत्रण में है।",
        "te": "మీ ఖర్చు నియంత్రణలో ఉంది.",
        "mr": "तुमचा खर्च नियंत्रणात आहे."
    },
    "commit_success": {
        "en": "Great! Saving ₹{amount} daily can strengthen your future 💛",
        "hi": "बहुत अच्छा! रोज ₹{amount} बचाने से आपका भविष्य सुरक्षित होगा 💛",
        "te": "చాలా బాగుంది! రోజూ ₹{amount} సేవ్ చేస్తే మీ భవిష్యత్తు బలపడుతుంది 💛",
        "mr": "खूप छान! दररोज ₹{amount} वाचवल्याने तुमचे भविष्य मजबूत होईल 💛"
    },
    "encourage": {
        "en": "You saved ₹{total} so far. Keep going 💛",
        "hi": "आपने अब तक ₹{total} बचाए हैं। ऐसे ही जारी रखें 💛",
        "te": "మీరు ఇప్పటివరకు ₹{total} సేవ్ చేశారు. కొనసాగించండి 💛"
    },
    "milestone": {
        "en": "Wonderful! You saved ₹{total}! 🎉",
        "hi": "शानदार! आपने ₹{total} बचाए! 🎉",
        "te": "అద్భుతం! మీరు ₹{total} సేవ్ చేశారు! 🎉"
    }
}


def get_message(key, lang="en", **kwargs):
    msg = MESSAGES.get(key, {}).get(lang, MESSAGES[key]["en"])
    return msg.format(**kwargs)
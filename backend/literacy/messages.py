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
            "cooking_fuel": "cooking fuel",
            "medicine": "medicine",
            "rent": "rent",
            "electricity": "electricity",
            "water": "water",
            "transport": "transport",
            "mobile_recharge": "mobile recharge",
            "loan_repayment": "loan repayment",
            "work_inputs": "work inputs",
            "family_care": "family care",
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
        "cashflow_message_within_safer_limit": "This looks within your safer limit for today.",
        "cashflow_message_watch_personalized": "This looks close to the safer amount for today.",
        "cashflow_message_burden_personalized": "This may add pressure to money needed for essentials.",
        "cashflow_message_high_pressure_overlay": "This payment looks likely to burden important needs like {goal_names}.",
        "cashflow_message_learning_suffix": "The app is still learning your pattern, so this guidance will get sharper over the next few days.",
        "cashflow_message_low_confidence": "This needs a soft pause. The estimate is still broad, so treat it as a caution signal rather than a precise limit.",
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
        "why_learning_suffix": "Routine overlays stay off while the app learns for about {min_days}-{max_days} days.",
        "why_low_confidence_suffix": "Some inputs are still approximate, so the app is keeping the wording intentionally soft.",
        "why_overlay_suffix": "This rose to a stronger warning because balance, essentials, and recent pressure all point in the same direction for {goal_names}.",
        "next_high_risk": "Pause here, verify what still must be paid today, and reduce the amount if you can.",
        "next_upi_open": "Pay only if it cannot wait today. Otherwise stop here and do it later.",
        "next_default": "Pause non-essential spending today and review what still must be paid.",
        "next_essential_pressure": "Keep money aside for {goal_names} first. Delay other spending today.",
        "next_essential_pressure_with_income": (
            "Keep part of the recent money received aside for {goal_names} first. Spend more only if it cannot wait."
        ),
        "next_learning_suffix": "Use this as a calm check-in while the app learns your routine.",
        "next_low_confidence_suffix": "If the amount is not urgent, wait for a clearer picture before spending more.",
        "next_overlay_high_pressure_suffix": "Pause here and confirm this payment cannot wait before proceeding.",
        "payment_inspection": {
            "ui": {
                "payment_risk_title": "Payment Risk Warning",
                "payment_uncertain_title": "Pause And Verify",
                "account_access_title": "Account Access Warning",
                "payment_primary_action": "Pause and check first",
                "account_access_primary_action": "Protect account first",
                "payment_action_pause": "Pause",
                "payment_action_secondary": "Decline",
                "payment_action_tertiary": "Proceed",
                "payment_action_confirm": "I understand, continue",
                "account_access_action_pause": "Pause",
                "account_access_action_secondary": "Protect account",
                "account_access_action_tertiary": "Continue anyway",
                "account_access_action_confirm": "I understand, continue",
            },
            "collect_request_confusion": {
                "message": "This is not incoming money. Approving this request can send money from your account.",
                "why": (
                    "Collect requests, approval prompts, and autopay mandates can look like money is coming in,"
                    " but approval usually authorizes a payment out from your account."
                ),
                "next": "Pause and verify why this person or business is asking you to approve a payment.",
            },
            "refund_reward_kyc_scam": {
                "message": (
                    "A real refund, reward, or KYC update should not require you to send money."
                    " Approving this can send money from your account."
                ),
                "why": (
                    "Scammers often use refund, cashback, reward, or KYC stories to make users approve"
                    " a collect request or a fake verification fee."
                ),
                "next": "Do not approve inside the payment app. Check with the official app or support separately.",
            },
            "unknown_payee_or_unusual_amount": {
                "message_template": "This request involves an unfamiliar payee or an amount that looks unusual. {direction_line} Pause before you approve it.",
                "why": (
                    "Arthamantri could not match a clearly known payee, or the amount is large enough"
                    " to deserve manual verification."
                ),
                "next": "Verify the payee name and amount on a separate channel. Decline if anything feels unexpected.",
            },
            "unknown": {
                "message_with_context_template": "This request is not fully clear yet. Pause and verify before you approve it. {direction_line}",
                "message_without_context_template": "This payment request could not be read clearly. Pause and verify before you approve it. {direction_line}",
                "why": "Arthamantri could not confidently interpret what this payment will do, so it is showing a cautious warning.",
                "next": "Pause and verify the request source before continuing.",
            },
            "account_access_risk": {
                "message": "This flow may give someone access to your bank or payment account.",
                "why": (
                    "A clicked link was followed by OTP, login, KYC, or banking-access steps."
                    " That pattern is common in account takeover scams."
                ),
                "next": (
                    "Do not share OTP, UPI PIN, banking password, or customer ID."
                    " Check the account only from the official app or number."
                ),
                "why_suffix_risky_domain": "The linked domain also looks risky.",
                "why_suffix_new_bank_like_domain": "The bank-like domain is still new or unverified.",
                "why_suffix_cross_user_reputation": "Similar risk signals have also appeared for this entity across participants.",
            },
            "direction_line_outgoing": "If you approve, money can go out from your account.",
            "direction_line_fallback": "Arthamantri still cannot confirm whether this will send money or receive money.",
            "risky_link_suffix": "This request followed a risky link click, which increases the chance of a scam flow.",
            "sequence_suffix_strong": "Recent app activity also matches a scam-like chain in the last few minutes.",
            "sequence_suffix_medium": "Recent app activity around this request adds more risk context.",
        },
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
            "cooking_fuel": "रसोई ईंधन",
            "medicine": "दवा",
            "rent": "किराया",
            "electricity": "बिजली",
            "water": "पानी",
            "transport": "यातायात",
            "mobile_recharge": "मोबाइल रिचार्ज",
            "loan_repayment": "कर्ज की किस्त",
            "work_inputs": "काम का सामान",
            "family_care": "परिवार देखभाल",
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
        "cashflow_message_within_safer_limit": "यह आज की आपकी सुरक्षित सीमा के भीतर लगता है।",
        "cashflow_message_watch_personalized": "यह आज के सुरक्षित खर्च के काफी करीब लगता है।",
        "cashflow_message_burden_personalized": "यह जरूरी जरूरतों के लिए रखे पैसे पर दबाव बढ़ा सकता है।",
        "cashflow_message_high_pressure_overlay": "यह भुगतान {goal_names} जैसी जरूरी जरूरतों पर ज्यादा दबाव डाल सकता है।",
        "cashflow_message_learning_suffix": "ऐप अभी आपका पैटर्न सीख रहा है, इसलिए यह सलाह अगले कुछ दिनों में और बेहतर होगी।",
        "cashflow_message_low_confidence": "यह एक हल्की सावधानी वाली चेतावनी है। अनुमान अभी चौड़ा है, इसलिए इसे पक्की सीमा नहीं मानें।",
        "why_daily_limit_template": "आज का खर्च लगभग ₹{projected_spend} है और आज का सुरक्षित खर्च लगभग ₹{daily_safe_limit} है।",
        "why_essential_pressure_template": (
            "{goal_names} के लिए पैसा अलग रखने के बाद आज खर्च के लिए लगभग ₹{protected_limit} ही सुरक्षित बचता है।"
        ),
        "why_recent_income_seen": "हाल की एक पैसे आने वाली सूचना भी दिखी थी, इसलिए उसका कुछ हिस्सा अलग रखना ज्यादा सुरक्षित है।",
        "why_multiple_expenses_seen": "हाल की सूचनाएं यह भी दिखा रही हैं कि आज पैसे कई बार निकल रहे हैं।",
        "why_suffix_catastrophic": "यह राशि आज के हिसाब से काफी बड़ी है।",
        "why_suffix_upi_open": "भुगतान ऐप खुलने पर भी यह चेतावनी बनी रही।",
        "why_suffix_anomaly": "यह राशि हाल के खर्च की तुलना में ज्यादा लग रही है।",
        "why_learning_suffix": "ऐप लगभग {min_days}-{max_days} दिनों तक सीखते समय नियमित ओवरले नहीं दिखाता।",
        "why_low_confidence_suffix": "कुछ संकेत अभी अनुमान पर आधारित हैं, इसलिए भाषा जानबूझकर नरम रखी गई है।",
        "why_overlay_suffix": "{goal_names} से जुड़ी जरूरतें, बैलेंस और हाल का दबाव एक साथ मजबूत जोखिम दिखा रहे हैं।",
        "next_high_risk": "यहीं रुकें, आज क्या जरूरी है उसे जांचें, और हो सके तो राशि कम करें।",
        "next_upi_open": "भुगतान केवल तभी करें जब यह आज ही जरूरी हो। नहीं तो इसे बाद में करें।",
        "next_default": "आज अनावश्यक खर्च रोकें और पहले देखें कि क्या सच में जरूरी है।",
        "next_essential_pressure": "{goal_names} के लिए पैसा पहले अलग रखें। बाकी खर्च आज टाल दें।",
        "next_essential_pressure_with_income": (
            "हाल में मिले पैसे का कुछ हिस्सा {goal_names} के लिए पहले अलग रखें। ज्यादा खर्च तभी करें जब बहुत जरूरी हो।"
        ),
        "next_learning_suffix": "इसे एक शांत संकेत की तरह लें, जब तक ऐप आपकी दिनचर्या सीख रहा है।",
        "next_low_confidence_suffix": "अगर भुगतान जरूरी नहीं है, तो थोड़ा रुककर ज्यादा साफ संकेत का इंतजार करें।",
        "next_overlay_high_pressure_suffix": "आगे बढ़ने से पहले रुककर पक्का करें कि यह भुगतान अभी टाला नहीं जा सकता।",
        "payment_inspection": {
            "ui": {
                "payment_risk_title": "भुगतान जोखिम चेतावनी",
                "payment_uncertain_title": "रुकें और जांचें",
                "account_access_title": "अकाउंट एक्सेस चेतावनी",
                "payment_primary_action": "रुकें और पहले जांचें",
                "account_access_primary_action": "पहले अकाउंट सुरक्षित करें",
                "payment_action_pause": "रुकें",
                "payment_action_secondary": "अस्वीकार करें",
                "payment_action_tertiary": "फिर भी आगे बढ़ें",
                "payment_action_confirm": "मैं समझता/समझती हूँ, आगे बढ़ें",
                "account_access_action_pause": "रुकें",
                "account_access_action_secondary": "अकाउंट सुरक्षित करें",
                "account_access_action_tertiary": "फिर भी जारी रखें",
                "account_access_action_confirm": "मैं समझता/समझती हूँ, जारी रखें",
            },
            "collect_request_confusion": {
                "message": "यह अनुरोध पैसा प्राप्त करने का नहीं है। इसे मंजूर करने पर आपके खाते से पैसा जा सकता है।",
                "why": (
                    "कलेक्ट अनुरोध, ऑटोपे या मंजूरी वाले प्रॉम्प्ट कई बार आने वाले पैसे जैसे दिखते हैं,"
                    " लेकिन इन्हें स्वीकार करने पर भुगतान बाहर जा सकता है।"
                ),
                "next": "रुकें और अलग से पुष्टि करें कि सामने वाला आपसे पैसा क्यों मांग रहा है।",
            },
            "refund_reward_kyc_scam": {
                "message": (
                    "असली रिफंड, इनाम या KYC अपडेट के लिए आपको पैसा भेजने की जरूरत नहीं होनी चाहिए।"
                    " यह मंजूरी आपके खाते से पैसा भेज सकती है।"
                ),
                "why": (
                    "ठगी में अक्सर रिफंड, कैशबैक, इनाम या KYC के नाम पर ऐसा अनुरोध भेजा जाता है"
                    " जिससे आप कलेक्ट या फीस जैसा भुगतान मंजूर कर दें।"
                ),
                "next": "भुगतान ऐप के अंदर मंजूरी न दें। आधिकारिक ऐप या सपोर्ट से अलग से जांच करें।",
            },
            "unknown_payee_or_unusual_amount": {
                "message_template": "यह अनुरोध किसी अनजान प्राप्तकर्ता या असामान्य राशि जैसा दिख रहा है। {direction_line} मंजूरी देने से पहले रुककर जांच लें.",
                "why": (
                    "अर्थमंत्री को प्राप्तकर्ता की साफ पहचान नहीं मिली या राशि इतनी अलग दिखी कि"
                    " हाथ से सत्यापन जरूरी हो गया।"
                ),
                "next": "प्राप्तकर्ता का नाम और राशि अलग से पुष्टि करें। कुछ भी अजीब लगे तो अस्वीकार करें।",
            },
            "unknown": {
                "message_with_context_template": "यह अनुरोध पूरी तरह साफ नहीं है। आगे बढ़ने से पहले रुककर जांच लें। {direction_line}",
                "message_without_context_template": "यह भुगतान अनुरोध साफ नहीं पढ़ा जा सका। आगे बढ़ने से पहले रुककर जांच लें। {direction_line}",
                "why": "ऐप इस भुगतान के मतलब को भरोसे के साथ तय नहीं कर सका, इसलिए यह सावधानी वाली चेतावनी दिखा रहा है।",
                "next": "रुकें और भेजने वाले या मांग करने वाले व्यक्ति से अलग से पुष्टि करें।",
            },
            "account_access_risk": {
                "message": "यह फ्लो किसी को आपके बैंक या पेमेंट अकाउंट तक पहुँच दे सकता है।",
                "why": (
                    "एक खुले हुए लिंक के बाद OTP, लॉगिन, KYC या बैंक-एक्सेस जैसा कदम दिखा।"
                    " यह पैटर्न अकाउंट टेकओवर ठगी में आम है।"
                ),
                "next": (
                    "OTP, UPI PIN, बैंक पासवर्ड या ग्राहक आईडी साझा न करें।"
                    " केवल आधिकारिक ऐप या नंबर से ही जाँच करें।"
                ),
                "why_suffix_risky_domain": "लिंक का डोमेन भी जोखिमभरा लग रहा है।",
                "why_suffix_new_bank_like_domain": "बैंक जैसा दिखने वाला डोमेन अभी नया या अप्रमाणित है।",
                "why_suffix_cross_user_reputation": "इसी एंटिटी के लिए अलग प्रतिभागियों में भी ऐसे जोखिम संकेत दिखे हैं।",
            },
            "direction_line_outgoing": "इस मंजूरी से आपके खाते से पैसा जा सकता है।",
            "direction_line_fallback": "ऐप अभी साफ नहीं बता पा रहा कि पैसा जाएगा या आएगा।",
            "risky_link_suffix": "इस अनुरोध से पहले एक जोखिमभरा लिंक खोला गया था, इसलिए ठगी की संभावना और बढ़ जाती है।",
            "sequence_suffix_strong": "पिछले कुछ मिनटों की ऐप गतिविधि भी ठगी जैसे क्रम से मेल खा रही है।",
            "sequence_suffix_medium": "इस अनुरोध के आसपास की हाल की ऐप गतिविधि जोखिम को बढ़ाती है।",
        },
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

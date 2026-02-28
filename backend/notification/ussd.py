from datetime import datetime

class USSDAlert:

    def __init__(self, title, message, options=None, priority="medium"):
        self.title = title
        self.message = message
        self.options = options or []
        self.priority = priority
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "type": "ussd_alert",
            "title": self.title,
            "message": self.message,
            "options": self.options,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat()
        }


def overspending_alert(amount):
    return USSDAlert(
        title="⚠️ Arthamantri Alert",
        message=f"Aapka kharch budget se zyada ho raha hai.\nAaj ₹{amount} kam kharch karein.",
        options=["Theek hai", "Ignore"],
        priority="medium"
    )


def fraud_alert():
    return USSDAlert(
        title="⚠️ Suraksha Alert",
        message="Yeh payment request suspicious ho sakti hai.",
        options=["Reject", "Continue"],
        priority="high"
    )


def night_activity_alert():
    return USSDAlert(
        title="⚠️ Raat ka transaction",
        message="Kripya verify karein. Yeh unusual samay hai.",
        options=["OK"],
        priority="medium"
    )
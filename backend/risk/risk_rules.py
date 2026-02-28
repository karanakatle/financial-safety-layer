from datetime import datetime

def large_transaction(event, state):
    if event["type"] == "expense" and event["amount"] > state["balance"] * 0.6:
        return {
            "risk": "high",
            "reason": "large_transaction",
            "message": "⚠️ Yeh transaction unusual lag raha hai."
        }


def balance_exceeded(event, state):
    if event["type"] == "expense" and event["amount"] > state["balance"]:
        return {
            "risk": "high",
            "reason": "balance_exceeded",
            "message": "⚠️ Yeh transaction aapke balance se zyada hai."
        }


def rapid_transactions(event, state):
    if state.get("recent_txn_count", 0) >= 3:
        return {
            "risk": "medium",
            "reason": "rapid_transactions",
            "message": "⚠️ Bahut jaldi jaldi transactions ho rahe hain."
        }


def night_transaction(event, state):
    hour = datetime.now().hour
    if event["type"] == "expense" and (hour >= 23 or hour < 5):
        return {
            "risk": "medium",
            "reason": "night_activity",
            "message": "⚠️ Raat ke samay transaction unusual ho sakta hai."
        }
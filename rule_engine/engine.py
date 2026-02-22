from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from backend.agent.pending_actions import set_pending_action



@dataclass
class FinancialAgent:
    initial_balance: float = 0.0
    balance: float = field(init=False)
    transactions: list[dict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.balance = self.initial_balance

    def process_event(self, event: dict, user_id) -> dict:
        tx_type = event["type"]
        amount = float(event["amount"])

        if tx_type == "income":
            self.balance += amount
        else:
            self.balance -= amount

        self.transactions.append(event)
        new_alerts = self._generate_alerts(event, user_id)
        self.alerts = new_alerts
        #self.alerts.extend(new_alerts)

        return {
            "balance": round(self.balance, 2),
            "new_alerts": new_alerts,
            "state": self.state_snapshot(),
        }

    def state_snapshot(self) -> dict:
        avg_daily_spend = self._avg_daily_spend()
        days_to_zero = self.balance / avg_daily_spend if avg_daily_spend > 0 else 999
        safe_spend_today = max(self.balance / 5, 0)

        return {
            "balance": round(self.balance, 2),
            "avg_daily_spend": round(avg_daily_spend, 2),
            "days_to_zero": round(days_to_zero, 1),
            "safe_spend_today": round(safe_spend_today, 2),
            "transaction_count": len(self.transactions),
        }

    def answer_query(self, query: str) -> str:
        q = query.lower()
        state = self.state_snapshot()

        if "bacha" in q or "balance" in q:
            return f"Aapke paas ₹{state['balance']} bache hain."
        if "kal" in q and "kharch" in q:
            yesterday_spend = self._latest_expense()
            return f"Recent expense ₹{yesterday_spend} tha."
        if "safe" in q or "aaj" in q:
            return f"Aaj ₹{state['safe_spend_today']} tak spend relatively safe hai."
        return "Main aapko balance, spending aur safe spend limit bata sakta hoon."

    def _latest_expense(self) -> float:
        for tx in reversed(self.transactions):
            if tx["type"] == "expense":
                return round(float(tx["amount"]), 2)
        return 0.0

    def _avg_daily_spend(self) -> float:
        expenses = [float(t["amount"]) for t in self.transactions if t["type"] == "expense"]
        if not expenses:
            return 0.0
        # Prototype approximation: assume last 3 spend events represent recent cadence.
        sample = expenses[-3:]
        return max(mean(sample), 1.0)

    def _generate_alerts(self, event: dict, user_id) -> list[dict]:
        now = datetime.utcnow().isoformat()
        state = self.state_snapshot()
        alerts: list[dict] = []

        if event["type"] == "income":
            suggestion = int(event["amount"] * 0.02)
            alerts.append(
                {
                    "timestamp": now,
                    "priority": "info",
                    "message": f"₹{event['amount']} income received. ₹{suggestion} save karna chahenge?",
                    "reason": "income_event",
                }
            )
            # store pending action
            set_pending_action(user_id, "SAVE_COMMIT", {"amount": suggestion})

        if event["type"] == "expense":
            if state['balance'] < 0:
                alerts.append({
                    "timestamp": now,
                    "priority": "info",
                    "message": "Aap udhaar mein chal rahe hain. Zaroori kharch ke alawa rukna behtar hoga.",
                    "reason": "post_spend_guidance"
                })
            else:
                alerts.append(
                    {
                        "timestamp": now,
                        "priority": "info",
                        "message": (
                            f"₹{state['balance']} bache hain. Aaj ₹{state['safe_spend_today']} aur kharch safe hai."
                        ),
                        "reason": "post_spend_guidance",
                    }
            )

        if state["days_to_zero"] < 3:
            alerts.append(
                {
                    "timestamp": now,
                    "priority": "high",
                    "message": "Agar kharch isi tarah raha to paisa jaldi kam ho sakta hai.",
                    "reason": "low_balance_risk",
                }
            )

        if state["avg_daily_spend"] > 400:
            alerts.append(
                {
                    "timestamp": now,
                    "priority": "medium",
                    "message": "Aaj thoda zyada kharch hua hai. Thoda control rakhen to behtar rahega.",
                    "reason": "overspending",
                }
            )

        return alerts

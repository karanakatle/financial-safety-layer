from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from backend.utils.logger import logger
from backend.risk.risk_engine import RiskEngine



@dataclass
class FinancialAgent:
    initial_balance: float = 0.0
    savings_goal: float = 1000
    balance: float = field(init=False)
    transactions: list[dict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
    pending_savings: float | None = None
    savings_balance: float = 0.0
    

    def __post_init__(self) -> None:
        self.balance = self.initial_balance
        self.recent_txn_count = 0
        self.risk_engine = RiskEngine()

    # =========================
    # EVENT PROCESSING
    # =========================

    def process_event(self, event: dict) -> dict:
        tx_type = event["type"]
        amount = float(event["amount"])

        if tx_type == "income":
            self.balance += amount
            # suggest savings (do not deduct yet)
            self.pending_savings = self._suggest_savings_amount(amount)
        else:
            self.balance -= amount

        self.transactions.append(event)
        new_alerts = self._generate_alerts(event)
        self.alerts.extend(new_alerts)

        risk = self.risk_engine.evaluate(
            event,
            {
                **self.state_snapshot(),
                "recent_txn_count": self.recent_txn_count,
            }
        )

        if risk:
            self.alerts.append({
                "priority": risk["risk"],
                "message": risk["message"],
                "reason": risk["reason"],
                "type": "fraud_warning"
            })

        return {
            "balance": round(self.balance, 2),
            "new_alerts": new_alerts,
            "state": self.state_snapshot(),
        }
    
    # =========================
    # STATE / AWARENESS
    # =========================

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
    
    # =========================
    # CONVERSATIONAL RESPONSES
    # =========================

    def handle_intent(self, intent: str) -> str:
        state = self.state_snapshot()

        if intent == "balance":
            return f"Aaj aapke paas ₹{state['balance']} bache hain."

        if intent == "safe_spend":
            return f"Aaj aap ₹{state['safe_spend_today']} tak kharch kar sakte hain."

        if intent == "schemes":
            return "Aap sarkari yojana ke liye eligible ho sakte hain."

        return self.generate_guidance()

    # =========================
    # COACHING / GUIDANCE
    # =========================

    def generate_guidance(self) -> str:
        """
        Context-aware financial coaching message.
        Used by chat, voice & proactive guidance.
        """
        state = self.state_snapshot()
        days = state["days_to_zero"]
        avg_spend = state["avg_daily_spend"]

        if days < 2:
            save_amount = int(avg_spend * 0.5)
            extra_days = round(save_amount / avg_spend, 1)
            return (
                f"Aaj ₹{save_amount} bachane se "
                f"aapka budget {extra_days} din aur chal sakta hai."
            )

        if days < 5:
            return "Aaj thoda kam kharch karne se financial safety badhegi."

        return "Aapka kharcha control mein hai. Isi tarah discipline banaye rakhein."
    
    def confirm_savings(self, accept: bool):
        """
        Call when user accepts or rejects saving suggestion.
        """
        logger.info(f"SAVINGS_DECISION accept={accept} amount={self.pending_savings}")

        if not self.pending_savings:
            return None

        if accept:
            self.savings_balance += self.pending_savings
            self.balance -= self.pending_savings

            self._update_savings_goal()

            saved = self.pending_savings
            self.pending_savings = None

            return {
                "message": f"₹{saved} safety fund mein add ho gaya.",
                "savings_balance": self.savings_balance
            }

        self.pending_savings = None
        return {"message": "Theek hai, is baar saving skip kar dete hain."}

    # =========================
    # ALERT / INTERVENTIONS
    # =========================

    def _generate_alerts(self, event: dict) -> list[dict]:
        alerts = []

        risk = self._generate_risk_alert()
        if risk:
            alerts.append(risk)

        if event["type"] == "income":
            alerts.append(self._generate_income_nudge(event))

        if event["type"] == "expense":
            alerts.append(self._generate_guidance_message())
            self.recent_txn_count += 1

        behavior = self._generate_behavior_nudge()
        if behavior:
            alerts.append(behavior)

        progress = self._generate_savings_progress()
        if progress:
            alerts.append(progress)

        return self._prioritize_alerts(alerts)
    
    def _prioritize_alerts(self, alerts):
        """
        Returns highest priority alerts only.
        Prevents alert fatigue.
        """

        if not alerts:
            return []

        priority_order = {"high": 3, "medium": 2, "info": 1}

        # sort by priority
        alerts.sort(key=lambda x: priority_order[x["priority"]], reverse=True)

        top_priority = alerts[0]["priority"]

        # return only alerts of highest priority
        filtered = [a for a in alerts if a["priority"] == top_priority]

        # limit count
        return filtered[:2]
    
    def _generate_risk_alert(self):
        state = self.state_snapshot()

        if state["days_to_zero"] < 3:
            return {
                "priority": "high",
                "message": "Paisa 3 din mein khatam ho sakta hai. Kal kam kharch karein.",
                "reason": "low_balance_risk",
            }
        
    def _generate_income_nudge(self, event):
        save = self._suggest_savings_amount(event["amount"])
        return {
            "priority": "info",
            "message": f"₹{event['amount']} income aayi. ₹{save} save karna chahenge?",
            "reason": "income_event",
        }
    
    def _generate_guidance_message(self):
        state = self.state_snapshot()

        return {
            "priority": "info",
            "message": (
                f"₹{state['balance']} bache hain. "
                f"Aaj ₹{state['safe_spend_today']} aur kharch safe hai."
            ),
            "reason": "post_spend_guidance",
        }
    
    def _generate_behavior_nudge(self):
        state = self.state_snapshot()

        if state["avg_daily_spend"] > 400:
            return {
                "priority": "medium",
                "message": "Aaj spending zyada hai. Thoda control karne se safety badhegi.",
                "reason": "overspending",
            }
        
    # =========================
    # INTERNAL HELPERS
    # =========================

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
    
    def _suggest_savings_amount(self, income_amount):
        """
        Suggest realistic savings based on income size.
        """

        if income_amount < 5000:
            return 50

        if income_amount < 15000:
            return 100

        if income_amount < 30000:
            return int(income_amount * 0.05)

        return int(income_amount * 0.08)
    
    def _update_savings_goal(self):
        goals = [500, 1000, 2000, 5000, 10000, 20000]

        for g in goals:
            if self.savings_balance < g:
                self.savings_goal = g
                return
            
    def _generate_savings_progress(self):
        if self.savings_balance == 0:
            return None

        if self.savings_balance >= self.savings_goal:
            return {
                "priority": "info",
                "message": f"Aapne ₹{self.savings_goal} safety fund complete kar liya!",
                "reason": "goal_completed",
            }

        remaining = self.savings_goal - self.savings_balance

        return {
            "priority": "info",
            "message": f"₹{remaining} aur bachakar aapka safety fund ready ho jayega.",
            "reason": "goal_progress",
        }

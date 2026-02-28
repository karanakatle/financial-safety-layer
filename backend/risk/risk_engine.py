from .risk_rules import (
    large_transaction,
    balance_exceeded,
    rapid_transactions,
    night_transaction,
)

RULES = [
    large_transaction,
    balance_exceeded,
    rapid_transactions,
    night_transaction,
]


class RiskEngine:

    def evaluate(self, event, state):
        risks = []

        for rule in RULES:
            result = rule(event, state)
            if result:
                risks.append(result)

        if not risks:
            return None

        # prioritize risk level
        priority = {"high": 3, "medium": 2, "low": 1}
        risks.sort(key=lambda x: priority[x["risk"]], reverse=True)

        return risks[0]  # highest risk only
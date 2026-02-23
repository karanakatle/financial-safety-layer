from rule_engine.engine import FinancialAgent


def test_income_event_generates_income_alert():
    agent = FinancialAgent(initial_balance=1000)
    result = agent.process_event({"type": "income", "amount": 500})
    assert result["balance"] == 1500
    assert any(a["reason"] == "income_event" for a in result["new_alerts"])


def test_low_balance_risk_alert_triggers():
    agent = FinancialAgent(initial_balance=500)
    agent.process_event({"type": "expense", "amount": 450})
    result = agent.process_event({"type": "expense", "amount": 40})
    assert any(a["reason"] == "low_balance_risk" for a in result["new_alerts"])

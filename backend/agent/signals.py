def generate_financial_signals(balance, daily_spend, monthly_income):
    signals = {}

    # runway (days money will last)
    if daily_spend > 0:
        signals["runway_days"] = round(balance / daily_spend, 1)
    else:
        signals["runway_days"] = None

    # spending vs income ratio
    if monthly_income > 0:
        signals["spend_ratio"] = round(
            (daily_spend * 30) / monthly_income, 2
        )
    else:
        signals["spend_ratio"] = None

    # safety buffer
    signals["low_balance"] = balance < daily_spend * 3

    return signals
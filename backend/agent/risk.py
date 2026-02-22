def classify_risk(signals):
    risks = []

    if signals["runway_days"] and signals["runway_days"] < 5:
        risks.append("RUNWAY_LOW")

    if signals["spend_ratio"] and signals["spend_ratio"] > 1.2:
        risks.append("OVERSPENDING")

    if signals["low_balance"]:
        risks.append("LOW_BALANCE")

    if not risks:
        risks.append("STABLE")

    return risks
# Agent Logic (v1)

Core intervention rules:
- Income event -> save suggestion
- Expense event -> safe-spend guidance
- `days_to_zero < 3` -> high-priority risk alert

- `avg_daily_spend > 400` -> overspending warning

This is deterministic and explainable, suitable for early-stage trust experiments.
Á
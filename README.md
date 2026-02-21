# Arthamantri Prototype (v1)

A working **event-driven financial safety agent** prototype to demonstrate agentic intervention logic, explainable alerts, and voice-based interaction.

## Why this exists
This is intentionally a **research-oriented prototype** (not a production fintech app). It is designed to test:
- Intervention timing
- Alert messaging clarity and trust
- User response to agent suggestions

## Features
- Event input (income/expense)
- Financial state engine (`balance`, `avg_daily_spend`, `days_to_zero`, `safe_spend_today`)
- Rule-based intervention engine
- Explainable alerts with priorities
- Voice query endpoint + browser speech interface
- Alert history for behavior analysis

## Architecture
```
User Input (manual/simulated)
  -> Financial State Engine
  -> Intervention Decision Engine
  -> Explainable Messaging
  -> Alerts + Voice Responses
```

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Then open http://localhost:8000.

## Example API
- `GET /api/state`
- `POST /api/transaction`
- `GET /api/alerts`
- `POST /api/voice-query`

## Research docs
- `research/hypotheses.md`
- `research/metrics.md`
- `docs/architecture.md`
- `docs/agent_logic.md`

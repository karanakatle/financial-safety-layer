# Arthamantri — Financial Safety Agent Prototype

**Arthamantri** is an event-driven, agentic financial assistant designed to improve financial resilience among underbanked and underserved individuals.

This prototype demonstrates how **proactive AI agents** can guide users toward safer financial behavior using explainable alerts, conversational interaction, and behavioral nudges.

## Problem Statement
Millions of individuals live paycheck-to-paycheck and lack:
- real-time financial awareness
- early risk warnings
- safe spending guidance
- behavioral support for saving

Traditional banking apps show balances — they do not prevent financial stress.
**Arthamantri acts before financial risk becomes crisis.**

## Project Goals
This research prototype explores:
- Agentic intervention timing
- Trustworthy & explainable alerts
- Behavioral nudging for savings
- Conversational financial guidance
- Human-centered financial literacy delivery

## Key Capabilities
### Financial State Intelligence
- balance tracking
- burn rate estimation
- days-to-zero prediction
- safe spend guidance

### Agentic Intervention Engine
- detects financial risk patterns
- proactive alerts & guidance
- explainable reasoning

### Conversable Agent Interaction
- voice & text queries
- yes/no action confirmations
- conversational decision loops

### Behavioral Savings Nudges
- micro-saving suggestions
- user confirmation workflow
- trust-building encouragement

### Multilingual & Inclusive Messaging
- designed for low-literacy users
- simple, supportive tone

## Architecture
```
User Device (Android/Web)
        ↓
Event Inputs Layer
(SMS parser / manual entry / simulator)
        ↓
Financial State Engine
(balance, burn rate, days-to-zero)
        ↓
Intervention Decision Engine
(when to alert, what to say)
        ↓
Notification & Interaction Layer
(push alerts + voice query)
        ↓
Behavior Tracking & Learning
(user responses & patterns)
```

## ⚙️ Tech Stack

### Backend
- FastAPI
- Python
- Rule-based decision engine
- Conversable intent detection

### Frontend
- Vanilla JS interface
- Voice input & speech output
- Dynamic alert interaction

### Data
- SQLite (prototype)
- SQLModel ORM

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Then open http://localhost:8000.

## How to test it
### 1) Unit tests (fastest)
```bash
pytest -q
```

### 2) Manual UI test
1. Start server with `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`.
2. Open `http://localhost:8000`.
3. Add an `expense` event and verify:
   - balance updates
   - a post-spend guidance alert appears
4. Add a large expense and verify low-balance warning triggers.
5. Ask: `Kitna paisa bacha hai?` and verify response text + TTS output.

### 3) API smoke test (scripted)
With server running:
```bash
./scripts/smoke_test.sh
```
Optional custom URL:
```bash
./scripts/smoke_test.sh http://localhost:8000
```

## Example API
| Endpoint                | Purpose                    |
| ----------------------- | -------------------------- |
| `POST /api/transaction` | Add income/expense         |
| `GET /api/state`        | Financial state            |
| `GET /api/alerts`       | Agent alerts               |
| `POST /api/voice-query` | Conversational interaction |


## Research & Experimentation

This prototype enables research into:
- behavioral response to financial nudges
- trust in AI-generated guidance
- intervention timing effectiveness
- conversational agent adoption

## See
- `research/hypotheses.md`
- `research/metrics.md`
- `docs/architecture.md`
- `docs/agent_logic.md`

## Disclaimer
This is a **research & experimental prototype.**
It does **not provide financial advice** and is not a production banking system.

## Future Directions
### Agent Intelligence
- anomaly detection & fraud alerts
- spending pattern learning
- personalized guidance

### Financial Inclusion
- community savings groups (SHG / bachat gat)
- alternative credit scoring signals
- offline-first accessibility

### AI Research
- agentic decision frameworks
- low-resource language interaction
- behavioral habit reinforcement loops
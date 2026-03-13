# Repository Architecture

This document is the canonical architecture reference for the repository. It describes the live runtime surfaces, the supporting research/simulator stack, and the main interfaces between browser, Android, backend, storage, and voice integrations.

The companion file `docs/architecture_audit.md` contains the file-by-file inventory that backs this document.

## 1. System Context

```mermaid
flowchart LR
    User["End user"]
    Facilitator["Facilitator / researcher"]

    subgraph Clients
        Browser["Browser / PWA\nfrontend/index.html\nfrontend/script.js\nfrontend/sw.js"]
        Android["Native Android app\nMainActivity + background services"]
    end

    subgraph Backend["FastAPI backend"]
        Main["backend/main.py"]
        Legacy["Legacy interaction APIs\n/api/state /api/transaction /api/voice-* /api/chat"]
        Literacy["Literacy APIs\n/api/literacy/*"]
        Pilot["Pilot + research APIs\n/api/pilot/* /api/research/*"]
    end

    subgraph Domain["Decisioning layers"]
        Agent["rule_engine/engine.py\nFinancialAgent"]
        Safety["backend/literacy/*\nSafety monitor + policy + explainability"]
        NLP["backend/nlp/pipeline.py\nbackend/utils/intent.py"]
        Voice["backend/voice/*\nOpenAI or Bhashini adapter"]
    end

    Storage["SQLite pilot store\nbackend/pilot/storage.py"]
    Simulator["Synthetic simulator\nresearch/simulator/*"]
    Scripts["Operator scripts\nscripts/*"]

    User --> Browser
    User --> Android
    Facilitator --> Browser
    Facilitator --> Android
    Facilitator --> Scripts

    Browser <-->|HTTP + static hosting| Main
    Android <-->|HTTPS JSON| Main
    Scripts -->|CLI / smoke checks| Main
    Scripts -->|CLI runs| Simulator

    Main --> Legacy
    Main --> Literacy
    Main --> Pilot

    Legacy --> Agent
    Legacy --> NLP
    Legacy --> Voice
    Literacy --> Safety
    Pilot --> Storage
    Literacy --> Storage
    Legacy --> Storage

    Agent --> Storage
    Safety --> Storage
    Simulator --> Safety
```

### Reading the system

- The browser frontend is served by the same FastAPI app that exposes the JSON endpoints.
- The Android app is a separate native client that sends SMS/UPI-derived events into the backend and renders alert payloads locally.
- Two decision layers coexist:
  - `rule_engine/*` powers the original balance, guidance, and fraud-like legacy agent behavior.
  - `backend/literacy/*` powers participant-scoped literacy safety monitoring, explainability, policy tuning, and research instrumentation.
- `PilotStorage` is the durable boundary for pilot state, feedback, experiment assignments, and alert context.
- `research/simulator/*` reuses the literacy safety model to evaluate policy variants offline.

## 2. Backend Containers And Layers

```mermaid
flowchart TB
    Main["backend/main.py\nFastAPI composition root"]

    subgraph Routers["HTTP surface"]
        PilotRouter["backend/routes/pilot.py"]
        LegacyRouter["backend/routes/legacy.py"]
        InlineLiteracy["Direct literacy endpoints in backend/main.py"]
        StaticHost["StaticFiles mount -> frontend/"]
    end

    subgraph SharedModels["Validation + config"]
        ApiModels["backend/api_models.py"]
        PolicyConfig["backend/config/literacy_policy.py"]
    end

    subgraph RuntimeServices["Runtime services"]
        Storage["backend/pilot/storage.py\nPilotStorage"]
        VoiceFactory["backend/voice/factory.py"]
        VoiceProviders["backend/voice/openai_provider.py\nbackend/voice/bhashini_provider.py"]
        NLP["backend/nlp/pipeline.py\nbackend/utils/normalize.py\nbackend/utils/intent.py"]
        Interaction["backend/interaction_manager.py"]
        RoutesInit["backend/routes/__init__.py"]
    end

    subgraph DomainLogic["Domain logic"]
        RuleEngine["rule_engine/engine.py"]
        Risk["backend/risk/*"]
        Literacy["backend/literacy/safety_monitor.py\ncontext.py\ndecisioning.py\ngoals.py\npolicy.py\nruntime.py\nmessages.py"]
        Schemes["rule_engine/schemes.py"]
    end

    Main --> ApiModels
    Main --> PolicyConfig
    Main --> Storage
    Main --> VoiceFactory
    Main --> NLP
    Main --> Interaction
    Main --> RoutesInit
    Main --> PilotRouter
    Main --> LegacyRouter
    Main --> InlineLiteracy
    Main --> StaticHost

    LegacyRouter --> RuleEngine
    LegacyRouter --> NLP
    LegacyRouter --> Interaction
    LegacyRouter --> Schemes
    LegacyRouter --> Storage
    LegacyRouter --> VoiceProviders

    RuleEngine --> Risk
    InlineLiteracy --> Literacy
    InlineLiteracy --> Storage
    PilotRouter --> Storage
    VoiceFactory --> VoiceProviders
```

### Backend composition notes

- `backend/main.py` is both the app bootstrap and a major controller module: it wires routers, configures CORS, instantiates storage and voice providers, defines literacy endpoints directly, and mounts the web frontend.
- `backend/routes/legacy.py` contains the older interaction surface for manual transactions, voice queries, chat, and schemes.
- `backend/routes/pilot.py` isolates consent, feedback, analytics, grievances, and experiment logging endpoints.
- `backend/literacy/runtime.py` reconstructs and persists `FinancialLiteracySafetyMonitor` from `PilotStorage`.
- `backend/literacy/context.py`, `decisioning.py`, `goals.py`, and `policy.py` enrich raw threshold alerts into explainable, participant-aware alerts.

## 3. Legacy Web / Manual Interaction Flow

```mermaid
sequenceDiagram
    actor User
    participant Web as Browser frontend/script.js
    participant API as FastAPI legacy endpoints
    participant Agent as FinancialAgent
    participant Risk as RiskEngine
    participant Monitor as FinancialLiteracySafetyMonitor
    participant Store as PilotStorage
    participant NLP as NLP pipeline
    participant Voice as Voice provider
    participant Orchestrator as interaction_manager

    User->>Web: Submit expense / ask voice-style query

    alt Manual transaction
        Web->>API: POST /api/transaction
        API->>Agent: process_event(event)
        Agent->>Risk: evaluate(event, state)
        API->>Store: add_literacy_event(...)
        API->>Monitor: ingest_expense(...)
        API->>Store: persist monitor + append alerts
        API-->>Web: balance/state/new_alerts/literacy_alerts
        Web-->>User: Refresh state + render alerts
    else Text query
        Web->>API: POST /api/voice-query
        API->>NLP: process_text(query)
        API->>Agent: handle_intent(intent)
        API-->>Web: text response
        Web-->>User: Render text + browser speech synthesis
    else Audio query
        Web->>API: POST /api/voice-audio
        API->>Voice: speech_to_text(audio)
        API->>NLP: process_text(transcript)
        API->>Agent: handle_intent(intent)
        API->>Orchestrator: orchestrate_response(..., mode=voice)
        Orchestrator->>Voice: text_to_speech(message)
        API-->>Web: text + base64 audio
        Web-->>User: Play returned audio
    end
```

### What is specific to the legacy path

- The browser client keeps a stable `participant_id` in `localStorage`.
- `FinancialAgent` owns transient in-memory participant state for the legacy surface.
- The literacy stack can still augment manual expense events, but the primary UI contract remains the older `/api/state`, `/api/alerts`, and `/api/transaction` loop.

## 4. Android Monitoring And Alert Delivery Flow

```mermaid
sequenceDiagram
    actor OS as Android OS / user context
    participant SMS as BankSmsReceiver
    participant Notif as TransactionNotificationListenerService
    participant Usage as AppUsageForegroundService
    participant Repo as LiteracyRepository
    participant Client as Retrofit LiteracyApi
    participant API as FastAPI literacy endpoints
    participant Monitor as FinancialLiteracySafetyMonitor
    participant Store as PilotStorage
    participant AlertUI as AlertNotifier + Overlay/Activity

    alt Bank SMS debit arrives
        OS->>SMS: SMS_RECEIVED
        SMS->>Repo: sendSmsExpense(amount, category, note)
        Repo->>Client: POST /api/literacy/sms-ingest
    else Transaction notification arrives
        OS->>Notif: onNotificationPosted(...)
        Notif->>Repo: sendSmsExpense(amount, category, notification note)
        Repo->>Client: POST /api/literacy/sms-ingest
    else UPI app enters foreground
        OS->>Usage: foreground app change
        Usage->>Repo: notifyUpiOpen(appName)
        Repo->>Client: POST /api/literacy/upi-open
    end

    Client->>API: JSON request with participant_id + language
    API->>Monitor: ingest_expense(...) or on_upi_app_open(...)
    API->>Store: persist literacy state, events, feedback context, experiment events
    API-->>Client: alert payload + literacy state + profile/envelope
    Client-->>Repo: DTO response
    Repo-->>AlertUI: structured alerts / optional stage-2 pause
    AlertUI-->>OS: notification, overlay, or full-screen activity
```

### What is specific to the Android path

- Android uses device-scoped `participant_id` derived from `ANDROID_ID`.
- SMS, notification, and foreground-app monitoring are three separate event sources that converge into the same literacy API surface.
- `AlertNotifier`, `OverlayAlertWindow`, and `AlertDisplayActivity` are the UI delivery layer for backend-issued alerts.
- The Android app also drives onboarding, consent, Money Setup Lite, and feedback submission against the pilot endpoints.

## 5. Research / Simulation Flow

```mermaid
flowchart LR
    Personas["personas.py\ncohort profiles"]
    Scenarios["scenarios.py\nscenario windows + event streams"]
    Runner["runner.py\nSimulationRunner"]
    Monitor["backend/literacy/safety_monitor.py\nFinancialLiteracySafetyMonitor"]
    Metrics["metrics.py\nparticipant + aggregate summaries"]
    Compare["compare.py\nadaptive vs static comparison"]
    Sweep["sweep.py\npreset scenario sweep"]
    Reports["JSON / text reports\nterminal output"]
    Docs["README + interpretation docs"]

    Personas --> Runner
    Scenarios --> Runner
    Runner --> Monitor
    Runner --> Metrics
    Metrics --> Compare
    Metrics --> Sweep
    Compare --> Reports
    Sweep --> Reports
    Reports --> Docs
```

### Why the simulator matters to architecture

- The simulator is not a separate product runtime, but it is a first-class architecture consumer of the literacy safety model.
- It exercises adaptive vs static policy variants with deterministic persona/scenario inputs and produces research-facing summaries.
- The simulator is the main offline validation path for changes to warning thresholds, warmup behavior, severity policy, and user-outcome assumptions.

## 6. Public Interfaces

### HTTP interfaces

- Legacy web/manual APIs:
  - `GET /api/state`
  - `GET /api/alerts`
  - `POST /api/transaction`
  - `POST /api/voice-query`
  - `POST /api/voice-audio`
  - `POST /api/chat`
  - `POST /api/confirm-savings`
  - `POST /api/schemes`
- Literacy/pilot APIs:
  - `POST /api/literacy/sms-ingest`
  - `POST /api/literacy/upi-open`
  - `GET /api/literacy/status`
  - `GET/POST /api/literacy/policy`
  - `GET/POST /api/literacy/essential-goals`
  - `GET /api/literacy/debug-trace`
  - `GET /api/literacy/storage-health`
  - `POST /api/literacy/reset`
  - `POST /api/literacy/reset-hard`
  - `POST /api/literacy/alert-feedback`
  - `POST /api/literacy/essential-feedback`
  - `GET /api/pilot/meta`
  - `POST /api/pilot/consent`
  - `POST /api/pilot/feedback`
  - `GET /api/pilot/summary`
  - `GET /api/pilot/analytics`
  - `POST /api/pilot/app-log`
  - `POST /api/pilot/grievance`
  - `GET /api/pilot/grievance`
  - `POST /api/pilot/grievance/status`
  - `POST /api/research/assignment`
  - `POST /api/research/event`
  - `GET /api/research/export/experiment-events`

### Backend configuration inputs

- Voice/config selection:
  - `VOICE_PROVIDER`
  - `OPENAI_API_KEY`
- Storage and web serving:
  - `PILOT_DB_PATH`
  - `CORS_ALLOWED_ORIGINS`
- Literacy policy tuning:
  - `LITERACY_DAILY_SAFE_LIMIT`
  - `LITERACY_WARNING_RATIO`
  - `LITERACY_STAGE1_MESSAGE`
  - `LITERACY_STAGE2_OVER_LIMIT_TEMPLATE`
  - `LITERACY_STAGE2_CLOSE_LIMIT_MESSAGE`
  - `LITERACY_WARMUP_DAYS`
  - `LITERACY_WARMUP_SEED_MULTIPLIER`
  - `LITERACY_WARMUP_EXTREME_SPIKE_RATIO`
  - `LITERACY_CATASTROPHIC_ABSOLUTE`
  - `LITERACY_CATASTROPHIC_MULTIPLIER`
  - `LITERACY_CATASTROPHIC_PROJECTED_CAP`

### Android client interfaces

- Build-time inputs:
  - `API_BASE_URL` / `DEFAULT_BASE_URL`
  - `PRIVACY_POLICY_URL`
- Runtime Android platform interfaces:
  - SMS broadcast receiver
  - notification listener service
  - usage-stats foreground service
  - overlay and full-screen alert presentation

### Storage boundary

- `backend/pilot/storage.py` is the only durable storage implementation in the repo.
- It owns SQLite schema creation, WAL configuration, participant policy state, literacy events, alert features, feedback, experiment assignment/events, grievances, and essential-goal learning tables.
- Runtime legacy `FinancialAgent` state is in-memory and participant-scoped inside `backend/main.py`; it is distinct from SQLite-backed literacy state.

## 7. Architectural Tensions To Keep In Mind

- `backend/main.py` is both composition root and feature controller; it currently contains direct literacy endpoint implementations in addition to router wiring.
- There are two alerting models by design:
  - legacy deterministic agent alerts for the browser/manual flow
  - literacy-stage alerts with explainability and persistence for Android/pilot flows
- Android has two ingestion paths for expense-like events (`BankSmsReceiver` and `TransactionNotificationListenerService`) that intentionally converge on the same backend endpoint.
- The web frontend and native Android app consume different subsets of the same backend, so API additions tend to be surface-specific rather than universally shared.

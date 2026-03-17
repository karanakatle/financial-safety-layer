> 🧠 Agentic AI System for Financial Safety • 📱 Android + ⚡ FastAPI • 🔍 Explainable Interventions • 📊 Research-Driven
![Platform](https://img.shields.io/badge/Platform-Android-green)
![Backend](https://img.shields.io/badge/Backend-FastAPI-blue)
![Architecture](https://img.shields.io/badge/Architecture-Event--Driven-orange)
![AI](https://img.shields.io/badge/AI-Agentic--Workflow-purple)
![Status](https://img.shields.io/badge/Status-Research--Prototype-yellow)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![Domain](https://img.shields.io/badge/Domain-Fintech-red)
![Focus](https://img.shields.io/badge/Focus-Financial--Inclusion-brightgreen)
![UX](https://img.shields.io/badge/UX-Explainable--AI-blueviolet)

# 🧠 Agentic Financial Safety Platform

> A research-driven system that helps underbanked users understand risky digital financial moments using phone-native signals and explainable AI.

---

## 🚀 Overview

This project explores how **agentic AI systems can design and implement real-world software products**, while solving a critical problem in financial inclusion:

> Helping users make safer financial decisions *at the moment of action*.

Instead of building another finance app, this system acts as a:

### 👉 Financial Safety & Comprehension Layer

It observes **phone-native signals** (SMS, notifications, app usage) and converts them into:

- explainable financial warnings  
- real-time guidance  
- safe next actions  

---

## ⚠️ Problem

Millions of users already have:

- bank accounts  
- UPI / payment apps  
- digital transactions  

Yet they struggle with:

- confusing **collect payment requests**
- refund / reward scams  
- ambiguous payment prompts  
- lack of awareness of spending impact  

These decisions happen **within seconds**, often leading to:

- accidental payments  
- fraud  
- poor financial decisions  

---

## 💡 Solution

A **real-time financial safety system** that:

- detects risky or confusing financial situations  
- explains them in simple language  
- suggests safe actions  
- measures whether interventions are useful  

Designed for:

- low-confidence users  
- multilingual environments  
- low-infrastructure conditions  

---

## 🚀 Why This is Different

- Does NOT rely on bank integrations  
- Uses phone-native signals (SMS, notifications, app usage)  
- Focuses on decision-time safety (not dashboards)  
- Combines product thinking + system design + AI workflows  
- Built using AI agent orchestration instead of manual coding  

> This project explores a new paradigm: **AI as a system builder, not just a tool.**

---

## 🏗️ System Architecture: Financial Safety Layer

```mermaid
flowchart TB

subgraph Device Layer
A[User Smartphone]
B[SMS Messages]
C[Payment App Notifications]
D[Foreground App Activity]
end

subgraph Signal Processing
E[Android Signal Capture]
F[Context Extraction & Normalization]
end

subgraph Intelligence Layer
G[Payment Risk Inspection Engine]
H[Cashflow Safety Engine]
end

subgraph Intervention Layer
I[Explainable Alert Generator]
J[User Safety Warning UI]
K[Safe Actions<br>Pause / Decline / Proceed]
end

subgraph Analytics Layer
L[Telemetry Capture]
M[Offline Event Queue]
N[Pilot Storage & Analytics]
end

A --> B
A --> C
A --> D

B --> E
C --> E
D --> E

E --> F

F --> G
F --> H

G --> I
H --> I

I --> J
J --> K

K --> L

L --> M
M --> N
```
---

## ⚡ Decision-Time Intervention Flow

```mermaid
sequenceDiagram
    participant User
    participant AndroidApp
    participant Backend
    participant RiskEngine
    participant AlertUI
    participant Telemetry

    User->>AndroidApp: Opens payment app / receives request
    AndroidApp->>Backend: Send context (SMS / notification / app state)
    Backend->>RiskEngine: Classify scenario
    RiskEngine-->>Backend: Risk + explanation

    Backend-->>AndroidApp: Alert payload
    AndroidApp->>AlertUI: Render warning

    AlertUI-->>User: Show consequence
    AlertUI-->>User: Show why this alert
    AlertUI-->>User: Show safest next action

    User->>AlertUI: Choose action

    AlertUI->>Telemetry: Record action
    Telemetry->>Backend: Store for analysis
```
---

## 🤖 AI-Orchestrated Development Architecture

```mermaid
flowchart LR

subgraph Product Design
A[Problem Exploration]
B[Brainstorming Agent]
C[PRD Generation]
D[Architecture Design]
E[UX Specification]
end

subgraph Planning
F[Epic Generation]
G[User Story Creation]
end

subgraph Implementation
H[Development Agent]
I[Backend Implementation]
J[Android Implementation]
K[Telemetry & Analytics]
end

subgraph Validation
L[Validation Agent]
M[Test Scenario Analysis]
N[Bug Fix Agent]
end

subgraph Output
O[Structured Codebase]
P[Research Prototype]
end

A --> B --> C --> D --> E
E --> F --> G

G --> H
H --> I
H --> J
H --> K

I --> L
J --> L
K --> L

L --> M --> N --> O --> P
```
---

## ✨ Key Features

### 🔍 Payment Risk Detection

- Detects collect requests, scams, ambiguous prompts
- Explains consequences before approval

### 💰 Cashflow Safety

- Uses SMS signals to estimate financial pressure
- Protects essential spending

### 🧠 Explainable Alerts

Each alert includes:

>1. what is happening
>2. why this alert
>3. safest next action

### 📊 Research Telemetry

- useful vs noisy alerts
- user actions
- cohort/language analysis

### 📡 Offline Resilience

- queues events offline
- idempotent replay

---

## 🛠️ Tech Stack

### Frontend

- Android (Kotlin)
- SMS + Notification listeners
- Overlay UI

### Backend

- FastAPI
- Decision engine
- Explainability layer
- SQLite storage

### Research Layer

- telemetry analytics
- pilot evaluation
- cohort slicing

---

## 🧪 Research Focus

This is a **research prototype (not production fintech).**

Key questions:

- Which alerts actually help users?
- How to reduce alert fatigue?
- How to personalize financial safety?

---

## 🔬 Deep Dive (Technical)

---

### Why this exists

This is intentionally a **research-oriented prototype** to test:

- intervention timing
- alert clarity
- user behavior

---

### Current MVP Scope

Focuses on:

- risky payment detection
- explainable alerts
- cashflow guidance
- telemetry + pilot analytics

Not intended to be:

- a banking app
- a lending/savings platform
- a full financial advisor

---

## 🏗️ Architecture (High level )

```mermaid
flowchart TD
    A[User Device]
    B["Event Inputs<br/>(SMS / Notifications)"]
    C[Financial State Engine]
    D[Intervention Decision Engine]
    E[Alert + Interaction Layer]
    F[Feedback + Telemetry]

    A --> B --> C --> D --> E --> F
```
The system captures real-time financial signals from the device,
analyzes risk, and intervenes at decision time with explainable guidance.

---

## Backend Structure

- `backend/main.py` → app entry
- `backend/literacy/decisioning.py` → core logic
- `backend/literacy/context.py` → context scoring
- `backend/pilot/storage.py` → telemetry storage
- `backend/routes/pilot.py` → analytics routes

---

## Research System

- pilot telemetry storage
- usefulness vs noise analysis
- cohort-based evaluation
- synthetic simulator

---

## Run Locally

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

---

## Key Insight

The future of software development is not just writing code —
it is designing systems that AI agents can build.

---

## 🔗 Repository

## 📱 Android App
https://github.com/karanakatle/Python-OOS-Project/tree/main/ArthamantriAndroid

## 🧠 Backend System
https://github.com/karanakatle/Python-OOS-Project

---

## 🤝 Discussion

Open to conversations on:

- agentic AI
- fintech systems
- system design
- financial inclusion

---
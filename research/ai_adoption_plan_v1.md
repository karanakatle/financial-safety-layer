# Arthamantri AI Adoption Plan v1

## Purpose
- Define where AI/ML can strengthen Arthamantri without weakening safety or trust.
- Prioritize research tasks that improve the existing financial-safety workflow for underserved users.
- Keep deterministic guardrails in control while AI is introduced in a staged, measurable way.

## Current Product Position
Arthamantri already has:
- phone-native signal capture from SMS, app usage, and notifications
- structured alert telemetry for payment-warning and cashflow guidance
- participant feedback (`useful`, `not_useful`, `dismissed`, payment actions)
- pilot review and analytics infrastructure for language, cohort, and variant analysis

This is enough to begin AI research. It is not yet the right stage to make the core intervention loop depend on unconstrained AI decisions.

## Guardrail Principles
1. AI augments decisions; deterministic rules enforce safety.
2. Payment-risk interventions remain bounded by explicit product rules.
3. User-facing wording should stay template-constrained for high-risk moments.
4. Research models must be evaluated offline before any production influence.
5. Internal/operator copilots can adopt AI earlier than user-facing financial decisions.

## Priority Opportunities

### 1. Message Classification
Use AI/ML to classify raw SMS and notification text into:
- income
- expense
- partial/uncertain
- collect request
- refund
- autopay / mandate
- likely fraud pattern

Why this matters:
- improves trigger quality
- reduces false positives
- broadens coverage of noisy real-world message formats

### 2. Alert Usefulness Prediction
Predict whether a candidate alert is likely to be:
- useful
- noisy
- likely dismissed

Why this matters:
- reduces alert fatigue
- improves trust
- directly supports pilot learning goals already instrumented in telemetry

### 3. Severity and Timing Recommendation
Recommend:
- `soft` vs `medium` vs `hard`
- when to suppress
- when pause friction is worth applying

Why this matters:
- makes interventions more proportionate
- reduces over-alerting for vulnerable or fatigue-prone users

### 4. Operator Analytics Copilot
Use AI to summarize:
- top noisy alert types
- cohort differences
- language-specific gaps
- changes in useful-rate over time

Why this matters:
- accelerates pilot learning
- low risk because it is internal, not direct user guidance

### 5. Facilitator Copilot
Use AI to generate constrained explanation scripts for:
- field workers
- support agents
- trusted-person escalation flows

Why this matters:
- helps low-literacy participants
- scales support without requiring freeform financial advice

## What Not To Do Yet
- do not replace payment-warning guardrails with opaque model decisions
- do not launch an unconstrained AI financial coach
- do not let an autonomous agent decide user-facing safety actions end-to-end
- do not introduce large-model dependencies into the critical runtime path before offline validation

## Six-Week Research Plan

### Week 1: Data Audit and Label Readiness
Goals:
- inventory current telemetry fields usable for AI research
- define target labels for `message_type`, `useful`, `dismissed`, `payment_action`, `fallback`
- identify missing data needed for evaluation

Outputs:
- task definitions
- label schema
- candidate training/evaluation dataset design

Success criteria:
- clear supervised targets for at least message classification and usefulness prediction

### Week 2: Baseline Message Classification
Goals:
- build a baseline offline classifier for message/notification understanding
- compare against current rule-based parsing

Suggested approaches:
- linear baseline with bag-of-words / TF-IDF
- small transformer or multilingual sentence encoder if data quality supports it

Outputs:
- baseline precision/recall by class
- confusion matrix for high-risk classes like collect request vs refund

Success criteria:
- classifier beats current heuristic parsing on offline evaluation for the most safety-relevant classes

### Week 3: Usefulness and Noise Prediction
Goals:
- train a first interpretable model for:
  - useful vs not useful
  - dismissed vs not dismissed

Inputs:
- severity
- risk_level
- scenario
- amount
- source
- language
- cohort
- recent dismissals
- essential-goal context

Outputs:
- baseline usefulness model
- calibration summary
- feature importance review

Success criteria:
- model shows enough lift to justify shadow-mode evaluation

### Week 4: Shadow-Mode Integration Design
Goals:
- design how AI outputs are logged without affecting live decisions
- add shadow prediction fields to telemetry or research exports

Outputs:
- shadow-mode contract
- model output schema
- evaluation dashboard requirements

Success criteria:
- production can record model recommendations without changing current alert behavior

### Week 5: Operator Copilot Prototype
Goals:
- build an internal summarization prototype over pilot analytics
- generate compact summaries of:
  - noisy scenarios
  - useful scenarios
  - language/cohort patterns

Outputs:
- prototype summary prompts or scripts
- operator-facing report examples

Success criteria:
- summaries are accurate enough to speed up pilot review without hallucinating unsupported claims

### Week 6: Decision Memo and Rollout Gate
Goals:
- decide which AI paths are ready for:
  - continued research only
  - shadow mode
  - limited guarded rollout

Outputs:
- recommendation memo
- risk register
- next-quarter implementation candidates

Success criteria:
- one or two AI opportunities selected for guarded next-phase implementation

## Evaluation Questions

### Message Classification
- does AI improve class accuracy for messy real-world texts?
- does it reduce confusion between collect request and refund-like language?

### Usefulness Prediction
- can the model predict likely-noisy alerts better than static thresholds?
- is the model calibrated enough to guide suppression or severity tuning?

### Copilot Outputs
- are summaries grounded in stored telemetry?
- do they reduce analyst effort without inventing unsupported conclusions?

## Recommended First Production Use
If the first research cycle is successful, the safest order for production adoption is:
1. shadow-mode message classification
2. shadow-mode usefulness prediction
3. internal analytics copilot
4. guarded severity/suppression assistance

Do not begin with end-user autonomous financial coaching.

## Dependencies
- stable participant identity
- durable telemetry storage
- enough pilot samples for usefulness/noise analysis
- clear separation between user-facing decisions and internal research outputs

## Decision Standard
AI should be adopted only when it does at least one of the following:
- improves safety capture without increasing false positives too much
- reduces alert fatigue without hiding critical risks
- improves analyst/operator learning speed with grounded evidence

If it cannot show one of these clearly, it should remain in research and not enter the main product loop.

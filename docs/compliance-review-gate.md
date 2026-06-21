# FinSaathi Compliance / Legal Review Gate

## Purpose

This document defines the compliance/legal review gate that must be passed before FinSaathi is used in an external pilot, scaled pilot, bank/NGO/BC-assisted rollout, or public release.

This is a governance checklist, not legal advice. The founder/team must consult a qualified fintech lawyer and privacy lawyer before scaling beyond internal or tightly controlled research testing.

## Product Boundary

FinSaathi is a financial safety guardrail. It can help users pause, understand risk signals, and take safer next steps in risky money moments.

FinSaathi must not present itself as:

- a bank
- a lender
- an investment advisor
- an insurance advisor
- a broker
- a credit approval service
- a product sales channel
- a replacement for regulated financial advice

## Allowed Outputs

FinSaathi may provide:

- simple risk labels such as Green, Yellow, or Red
- plain-language explanation of why a message, payment prompt, loan offer, scheme, or account-access request may be risky
- reminders not to share OTP, UPI PIN, Aadhaar, PAN, bank password, card details, or exact balance
- non-product-specific safety steps such as pause, verify with the official bank/app/source, ask a trusted person, or avoid paying upfront fees
- general financial literacy explanation of terms such as EMI, minimum due, credit score, OTP, UPI collect request, or late fee
- escalation guidance to official bank channels, a verified BC/business correspondent, an NGO facilitator, or a trained human reviewer

## Prohibited Outputs

FinSaathi must not generate or display:

- investment advice, including recommendations to buy, sell, hold, or switch stocks, mutual funds, SIPs, ETFs, gold schemes, crypto, bonds, or any other investment product
- loan recommendation, including telling users which loan to take, where to borrow, or whether a specific lender is best
- lender ranking, lender comparison, loan marketplace ranking, or "best loan app" guidance
- product sales or cross-selling for loans, credit cards, insurance, mutual funds, trading accounts, bank accounts, pensions, or savings products
- guaranteed return claims, income promises, or repayment guarantees
- credit approval, eligibility approval, or repayment-capacity certification
- portfolio allocation, tax planning, insurance planning, or regulated financial planning
- instructions to bypass bank/app security controls
- requests for OTP, UPI PIN, Aadhaar, PAN, card details, bank password, exact bank balance, or login credentials

## External Pilot Gate

Before external pilot or scaled pilot, complete and record the following:

- fintech lawyer review completed
- privacy lawyer review completed
- privacy policy reviewed against the exact Android permissions and backend data flows
- Play Console Data Safety declarations reviewed against the production build
- consent copy reviewed for SMS, notification access, usage access, overlay, and backend processing
- alert copy reviewed for prohibited outputs and regulated financial advice risk
- escalation flow reviewed for high-risk, ambiguous, or user-harm cases
- grievance/contact path reviewed and working
- bank, NGO, or BC partnership compliance needs reviewed where partner-assisted onboarding is used

Do not move to an external pilot until the review owner records a Go decision. Use No-Go when any prohibited output, unclear consent, missing privacy disclosure, unsafe escalation, or partner-compliance gap remains unresolved.

## Copy Review Checklist

Every alert string, onboarding message, store-listing claim, support script, and facilitator script must pass this copy review checklist before external use:

- Uses "safety warning", "rough check", "risk signal", or "pause and verify" language.
- Does not recommend a specific financial product.
- Does not contain investment advice.
- Does not contain loan recommendation.
- Does not rank lenders, loan apps, banks, or investment products.
- Does not imply guaranteed fraud prevention, guaranteed savings, guaranteed income, or guaranteed approval.
- Does not shame the user or create unnecessary fear.
- Explains the reason for the risk in simple language.
- Gives a safe next step such as verify officially, do not pay upfront, do not share sensitive data, contact bank support, or ask a trusted person.
- Includes a human/official escalation path for serious or ambiguous cases.
- Never asks for OTP, UPI PIN, Aadhaar, PAN, bank password, card details, or exact balance.
- Keeps language local, simple, and non-judgmental.

## AI Hallucination And Advice Review

Future AI explanation features must pass a separate hallucination/advice review before being exposed to users.

Minimum requirements:

- AI explanations are grounded in deterministic detector outputs, stored risk category, and approved response templates.
- High-risk alerts remain template-constrained.
- AI cannot invent facts about banks, lenders, schemes, interest rates, approvals, or product eligibility.
- AI cannot recommend financial products, investment actions, lenders, or loans.
- Ambiguous high-risk cases route to human review or official-source verification instead of confident AI advice.
- Test sets include scams, benign messages, confusing payment prompts, and vulnerable-user scenarios.
- Prompt/response review uses redacted data only.
- A kill switch exists to disable AI explanation without disabling basic safety warnings.
- Logged AI outputs are sampled for hallucination, unsafe advice, overconfidence, and language clarity.

## Bank / NGO / BC Partnership Compliance Needs

Before any bank, NGO, or BC/business correspondent assisted rollout:

- document the partner role: outreach only, facilitator, support, escalation, data processor, or co-branded pilot
- define who obtains user consent
- define who can access participant data
- define what data is shared with the partner
- define grievance ownership and response SLA
- train facilitators on prohibited outputs and sensitive-data boundaries
- avoid sales incentives tied to loans, investments, insurance, or other products
- separate safety education from product distribution
- document official escalation routes for fraud, account block, failed payment, and harassment cases

## Review Record Template

Use this template for each review cycle:

| Field | Entry |
|---|---|
| Review date |  |
| Review type | Fintech legal / Privacy legal / Partner compliance / Copy safety / AI hallucination |
| Reviewer name and role |  |
| Build or document version reviewed |  |
| Scope reviewed |  |
| Findings |  |
| Required changes |  |
| Decision | Go / No-Go / Go with conditions |
| Next review trigger |  |

If the decision is "Go with conditions", every condition must have an owner, due date, and written closure note before any external pilot enrollment, scaled pilot enrollment, partner-assisted rollout, or public release. A conditional Go must not be used to bypass a No-Go item.

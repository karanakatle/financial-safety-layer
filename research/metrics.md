# Metrics (Pilot v1)

## Core outcome metrics
- `useful_rate`: useful / (useful + not_useful + dismissed)
- `dismiss_rate`: dismissed / total_feedback_events
- `hard_alert_rate`: hard_bucket_alerts / total_alerts
- `suppression_rate`: suppressed_candidates / total_candidates
- `stage2_conversion`: stage2_alerts / stage1_sessions

## Stability and resilience metrics
- Daily spend variance (7-day rolling).
- High-spike incidence (`txn_anomaly_score >= threshold`) per week.
- Essential-goal pressure incidence (alerts containing goal-impact).

## Trust and usability metrics
- Self-reported trust score (Likert).
- Time-to-action after alert feedback event.
- Language parity: Hindi vs English useful-rate and dismiss-rate.

## Data sources
- `/api/research/export/experiment-events`
- `alert_features` (SQLite)
- `alert_feedback` (SQLite)
- `/api/literacy/debug-trace` for participant-level audits

from __future__ import annotations

"""Shared intervention telemetry helpers.

Payment warnings and cashflow guidance stay as separate intervention families.
Future modules should extend records through additive metadata and trace ids
rather than collapsing family-specific decisioning into one opaque path.
"""


def record_payment_warning_generated(
    *,
    pilot_storage,
    participant_id: str,
    payload,
    inspection: dict,
    timestamp: str,
) -> None:
    pilot_storage.add_unified_telemetry(
        participant_id=participant_id,
        telemetry_family="payment_warning",
        record_type="generated",
        event_name="upi_request_inspection",
        alert_id=inspection.get("alert_id"),
        source_route="/api/literacy/upi-request-inspect",
        source=str(getattr(payload, "source", "") or "android"),
        timestamp=timestamp,
        amount=getattr(payload, "amount", None),
        category="upi_request",
        app_name=(getattr(payload, "app_name", "") or None),
        scenario=str(inspection.get("scenario") or ""),
        risk_level=str(inspection.get("risk_level") or ""),
        summary_text=str(inspection.get("message") or ""),
        context={
            "why_this_alert": inspection.get("why_this_alert"),
            "next_best_action": inspection.get("next_best_action"),
            "actions": list(inspection.get("actions") or []),
            "request_kind": getattr(payload, "request_kind", None),
            "payee_label": getattr(payload, "payee_label", None),
            "payee_handle": getattr(payload, "payee_handle", None),
        },
        extensions={
            "raw_text": getattr(payload, "raw_text", None),
            "language": getattr(payload, "language", None),
        },
    )


def record_cashflow_alert_generated(
    *,
    pilot_storage,
    participant_id: str,
    source_route: str,
    source: str,
    timestamp: str,
    alert: dict,
    amount: float | None = None,
    category: str | None = None,
    app_name: str | None = None,
    signal_type: str | None = None,
    signal_confidence: str | None = None,
    extensions: dict | None = None,
) -> None:
    pilot_storage.add_unified_telemetry(
        participant_id=participant_id,
        telemetry_family="cashflow",
        record_type="generated",
        event_name=f"{source}_alert_generated",
        alert_id=str(alert.get("alert_id") or ""),
        source_route=source_route,
        source=source,
        timestamp=timestamp,
        amount=amount,
        category=category,
        app_name=app_name,
        risk_level=str(alert.get("risk_level") or ""),
        reason=str(alert.get("reason") or ""),
        stage=alert.get("stage"),
        signal_type=signal_type,
        signal_confidence=signal_confidence,
        projected_daily_spend=alert.get("projected_daily_spend"),
        daily_safe_limit=alert.get("daily_safe_limit"),
        risk_score=alert.get("risk_score"),
        confidence_score=alert.get("confidence_score"),
        frequency_bucket=alert.get("frequency_bucket"),
        tone_selected=alert.get("tone_selected"),
        summary_text=str(alert.get("message") or ""),
        context={
            "why_this_alert": alert.get("why_this_alert"),
            "next_best_action": alert.get("next_best_action"),
            "essential_goal_impact": alert.get("essential_goal_impact"),
            "essential_goals": list(alert.get("essential_goals") or []),
            "severity": alert.get("severity"),
            "priority": alert.get("priority"),
            "pause_seconds": alert.get("pause_seconds"),
        },
        extensions={
            "txn_goal_inferred": alert.get("txn_goal_inferred"),
            "txn_goal_confidence": alert.get("txn_goal_confidence"),
            "txn_goal_confidence_gate_passed": alert.get("txn_goal_confidence_gate_passed"),
            "txn_goal_inference_source": alert.get("txn_goal_inference_source"),
            **(extensions or {}),
        },
    )


def record_cashflow_fallback(
    *,
    pilot_storage,
    participant_id: str,
    source_route: str,
    source: str,
    timestamp: str,
    fallback_reason: str,
    summary_text: str,
    alert: dict | None = None,
    amount: float | None = None,
    category: str | None = None,
    app_name: str | None = None,
    signal_type: str | None = None,
    signal_confidence: str | None = None,
    extensions: dict | None = None,
) -> None:
    pilot_storage.add_unified_telemetry(
        participant_id=participant_id,
        telemetry_family="cashflow",
        record_type="fallback",
        event_name=f"{source}_alert_fallback",
        alert_id=str((alert or {}).get("alert_id") or "") or None,
        source_route=source_route,
        source=source,
        timestamp=timestamp,
        amount=amount,
        category=category,
        app_name=app_name,
        risk_level=str((alert or {}).get("risk_level") or ""),
        reason=str((alert or {}).get("reason") or fallback_reason),
        stage=(alert or {}).get("stage"),
        signal_type=signal_type,
        signal_confidence=signal_confidence,
        projected_daily_spend=(alert or {}).get("projected_daily_spend"),
        daily_safe_limit=(alert or {}).get("daily_safe_limit"),
        risk_score=(alert or {}).get("risk_score"),
        confidence_score=(alert or {}).get("confidence_score"),
        frequency_bucket=(alert or {}).get("frequency_bucket"),
        tone_selected=(alert or {}).get("tone_selected"),
        summary_text=summary_text,
        context={
            "fallback_reason": fallback_reason,
            "why_this_alert": (alert or {}).get("why_this_alert"),
            "next_best_action": (alert or {}).get("next_best_action"),
        },
        extensions=extensions,
    )


def record_alert_feedback_telemetry(
    *,
    pilot_storage,
    participant_id: str,
    event_id: str | None,
    alert_id: str,
    action: str,
    channel: str,
    title: str,
    message: str,
    timestamp: str,
) -> None:
    existing = pilot_storage.latest_unified_telemetry_for_alert(alert_id=alert_id, participant_id=participant_id)
    telemetry_family = str((existing or {}).get("telemetry_family") or "cashflow")
    normalized_action = action.strip().lower()
    record_type = (
        "usefulness"
        if telemetry_family == "cashflow" and normalized_action in {"useful", "not_useful"}
        else "action"
    )
    pilot_storage.add_unified_telemetry(
        event_id=event_id,
        participant_id=participant_id,
        telemetry_family=telemetry_family,
        record_type=record_type,
        event_name="alert_feedback",
        alert_id=alert_id,
        source_route="/api/literacy/alert-feedback",
        source="participant_feedback",
        timestamp=timestamp,
        action=normalized_action,
        channel=channel,
        risk_level=(existing or {}).get("risk_level"),
        reason=(existing or {}).get("reason"),
        stage=(existing or {}).get("stage"),
        summary_text=message or title or action,
        context={
            "title": title,
            "message": message,
            "linked_record_type": (existing or {}).get("record_type"),
            "linked_event_name": (existing or {}).get("event_name"),
        },
        extensions={
            "linked_source_route": (existing or {}).get("source_route"),
            "linked_source": (existing or {}).get("source"),
        },
    )


def record_client_app_log_telemetry(
    *,
    pilot_storage,
    participant_id: str,
    event_id: str | None,
    level: str,
    message: str,
    language: str,
    timestamp: str,
) -> bool:
    normalized_message = message.strip()
    if normalized_message.startswith("payment_fallback_shown:"):
        parts = normalized_message.split(":", 5)
        if len(parts) == 6:
            _, alert_id, request_kind, amount_text, payee_label, payee_handle = parts
            amount = None if amount_text in {"", "unknown"} else _safe_float(amount_text)
            return pilot_storage.add_unified_telemetry(
                event_id=event_id,
                participant_id=participant_id,
                telemetry_family="payment_warning",
                record_type="fallback",
                event_name="payment_fallback_shown",
                alert_id=alert_id or None,
                source_route="/api/pilot/app-log",
                source="android_client",
                timestamp=timestamp,
                amount=amount,
                category="upi_request",
                scenario=request_kind or "unknown",
                risk_level="medium",
                summary_text="Device-side payment fallback shown.",
                context={
                    "request_kind": request_kind,
                    "payee_label": payee_label,
                    "payee_handle": payee_handle,
                },
                extensions={
                    "language": language,
                    "log_level": level,
                    "module_family": "payment_warning",
                    "policy_variant": "deterministic_guardrails",
                },
            )
    if normalized_message.startswith("cashflow_fallback_shown:"):
        parts = normalized_message.split(":", 4)
        if len(parts) == 5:
            _, alert_id, fallback_reason, signal_type, amount_text = parts
            amount = None if amount_text in {"", "unknown"} else _safe_float(amount_text)
            return pilot_storage.add_unified_telemetry(
                event_id=event_id,
                participant_id=participant_id,
                telemetry_family="cashflow",
                record_type="fallback",
                event_name="cashflow_fallback_shown",
                alert_id=alert_id or None,
                source_route="/api/pilot/app-log",
                source="android_client",
                timestamp=timestamp,
                amount=amount,
                reason=fallback_reason or "unknown",
                signal_type=signal_type or None,
                summary_text="Device-side cashflow fallback shown.",
                context={"fallback_reason": fallback_reason, "signal_type": signal_type},
                extensions={
                    "language": language,
                    "log_level": level,
                    "module_family": "cashflow",
                    "policy_variant": "deterministic_guardrails",
                },
            )
    return False


def _safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

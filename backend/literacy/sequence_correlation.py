from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


STRONG_WINDOW_SECONDS = 120
MEDIUM_WINDOW_SECONDS = 600
_MESSAGING_MARKERS = ("whatsapp", "telegram", "messages", "messaging", "sms", "call", "phone")
_PAYMENT_APP_MARKERS = ("phonepe", "gpay", "google pay", "paytm", "upi", "bhim", "bank")


@dataclass(frozen=True)
class SequenceEvidence:
    access_confidence: str = "none"
    payment_confidence: str = "none"
    sequence_score: float = 0.0
    sequence_window: str = ""
    sequence_summary: str = ""
    sequence_trace: list[dict] | None = None


def build_sequence_evidence(
    *,
    pilot_storage,
    participant_id: str,
    timestamp: str | None,
    correlation_id: str | None = None,
) -> SequenceEvidence:
    if not participant_id or not timestamp:
        return SequenceEvidence(sequence_trace=[])
    now = _parse_iso(timestamp)
    if now is None:
        return SequenceEvidence(sequence_trace=[])

    records = pilot_storage.recent_app_logs(
        participant_id=participant_id,
        limit=120,
        correlation_id=correlation_id,
        context_only=True,
    )
    relevant: list[dict] = []
    for record in records:
        event_time = _parse_iso(record.get("timestamp"))
        if event_time is None or event_time > now:
            continue
        delta_seconds = int((now - event_time).total_seconds())
        if delta_seconds < 0 or delta_seconds > MEDIUM_WINDOW_SECONDS:
            continue
        weighted = _weight_record(record, delta_seconds)
        if weighted is not None:
            relevant.append(weighted)

    if not relevant:
        return SequenceEvidence(sequence_trace=[])

    relevant.sort(key=lambda item: (item["timestamp"], item["event_type"]))
    access_score = float(sum(item["access_weight"] for item in relevant))
    payment_score = float(sum(item["payment_weight"] for item in relevant))
    max_score = max(access_score, payment_score)
    strongest_recent_delta = min(item["delta_seconds"] for item in relevant)
    window = "0-120s" if strongest_recent_delta <= STRONG_WINDOW_SECONDS else "2-10m"
    trace = [
        {
            "timestamp": item["timestamp"],
            "event_type": item["event_type"],
            "message_family": item["message_family"],
            "source_app": item["source_app"],
            "target_app": item["target_app"],
            "delta_seconds": item["delta_seconds"],
            "signal": item["signal"],
        }
        for item in relevant[:5]
    ]

    return SequenceEvidence(
        access_confidence=_access_confidence(relevant, access_score),
        payment_confidence=_payment_confidence(relevant, payment_score),
        sequence_score=max_score,
        sequence_window=window,
        sequence_summary=_sequence_summary(relevant),
        sequence_trace=trace,
    )


def build_recent_sequence_groups(
    *,
    pilot_storage,
    participant_id: str | None = None,
    limit: int = 25,
) -> list[dict]:
    records = pilot_storage.recent_app_logs(
        participant_id=participant_id,
        limit=max(limit * 12, 60),
        context_only=True,
    )
    ordered: list[dict] = []
    for record in reversed(records):
        event_time = _parse_iso(record.get("timestamp"))
        if event_time is None:
            continue
        ordered.append({**record, "_event_time": event_time})

    groups: list[dict] = []
    current: list[dict] = []
    current_key: tuple[str, str] | None = None

    for record in ordered:
        participant = str(record.get("participant_id") or "")
        correlation = str(record.get("correlation_id") or "").strip()
        key = (participant, correlation or "")
        if not current:
            current = [record]
            current_key = key
            continue

        last = current[-1]
        same_key = current_key == key and bool(correlation)
        within_window = participant == str(last.get("participant_id") or "") and (
            record["_event_time"] - last["_event_time"]
        ) <= timedelta(seconds=MEDIUM_WINDOW_SECONDS)

        if same_key or within_window:
            current.append(record)
        else:
            groups.append(_format_group(current))
            current = [record]
            current_key = key

    if current:
        groups.append(_format_group(current))

    groups.sort(key=lambda item: item["ended_at"], reverse=True)
    return groups[:limit]


def _format_group(records: list[dict]) -> dict:
    started = records[0]["_event_time"]
    ended = records[-1]["_event_time"]
    span_seconds = int((ended - started).total_seconds())
    window = "0-120s" if span_seconds <= STRONG_WINDOW_SECONDS else "2-10m"
    event_types = [str(record.get("event_type") or "") for record in records if str(record.get("event_type") or "")]
    return {
        "participant_id": records[0].get("participant_id"),
        "correlation_id": records[0].get("correlation_id"),
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "window": window,
        "event_count": len(records),
        "event_types": event_types,
        "trace": [
            {
                "timestamp": record.get("timestamp"),
                "event_type": record.get("event_type"),
                "message_family": record.get("message_family"),
                "source_app": record.get("source_app"),
                "target_app": record.get("target_app"),
            }
            for record in records[:5]
        ],
    }


def _weight_record(record: dict, delta_seconds: int) -> dict | None:
    event_type = str(record.get("event_type") or "").strip().lower()
    message_family = str(record.get("message_family") or "").strip().lower()
    source_app = str(record.get("source_app") or "").strip().lower()
    target_app = str(record.get("target_app") or "").strip().lower()
    signal = None
    access_weight = 0.0
    payment_weight = 0.0
    multiplier = 1.0 if delta_seconds <= STRONG_WINDOW_SECONDS else 0.5

    if event_type == "chat_context" or _looks_messaging(source_app) or _looks_messaging(target_app):
        signal = "chat_or_call_context"
        access_weight = 2.0 * multiplier
        payment_weight = 1.0 * multiplier
    elif event_type == "link_click" or bool(record.get("link_clicked")):
        signal = "clicked_link"
        access_weight = 4.0 * multiplier
        payment_weight = 2.0 * multiplier
    elif event_type == "app_open" and (_looks_payment_app(source_app) or _looks_payment_app(target_app)):
        signal = "payment_or_bank_app_open"
        access_weight = 1.0 * multiplier
        payment_weight = 2.0 * multiplier
    elif event_type in {"sms_observed", "notification_observed"} and (
        bool(record.get("has_otp")) or message_family == "otp_verification"
    ):
        signal = "otp_or_access_message"
        access_weight = 3.0 * multiplier
    elif event_type == "account_access_candidate" or message_family in {"otp_verification", "sensitive_access"}:
        signal = "account_access_candidate"
        access_weight = 4.0 * multiplier
    elif event_type == "payment_candidate" or message_family == "payment_signal":
        signal = "payment_candidate"
        payment_weight = 4.0 * multiplier

    if not signal:
        return None

    return {
        "timestamp": str(record.get("timestamp") or ""),
        "event_type": event_type,
        "message_family": message_family,
        "source_app": source_app,
        "target_app": target_app,
        "delta_seconds": delta_seconds,
        "signal": signal,
        "access_weight": access_weight,
        "payment_weight": payment_weight,
    }


def _access_confidence(relevant: list[dict], score: float) -> str:
    signals = {item["signal"] for item in relevant}
    if score >= 7.0 and "clicked_link" in signals and ("otp_or_access_message" in signals or "account_access_candidate" in signals):
        return "strong"
    if score >= 5.0 and len(signals) >= 2:
        return "medium"
    return "none"


def _payment_confidence(relevant: list[dict], score: float) -> str:
    signals = {item["signal"] for item in relevant}
    if score >= 7.0 and "payment_candidate" in signals:
        return "strong"
    if score >= 5.0 and len(signals) >= 2:
        return "medium"
    return "none"


def _sequence_summary(relevant: list[dict]) -> str:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in relevant:
        signal = item["signal"]
        if signal in seen:
            continue
        seen.add(signal)
        ordered.append(signal)
    return " -> ".join(ordered[:4])


def _looks_messaging(value: str) -> bool:
    return any(marker in value for marker in _MESSAGING_MARKERS)


def _looks_payment_app(value: str) -> bool:
    return any(marker in value for marker in _PAYMENT_APP_MARKERS)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None

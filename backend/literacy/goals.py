from __future__ import annotations

import hashlib
import re

from fastapi import HTTPException


def merchant_key_from_note(note: str, source: str, category: str) -> str:
    base = f"{note} {source} {category}".lower()
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", base)
    cleaned = re.sub(r"\b\d{3,}\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = f"{source}:{category}"
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    return digest[:24]


def goal_from_keywords(
    text: str,
    *,
    non_essential_keywords: set[str],
    merchant_keyword_map: dict[str, set[str]],
    non_essential_goal: str,
) -> tuple[str, float, str]:
    lower = text.lower()
    if any(token in lower for token in non_essential_keywords):
        return non_essential_goal, 0.78, "keyword_non_essential"
    for goal, words in merchant_keyword_map.items():
        if any(word in lower for word in words):
            return goal, 0.58, "keyword_essential"
    return "unknown", 0.0, "none"


def goal_from_memory(participant_id: str, merchant_key: str, *, pilot_storage) -> tuple[str, float, str]:
    rows = pilot_storage.goal_memory_rows(participant_id, merchant_key)
    if not rows:
        return "unknown", 0.0, "none"

    best_goal = "unknown"
    best_score = 0.0
    best_count = 0
    for row in rows:
        pos = int(row.get("positive_count") or 0)
        neg = int(row.get("negative_count") or 0)
        total = pos + neg
        if total <= 0:
            continue
        score = (pos + 1.0) / (total + 2.0)
        if score > best_score:
            best_score = score
            best_goal = str(row.get("goal") or "unknown")
            best_count = total

    if best_goal == "unknown":
        return "unknown", 0.0, "none"

    memory_conf = min(0.55, 0.22 + (best_count * 0.06))
    return best_goal, memory_conf, "memory"


def infer_goal_context(
    *,
    participant_id: str,
    note: str,
    source: str,
    category: str,
    profile: dict | None,
    effective_goal_profile,
    pilot_storage,
    non_essential_keywords: set[str],
    merchant_keyword_map: dict[str, set[str]],
    supported_essential_goals: set[str],
    non_essential_goal: str,
    goal_confidence_gate: float,
) -> dict:
    profile_goals = set((effective_goal_profile(profile).get("essential_goals") or []))
    merchant_key = merchant_key_from_note(note=note, source=source, category=category)
    keyword_goal, keyword_conf, keyword_source = goal_from_keywords(
        note,
        non_essential_keywords=non_essential_keywords,
        merchant_keyword_map=merchant_keyword_map,
        non_essential_goal=non_essential_goal,
    )
    memory_goal, memory_conf, _ = goal_from_memory(
        participant_id,
        merchant_key,
        pilot_storage=pilot_storage,
    )

    inferred_goal = "unknown"
    confidence = 0.0
    confidence_source = "none"

    if keyword_conf > 0 or memory_conf > 0:
        if keyword_goal == memory_goal and keyword_goal != "unknown":
            inferred_goal = keyword_goal
            confidence = min(0.95, keyword_conf + memory_conf + 0.12)
            confidence_source = "keyword+memory"
        elif memory_conf >= keyword_conf and memory_goal != "unknown":
            inferred_goal = memory_goal
            confidence = memory_conf
            confidence_source = "memory"
        elif keyword_goal != "unknown":
            inferred_goal = keyword_goal
            confidence = keyword_conf
            confidence_source = keyword_source

    if inferred_goal in supported_essential_goals and confidence_source == "memory":
        confidence = min(confidence, 0.7)

    gate_passed = (
        confidence >= goal_confidence_gate
        and (
            inferred_goal == non_essential_goal
            or inferred_goal in profile_goals
        )
    )
    gated_goal = inferred_goal if gate_passed else "unknown"

    return {
        "merchant_key": merchant_key,
        "raw_goal": inferred_goal,
        "gated_goal": gated_goal,
        "confidence": round(confidence, 4),
        "gate_passed": gate_passed,
        "source": confidence_source,
        "profile_goals": sorted(profile_goals),
    }


def apply_goal_feedback_learning(
    *,
    participant_id: str,
    alert_id: str,
    is_essential: bool,
    selected_goal: str | None,
    timestamp: str,
    pilot_storage,
    normalized_goal_feedback_value,
    supported_goal_feedback_values: set[str],
    supported_essential_goals: set[str],
    non_essential_goal: str,
) -> dict:
    context = pilot_storage.get_alert_goal_context(alert_id, participant_id)
    if not context:
        raise HTTPException(status_code=404, detail="Alert context not found for participant")

    chosen = normalized_goal_feedback_value(selected_goal)
    if chosen == "unknown":
        inferred_goal = str(context.get("inferred_goal") or "unknown")
        chosen = inferred_goal if inferred_goal in supported_goal_feedback_values else non_essential_goal

    source_confidence = float(context.get("confidence") or 0.0)
    merchant_key = str(context.get("merchant_key") or "")
    if not merchant_key:
        raise HTTPException(status_code=400, detail="Invalid merchant context")

    if is_essential:
        if chosen not in supported_essential_goals:
            raise HTTPException(status_code=400, detail="Essential feedback requires a supported essential goal")
        positive_delta = 1
        negative_delta = 0
    else:
        positive_delta = 1 if chosen == non_essential_goal else 0
        negative_delta = 1 if chosen in supported_essential_goals else 0

    pilot_storage.upsert_goal_memory(
        participant_id=participant_id,
        merchant_key=merchant_key,
        goal=chosen,
        delta_positive=positive_delta,
        delta_negative=negative_delta,
        timestamp=timestamp,
    )
    pilot_storage.add_goal_feedback(
        participant_id=participant_id,
        alert_id=alert_id,
        merchant_key=merchant_key,
        selected_goal=chosen,
        is_essential=is_essential,
        source_confidence=source_confidence,
        timestamp=timestamp,
    )
    return {
        "merchant_key": merchant_key,
        "selected_goal": chosen,
        "is_essential": is_essential,
        "source_confidence": source_confidence,
    }

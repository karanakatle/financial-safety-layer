from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "ArthamantriAndroid"
    / "app"
    / "src"
    / "main"
    / "assets"
    / "essential_goal_setup_config.json"
)
_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


def _validate_identifier(value: str, *, label: str) -> str:
    normalized = str(value or "").strip().lower()
    if not _ID_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid {label}: {value!r}")
    return normalized


def _parse_config() -> dict[str, Any]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    categories = data.get("categories") or []
    cohorts = data.get("cohorts") or []
    if not isinstance(categories, list) or not categories:
        raise ValueError("essential goal config requires categories")
    if not isinstance(cohorts, list) or not cohorts:
        raise ValueError("essential goal config requires cohorts")

    category_ids: set[str] = set()
    alias_ids: set[str] = set()
    for category in categories:
        category_id = _validate_identifier(category.get("id"), label="category id")
        if category_id in category_ids:
            raise ValueError(f"Duplicate category id: {category_id}")
        category_ids.add(category_id)
        for alias in list(category.get("legacy_aliases") or []):
            normalized_alias = _validate_identifier(alias, label="legacy alias")
            if normalized_alias in alias_ids or normalized_alias in category_ids:
                raise ValueError(f"Duplicate legacy alias: {normalized_alias}")
            alias_ids.add(normalized_alias)

    cohort_ids: set[str] = set()
    for cohort in cohorts:
        cohort_id = _validate_identifier(cohort.get("id"), label="cohort id")
        if cohort_id in cohort_ids:
            raise ValueError(f"Duplicate cohort id: {cohort_id}")
        cohort_ids.add(cohort_id)

        supported = [_validate_identifier(value, label="supported category") for value in list(cohort.get("supported_categories") or [])]
        defaults = [_validate_identifier(value, label="default priority") for value in list(cohort.get("default_priorities") or [])]
        if len(defaults) < 5 or len(defaults) > int(data.get("active_priority_limit") or 6):
            raise ValueError(f"Cohort {cohort_id} must define 5-6 default priorities")
        unknown = (set(supported) | set(defaults)) - category_ids
        if unknown:
            raise ValueError(f"Cohort {cohort_id} references unknown categories: {sorted(unknown)}")

        prompt = cohort.get("affordability_prompt") or {}
        _validate_identifier(prompt.get("question_key"), label="affordability question key")
        bucket_ids: set[str] = set()
        for bucket in list(prompt.get("buckets") or []):
            bucket_id = _validate_identifier(bucket.get("id"), label="bucket id")
            if bucket_id in bucket_ids:
                raise ValueError(f"Duplicate bucket id {bucket_id} in cohort {cohort_id}")
            bucket_ids.add(bucket_id)
            boosts = bucket.get("seed_boosts") or {}
            if not isinstance(boosts, dict):
                raise ValueError(f"Bucket boosts must be an object for cohort {cohort_id}:{bucket_id}")
            unknown_boosts = {_validate_identifier(goal_id, label="seed boost key") for goal_id in boosts.keys()} - category_ids
            if unknown_boosts:
                raise ValueError(
                    f"Bucket {bucket_id} in cohort {cohort_id} references unknown categories: {sorted(unknown_boosts)}"
                )
    return data


@lru_cache(maxsize=1)
def essential_goal_setup_config() -> dict[str, Any]:
    return _parse_config()


def active_priority_limit() -> int:
    return int(essential_goal_setup_config().get("active_priority_limit") or 6)


def config_version() -> str:
    return str(essential_goal_setup_config().get("config_version") or "unknown")


def category_catalog() -> list[dict[str, Any]]:
    return list(essential_goal_setup_config().get("categories") or [])


def supported_goal_ids() -> set[str]:
    return {str(category.get("id")) for category in category_catalog()}


def supported_cohort_ids() -> set[str]:
    return {str(cohort.get("id")) for cohort in list(essential_goal_setup_config().get("cohorts") or [])}


def goal_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for category in category_catalog():
        category_id = str(category.get("id"))
        aliases[category_id] = category_id
        for alias in list(category.get("legacy_aliases") or []):
            aliases[str(alias)] = category_id
    return aliases


def normalize_goal_id(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return goal_aliases().get(normalized, "")


def normalize_cohort_id(value: str | None, *, default: str = "daily_cashflow_worker") -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in supported_cohort_ids() else default


def cohort_config(cohort_id: str) -> dict[str, Any]:
    normalized = normalize_cohort_id(cohort_id)
    for cohort in list(essential_goal_setup_config().get("cohorts") or []):
        if str(cohort.get("id")) == normalized:
            return cohort
    raise KeyError(normalized)


def prompt_config(cohort_id: str) -> dict[str, Any]:
    return dict(cohort_config(cohort_id).get("affordability_prompt") or {})


def normalize_affordability_bucket_id(cohort_id: str, bucket_id: str | None) -> str | None:
    normalized = str(bucket_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return None
    for bucket in list(prompt_config(cohort_id).get("buckets") or []):
        if str(bucket.get("id")) == normalized:
            return normalized
    return None


def affordability_question_key(cohort_id: str) -> str:
    return str(prompt_config(cohort_id).get("question_key") or "")


def default_priorities_for_cohort(cohort_id: str) -> list[str]:
    return [normalize_goal_id(value) for value in list(cohort_config(cohort_id).get("default_priorities") or []) if normalize_goal_id(value)]


def supported_categories_for_cohort(cohort_id: str) -> list[str]:
    cohort = cohort_config(cohort_id)
    supported = [normalize_goal_id(value) for value in list(cohort.get("supported_categories") or []) if normalize_goal_id(value)]
    return supported or default_priorities_for_cohort(cohort_id)


def deterministic_seed_order(cohort_id: str, bucket_id: str | None = None) -> list[str]:
    normalized_cohort = normalize_cohort_id(cohort_id)
    normalized_bucket = normalize_affordability_bucket_id(normalized_cohort, bucket_id)
    supported = supported_categories_for_cohort(normalized_cohort)
    defaults = default_priorities_for_cohort(normalized_cohort)
    default_rank = {goal_id: index for index, goal_id in enumerate(defaults)}
    global_rank = {str(category.get("id")): index for index, category in enumerate(category_catalog())}
    boosts: dict[str, int] = {}
    if normalized_bucket:
        for bucket in list(prompt_config(normalized_cohort).get("buckets") or []):
            if str(bucket.get("id")) == normalized_bucket:
                raw_boosts = bucket.get("seed_boosts") or {}
                boosts = {normalize_goal_id(goal_id): int(value) for goal_id, value in raw_boosts.items() if normalize_goal_id(goal_id)}
                break

    def _score(goal_id: str) -> tuple[int, int, int]:
        boost = boosts.get(goal_id, 0)
        rank = default_rank.get(goal_id, 999)
        return (-boost, rank, global_rank.get(goal_id, 999))

    return sorted(supported, key=_score)


def goal_setup_payload() -> dict[str, Any]:
    config = essential_goal_setup_config()
    return {
        "config_version": config_version(),
        "active_priority_limit": active_priority_limit(),
        "selection_sources": list(config.get("selection_sources") or []),
        "future_ranking_inputs": list(config.get("future_ranking_inputs") or []),
        "rules": dict(config.get("rules") or {}),
        "categories": [dict(item) for item in list(config.get("categories") or [])],
        "cohorts": [dict(item) for item in list(config.get("cohorts") or [])],
    }

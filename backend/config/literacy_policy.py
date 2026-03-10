from __future__ import annotations

import os
from dataclasses import dataclass

from backend.literacy.messages import (
    DEFAULT_STAGE1_MESSAGE,
    DEFAULT_STAGE2_CLOSE_LIMIT_MESSAGE,
    DEFAULT_STAGE2_OVER_LIMIT_TEMPLATE,
)


@dataclass(frozen=True)
class LiteracyPolicyConfig:
    daily_safe_limit: float = 1200.0
    warning_ratio: float = 0.9
    stage1_message: str = DEFAULT_STAGE1_MESSAGE
    stage2_over_limit_template: str = DEFAULT_STAGE2_OVER_LIMIT_TEMPLATE
    stage2_close_limit_message: str = DEFAULT_STAGE2_CLOSE_LIMIT_MESSAGE
    warmup_days: int = 3
    warmup_seed_multiplier: float = 1.2
    warmup_extreme_spike_ratio: float = 0.4
    catastrophic_absolute: float = 5000.0
    catastrophic_multiplier: float = 2.5
    catastrophic_projected_cap: float = 1.8


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def load_literacy_policy() -> LiteracyPolicyConfig:
    warmup_days_raw = os.getenv("LITERACY_WARMUP_DAYS", "3")
    try:
        warmup_days = max(0, int(warmup_days_raw))
    except ValueError:
        warmup_days = 3

    return LiteracyPolicyConfig(
        daily_safe_limit=_env_float("LITERACY_DAILY_SAFE_LIMIT", 1200.0),
        warning_ratio=_env_float("LITERACY_WARNING_RATIO", 0.9),
        stage1_message=os.getenv(
            "LITERACY_STAGE1_MESSAGE",
            LiteracyPolicyConfig.stage1_message,
        ),
        stage2_over_limit_template=os.getenv(
            "LITERACY_STAGE2_OVER_LIMIT_TEMPLATE",
            LiteracyPolicyConfig.stage2_over_limit_template,
        ),
        stage2_close_limit_message=os.getenv(
            "LITERACY_STAGE2_CLOSE_LIMIT_MESSAGE",
            LiteracyPolicyConfig.stage2_close_limit_message,
        ),
        warmup_days=warmup_days,
        warmup_seed_multiplier=_env_float("LITERACY_WARMUP_SEED_MULTIPLIER", 1.2),
        warmup_extreme_spike_ratio=_env_float("LITERACY_WARMUP_EXTREME_SPIKE_RATIO", 0.4),
        catastrophic_absolute=_env_float("LITERACY_CATASTROPHIC_ABSOLUTE", 5000.0),
        catastrophic_multiplier=_env_float("LITERACY_CATASTROPHIC_MULTIPLIER", 2.5),
        catastrophic_projected_cap=_env_float("LITERACY_CATASTROPHIC_PROJECTED_CAP", 1.8),
    )

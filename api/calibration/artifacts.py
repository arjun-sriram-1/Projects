"""Load optional calibrated artifacts with safe fallbacks."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.calibration.paths import (
    COLLATERAL_STRENGTH_CONFIG,
    DEFAULT_CORRELATION_CONFIG,
    PD_BLEND_CONFIG,
    SCENARIO_MULTIPLIER_CONFIG,
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@lru_cache(maxsize=1)
def pd_blend_config() -> dict[str, Any]:
    return _load_json(PD_BLEND_CONFIG)


@lru_cache(maxsize=1)
def collateral_strength_config() -> dict[str, Any]:
    return _load_json(COLLATERAL_STRENGTH_CONFIG)


@lru_cache(maxsize=1)
def scenario_multiplier_config() -> dict[str, Any]:
    return _load_json(SCENARIO_MULTIPLIER_CONFIG)


@lru_cache(maxsize=1)
def default_correlation_config() -> dict[str, Any]:
    return _load_json(DEFAULT_CORRELATION_CONFIG)


def clear_artifact_caches() -> None:
    pd_blend_config.cache_clear()
    collateral_strength_config.cache_clear()
    scenario_multiplier_config.cache_clear()
    default_correlation_config.cache_clear()


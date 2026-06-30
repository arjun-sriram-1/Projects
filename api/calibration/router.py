"""API routes for calibration transparency and artifact governance."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from api.calibration.paths import (
    ARTIFACT_MANIFEST_JSON,
    REPORT_ROOT,
    VALIDATION_REPORT_JSON,
)
from api.calibration.registry import build_artifact_manifest


router = APIRouter(prefix="/api/v1/calibration", tags=["calibration"])


def _load_json(path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


@router.get("/status")
def calibration_status() -> dict[str, Any]:
    """Return calibration artifact readiness, validation metrics, and summaries."""
    manifest = build_artifact_manifest()
    validation = _load_json(VALIDATION_REPORT_JSON)
    training = _load_json(REPORT_ROOT / "training_summary.json")
    synthetic = _load_json(REPORT_ROOT / "synthetic_trade_history_summary.json")
    return {
        "manifest": manifest,
        "validation": validation,
        "training": training,
        "synthetic_trade_history": synthetic,
        "manifest_path": str(ARTIFACT_MANIFEST_JSON),
        "validation_report_path": str(VALIDATION_REPORT_JSON),
    }

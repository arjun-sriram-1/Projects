"""Runtime registry for optional calibration artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.calibration.paths import (
    ARTIFACT_MANIFEST_JSON,
    COLLATERAL_STRENGTH_CONFIG,
    DEFAULT_CORRELATION_CONFIG,
    EAD_MODEL,
    HISTORICAL_LGD_MODEL,
    HISTORICAL_PD_MODEL,
    PD_BLEND_CONFIG,
    REPORT_ROOT,
    SCENARIO_MULTIPLIER_CONFIG,
    VALIDATION_REPORT_JSON,
    ensure_calibration_dirs,
)


TRAINING_SUMMARY_JSON = REPORT_ROOT / "training_summary.json"
DATASET_BUILD_SUMMARY_JSON = REPORT_ROOT / "dataset_build_summary.json"


ARTIFACTS = {
    "historical_pd_model": {
        "path": HISTORICAL_PD_MODEL,
        "kind": "model",
        "runtime_use": "PD ML cross-check",
        "fallback": "rule_based_logistic_proxy",
    },
    "historical_lgd_model": {
        "path": HISTORICAL_LGD_MODEL,
        "kind": "model",
        "runtime_use": "LGD cross-check",
        "fallback": "rule_based_lgd_engine",
    },
    "calibrated_ead_model": {
        "path": EAD_MODEL,
        "kind": "model",
        "runtime_use": "EAD estimate",
        "fallback": "limit_or_invoice_based_ead",
    },
    "pd_blend_config": {
        "path": PD_BLEND_CONFIG,
        "kind": "config",
        "runtime_use": "structural/ML PD blend weights",
        "fallback": "0.65_structural_0.35_ml",
    },
    "collateral_strength_config": {
        "path": COLLATERAL_STRENGTH_CONFIG,
        "kind": "config",
        "runtime_use": "collateral recovery strength",
        "fallback": "policy_heuristic_collateral_scores",
    },
    "scenario_multiplier_config": {
        "path": SCENARIO_MULTIPLIER_CONFIG,
        "kind": "config",
        "runtime_use": "Monte Carlo stress multipliers",
        "fallback": "default_stress_coefficients",
    },
    "default_correlation_config": {
        "path": DEFAULT_CORRELATION_CONFIG,
        "kind": "config",
        "runtime_use": "Monte Carlo default correlation",
        "fallback": "default_correlation_formula",
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_status(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    path = spec["path"]
    exists = path.exists()
    stat = path.stat() if exists else None
    payload = _load_json(path) if exists and path.suffix.lower() == ".json" else {}
    return {
        "name": name,
        "kind": spec["kind"],
        "path": str(path),
        "exists": exists,
        "active": exists,
        "fallback_if_missing": spec["fallback"],
        "runtime_use": spec["runtime_use"],
        "size_bytes": int(stat.st_size) if stat else 0,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat() if stat else None,
        "sha256": _sha256(path) if exists else None,
        "calibration_method": payload.get("calibration_method"),
    }


def build_artifact_manifest() -> dict[str, Any]:
    ensure_calibration_dirs()
    training_summary = _load_json(TRAINING_SUMMARY_JSON)
    validation_report = _load_json(VALIDATION_REPORT_JSON)
    dataset_summary = _load_json(DATASET_BUILD_SUMMARY_JSON)
    artifacts = [_artifact_status(name, spec) for name, spec in ARTIFACTS.items()]
    active_models = [item["name"] for item in artifacts if item["exists"] and item["kind"] == "model"]
    missing_models = [item["name"] for item in artifacts if not item["exists"] and item["kind"] == "model"]
    lgd_ready = any(item["name"] == "historical_lgd_model" and item["exists"] for item in artifacts)
    ead_ready = any(item["name"] == "calibrated_ead_model" and item["exists"] for item in artifacts)
    manifest = {
        "phase": "phase_5_runtime_artifact_registry",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts,
        "active_models": active_models,
        "missing_models_using_fallbacks": missing_models,
        "dataset_summary": dataset_summary,
        "training_summary_path": str(TRAINING_SUMMARY_JSON),
        "validation_report_path": str(VALIDATION_REPORT_JSON),
        "pd_validation_metrics": validation_report.get("pd", {}).get("metrics", {}),
        "readiness": {
            "pd_calibration_ready": any(item["name"] == "historical_pd_model" and item["exists"] for item in artifacts),
            "lgd_calibration_ready": lgd_ready,
            "ead_calibration_ready": ead_ready,
            "runtime_safe": True,
            "reason": "Missing optional artifacts use existing fallback logic.",
        },
        "notes": [
            "The manifest is an audit layer; it does not mutate live model behavior.",
            "PD is calibrated from free-source financial and market data when the PD artifact exists.",
            (
                "LGD/EAD artifacts are active; check data_source fields to distinguish synthetic/proxy rows from real internal observations."
                if lgd_ready or ead_ready
                else "LGD/EAD remain fallback-driven until realized recovery and exposure-at-default rows are supplied."
            ),
        ],
        "training_summary": training_summary,
    }
    ARTIFACT_MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create runtime manifest for calibration artifacts.")
    parser.parse_args()
    print(json.dumps(build_artifact_manifest(), indent=2))


if __name__ == "__main__":
    main()

"""Validation reports for free-source calibration artifacts."""

from __future__ import annotations

import argparse
import json
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, mean_squared_error, roc_auc_score

from api.calibration.paths import (
    EAD_MODEL,
    EAD_TRAINING_CSV,
    HISTORICAL_LGD_MODEL,
    HISTORICAL_PD_MODEL,
    LGD_TRAINING_CSV,
    PD_TRAINING_CSV,
    VALIDATION_REPORT_JSON,
    ensure_calibration_dirs,
)


def _read(path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path).dropna(how="all")


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or not np.isfinite(float(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _classification_metrics(y_true: pd.Series, probabilities: pd.Series) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "rows": int(len(y_true)),
        "default_rate": _safe_float(y_true.mean()),
        "mean_predicted_pd": _safe_float(probabilities.mean()),
        "brier_score": _safe_float(brier_score_loss(y_true, probabilities)),
    }
    try:
        metrics["auc"] = _safe_float(roc_auc_score(y_true, probabilities))
    except ValueError:
        metrics["auc"] = None
    try:
        metrics["log_loss"] = _safe_float(log_loss(y_true, probabilities, labels=[0, 1]))
    except ValueError:
        metrics["log_loss"] = None
    return metrics


def _calibration_bins(y_true: pd.Series, probabilities: pd.Series, bins: int = 10) -> list[dict[str, Any]]:
    working = pd.DataFrame({"actual": y_true, "predicted": probabilities}).dropna()
    if working.empty:
        return []
    working["bucket"] = pd.qcut(working["predicted"], q=min(bins, working["predicted"].nunique()), duplicates="drop")
    grouped = working.groupby("bucket", observed=False)
    result = []
    for bucket, group in grouped:
        result.append(
            {
                "bucket": str(bucket),
                "rows": int(len(group)),
                "mean_predicted_pd": _safe_float(group["predicted"].mean()),
                "observed_default_rate": _safe_float(group["actual"].mean()),
                "absolute_gap": _safe_float(abs(group["predicted"].mean() - group["actual"].mean())),
            }
        )
    return result


def _temporal_pd_metrics(frame: pd.DataFrame, probabilities: pd.Series) -> list[dict[str, Any]]:
    if "period_end_date" not in frame:
        return []
    working = pd.DataFrame(
        {
            "period_end_date": pd.to_datetime(frame["period_end_date"], errors="coerce"),
            "actual": pd.to_numeric(frame["default_label"], errors="coerce"),
            "predicted": probabilities,
        }
    ).dropna()
    if working.empty:
        return []
    working["year"] = working["period_end_date"].dt.year
    result = []
    for year, group in working.groupby("year"):
        if len(group) < 20 or group["actual"].nunique() < 2:
            result.append(
                {
                    "year": int(year),
                    "rows": int(len(group)),
                    "default_rate": _safe_float(group["actual"].mean()),
                    "mean_predicted_pd": _safe_float(group["predicted"].mean()),
                    "auc": None,
                    "brier_score": _safe_float(brier_score_loss(group["actual"], group["predicted"])),
                    "note": "AUC skipped because too few rows or one label class.",
                }
            )
            continue
        metrics = _classification_metrics(group["actual"], group["predicted"])
        metrics["year"] = int(year)
        result.append(metrics)
    return result


def validate_pd_artifact() -> dict[str, Any]:
    frame = _read(PD_TRAINING_CSV)
    if frame.empty or "default_label" not in frame:
        return {"available": False, "reason": "pd_training_dataset_missing"}
    if not HISTORICAL_PD_MODEL.exists():
        return {"available": False, "reason": "historical_pd_model_missing", "rows": int(len(frame))}

    artifact = joblib.load(HISTORICAL_PD_MODEL)
    model = artifact["model"] if isinstance(artifact, dict) else artifact
    features = artifact.get("feature_columns", []) if isinstance(artifact, dict) else []
    if not features:
        return {"available": False, "reason": "pd_artifact_feature_columns_missing", "rows": int(len(frame))}

    for feature in features:
        if feature not in frame.columns:
            frame[feature] = np.nan
    X = frame[features].apply(pd.to_numeric, errors="coerce")
    y = pd.to_numeric(frame["default_label"], errors="coerce")
    valid = y.notna()
    X = X.loc[valid]
    y = y.loc[valid].astype(int)
    probabilities = pd.Series(model.predict_proba(X)[:, 1], index=X.index).clip(0.0001, 0.9999)

    feature_coverage = {
        feature: _safe_float(1 - X[feature].isna().mean())
        for feature in features
    }
    report = {
        "available": True,
        "validation_scope": "in_sample_proxy_label_validation",
        "artifact": str(HISTORICAL_PD_MODEL),
        "rows": int(len(y)),
        "features": features,
        "feature_coverage": feature_coverage,
        "label_balance": {
            "non_default_rows": int((y == 0).sum()),
            "default_rows": int((y == 1).sum()),
            "default_rate": _safe_float(y.mean()),
            "label_source": str(frame.get("default_type", pd.Series(["unknown"])).dropna().mode().iloc[0])
            if "default_type" in frame and not frame["default_type"].dropna().empty
            else "unknown",
        },
        "metrics": _classification_metrics(y, probabilities),
        "calibration_bins": _calibration_bins(y, probabilities),
        "temporal_metrics": _temporal_pd_metrics(frame.loc[valid].copy(), probabilities),
        "limitations": [
            "This report validates against free-source or proxy labels, not confidential bank default history.",
            "In-sample metrics are useful for sanity checks but should not be presented as final production backtests.",
        ],
    }
    return report


def validate_lgd_artifact() -> dict[str, Any]:
    frame = _read(LGD_TRAINING_CSV)
    if frame.empty:
        return {"available": False, "reason": "lgd_training_dataset_missing"}
    if "lgd" not in frame:
        return {"available": False, "reason": "lgd_column_missing", "rows": int(len(frame))}
    if not HISTORICAL_LGD_MODEL.exists():
        return {"available": False, "reason": "historical_lgd_model_missing", "rows": int(len(frame))}

    artifact = joblib.load(HISTORICAL_LGD_MODEL)
    model = artifact["model"] if isinstance(artifact, dict) else artifact
    features = artifact.get("feature_columns", []) if isinstance(artifact, dict) else []
    if not features:
        return {"available": False, "reason": "lgd_artifact_feature_columns_missing", "rows": int(len(frame))}

    for feature in features:
        if feature not in frame.columns:
            frame[feature] = np.nan
    X = frame[features].apply(pd.to_numeric, errors="coerce")
    y = pd.to_numeric(frame["lgd"], errors="coerce").clip(0.01, 0.99)
    valid = y.notna()
    X = X.loc[valid]
    y = y.loc[valid]
    predictions = pd.Series(model.predict(X), index=X.index).clip(0.01, 0.99)
    report = {
        "available": True,
        "validation_scope": "in_sample_synthetic_or_proxy_recovery_validation",
        "artifact": str(HISTORICAL_LGD_MODEL),
        "rows": int(len(y)),
        "features": features,
        "metrics": {
            "mae": _safe_float(mean_absolute_error(y, predictions)),
            "rmse": _safe_float(mean_squared_error(y, predictions) ** 0.5),
            "mean_actual_lgd": _safe_float(y.mean()),
            "mean_predicted_lgd": _safe_float(predictions.mean()),
        },
        "limitations": [
            "Synthetic or proxy recovery rows improve model wiring but should be replaced by real realized recovery history.",
        ],
    }
    if "collateral_type" in frame:
        working = frame.loc[valid, ["collateral_type"]].copy()
        working["actual_lgd"] = y
        working["predicted_lgd"] = predictions
        report["lgd_by_collateral"] = (
            working.groupby("collateral_type")[["actual_lgd", "predicted_lgd"]].mean().round(4).to_dict("index")
        )
    return report


def validate_ead_artifact() -> dict[str, Any]:
    frame = _read(EAD_TRAINING_CSV)
    if frame.empty:
        return {"available": False, "reason": "ead_training_dataset_missing"}
    if "realized_ead" not in frame:
        return {"available": False, "reason": "realized_ead_column_missing", "rows": int(len(frame))}
    if not EAD_MODEL.exists():
        return {"available": False, "reason": "calibrated_ead_model_missing", "rows": int(len(frame))}

    artifact = joblib.load(EAD_MODEL)
    model = artifact["model"] if isinstance(artifact, dict) else artifact
    features = artifact.get("feature_columns", []) if isinstance(artifact, dict) else []
    if not features:
        return {"available": False, "reason": "ead_artifact_feature_columns_missing", "rows": int(len(frame))}

    for feature in features:
        if feature not in frame.columns:
            frame[feature] = np.nan
    X = frame[features].apply(pd.to_numeric, errors="coerce")
    y = pd.to_numeric(frame["realized_ead"], errors="coerce").clip(lower=0)
    valid = y.notna()
    X = X.loc[valid]
    y = y.loc[valid]
    predictions = pd.Series(model.predict(X), index=X.index).clip(lower=0)
    absolute_error = (predictions - y).abs()
    return {
        "available": True,
        "validation_scope": "in_sample_synthetic_or_proxy_ead_validation",
        "rows": int(len(y)),
        "artifact": str(EAD_MODEL),
        "features": features,
        "metrics": {
            "mae": _safe_float(mean_absolute_error(y, predictions)),
            "rmse": _safe_float(mean_squared_error(y, predictions) ** 0.5),
            "mean_actual_ead": _safe_float(y.mean()),
            "mean_predicted_ead": _safe_float(predictions.mean()),
            "median_absolute_error": _safe_float(absolute_error.median()),
        },
        "limitations": [
            "Synthetic or proxy EAD rows improve model wiring but should be replaced by real utilization/default exposure history.",
        ],
    }


def build_validation_report() -> dict[str, Any]:
    ensure_calibration_dirs()
    report = {
        "phase": "phase_4_model_validation",
        "pd": validate_pd_artifact(),
        "lgd": validate_lgd_artifact(),
        "ead": validate_ead_artifact(),
    }
    VALIDATION_REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate free-source calibration model artifacts.")
    parser.parse_args()
    print(json.dumps(build_validation_report(), indent=2))


if __name__ == "__main__":
    main()

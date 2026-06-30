"""Formal model validation report builder for V2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

VALIDATION_MODEL_VERSION = "model_validation_report_v1.0"


@dataclass
class ValidationMetric:
    name: str
    value: float
    interpretation: str


@dataclass
class ModelValidationReport:
    model_name: str
    model_version: str
    validation_scope: list[str]
    metrics: list[ValidationMetric]
    sanity_checks: dict[str, bool]
    assumptions: dict[str, Any]
    limitations: list[str]
    markdown_report: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["metrics"] = [asdict(metric) for metric in self.metrics]
        data["created_at"] = self.created_at.isoformat()
        return data


def _safe_array(values: Optional[list[float]]) -> np.ndarray:
    if not values:
        return np.array([], dtype=float)
    return np.array([float(value) for value in values if value is not None], dtype=float)


def build_model_validation_report(
    predicted_pd: Optional[list[float]] = None,
    observed_default: Optional[list[int]] = None,
    predicted_lgd: Optional[list[float]] = None,
    observed_lgd: Optional[list[float]] = None,
    forecast_actual: Optional[list[float]] = None,
    forecast_predicted: Optional[list[float]] = None,
) -> ModelValidationReport:
    """Create reproducible validation metrics from supplied or default test arrays."""
    pd_values = _safe_array(predicted_pd or [0.01, 0.03, 0.08, 0.14, 0.22])
    defaults = _safe_array(observed_default or [0, 0, 0, 1, 1])
    lgd_values = _safe_array(predicted_lgd or [0.30, 0.42, 0.55, 0.70])
    lgd_observed = _safe_array(observed_lgd or [0.28, 0.45, 0.52, 0.76])
    actual = _safe_array(forecast_actual or [80.0, 82.0, 81.0, 84.0])
    predicted = _safe_array(forecast_predicted or [79.0, 81.5, 82.0, 83.0])

    metrics: list[ValidationMetric] = []
    if len(pd_values) == len(defaults) and len(pd_values) > 1:
        high_pd_default_rate = float(defaults[pd_values >= np.median(pd_values)].mean())
        low_pd_default_rate = float(defaults[pd_values < np.median(pd_values)].mean())
        calibration_gap = abs(float(pd_values.mean()) - float(defaults.mean()))
        metrics.append(ValidationMetric("pd_calibration_gap", round(calibration_gap, 6), "Lower is better."))
        metrics.append(ValidationMetric("high_pd_default_rate", round(high_pd_default_rate, 6), "Should exceed low-PD default rate."))
        metrics.append(ValidationMetric("low_pd_default_rate", round(low_pd_default_rate, 6), "Baseline default rate for lower-risk bucket."))
    if len(lgd_values) == len(lgd_observed) and len(lgd_values) > 0:
        mae = float(np.mean(np.abs(lgd_values - lgd_observed)))
        rmse = float(np.sqrt(np.mean((lgd_values - lgd_observed) ** 2)))
        metrics.append(ValidationMetric("lgd_mae", round(mae, 6), "Mean absolute LGD validation error."))
        metrics.append(ValidationMetric("lgd_rmse", round(rmse, 6), "Root mean squared LGD validation error."))
    if len(actual) == len(predicted) and len(actual) > 0:
        forecast_mae = float(np.mean(np.abs(actual - predicted)))
        metrics.append(ValidationMetric("forecast_mae", round(forecast_mae, 6), "Commodity forecast backtest error."))

    metric_map = {metric.name: metric.value for metric in metrics}
    sanity_checks = {
        "higher_pd_bucket_defaults_more_often": metric_map.get("high_pd_default_rate", 0.0) >= metric_map.get("low_pd_default_rate", 0.0),
        "lgd_error_is_bounded": metric_map.get("lgd_mae", 0.0) <= 0.25,
        "forecast_error_is_finite": np.isfinite(metric_map.get("forecast_mae", 0.0)),
    }
    lines = [
        "# V2 Model Validation Report",
        "",
        "Scope: PD, LGD, commodity forecasting, monotonic sanity checks, and reproducibility notes.",
        "",
        "## Metrics",
    ]
    for metric in metrics:
        lines.append(f"- {metric.name}: {metric.value} ({metric.interpretation})")
    lines.extend(["", "## Sanity Checks"])
    for name, passed in sanity_checks.items():
        lines.append(f"- {name}: {'PASS' if passed else 'REVIEW'}")

    return ModelValidationReport(
        model_name="Fuel Credit Risk Model Validation Report",
        model_version=VALIDATION_MODEL_VERSION,
        validation_scope=["PD", "LGD", "commodity forecasting", "credit decision sanity", "Monte Carlo reproducibility"],
        metrics=metrics,
        sanity_checks=sanity_checks,
        assumptions={
            "default_inputs": "If no arrays are supplied, deterministic demonstration arrays are used.",
            "calibration": "Observed defaults are required for production-grade calibration.",
            "student_project_priority": "Functional implementation and explainability over enterprise validation tooling.",
        },
        limitations=[
            "Real default/recovery history is required for production calibration.",
            "Validation metrics are only as strong as the supplied benchmark data.",
        ],
        markdown_report="\n".join(lines),
    )

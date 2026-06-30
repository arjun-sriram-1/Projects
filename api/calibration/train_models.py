"""Train calibrated model artifacts from processed free-source datasets."""

from __future__ import annotations

import argparse
import json
from math import erf
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, mean_absolute_error, mean_squared_error, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from api.market_data.assets import PD_MARKET_FEATURES
from api.calibration.paths import (
    COLLATERAL_STRENGTH_CONFIG,
    DEFAULT_CORRELATION_CONFIG,
    EAD_MODEL,
    EAD_TRAINING_CSV,
    HISTORICAL_LGD_MODEL,
    HISTORICAL_PD_MODEL,
    LGD_TRAINING_CSV,
    MARKET_CONTEXT_CSV,
    PD_BLEND_CONFIG,
    PD_TRAINING_CSV,
    REPORT_ROOT,
    SCENARIO_MULTIPLIER_CONFIG,
    ensure_calibration_dirs,
)


PD_FEATURES = [
    "current_ratio",
    "quick_ratio",
    "cash_ratio",
    "working_capital",
    "debt_to_equity",
    "debt_to_ebitda",
    "liabilities_to_assets",
    "interest_coverage",
    "operating_margin",
    "net_margin",
    "return_on_assets",
    "return_on_equity",
] + PD_MARKET_FEATURES

LGD_FEATURES = [
    "exposure_at_default",
    "approved_credit_limit",
    "requested_credit_limit",
    "payment_tenor_days",
    "deposit_percentage",
    "country_risk_score",
    "days_to_recovery",
    "legal_cost",
    "letter_of_credit_flag",
    "guarantee_flag",
]

EAD_FEATURES = [
    "invoice_amount",
    "invoice_exposure",
    "fuel_volume",
    "fuel_price",
    "approved_credit_limit",
    "requested_credit_limit",
    "outstanding_receivables",
    "payment_tenor_days",
    "utilization_rate",
    "deposit_percentage",
    "days_past_due",
]


def _read(path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).dropna(how="all")


def _available(frame: pd.DataFrame, features: list[str]) -> list[str]:
    return [feature for feature in features if feature in frame.columns]


def _classification_metrics(y_true, probabilities) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "brier_score": float(brier_score_loss(y_true, probabilities)),
    }
    try:
        metrics["auc"] = float(roc_auc_score(y_true, probabilities))
    except ValueError:
        metrics["auc"] = None
    try:
        metrics["log_loss"] = float(log_loss(y_true, probabilities, labels=[0, 1]))
    except ValueError:
        metrics["log_loss"] = None
    return metrics


def _clip_probability(values) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), 0.0001, 0.9999)


def _derived_structural_pd(frame: pd.DataFrame) -> pd.Series:
    assets = pd.to_numeric(frame.get("total_assets"), errors="coerce")
    revenue = pd.to_numeric(frame.get("revenue"), errors="coerce")
    liabilities = pd.to_numeric(frame.get("total_liabilities"), errors="coerce")
    debt = pd.to_numeric(frame.get("total_debt"), errors="coerce")
    current_ratio = pd.to_numeric(frame.get("current_ratio"), errors="coerce").fillna(1.0)
    debt_to_equity = pd.to_numeric(frame.get("debt_to_equity"), errors="coerce").fillna(1.5)
    stress = pd.to_numeric(frame.get("stress_index"), errors="coerce").fillna(50.0).clip(0, 100) / 100
    risk_free = pd.to_numeric(frame.get("us_10y_yield"), errors="coerce").fillna(4.0)
    risk_free = np.where(risk_free > 1, risk_free / 100, risk_free)

    asset_value = assets.where(assets > 0, revenue * 1.5).fillna(1.0).clip(lower=1.0)
    debt_threshold = debt.where(debt > 0, liabilities * 0.60).fillna(1.0).clip(lower=1.0)
    leverage = debt_to_equity.where(debt_to_equity > 0, 8.0).clip(0, 8)
    liquidity_penalty = (1 - current_ratio.clip(0, 2) / 2).clip(lower=0)
    volatility = (0.18 + 0.08 * leverage.clip(upper=5) + 0.12 * stress + 0.05 * liquidity_penalty).clip(0.08, 0.95)

    numerator = np.log(asset_value / debt_threshold) + (risk_free - 0.5 * volatility**2)
    denominator = volatility
    distance_to_default = numerator / denominator
    pd_values = 1 - pd.Series(distance_to_default).map(lambda value: float(0.5 * (1 + erf(value / np.sqrt(2)))))
    return pd.Series(_clip_probability(pd_values), index=frame.index)


def _derived_rule_ml_pd(frame: pd.DataFrame) -> pd.Series:
    debt_to_ebitda = pd.to_numeric(frame.get("debt_to_ebitda"), errors="coerce").fillna(4.0).clip(upper=10)
    debt_to_equity = pd.to_numeric(frame.get("debt_to_equity"), errors="coerce").fillna(1.5)
    debt_to_equity = debt_to_equity.where(debt_to_equity > 0, 8.0).clip(upper=8)
    current_ratio = pd.to_numeric(frame.get("current_ratio"), errors="coerce").fillna(1.0)
    cash_ratio = pd.to_numeric(frame.get("cash_ratio"), errors="coerce").fillna(0.4)
    interest_coverage = pd.to_numeric(frame.get("interest_coverage"), errors="coerce").fillna(3.0)
    net_margin = pd.to_numeric(frame.get("net_margin"), errors="coerce").fillna(0.03)
    stress = pd.to_numeric(frame.get("stress_index"), errors="coerce").fillna(50.0).clip(0, 100) / 100
    logit = (
        -3.40
        + 0.20 * debt_to_ebitda
        + 0.15 * debt_to_equity
        + 0.70 * (1.20 - current_ratio).clip(lower=0)
        + 0.35 * (0.50 - cash_ratio).clip(lower=0)
        + 0.25 * (3.0 - interest_coverage).clip(lower=0)
        + 2.00 * (-net_margin).clip(lower=0)
        + 1.25 * stress
        + 0.55 * 0.50
        + 0.35 * 0.45
        + 0.45 * (0.35 + 0.30 * stress)
    )
    logit = logit.clip(-30, 30)
    return pd.Series(_clip_probability(1 / (1 + np.exp(-logit))), index=frame.index)


def _derived_historical_ml_pd(frame: pd.DataFrame) -> pd.Series | None:
    if not HISTORICAL_PD_MODEL.exists():
        return None
    try:
        artifact = joblib.load(HISTORICAL_PD_MODEL)
        model = artifact["model"] if isinstance(artifact, dict) else artifact
        features = artifact.get("feature_columns", []) if isinstance(artifact, dict) else []
        if not features:
            return None
        working = frame.copy()
        for feature in features:
            if feature not in working.columns:
                working[feature] = np.nan
        X = working[features].apply(pd.to_numeric, errors="coerce")
        return pd.Series(_clip_probability(model.predict_proba(X)[:, 1]), index=frame.index)
    except Exception:
        return None


def train_pd_model(min_rows: int = 30) -> dict[str, Any]:
    frame = _read(PD_TRAINING_CSV)
    if frame.empty or "default_label" not in frame:
        return {"trained": False, "reason": "pd_training_dataset_missing"}
    frame["default_label"] = pd.to_numeric(frame["default_label"], errors="coerce")
    frame = frame.dropna(subset=["default_label"])
    if len(frame) < min_rows or frame["default_label"].nunique() < 2:
        return {"trained": False, "reason": "not_enough_pd_rows_or_classes", "rows": int(len(frame))}

    features = _available(frame, PD_FEATURES)
    X = frame[features].apply(pd.to_numeric, errors="coerce")
    y = frame["default_label"].astype(int)
    stratify = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=stratify)
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, 1]
    metrics = _classification_metrics(y_test, probabilities)
    artifact = {
        "model": model,
        "feature_columns": features,
        "model_type": "pd_classifier",
        "training_rows": int(len(frame)),
        "metrics": metrics,
        "data_source": "free_source_calibration",
    }
    joblib.dump(artifact, HISTORICAL_PD_MODEL)
    return {"trained": True, "rows": int(len(frame)), "features": features, "metrics": metrics, "artifact": str(HISTORICAL_PD_MODEL)}


def train_lgd_model(min_rows: int = 20) -> dict[str, Any]:
    frame = _read(LGD_TRAINING_CSV)
    if frame.empty or "lgd" not in frame:
        return {"trained": False, "reason": "lgd_training_dataset_missing"}
    frame["lgd"] = pd.to_numeric(frame["lgd"], errors="coerce").clip(0.01, 0.99)
    frame = frame.dropna(subset=["lgd"])
    if len(frame) < min_rows:
        return {"trained": False, "reason": "not_enough_lgd_rows", "rows": int(len(frame))}
    features = _available(frame, LGD_FEATURES)
    X = frame[features].apply(pd.to_numeric, errors="coerce")
    y = frame["lgd"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(n_estimators=200, min_samples_leaf=3, random_state=42)),
        ]
    )
    model.fit(X_train, y_train)
    preds = np.clip(model.predict(X_test), 0.01, 0.99)
    metrics = {
        "mae": float(mean_absolute_error(y_test, preds)),
        "rmse": float(mean_squared_error(y_test, preds) ** 0.5),
    }
    artifact = {
        "model": model,
        "feature_columns": features,
        "model_type": "lgd_regressor",
        "training_rows": int(len(frame)),
        "metrics": metrics,
        "data_source": "free_source_calibration",
    }
    joblib.dump(artifact, HISTORICAL_LGD_MODEL)
    return {"trained": True, "rows": int(len(frame)), "features": features, "metrics": metrics, "artifact": str(HISTORICAL_LGD_MODEL)}


def train_ead_model(min_rows: int = 20) -> dict[str, Any]:
    frame = _read(EAD_TRAINING_CSV)
    if frame.empty or "realized_ead" not in frame:
        return {"trained": False, "reason": "ead_training_dataset_missing"}
    frame["realized_ead"] = pd.to_numeric(frame["realized_ead"], errors="coerce")
    frame = frame.dropna(subset=["realized_ead"])
    if len(frame) < min_rows:
        return {"trained": False, "reason": "not_enough_ead_rows", "rows": int(len(frame))}
    features = _available(frame, EAD_FEATURES)
    X = frame[features].apply(pd.to_numeric, errors="coerce")
    y = frame["realized_ead"].clip(lower=0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingRegressor(random_state=42)),
        ]
    )
    model.fit(X_train, y_train)
    preds = np.maximum(model.predict(X_test), 0)
    metrics = {
        "mae": float(mean_absolute_error(y_test, preds)),
        "rmse": float(mean_squared_error(y_test, preds) ** 0.5),
    }
    artifact = {
        "model": model,
        "feature_columns": features,
        "model_type": "ead_regressor",
        "training_rows": int(len(frame)),
        "metrics": metrics,
        "data_source": "free_source_calibration",
    }
    joblib.dump(artifact, EAD_MODEL)
    return {"trained": True, "rows": int(len(frame)), "features": features, "metrics": metrics, "artifact": str(EAD_MODEL)}


def build_collateral_config() -> dict[str, Any]:
    frame = _read(LGD_TRAINING_CSV)
    if frame.empty or "collateral_type" not in frame:
        return {"created": False, "reason": "lgd_training_dataset_missing"}
    if "recovery_rate" not in frame:
        if "lgd" in frame:
            frame["recovery_rate"] = 1 - pd.to_numeric(frame["lgd"], errors="coerce")
        else:
            return {"created": False, "reason": "recovery_or_lgd_missing"}
    grouped = frame.dropna(subset=["collateral_type", "recovery_rate"]).groupby("collateral_type")["recovery_rate"].mean()
    if grouped.empty:
        return {"created": False, "reason": "no_collateral_recovery_rows"}
    config = {str(key).strip().lower(): float(np.clip(value, 0.0, 1.0)) for key, value in grouped.items()}
    COLLATERAL_STRENGTH_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return {"created": True, "config": config, "artifact": str(COLLATERAL_STRENGTH_CONFIG)}


def build_pd_blend_config() -> dict[str, Any]:
    frame = _read(PD_TRAINING_CSV)
    config = {
        "structural_weight": 0.65,
        "ml_weight": 0.35,
        "calibration_method": "default_until_structural_backtest_available",
    }
    if frame.empty or "default_label" not in frame:
        PD_BLEND_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return {"created": True, "config": config, "artifact": str(PD_BLEND_CONFIG)}

    y = pd.to_numeric(frame["default_label"], errors="coerce")
    if y.nunique() < 2:
        PD_BLEND_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return {"created": True, "config": config, "artifact": str(PD_BLEND_CONFIG)}

    if {"structural_pd", "ml_pd"}.issubset(frame.columns):
        structural = pd.to_numeric(frame["structural_pd"], errors="coerce")
        ml = pd.to_numeric(frame["ml_pd"], errors="coerce")
        method = "grid_search_min_brier_explicit_backtest_columns"
    else:
        structural = _derived_structural_pd(frame)
        trained_ml = _derived_historical_ml_pd(frame)
        rule_ml = _derived_rule_ml_pd(frame)
        ml = 0.50 * rule_ml + 0.50 * trained_ml if trained_ml is not None else rule_ml
        method = "grid_search_min_brier_derived_structural_and_ml_pd"

    working = pd.DataFrame({"y": y, "structural": structural, "ml": ml}).dropna()
    if len(working) < 30 or working["y"].nunique() < 2:
        PD_BLEND_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return {"created": True, "config": config, "artifact": str(PD_BLEND_CONFIG)}

    best = None
    for structural_weight in np.linspace(0, 1, 41):
        score = structural_weight * working["structural"] + (1 - structural_weight) * working["ml"]
        brier = brier_score_loss(working["y"], np.clip(score, 0.0001, 0.9999))
        if best is None or brier < best["brier_score"]:
            best = {
                "structural_weight": float(structural_weight),
                "ml_weight": float(1 - structural_weight),
                "brier_score": float(brier),
            }
    if best:
        structural_brier = brier_score_loss(working["y"], np.clip(working["structural"], 0.0001, 0.9999))
        ml_brier = brier_score_loss(working["y"], np.clip(working["ml"], 0.0001, 0.9999))
        config = {
            **best,
            "structural_only_brier_score": float(structural_brier),
            "ml_only_brier_score": float(ml_brier),
            "rows": int(len(working)),
            "calibration_method": method,
            "label_source_note": "Uses current PD training labels, which may include free-source proxy distress labels.",
        }
    PD_BLEND_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return {"created": True, "config": config, "artifact": str(PD_BLEND_CONFIG)}


def _merge_by_nearest_market_date(frame: pd.DataFrame, date_column: str) -> pd.DataFrame:
    market = _read(MARKET_CONTEXT_CSV)
    if frame.empty or market.empty or date_column not in frame or "date" not in market:
        return frame.copy()
    left = frame.copy()
    right = market.copy()
    left[date_column] = pd.to_datetime(left[date_column], errors="coerce")
    right["date"] = pd.to_datetime(right["date"], errors="coerce")
    left = left.dropna(subset=[date_column]).sort_values(date_column)
    right = right.dropna(subset=["date"]).sort_values("date")
    if left.empty or right.empty:
        return frame.copy()
    return pd.merge_asof(left, right, left_on=date_column, right_on="date", direction="backward")


def _stress_series(frame: pd.DataFrame) -> pd.Series:
    if "stress_index" in frame:
        stress = pd.to_numeric(frame["stress_index"], errors="coerce")
        if stress.notna().any():
            return stress.clip(0, 100) / 100
    pieces = []
    for column in ["vix", "crude_oil", "brent_oil"]:
        if column in frame:
            values = pd.to_numeric(frame[column], errors="coerce")
            if values.notna().any():
                pieces.append((values.rank(pct=True) - 0.5).abs() * 2)
    if pieces:
        return pd.concat(pieces, axis=1).mean(axis=1).clip(0, 1)
    return pd.Series(0.5, index=frame.index)


def _safe_ratio_value(numerator: float, denominator: float, default: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return default
    return float(numerator / denominator)


def build_scenario_and_correlation_configs() -> dict[str, Any]:
    pd_frame = _read(PD_TRAINING_CSV)
    lgd_frame = _read(LGD_TRAINING_CSV)
    ead_frame = _read(EAD_TRAINING_CSV)

    scenario_config = {
        "pd_stress_coefficient": 0.18,
        "lgd_stress_coefficient": 0.035,
        "ead_commodity_coefficient": 0.035,
        "ead_commodity_cap": 0.30,
        "calibration_method": "default_until_stress_backtest_available",
    }
    correlation_config = {
        "base_correlation": 0.06,
        "stress_coefficient": 0.18,
        "vix_stress_coefficient": 0.025,
        "min_correlation": 0.03,
        "max_correlation": 0.55,
        "calibration_method": "default_until_default_clustering_available",
    }

    calibration_notes: list[str] = []
    if not pd_frame.empty and "default_label" in pd_frame:
        pd_working = pd_frame.copy()
        pd_working["default_label"] = pd.to_numeric(pd_working["default_label"], errors="coerce")
        pd_working = pd_working.dropna(subset=["default_label"])
        stress = _stress_series(pd_working)
        if len(pd_working) >= 100 and stress.notna().any() and pd_working["default_label"].nunique() >= 2:
            high_stress = stress >= stress.quantile(0.75)
            low_stress = stress <= stress.quantile(0.25)
            high_default_rate = float(pd_working.loc[high_stress, "default_label"].mean())
            low_default_rate = float(pd_working.loc[low_stress, "default_label"].mean())
            if np.isfinite(high_default_rate) and np.isfinite(low_default_rate):
                log_ratio = np.log((high_default_rate + 0.01) / (low_default_rate + 0.01))
                scenario_config["pd_stress_coefficient"] = float(np.clip(log_ratio / 2.0, 0.03, 0.45))
                calibration_notes.append("pd_stress_coefficient calibrated from high/low market-stress default-label rates")

            if "period_end_date" in pd_working:
                temporal = pd_working.copy()
                temporal["year"] = pd.to_datetime(temporal["period_end_date"], errors="coerce").dt.year
                grouped = temporal.dropna(subset=["year"]).groupby("year").agg(
                    default_rate=("default_label", "mean"),
                    rows=("default_label", "size"),
                    stress_index=("stress_index", "mean") if "stress_index" in temporal else ("default_label", "mean"),
                    vix=("vix", "mean") if "vix" in temporal else ("default_label", "mean"),
                )
                grouped = grouped[grouped["rows"] >= 20]
                if len(grouped) >= 3:
                    mean_p = float(pd_working["default_label"].mean())
                    avg_n = float(grouped["rows"].mean())
                    observed_variance = float(grouped["default_rate"].var(ddof=0))
                    idiosyncratic_variance = mean_p * (1 - mean_p) / max(avg_n, 1.0)
                    systematic_variance = max(0.0, observed_variance - idiosyncratic_variance)
                    base_corr = _safe_ratio_value(systematic_variance, mean_p * (1 - mean_p), 0.06)
                    correlation_config["base_correlation"] = float(np.clip(base_corr, 0.03, 0.18))

                    stress_values = pd.to_numeric(grouped["stress_index"], errors="coerce")
                    if stress_values.notna().any():
                        high = grouped[stress_values >= stress_values.quantile(0.75)]["default_rate"].mean()
                        low = grouped[stress_values <= stress_values.quantile(0.25)]["default_rate"].mean()
                        stress_slope = _safe_ratio_value(float(high - low), max(mean_p, 0.01), 0.18)
                        correlation_config["stress_coefficient"] = float(np.clip(stress_slope, 0.03, 0.35))
                    vix_values = pd.to_numeric(grouped["vix"], errors="coerce")
                    if vix_values.notna().any():
                        high = grouped[vix_values >= vix_values.quantile(0.75)]["default_rate"].mean()
                        low = grouped[vix_values <= vix_values.quantile(0.25)]["default_rate"].mean()
                        vix_slope = _safe_ratio_value(float(high - low), max(mean_p, 0.01), 0.025)
                        correlation_config["vix_stress_coefficient"] = float(np.clip(vix_slope / 10.0, 0.005, 0.06))
                    correlation_config["calibration_method"] = "temporal_default_label_clustering"
                    correlation_config["rows"] = int(len(pd_working))
                    correlation_config["years"] = int(len(grouped))
                    correlation_config["label_source_note"] = "Uses current PD training labels, which may include free-source proxy distress labels."
                    calibration_notes.append("default correlation calibrated from year-level default-label clustering")

    if not lgd_frame.empty and "lgd" in lgd_frame:
        lgd_working = lgd_frame.copy()
        if "default_date" in lgd_working:
            lgd_working = _merge_by_nearest_market_date(lgd_working, "default_date")
        lgd_working["lgd"] = pd.to_numeric(lgd_working["lgd"], errors="coerce")
        stress = _stress_series(lgd_working)
        valid = lgd_working["lgd"].notna() & stress.notna()
        if valid.sum() >= 50:
            high_lgd = float(lgd_working.loc[valid & (stress >= stress[valid].quantile(0.75)), "lgd"].mean())
            low_lgd = float(lgd_working.loc[valid & (stress <= stress[valid].quantile(0.25)), "lgd"].mean())
            lgd_gap = max(0.0, high_lgd - low_lgd)
            scenario_config["lgd_stress_coefficient"] = float(np.clip(lgd_gap / 2.0, 0.01, 0.12))
            calibration_notes.append("lgd_stress_coefficient calibrated from high/low stress LGD observations")

    if not ead_frame.empty and "realized_ead" in ead_frame:
        ead_working = ead_frame.copy()
        if "observation_date" in ead_working:
            ead_working = _merge_by_nearest_market_date(ead_working, "observation_date")
        ead_working["realized_ead"] = pd.to_numeric(ead_working["realized_ead"], errors="coerce")
        limit = pd.to_numeric(ead_working.get("approved_credit_limit"), errors="coerce").fillna(
            pd.to_numeric(ead_working.get("requested_credit_limit"), errors="coerce")
        )
        ead_ratio = (ead_working["realized_ead"] / limit.replace(0, np.nan)).clip(0, 2)
        commodity_pressure = None
        for column in ["crude_oil", "brent_oil", "jet_fuel_proxy", "heating_oil_proxy"]:
            if column in ead_working:
                values = pd.to_numeric(ead_working[column], errors="coerce")
                if values.notna().any():
                    commodity_pressure = values.rank(pct=True)
                    break
        if commodity_pressure is not None:
            valid = ead_ratio.notna() & commodity_pressure.notna()
            if valid.sum() >= 50:
                high_ead = float(ead_ratio[valid & (commodity_pressure >= commodity_pressure[valid].quantile(0.75))].mean())
                low_ead = float(ead_ratio[valid & (commodity_pressure <= commodity_pressure[valid].quantile(0.25))].mean())
                ead_gap = max(0.0, high_ead - low_ead)
                scenario_config["ead_commodity_coefficient"] = float(np.clip(ead_gap / 2.0, 0.005, 0.12))
                scenario_config["ead_commodity_cap"] = float(np.clip(max(0.15, ead_gap * 2.0), 0.15, 0.45))
                calibration_notes.append("ead commodity coefficient calibrated from high/low commodity-price utilization")

    if calibration_notes:
        scenario_config["calibration_method"] = "historical_market_stress_proxy_calibration"
        scenario_config["calibration_notes"] = calibration_notes
        scenario_config["pd_rows"] = int(len(pd_frame)) if not pd_frame.empty else 0
        scenario_config["lgd_rows"] = int(len(lgd_frame)) if not lgd_frame.empty else 0
        scenario_config["ead_rows"] = int(len(ead_frame)) if not ead_frame.empty else 0

    SCENARIO_MULTIPLIER_CONFIG.write_text(json.dumps(scenario_config, indent=2), encoding="utf-8")
    DEFAULT_CORRELATION_CONFIG.write_text(json.dumps(correlation_config, indent=2), encoding="utf-8")
    return {
        "scenario_multiplier_config": scenario_config,
        "default_correlation_config": correlation_config,
    }


def train_all() -> dict[str, Any]:
    ensure_calibration_dirs()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    summary = {
        "pd": train_pd_model(),
        "lgd": train_lgd_model(),
        "ead": train_ead_model(),
        "collateral_strength": build_collateral_config(),
        "pd_blend": build_pd_blend_config(),
        "scenario_and_correlation": build_scenario_and_correlation_configs(),
    }
    (REPORT_ROOT / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train calibrated artifacts from free-source datasets.")
    parser.parse_args()
    print(json.dumps(train_all(), indent=2))


if __name__ == "__main__":
    main()

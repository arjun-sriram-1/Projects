"""
LGD, EAD, and Expected Loss Engine

Business purpose:
Translate collateral/security, trade exposure, and Phase 5 PD into loss severity,
exposure at default, and expected loss for fuel trade credit decisions.

Inputs:
PD prediction, collateral/security terms, invoice amount, fuel volume and price,
approved credit limit, outstanding receivables, tenor, and utilization.

Outputs:
Loss given default, exposure at default, expected loss, model assumptions,
business-rule warnings, and audit references.

Method:
LGD uses transparent Random-Forest-compatible business logic with collateral
drivers. EAD uses fuel trade exposure logic:
EAD = min(approved_credit_limit, outstanding_receivables + expected_drawdown)
Expected Loss is always:
EL = PD * LGD * EAD

Assumptions:
If invoice amount is missing, invoice exposure is estimated from fuel volume
times fuel price. Tenor-driven expected drawdown assumes a 30-day billing cycle.

Limitations:
This module estimates point-in-time exposure and loss. It does not simulate
portfolio VaR or scenario paths; those are later phases.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd

from api.calibration.artifacts import collateral_strength_config


LOSS_MODEL_VERSION = "lgd_ead_expected_loss_v1.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_LGD_MODEL_PATH = PROJECT_ROOT / "data" / "models" / "historical_lgd_model.pkl"
CALIBRATED_EAD_MODEL_PATH = PROJECT_ROOT / "data" / "models" / "calibrated_ead_model.pkl"


@dataclass
class TradeExposureInput:
    counterparty_id: int
    invoice_amount: Optional[float] = None
    fuel_volume: Optional[float] = None
    fuel_price: Optional[float] = None
    approved_credit_limit: Optional[float] = None
    requested_credit_limit: Optional[float] = None
    outstanding_receivables: float = 0.0
    payment_tenor_days: int = 30
    utilization_rate: float = 0.50
    collateral_type: str = "unsecured"
    letter_of_credit_flag: bool = False
    guarantee_flag: bool = False
    deposit_percentage: float = 0.0
    counterparty_type: Optional[str] = None
    country_risk_score: float = 2.0
    seniority_score: float = 2.0
    notes: Optional[str] = None


@dataclass
class LossEstimateResult:
    run_id: str
    counterparty_id: int
    pd_prediction_id: Optional[int]
    trade_exposure_id: Optional[int]
    model_name: str = "LGD/EAD/Expected Loss Engine"
    model_version: str = LOSS_MODEL_VERSION
    probability_of_default: float = 0.0
    predicted_lgd: float = 0.0
    exposure_at_default: float = 0.0
    expected_loss: float = 0.0
    collateral_strength: float = 0.0
    liquidity_score: Optional[float] = None
    ead_cap_applied: bool = False
    expected_drawdown: float = 0.0
    invoice_exposure: float = 0.0
    model_assumptions: Dict[str, Any] = field(default_factory=dict)
    input_data_reference: Dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _positive(value: Optional[float], default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return default


def normalize_collateral_type(collateral_type: Optional[str]) -> str:
    normalized = (collateral_type or "unsecured").strip().lower()
    aliases = {
        "none": "unsecured",
        "no collateral": "unsecured",
        "lc": "letter_of_credit",
        "letter of credit": "letter_of_credit",
        "standby lc": "letter_of_credit",
        "bank guarantee": "guarantee",
        "guarantee": "guarantee",
        "cash deposit": "cash_deposit",
        "deposit": "cash_deposit",
        "secured": "secured_collateral",
        "collateral": "secured_collateral",
    }
    return aliases.get(normalized, normalized)


def calculate_collateral_strength(exposure: TradeExposureInput) -> float:
    collateral_type = normalize_collateral_type(exposure.collateral_type)
    calibrated = collateral_strength_config()
    base_strength = {
        "letter_of_credit": 0.90,
        "cash_deposit": 0.80,
        "guarantee": 0.65,
        "secured_collateral": 0.55,
        "unsecured": 0.05,
    }.get(collateral_type, 0.20)
    if collateral_type in calibrated:
        try:
            base_strength = float(calibrated[collateral_type])
        except (TypeError, ValueError):
            pass
    if exposure.letter_of_credit_flag:
        base_strength = max(base_strength, 0.90)
    if exposure.guarantee_flag:
        base_strength = max(base_strength, 0.65)
    deposit_strength = _clip01(_positive(exposure.deposit_percentage) / 100)
    return _clip01(max(base_strength, deposit_strength))


def calculate_lgd(
    exposure: TradeExposureInput,
    liquidity_score: Optional[float] = None,
) -> tuple[float, float, list[str], Dict[str, float]]:
    """Estimate LGD with collateral-aware business logic."""
    warnings: list[str] = []
    collateral_strength = calculate_collateral_strength(exposure)
    country_risk = _positive(exposure.country_risk_score, 2.0)
    seniority = _positive(exposure.seniority_score, 2.0)
    tenor = max(int(exposure.payment_tenor_days or 30), 1)
    liquidity = _clip01(liquidity_score if liquidity_score is not None else 0.50)

    lgd = (
        0.62
        - 0.42 * collateral_strength
        - 0.08 * liquidity
        + 0.035 * max(country_risk - 2, 0)
        - 0.025 * max(seniority - 2, 0)
        + 0.06 * max(tenor - 30, 0) / 90
    )

    if normalize_collateral_type(exposure.collateral_type) == "unsecured" and not (
        exposure.letter_of_credit_flag or exposure.guarantee_flag or exposure.deposit_percentage > 0
    ):
        warnings.append("Exposure is unsecured; LGD floor increased for weak recovery protection.")
        lgd = max(lgd, 0.55)
    if exposure.letter_of_credit_flag:
        warnings.append("Letter of credit present; LGD reduced through strong bank-backed security.")
    if exposure.guarantee_flag:
        warnings.append("Guarantee present; LGD reduced through third-party support.")
    if exposure.deposit_percentage > 0:
        warnings.append("Deposit present; LGD reduced through cash support.")

    drivers = {
        "base_lgd": 0.62,
        "collateral_strength_effect": -0.42 * collateral_strength,
        "liquidity_effect": -0.08 * liquidity,
        "country_risk_effect": 0.035 * max(country_risk - 2, 0),
        "seniority_effect": -0.025 * max(seniority - 2, 0),
        "tenor_effect": 0.06 * max(tenor - 30, 0) / 90,
    }

    business_lgd = float(np.clip(lgd, 0.01, 0.99))
    trained_lgd, trained_warning = calculate_trained_historical_lgd(
        exposure,
        liquidity_score=liquidity_score,
    )
    if trained_warning:
        warnings.append(trained_warning)
    if trained_lgd is not None:
        blended_lgd = float(np.clip(0.65 * business_lgd + 0.35 * trained_lgd, 0.01, 0.99))
        drivers["business_rule_lgd"] = business_lgd
        drivers["historical_trained_lgd"] = trained_lgd
        drivers["blended_lgd"] = blended_lgd
        warnings.append("Historical trained LGD model artifact used as collateral-aware cross-check.")
        return blended_lgd, collateral_strength, warnings, drivers

    return business_lgd, collateral_strength, warnings, drivers


def calculate_trained_historical_lgd(
    exposure: TradeExposureInput,
    liquidity_score: Optional[float] = None,
) -> tuple[Optional[float], Optional[str]]:
    """Use the stored historical LGD model as an optional severity cross-check."""

    if not HISTORICAL_LGD_MODEL_PATH.exists():
        return None, None

    try:
        artifact = joblib.load(HISTORICAL_LGD_MODEL_PATH)
        model = artifact["model"] if isinstance(artifact, dict) else artifact
        feature_columns = artifact.get("feature_columns", []) if isinstance(artifact, dict) else []

        collateral_type = normalize_collateral_type(exposure.collateral_type)
        liquidity = _clip01(liquidity_score if liquidity_score is not None else 0.50)
        deposit = _positive(exposure.deposit_percentage, 0.0)
        deposit_fraction = deposit / 100 if deposit > 1 else deposit
        exposure_size = (
            _positive(exposure.approved_credit_limit, 0.0)
            or _positive(exposure.requested_credit_limit, 0.0)
            or _positive(exposure.invoice_amount, 0.0)
            or _positive(exposure.fuel_volume, 0.0) * _positive(exposure.fuel_price, 0.0)
        )
        tenor = max(int(exposure.payment_tenor_days or 30), 1)
        country_risk = _positive(exposure.country_risk_score, 2.0)
        row = {
            "exposure_at_default": exposure_size,
            "approved_credit_limit": _positive(exposure.approved_credit_limit, 0.0),
            "requested_credit_limit": _positive(exposure.requested_credit_limit, 0.0),
            "current_ratio": 0.60 + 1.40 * liquidity,
            "quick_ratio": 0.45 + 1.05 * liquidity,
            "cash_ratio": 0.05 + 0.70 * liquidity,
            "working_capital": exposure_size * (liquidity - 0.50),
            "debt_to_equity": 1.5,
            "debt_to_ebitda": 3.5,
            "liabilities_to_assets": 0.65,
            "interest_coverage": 3.0,
            "operating_margin": 0.06,
            "net_margin": 0.03,
            "return_on_assets": 0.03,
            "return_on_equity": 0.08,
            "market_stress_index": 50.0,
            "oil_volatility": 0.25,
            "fuel_return": 0.0,
            "dxy_return": 0.0,
            "vix_level": 20.0,
            "sp500_return": 0.0,
            "country_risk_score": country_risk,
            "payment_tenor_days": tenor,
            "deposit_percentage": deposit_fraction,
            "exposure_size": exposure_size,
            "letter_of_credit_flag": int(
                exposure.letter_of_credit_flag or collateral_type == "letter_of_credit"
            ),
            "guarantee_flag": int(exposure.guarantee_flag or collateral_type == "guarantee"),
            "days_to_recovery": max(30.0, 120.0 + 45.0 * max(country_risk - 2.0, 0.0) + tenor),
            "legal_cost": exposure_size * (0.02 + 0.01 * max(country_risk - 2.0, 0.0)),
        }
        if not feature_columns:
            feature_columns = list(row.keys())
        frame = pd.DataFrame([row])
        for column in feature_columns:
            if column not in frame.columns:
                frame[column] = 0.0
        frame = frame[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        return float(np.clip(model.predict(frame)[0], 0.01, 0.99)), None
    except Exception as exc:
        return None, f"Historical LGD model artifact could not be used: {exc}"


def calculate_invoice_exposure(exposure: TradeExposureInput) -> tuple[float, list[str]]:
    warnings: list[str] = []
    invoice_amount = _positive(exposure.invoice_amount, 0.0)
    if invoice_amount > 0:
        return invoice_amount, warnings

    fuel_volume = _positive(exposure.fuel_volume, 0.0)
    fuel_price = _positive(exposure.fuel_price, 0.0)
    if fuel_volume > 0 and fuel_price > 0:
        warnings.append("invoice_amount missing; invoice exposure estimated from fuel_volume * fuel_price.")
        return fuel_volume * fuel_price, warnings

    warnings.append("invoice_amount and fuel volume/price missing; invoice exposure set to 0.")
    return 0.0, warnings


def calculate_ead(exposure: TradeExposureInput) -> tuple[float, float, float, bool, list[str]]:
    """Calculate exposure at default from fuel trade exposure logic."""
    warnings: list[str] = []
    invoice_exposure, invoice_warnings = calculate_invoice_exposure(exposure)
    warnings.extend(invoice_warnings)

    outstanding = _positive(exposure.outstanding_receivables, 0.0)
    approved_limit = _positive(exposure.approved_credit_limit, 0.0)
    requested_limit = _positive(exposure.requested_credit_limit, 0.0)
    tenor = max(int(exposure.payment_tenor_days or 30), 1)
    utilization = _clip01(float(exposure.utilization_rate if exposure.utilization_rate is not None else 0.50))

    expected_drawdown = invoice_exposure * utilization * max(1.0, tenor / 30)
    uncapped_ead = outstanding + expected_drawdown

    logical_limit = approved_limit or requested_limit
    cap_applied = False
    if logical_limit > 0 and uncapped_ead > logical_limit:
        ead = logical_limit
        cap_applied = True
        warnings.append("EAD capped by approved/requested credit limit.")
    else:
        ead = uncapped_ead
        if logical_limit <= 0:
            warnings.append("No credit limit provided; EAD is uncapped and should be reviewed.")

    business_ead = float(ead)
    trained_ead, trained_warning = calculate_trained_historical_ead(
        exposure,
        invoice_exposure=invoice_exposure,
    )
    if trained_warning:
        warnings.append(trained_warning)
    if trained_ead is not None and logical_limit > 0:
        blended_ead = 0.70 * business_ead + 0.30 * trained_ead
        if logical_limit > 0 and blended_ead > logical_limit:
            blended_ead = logical_limit
            cap_applied = True
        warnings.append("Calibrated EAD model artifact used as exposure cross-check.")
        return float(blended_ead), float(expected_drawdown), float(invoice_exposure), cap_applied, warnings
    if trained_ead is not None and logical_limit <= 0:
        warnings.append("Calibrated EAD model artifact skipped because no credit limit was provided.")

    return business_ead, float(expected_drawdown), float(invoice_exposure), cap_applied, warnings


def calculate_trained_historical_ead(
    exposure: TradeExposureInput,
    invoice_exposure: Optional[float] = None,
) -> tuple[Optional[float], Optional[str]]:
    """Use the stored calibrated EAD model as an optional exposure cross-check."""

    if not CALIBRATED_EAD_MODEL_PATH.exists():
        return None, None

    try:
        artifact = joblib.load(CALIBRATED_EAD_MODEL_PATH)
        model = artifact["model"] if isinstance(artifact, dict) else artifact
        feature_columns = artifact.get("feature_columns", []) if isinstance(artifact, dict) else []

        invoice = _positive(invoice_exposure, 0.0)
        if invoice <= 0:
            invoice, _ = calculate_invoice_exposure(exposure)
        fuel_volume = _positive(exposure.fuel_volume, 0.0)
        fuel_price = _positive(exposure.fuel_price, 0.0)
        if fuel_volume <= 0 and fuel_price > 0 and invoice > 0:
            fuel_volume = invoice / fuel_price
        if fuel_price <= 0 and fuel_volume > 0 and invoice > 0:
            fuel_price = invoice / fuel_volume

        row = {
            "invoice_amount": invoice,
            "invoice_exposure": invoice,
            "fuel_volume": fuel_volume,
            "fuel_price": fuel_price,
            "approved_credit_limit": _positive(exposure.approved_credit_limit, 0.0),
            "requested_credit_limit": _positive(exposure.requested_credit_limit, 0.0),
            "outstanding_receivables": _positive(exposure.outstanding_receivables, 0.0),
            "payment_tenor_days": max(int(exposure.payment_tenor_days or 30), 1),
            "utilization_rate": _clip01(float(exposure.utilization_rate if exposure.utilization_rate is not None else 0.50)),
            "deposit_percentage": _positive(exposure.deposit_percentage, 0.0),
            "days_past_due": 0.0,
        }
        if not feature_columns:
            feature_columns = list(row.keys())
        frame = pd.DataFrame([row])
        for column in feature_columns:
            if column not in frame.columns:
                frame[column] = 0.0
        frame = frame[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        return float(max(model.predict(frame)[0], 0.0)), None
    except Exception as exc:
        return None, f"Calibrated EAD model artifact could not be used: {exc}"


def calculate_expected_loss(probability_of_default: float, loss_given_default: float, exposure_at_default: float) -> float:
    """Canonical expected loss formula: EL = PD * LGD * EAD."""
    return float(probability_of_default) * float(loss_given_default) * float(exposure_at_default)


def estimate_loss(
    probability_of_default: float,
    exposure: TradeExposureInput,
    pd_prediction_id: Optional[int] = None,
    trade_exposure_id: Optional[int] = None,
    liquidity_score: Optional[float] = None,
    financial_trend_overlay: Optional[dict[str, Any]] = None,
) -> LossEstimateResult:
    """Estimate LGD, EAD, and expected loss from PD and trade exposure inputs."""
    pd_value = _clip01(float(probability_of_default))
    overlay = financial_trend_overlay or {}
    overlay_liquidity = overlay.get("liquidity_score")
    if liquidity_score is None and overlay_liquidity is not None:
        liquidity_score = _clip01(float(overlay_liquidity))
    lgd, collateral_strength, lgd_warnings, lgd_drivers = calculate_lgd(exposure, liquidity_score)
    trend_lgd_addon = float(overlay.get("lgd_addon") or 0.0)
    if trend_lgd_addon:
        lgd_drivers["financial_trend_lgd_addon"] = trend_lgd_addon
        lgd = float(np.clip(lgd + trend_lgd_addon, 0.01, 0.99))
        lgd_warnings.append("Financial history trend overlay increased LGD for deteriorating liquidity, leverage, or earnings trend.")
    ead, expected_drawdown, invoice_exposure, cap_applied, ead_warnings = calculate_ead(exposure)
    expected_loss = calculate_expected_loss(pd_value, lgd, ead)

    return LossEstimateResult(
        run_id=str(uuid4()),
        counterparty_id=exposure.counterparty_id,
        pd_prediction_id=pd_prediction_id,
        trade_exposure_id=trade_exposure_id,
        probability_of_default=pd_value,
        predicted_lgd=lgd,
        exposure_at_default=ead,
        expected_loss=expected_loss,
        collateral_strength=collateral_strength,
        liquidity_score=liquidity_score,
        ead_cap_applied=cap_applied,
        expected_drawdown=expected_drawdown,
        invoice_exposure=invoice_exposure,
        model_assumptions={
            "lgd_method": "Collateral-aware business logic compatible with Random Forest feature intuition.",
            "ead_formula": "min(approved_credit_limit, outstanding_receivables + expected_drawdown)",
            "expected_drawdown": "invoice_exposure * utilization_rate * max(1, payment_tenor_days / 30)",
            "expected_loss_formula": "EL = PD * LGD * EAD",
            "collateral_logic": "LC/guarantee/deposit/strong collateral reduce LGD; unsecured and long tenor increase LGD.",
            "historical_lgd_artifact": str(HISTORICAL_LGD_MODEL_PATH.relative_to(PROJECT_ROOT))
            if HISTORICAL_LGD_MODEL_PATH.exists()
            else "not_available",
            "calibrated_ead_artifact": str(CALIBRATED_EAD_MODEL_PATH.relative_to(PROJECT_ROOT))
            if CALIBRATED_EAD_MODEL_PATH.exists()
            else "not_available",
            "financial_trend_overlay": overlay or "not_available_or_neutral",
            "lgd_driver_components": lgd_drivers,
        },
        input_data_reference={
            "pd_prediction_id": pd_prediction_id,
            "trade_exposure_id": trade_exposure_id,
            "financial_trend_features": "financial_metrics_extracted history + financial_ratios by period",
        },
        warnings=lgd_warnings + ead_warnings,
    )


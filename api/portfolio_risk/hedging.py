"""
Hedging sensitivity engine for fuel credit risk.

Business purpose:
Estimate how oil or FX hedges may reduce effective exposure and expected loss
under a scenario market move.

Inputs:
Exposure, PD, LGD, hedge type, notional, hedge ratio, market move, and optional
commodity/FX sensitivity.

Outputs:
Before/after exposure, hedge payoff, expected loss reduction, assumptions, and
warnings.

Method:
A transparent delta-style hedge payoff model. Positive hedge payoff reduces
effective exposure; PD is not reduced directly.

Economic intuition:
A valid hedge may offset fuel/FX-driven invoice exposure, but basis risk and
hedge-ratio limits must be explicit.

Assumptions:
Scenario market move is a decimal return, e.g. 0.10 for +10 percent.

Limitations:
This is a sensitivity tool, not proof that a real hedge will settle or fully
cover credit exposure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import numpy as np

HEDGING_MODEL_VERSION = "hedging_sensitivity_v1.0"


@dataclass
class HedgeSensitivityInput:
    exposure: float
    probability_of_default: float
    loss_given_default: float
    hedge_type: str
    hedge_notional: float
    hedge_ratio: float
    scenario_market_move: float
    commodity_sensitivity_score: Optional[float] = None
    fx_sensitivity_score: Optional[float] = None
    hedge_price: Optional[float] = None
    reference_price: Optional[float] = None
    hedge_direction: str = "long"
    counterparty_id: Optional[int] = None


@dataclass
class HedgeSensitivityResult:
    run_id: str
    model_name: str
    model_version: str
    counterparty_id: Optional[int]
    hedge_type: str
    unhedged_exposure: float
    hedge_payoff: float
    hedge_benefit: float
    hedged_exposure: float
    unhedged_expected_loss: float
    hedged_expected_loss: float
    exposure_reduction: float
    expected_loss_reduction: float
    before_after_metrics: dict[str, Any]
    assumptions: dict[str, Any]
    warnings: list[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def _clip(value: float, lower: float, upper: float) -> float:
    return float(np.clip(value, lower, upper))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        if np.isnan(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def calculate_hedging_sensitivity(inputs: HedgeSensitivityInput) -> HedgeSensitivityResult:
    """Calculate before/after exposure and expected loss under a simple hedge."""
    warnings: list[str] = []
    exposure = max(_safe_float(inputs.exposure), 0.0)
    pd_value = _clip(_safe_float(inputs.probability_of_default), 0.0, 1.0)
    lgd_value = _clip(_safe_float(inputs.loss_given_default), 0.0, 1.0)
    hedge_notional = max(_safe_float(inputs.hedge_notional), 0.0)
    hedge_ratio = _clip(_safe_float(inputs.hedge_ratio), 0.0, 1.0)
    market_move = _safe_float(inputs.scenario_market_move)

    if hedge_ratio == 0 or hedge_notional == 0:
        warnings.append("Zero hedge ratio or notional; no hedge benefit applied.")
    if abs(market_move) > 1.0:
        warnings.append("Scenario market move exceeds 100%; confirm decimal input convention.")

    sensitivity = inputs.commodity_sensitivity_score
    if sensitivity is None:
        sensitivity = inputs.fx_sensitivity_score
    sensitivity_value = _clip(_safe_float(sensitivity, 1.0), 0.0, 1.0)

    direction = str(inputs.hedge_direction or "long").lower()
    direction_sign = -1.0 if direction in {"short", "sell", "payer"} else 1.0
    raw_payoff = hedge_notional * hedge_ratio * sensitivity_value * market_move * direction_sign
    hedge_benefit = min(max(raw_payoff, 0.0), exposure)
    if raw_payoff < 0:
        warnings.append("Hedge payoff is negative for this market move; benefit floored at zero for credit exposure sensitivity.")
    if hedge_benefit >= exposure and exposure > 0:
        warnings.append("Hedge benefit capped at modeled exposure.")

    hedged_exposure = max(exposure - hedge_benefit, 0.0)
    unhedged_el = pd_value * lgd_value * exposure
    hedged_el = pd_value * lgd_value * hedged_exposure
    exposure_reduction = exposure - hedged_exposure
    expected_loss_reduction = unhedged_el - hedged_el

    return HedgeSensitivityResult(
        run_id=str(uuid4()),
        model_name="Hedging Sensitivity Engine",
        model_version=HEDGING_MODEL_VERSION,
        counterparty_id=inputs.counterparty_id,
        hedge_type=inputs.hedge_type,
        unhedged_exposure=exposure,
        hedge_payoff=float(raw_payoff),
        hedge_benefit=float(hedge_benefit),
        hedged_exposure=float(hedged_exposure),
        unhedged_expected_loss=float(unhedged_el),
        hedged_expected_loss=float(hedged_el),
        exposure_reduction=float(exposure_reduction),
        expected_loss_reduction=float(expected_loss_reduction),
        before_after_metrics={
            "unhedged": {"exposure": exposure, "expected_loss": unhedged_el},
            "hedged": {"exposure": hedged_exposure, "expected_loss": hedged_el},
        },
        assumptions={
            "pd_treatment": "PD is not reduced directly by hedge existence.",
            "payoff_formula": "hedge_notional * hedge_ratio * sensitivity * scenario_market_move * direction_sign",
            "benefit_cap": "Positive hedge benefit is capped at unhedged exposure.",
            "basis_risk": "Basis risk is not modeled beyond the supplied sensitivity score.",
            "hedge_price": inputs.hedge_price,
            "reference_price": inputs.reference_price,
        },
        warnings=warnings,
    )

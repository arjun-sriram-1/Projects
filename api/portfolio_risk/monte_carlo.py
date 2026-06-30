"""
Phase 7 Monte Carlo portfolio loss simulation.

Business purpose:
Simulate default, LGD, and EAD uncertainty for a portfolio of fuel trade credit
counterparties under historical-quantile market scenarios.

Inputs:
Phase 6 loss estimates, scenario market shocks/z-scores, number of simulations,
and random seed.

Outputs:
Expected loss, unexpected loss, credit VaR, expected shortfall, loss
distribution summary, default diagnostics, and marginal contribution by
counterparty.

Method:
Defaults are simulated with a Gaussian copula baseline for portfolio default
dependence. Scenario z-scores adjust PD, LGD, and EAD through transparent
sensitivity coefficients; the scenario movements themselves are generated from
historical data in scenario_generator.py.

Assumptions:
The default-correlation estimate is regime/stress aware and bounded. LGD and
EAD are stochastic around scenario-adjusted values.

Limitations:
This is a student-project risk engine. It is explainable and reproducible, but
not calibrated to proprietary default/recovery data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from statistics import NormalDist
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

import numpy as np
from scipy.stats import t as student_t

from api.calibration.artifacts import default_correlation_config, scenario_multiplier_config
from api.portfolio_risk.scenario_generator import ScenarioDefinition


MONTE_CARLO_MODEL_VERSION = "gaussian_copula_portfolio_loss_v1.0"
T_COPULA_MODEL_VERSION = "t_copula_portfolio_loss_v1.0"
_NORMAL = NormalDist()


@dataclass
class PortfolioExposure:
    counterparty_id: int
    loss_estimate_id: Optional[int]
    pd_prediction_id: Optional[int]
    trade_exposure_id: Optional[int]
    probability_of_default: float
    loss_given_default: float
    exposure_at_default: float
    expected_loss: float
    collateral_strength: Optional[float] = None
    commodity_sensitivity_score: Optional[float] = None
    fx_sensitivity_score: Optional[float] = None
    macro_sensitivity_score: Optional[float] = None
    market_stress_index: Optional[float] = None
    market_regime: Optional[str] = None


@dataclass
class MonteCarloResult:
    run_id: str
    scenario_type: str
    scenario_name: str
    model_name: str
    model_version: str
    number_of_simulations: int
    random_seed: int
    expected_loss: float
    unexpected_loss: float
    credit_var_95: float
    credit_var_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    avg_defaults: float
    max_defaults: int
    max_loss: float
    default_correlation: float
    copula_type: str
    degrees_of_freedom: Optional[int]
    tail_dependence_note: str
    loss_distribution_summary: Dict[str, Any]
    marginal_risk_contribution: Dict[str, float]
    scenario_inputs: Dict[str, Any]
    scenario_impacts: Dict[str, Any]
    input_data_reference: Dict[str, Any]
    assumptions_reference: Dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def _clip(value: float, lower: float, upper: float) -> float:
    return float(np.clip(value, lower, upper))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or np.isnan(float(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _positive_z(value: Any) -> float:
    return max(_safe_float(value), 0.0)


def _scenario_pressure(scenario: ScenarioDefinition, exposure: PortfolioExposure) -> Dict[str, float]:
    z = scenario.driver_zscores
    commodity_z = float(np.mean([
        _positive_z(z.get("brent_change")),
        _positive_z(z.get("jet_fuel_change")),
        _positive_z(z.get("marine_fuel_change")),
    ]))
    fx_z = _positive_z(z.get("dxy_change"))
    macro_z = float(np.mean([
        _positive_z(z.get("vix_change")),
        _positive_z(z.get("yield_change")),
        _positive_z(z.get("stress_index_change")),
        _positive_z(-_safe_float(z.get("sp500_change"))),
        _positive_z(-_safe_float(z.get("baltic_dry_change"))),
    ]))

    commodity_sensitivity = _safe_float(exposure.commodity_sensitivity_score, 0.50)
    fx_sensitivity = _safe_float(exposure.fx_sensitivity_score, 0.35)
    macro_sensitivity = _safe_float(exposure.macro_sensitivity_score, 0.45)

    combined = (
        commodity_sensitivity * commodity_z
        + fx_sensitivity * fx_z
        + macro_sensitivity * macro_z
    ) / 3.0
    return {
        "commodity_pressure_z": commodity_z,
        "fx_pressure_z": fx_z,
        "macro_pressure_z": macro_z,
        "combined_pressure_z": combined,
    }


def apply_scenario_to_exposure(
    exposure: PortfolioExposure,
    scenario: ScenarioDefinition,
) -> Dict[str, float]:
    """Return scenario-adjusted PD/LGD/EAD for one counterparty."""
    pressure = _scenario_pressure(scenario, exposure)
    combined = pressure["combined_pressure_z"]
    collateral_strength = _clip(_safe_float(exposure.collateral_strength, 0.0), 0.0, 1.0)

    multipliers = scenario_multiplier_config()
    pd_stress_coefficient = _safe_float(multipliers.get("pd_stress_coefficient"), 0.18)
    lgd_stress_coefficient = _safe_float(multipliers.get("lgd_stress_coefficient"), 0.035)
    ead_commodity_coefficient = _safe_float(multipliers.get("ead_commodity_coefficient"), 0.035)
    ead_commodity_cap = _safe_float(multipliers.get("ead_commodity_cap"), 0.30)

    pd_multiplier = float(np.exp(pd_stress_coefficient * max(combined, -2.0)))
    lgd_add_on = lgd_stress_coefficient * max(combined, 0.0) * (1.0 - collateral_strength)
    ead_multiplier = 1.0 + min(ead_commodity_coefficient * max(pressure["commodity_pressure_z"], 0.0), ead_commodity_cap)

    adjusted_pd = _clip(exposure.probability_of_default * pd_multiplier, 0.0001, 0.95)
    adjusted_lgd = _clip(exposure.loss_given_default + lgd_add_on, 0.01, 0.99)
    adjusted_ead = max(exposure.exposure_at_default * ead_multiplier, 0.0)

    return {
        **pressure,
        "adjusted_pd": adjusted_pd,
        "adjusted_lgd": adjusted_lgd,
        "adjusted_ead": adjusted_ead,
        "scenario_expected_loss": adjusted_pd * adjusted_lgd * adjusted_ead,
        "pd_multiplier": pd_multiplier,
        "lgd_add_on": lgd_add_on,
        "ead_multiplier": ead_multiplier,
    }


def estimate_default_correlation(scenario: ScenarioDefinition, exposures: Iterable[PortfolioExposure]) -> float:
    """Estimate Gaussian copula correlation from market stress and portfolio size."""
    stress_level = _positive_z(scenario.driver_zscores.get("stress_index_change"))
    vix_level = _positive_z(scenario.driver_zscores.get("vix_change"))
    avg_market_stress = np.mean([
        _safe_float(exposure.market_stress_index, 50.0) for exposure in exposures
    ])
    stress_component = _clip(avg_market_stress / 100.0, 0.0, 1.0)
    config = default_correlation_config()
    base_correlation = _safe_float(config.get("base_correlation"), 0.06)
    stress_coefficient = _safe_float(config.get("stress_coefficient"), 0.18)
    vix_stress_coefficient = _safe_float(config.get("vix_stress_coefficient"), 0.025)
    min_correlation = _safe_float(config.get("min_correlation"), 0.03)
    max_correlation = _safe_float(config.get("max_correlation"), 0.55)
    correlation = base_correlation + stress_coefficient * stress_component + vix_stress_coefficient * min(stress_level + vix_level, 6.0)
    return _clip(correlation, min_correlation, max_correlation)


def _expected_shortfall(losses: np.ndarray, confidence: float) -> float:
    if len(losses) == 0:
        return 0.0
    threshold = float(np.percentile(losses, confidence * 100))
    tail = losses[losses >= threshold]
    return float(np.mean(tail)) if len(tail) else threshold


def simulate_portfolio_loss(
    exposures: Optional[list[PortfolioExposure]] = None,
    scenario: Optional[ScenarioDefinition] = None,
    n_simulations: int = 1000,
    random_seed: Optional[int] = None,
    df=None,
    copula_type: str = "gaussian",
    degrees_of_freedom: int = 5,
) -> MonteCarloResult:
    """Run portfolio Monte Carlo loss simulation for one scenario."""
    if df is not None:
        exposures = df
    if hasattr(exposures, "iterrows"):
        if scenario is None:
            raise ValueError("A data-driven ScenarioDefinition is required for Phase 7 Monte Carlo.")
        return simulate_portfolio_loss_from_dataframe(
            exposures,
            n_simulations=n_simulations,
            scenario=scenario,
            copula_type=copula_type,
            degrees_of_freedom=degrees_of_freedom,
        )
    if not exposures:
        raise ValueError("At least one Phase 6 loss estimate is required for Monte Carlo simulation.")
    if scenario is None:
        raise ValueError("A data-driven ScenarioDefinition is required for Phase 7 Monte Carlo.")
    if n_simulations <= 0:
        raise ValueError("n_simulations must be positive.")

    normalized_copula = str(copula_type or "gaussian").lower().replace("-", "_")
    if normalized_copula in {"t", "student", "student_t", "t_copula"}:
        normalized_copula = "t_copula"
    elif normalized_copula in {"gaussian", "gaussian_copula"}:
        normalized_copula = "gaussian"
    else:
        raise ValueError("copula_type must be gaussian or t_copula.")
    if normalized_copula == "t_copula" and degrees_of_freedom <= 2:
        raise ValueError("degrees_of_freedom must be greater than 2 for t-Copula.")

    seed = int(random_seed if random_seed is not None else 202607)
    rng = np.random.default_rng(seed)
    adjusted = [apply_scenario_to_exposure(exposure, scenario) for exposure in exposures]

    pd_values = np.array([row["adjusted_pd"] for row in adjusted], dtype=float)
    lgd_values = np.array([row["adjusted_lgd"] for row in adjusted], dtype=float)
    ead_values = np.array([row["adjusted_ead"] for row in adjusted], dtype=float)
    if normalized_copula == "t_copula":
        thresholds = np.array([student_t.ppf(_clip(pd, 0.0001, 0.9999), df=degrees_of_freedom) for pd in pd_values])
    else:
        thresholds = np.array([_NORMAL.inv_cdf(_clip(pd, 0.0001, 0.9999)) for pd in pd_values])

    default_correlation = estimate_default_correlation(scenario, exposures)
    systematic_weight = np.sqrt(default_correlation)
    idiosyncratic_weight = np.sqrt(1.0 - default_correlation)

    portfolio_losses = np.zeros(n_simulations)
    default_counts = np.zeros(n_simulations, dtype=int)
    contribution_losses = {str(exposure.counterparty_id): 0.0 for exposure in exposures}

    for sim_idx in range(n_simulations):
        systematic_factor = rng.normal()
        idiosyncratic_factors = rng.normal(size=len(exposures))
        gaussian_scores = (
            systematic_weight * systematic_factor
            + idiosyncratic_weight * idiosyncratic_factors
        )
        if normalized_copula == "t_copula":
            tail_scale = np.sqrt(degrees_of_freedom / rng.chisquare(degrees_of_freedom))
            latent_default_scores = gaussian_scores * tail_scale
        else:
            latent_default_scores = gaussian_scores
        defaults = latent_default_scores < thresholds
        lgd_draws = np.clip(
            rng.normal(lgd_values, np.maximum(0.03, 0.10 * lgd_values)),
            0.01,
            0.99,
        )
        ead_draws = np.maximum(
            rng.normal(ead_values, np.maximum(1.0, 0.05 * ead_values)),
            0.0,
        )
        losses = defaults * lgd_draws * ead_draws
        portfolio_losses[sim_idx] = float(losses.sum())
        default_counts[sim_idx] = int(defaults.sum())
        for exposure, loss in zip(exposures, losses):
            contribution_losses[str(exposure.counterparty_id)] += float(loss)

    expected_loss = float(np.mean(portfolio_losses))
    unexpected_loss = float(np.std(portfolio_losses))
    var_95 = float(np.percentile(portfolio_losses, 95))
    var_99 = float(np.percentile(portfolio_losses, 99))
    es_95 = _expected_shortfall(portfolio_losses, 0.95)
    es_99 = _expected_shortfall(portfolio_losses, 0.99)
    total_contribution = sum(contribution_losses.values()) or 1.0
    marginal_contribution = {
        counterparty_id: float(value / total_contribution)
        for counterparty_id, value in contribution_losses.items()
    }

    scenario_impacts = {
        str(exposure.counterparty_id): {
            "base_pd": exposure.probability_of_default,
            "base_lgd": exposure.loss_given_default,
            "base_ead": exposure.exposure_at_default,
            **impact,
        }
        for exposure, impact in zip(exposures, adjusted)
    }
    validation_diagnostics = {
        "loss_distribution_non_empty": len(portfolio_losses) == int(n_simulations),
        "expected_shortfall_95_exceeds_var_95": es_95 >= var_95,
        "expected_shortfall_99_exceeds_var_99": es_99 >= var_99,
        "var_99_exceeds_var_95": var_99 >= var_95,
        "max_loss_exceeds_expected_loss": float(np.max(portfolio_losses)) >= expected_loss,
        "random_seed_reproducible": seed is not None,
        "portfolio_size": len(exposures),
        "scenario_is_data_driven": bool(getattr(scenario, "source_observations", 0)),
        "scenario_observations": int(getattr(scenario, "source_observations", 0)),
        "scenario_source_window": {
            "start": getattr(scenario, "source_start_date", None),
            "end": getattr(scenario, "source_end_date", None),
        },
    }
    scenario_config = scenario_multiplier_config()
    correlation_config = default_correlation_config()
    pd_stress_coefficient = _safe_float(scenario_config.get("pd_stress_coefficient"), 0.18)
    lgd_stress_coefficient = _safe_float(scenario_config.get("lgd_stress_coefficient"), 0.035)
    ead_commodity_coefficient = _safe_float(scenario_config.get("ead_commodity_coefficient"), 0.035)

    return MonteCarloResult(
        run_id=str(uuid4()),
        scenario_type=scenario.scenario_type,
        scenario_name=scenario.scenario_name,
        model_name="t-Copula Portfolio Monte Carlo" if normalized_copula == "t_copula" else "Gaussian Copula Portfolio Monte Carlo",
        model_version=T_COPULA_MODEL_VERSION if normalized_copula == "t_copula" else MONTE_CARLO_MODEL_VERSION,
        number_of_simulations=int(n_simulations),
        random_seed=seed,
        expected_loss=expected_loss,
        unexpected_loss=unexpected_loss,
        credit_var_95=var_95,
        credit_var_99=var_99,
        expected_shortfall_95=es_95,
        expected_shortfall_99=es_99,
        avg_defaults=float(np.mean(default_counts)),
        max_defaults=int(np.max(default_counts)),
        max_loss=float(np.max(portfolio_losses)),
        default_correlation=default_correlation,
        copula_type=normalized_copula,
        degrees_of_freedom=int(degrees_of_freedom) if normalized_copula == "t_copula" else None,
        tail_dependence_note=(
            "t-Copula uses an explicit degrees-of-freedom tail scale; lower values imply stronger tail dependence."
            if normalized_copula == "t_copula"
            else "Gaussian copula baseline has no explicit tail-dependence parameter."
        ),
        loss_distribution_summary={
            "min": float(np.min(portfolio_losses)),
            "p50": float(np.percentile(portfolio_losses, 50)),
            "p75": float(np.percentile(portfolio_losses, 75)),
            "p90": float(np.percentile(portfolio_losses, 90)),
            "p95": var_95,
            "p99": var_99,
            "max": float(np.max(portfolio_losses)),
            "mean": expected_loss,
            "std": unexpected_loss,
        },
        marginal_risk_contribution=marginal_contribution,
        scenario_inputs=scenario.to_dict(),
        scenario_impacts=scenario_impacts,
        input_data_reference={
            "loss_estimate_ids": [exposure.loss_estimate_id for exposure in exposures],
            "pd_prediction_ids": [exposure.pd_prediction_id for exposure in exposures],
            "trade_exposure_ids": [exposure.trade_exposure_id for exposure in exposures],
        },
        assumptions_reference={
            "calibration_status": "distributional_validation_pending_real_portfolio_loss_history",
            "validation_status": "internal_distribution_sanity_checks_embedded",
            "default_dependence": (
                "t-Copula tail-dependence model used only for portfolio default dependence."
                if normalized_copula == "t_copula"
                else "Gaussian copula baseline used only for portfolio default dependence."
            ),
            "copula_type": normalized_copula,
            "degrees_of_freedom": int(degrees_of_freedom) if normalized_copula == "t_copula" else None,
            "tail_dependence_note": (
                "Lower degrees of freedom imply stronger tail dependence."
                if normalized_copula == "t_copula"
                else "No explicit tail-dependence parameter in Gaussian baseline."
            ),
            "default_correlation": default_correlation,
            "scenario_multiplier_calibration_method": scenario_config.get("calibration_method", "hardcoded_default_fallback"),
            "default_correlation_calibration_method": correlation_config.get("calibration_method", "hardcoded_default_fallback"),
            "pd_adjustment": f"base_pd * exp({pd_stress_coefficient:.4f} * combined scenario pressure z-score)",
            "lgd_adjustment": f"LGD add-on uses {lgd_stress_coefficient:.4f} * pressure * unsecured share.",
            "ead_adjustment": f"Commodity pressure can increase EAD with coefficient {ead_commodity_coefficient:.4f}.",
            "random_seed": seed,
            "scenario_data_source": getattr(scenario, "data_source", "unknown"),
            "scenario_model_version": getattr(scenario, "model_version", "unknown"),
            "validation_diagnostics": validation_diagnostics,
        },
    )


def simulate_portfolio_loss_from_dataframe(
    df,
    n_simulations: int = 1000,
    scenario=None,
    copula_type: str = "gaussian",
    degrees_of_freedom: int = 5,
):
    """Compatibility helper for old callers that pass pd/lgd/exposure columns."""
    exposures = []
    for idx, row in df.reset_index(drop=True).iterrows():
        exposures.append(
            PortfolioExposure(
                counterparty_id=int(row.get("counterparty_id", idx + 1)),
                loss_estimate_id=None,
                pd_prediction_id=None,
                trade_exposure_id=None,
                probability_of_default=_safe_float(row.get("pd", row.get("probability_of_default", 0.05)), 0.05),
                loss_given_default=_safe_float(row.get("lgd", row.get("loss_given_default", 0.60)), 0.60),
                exposure_at_default=_safe_float(row.get("exposure", row.get("exposure_at_default", 1_000_000)), 1_000_000),
                expected_loss=0.0,
            )
        )
    if scenario is None:
        raise ValueError("A data-driven ScenarioDefinition is required.")
    result = simulate_portfolio_loss(
        exposures,
        scenario,
        n_simulations=n_simulations,
        copula_type=copula_type,
        degrees_of_freedom=degrees_of_freedom,
    )
    return {
        "portfolio_losses": result.loss_distribution_summary,
        "diagnostics": result.to_dict(),
    }


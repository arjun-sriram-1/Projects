"""Database service for Phase 7 scenario analysis and Monte Carlo simulation."""

from __future__ import annotations

import json
from typing import Any, Optional

import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from api.portfolio_risk.monte_carlo import MonteCarloResult, PortfolioExposure, simulate_portfolio_loss
from api.portfolio_risk.scenario_generator import ScenarioDefinition, generate_market_scenarios


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _load_dataframe(db: Session, query: str, params: Optional[dict[str, Any]] = None) -> pd.DataFrame:
    result = db.execute(text(query), params or {})
    return pd.DataFrame(result.mappings().all())


def load_market_history(db: Session) -> pd.DataFrame:
    return _load_dataframe(
        db,
        """
        SELECT date, asset, price
        FROM market_prices
        ORDER BY date, asset
        """,
    )


def load_stress_history(db: Session) -> pd.DataFrame:
    return _load_dataframe(
        db,
        """
        SELECT date, stress_index
        FROM stress_index_history
        ORDER BY date
        """,
    )


def load_regime_history(db: Session) -> pd.DataFrame:
    return _load_dataframe(
        db,
        """
        SELECT date, regime_label
        FROM market_regime_history
        ORDER BY date
        """,
    )


def generate_scenarios_from_database(
    db: Session,
    target_regime: Optional[str] = None,
) -> list[ScenarioDefinition]:
    market_prices = load_market_history(db)
    stress_history = load_stress_history(db)
    regime_history = load_regime_history(db)
    return generate_market_scenarios(
        market_prices=market_prices,
        stress_history=stress_history,
        regime_history=regime_history,
        target_regime=target_regime,
    )


def load_latest_portfolio_exposures(
    db: Session,
    counterparty_ids: Optional[list[int]] = None,
) -> list[PortfolioExposure]:
    base_query = """
        SELECT *
        FROM (
            SELECT
                le.id AS loss_estimate_id,
                le.counterparty_id,
                le.pd_prediction_id,
                le.trade_exposure_id,
                le.probability_of_default,
                le.predicted_lgd,
                le.exposure_at_default,
                le.expected_loss,
                le.collateral_strength,
                pd.commodity_sensitivity_score,
                pd.fx_sensitivity_score,
                pd.macro_sensitivity_score,
                pd.market_stress_index,
                pd.market_regime,
                ROW_NUMBER() OVER (
                    PARTITION BY le.counterparty_id
                    ORDER BY le.created_at DESC, le.id DESC
                ) AS rn
            FROM loss_estimates le
            LEFT JOIN pd_model_predictions pd
                ON pd.id = le.pd_prediction_id
            {where_clause}
        ) latest
        WHERE rn = 1
        ORDER BY counterparty_id
    """
    params: dict[str, Any] = {}
    where_clause = ""
    statement = text(base_query.format(where_clause=where_clause))
    if counterparty_ids:
        where_clause = "WHERE le.counterparty_id IN :counterparty_ids"
        statement = text(base_query.format(where_clause=where_clause)).bindparams(
            bindparam("counterparty_ids", expanding=True)
        )
        params["counterparty_ids"] = [int(value) for value in counterparty_ids]

    rows = db.execute(statement, params).mappings().all()
    exposures: list[PortfolioExposure] = []
    for row in rows:
        exposures.append(
            PortfolioExposure(
                counterparty_id=int(row["counterparty_id"]),
                loss_estimate_id=int(row["loss_estimate_id"]),
                pd_prediction_id=int(row["pd_prediction_id"]) if row["pd_prediction_id"] is not None else None,
                trade_exposure_id=int(row["trade_exposure_id"]) if row["trade_exposure_id"] is not None else None,
                probability_of_default=float(row["probability_of_default"]),
                loss_given_default=float(row["predicted_lgd"]),
                exposure_at_default=float(row["exposure_at_default"]),
                expected_loss=float(row["expected_loss"]),
                collateral_strength=float(row["collateral_strength"]) if row["collateral_strength"] is not None else None,
                commodity_sensitivity_score=float(row["commodity_sensitivity_score"]) if row["commodity_sensitivity_score"] is not None else None,
                fx_sensitivity_score=float(row["fx_sensitivity_score"]) if row["fx_sensitivity_score"] is not None else None,
                macro_sensitivity_score=float(row["macro_sensitivity_score"]) if row["macro_sensitivity_score"] is not None else None,
                market_stress_index=float(row["market_stress_index"]) if row["market_stress_index"] is not None else None,
                market_regime=str(row["market_regime"]) if row["market_regime"] is not None else None,
            )
        )
    return exposures


def save_phase7_result(db: Session, result: MonteCarloResult):
    scenario_row = db.execute(
        text(
            """
            INSERT INTO scenario_results (
                run_id,
                scenario_name,
                scenario_type,
                model_name,
                model_version,
                expected_loss,
                var_95,
                var_99,
                expected_shortfall_95,
                expected_shortfall_99,
                expected_shortfall,
                unexpected_loss,
                max_loss,
                scenario_inputs,
                scenario_impacts,
                input_data_reference,
                assumptions_reference,
                number_of_counterparties,
                number_of_simulations,
                random_seed
            )
            VALUES (
                :run_id,
                :scenario_name,
                :scenario_type,
                :model_name,
                :model_version,
                :expected_loss,
                :var_95,
                :var_99,
                :expected_shortfall_95,
                :expected_shortfall_99,
                :expected_shortfall,
                :unexpected_loss,
                :max_loss,
                CAST(:scenario_inputs AS JSONB),
                CAST(:scenario_impacts AS JSONB),
                CAST(:input_data_reference AS JSONB),
                CAST(:assumptions_reference AS JSONB),
                :number_of_counterparties,
                :number_of_simulations,
                :random_seed
            )
            RETURNING *
            """
        ),
        {
            "run_id": result.run_id,
            "scenario_name": result.scenario_name,
            "scenario_type": result.scenario_type,
            "model_name": result.model_name,
            "model_version": result.model_version,
            "expected_loss": result.expected_loss,
            "var_95": result.credit_var_95,
            "var_99": result.credit_var_99,
            "expected_shortfall_95": result.expected_shortfall_95,
            "expected_shortfall_99": result.expected_shortfall_99,
            "expected_shortfall": result.expected_shortfall_95,
            "unexpected_loss": result.unexpected_loss,
            "max_loss": result.max_loss,
            "scenario_inputs": _json_dumps(result.scenario_inputs),
            "scenario_impacts": _json_dumps(result.scenario_impacts),
            "input_data_reference": _json_dumps(result.input_data_reference),
            "assumptions_reference": _json_dumps(result.assumptions_reference),
            "number_of_counterparties": len(result.scenario_impacts),
            "number_of_simulations": result.number_of_simulations,
            "random_seed": result.random_seed,
        },
    ).mappings().first()

    scenario_result_id = scenario_row.get("id") if hasattr(scenario_row, "get") else None
    if scenario_result_id is None:
        scenario_result_id = scenario_row.get("scenario_id")

    simulation_row = db.execute(
        text(
            """
            INSERT INTO simulation_results (
                run_id,
                scenario,
                scenario_result_id,
                model_name,
                model_version,
                expected_loss,
                var_95,
                var_99,
                expected_shortfall_95,
                expected_shortfall_99,
                expected_shortfall,
                unexpected_loss,
                avg_defaults,
                max_defaults,
                number_of_simulations,
                random_seed,
                loss_distribution_summary,
                marginal_risk_contribution,
                default_correlation,
                input_data_reference,
                assumptions_reference
            )
            VALUES (
                :run_id,
                :scenario,
                :scenario_result_id,
                :model_name,
                :model_version,
                :expected_loss,
                :var_95,
                :var_99,
                :expected_shortfall_95,
                :expected_shortfall_99,
                :expected_shortfall,
                :unexpected_loss,
                :avg_defaults,
                :max_defaults,
                :number_of_simulations,
                :random_seed,
                CAST(:loss_distribution_summary AS JSONB),
                CAST(:marginal_risk_contribution AS JSONB),
                :default_correlation,
                CAST(:input_data_reference AS JSONB),
                CAST(:assumptions_reference AS JSONB)
            )
            RETURNING *
            """
        ),
        {
            "run_id": result.run_id,
            "scenario": result.scenario_type,
            "scenario_result_id": scenario_result_id,
            "model_name": result.model_name,
            "model_version": result.model_version,
            "expected_loss": result.expected_loss,
            "var_95": result.credit_var_95,
            "var_99": result.credit_var_99,
            "expected_shortfall_95": result.expected_shortfall_95,
            "expected_shortfall_99": result.expected_shortfall_99,
            "expected_shortfall": result.expected_shortfall_95,
            "unexpected_loss": result.unexpected_loss,
            "avg_defaults": result.avg_defaults,
            "max_defaults": result.max_defaults,
            "number_of_simulations": result.number_of_simulations,
            "random_seed": result.random_seed,
            "loss_distribution_summary": _json_dumps(result.loss_distribution_summary),
            "marginal_risk_contribution": _json_dumps(result.marginal_risk_contribution),
            "default_correlation": result.default_correlation,
            "input_data_reference": _json_dumps(result.input_data_reference),
            "assumptions_reference": _json_dumps(result.assumptions_reference),
        },
    ).mappings().first()
    db.commit()
    return scenario_row, simulation_row


def run_phase7_scenario_analysis(
    db: Session,
    scenario_type: str = "adverse",
    counterparty_ids: Optional[list[int]] = None,
    n_simulations: int = 1000,
    random_seed: Optional[int] = None,
    persist: bool = True,
    target_regime: Optional[str] = None,
    copula_type: str = "gaussian",
    degrees_of_freedom: int = 5,
) -> tuple[MonteCarloResult, Optional[Any], Optional[Any]]:
    scenarios = generate_scenarios_from_database(db, target_regime=target_regime)
    scenario_lookup = {scenario.scenario_type: scenario for scenario in scenarios}
    if scenario_type not in scenario_lookup:
        raise ValueError(
            f"Scenario '{scenario_type}' not found. Available scenarios: {sorted(scenario_lookup)}"
        )

    exposures = load_latest_portfolio_exposures(db, counterparty_ids=counterparty_ids)
    if not exposures:
        raise ValueError("No Phase 6 loss estimates found. Run Phase 6 before Phase 7.")

    result = simulate_portfolio_loss(
        exposures=exposures,
        scenario=scenario_lookup[scenario_type],
        n_simulations=n_simulations,
        random_seed=random_seed,
        copula_type=copula_type,
        degrees_of_freedom=degrees_of_freedom,
    )

    scenario_row = simulation_row = None
    if persist:
        scenario_row, simulation_row = save_phase7_result(db, result)
    return result, scenario_row, simulation_row


def get_latest_simulation_result(db: Session):
    return db.execute(
        text(
            """
            SELECT *
            FROM simulation_results
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """
        )
    ).mappings().first()


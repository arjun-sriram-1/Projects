"""FastAPI routes for Phase 7 scenarios and Monte Carlo simulation."""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.portfolio_risk.schemas import (
    HedgeSensitivityRequest,
    HedgeSensitivityResponse,
    MonteCarloRunRequest,
    MonteCarloRunResponse,
    ScenarioListResponse,
    ScenarioResponse,
    StoredSimulationResponse,
)
from api.db.session import get_db
from api.portfolio_risk.hedging import HedgeSensitivityInput, calculate_hedging_sensitivity
from api.portfolio_risk.service import (
    generate_scenarios_from_database,
    get_latest_simulation_result,
    run_phase7_scenario_analysis,
)


router = APIRouter(prefix="/api/v1/scenario-analysis", tags=["scenario-analysis"])


def _row_to_dict(row):
    converted = {}
    for key, value in dict(row).items():
        if isinstance(value, Decimal):
            converted[key] = float(value)
        elif isinstance(value, (datetime, date)):
            converted[key] = value.isoformat()
        else:
            converted[key] = value
    return converted


@router.get("/scenarios", response_model=ScenarioListResponse)
def list_data_driven_scenarios(
    target_regime: str | None = None,
    db: Session = Depends(get_db),
):
    """Generate Phase 7 scenarios from stored market/stress/regime history."""
    try:
        scenarios = generate_scenarios_from_database(db, target_regime=target_regime)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ScenarioListResponse(
        message="Data-driven scenarios generated from historical market data.",
        scenarios=[ScenarioResponse(**scenario.to_dict()) for scenario in scenarios],
    )


@router.post("/monte-carlo/run", response_model=MonteCarloRunResponse)
def run_monte_carlo_analysis(
    request: MonteCarloRunRequest,
    db: Session = Depends(get_db),
):
    """Run and optionally store Phase 7 Monte Carlo portfolio simulation."""
    try:
        result, _, _ = run_phase7_scenario_analysis(
            db,
            scenario_type=request.scenario_type,
            counterparty_ids=request.counterparty_ids,
            n_simulations=request.n_simulations,
            random_seed=request.random_seed,
            persist=request.persist,
            target_regime=request.target_regime,
            copula_type=request.copula_type,
            degrees_of_freedom=request.degrees_of_freedom,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return MonteCarloRunResponse(
        message="Monte Carlo scenario analysis completed.",
        **{
            key: value
            for key, value in result.to_dict().items()
            if key
            in MonteCarloRunResponse.model_fields
            and key != "message"
        },
    )


@router.post("/hedging/sensitivity", response_model=HedgeSensitivityResponse)
def run_hedging_sensitivity(request: HedgeSensitivityRequest):
    """Calculate before/after exposure and expected loss with hedge sensitivity."""
    result = calculate_hedging_sensitivity(HedgeSensitivityInput(**request.model_dump()))
    return HedgeSensitivityResponse(**result.to_dict())


@router.get("/monte-carlo/latest", response_model=StoredSimulationResponse)
def get_latest_monte_carlo_result(db: Session = Depends(get_db)):
    """Return latest stored Phase 7 simulation result."""
    latest = get_latest_simulation_result(db)
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulation results found. Run /api/v1/scenario-analysis/monte-carlo/run first.",
        )
    return StoredSimulationResponse(**_row_to_dict(latest))


__all__ = ["router"]



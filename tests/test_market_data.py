"""Market stress and regime detection tests for V2."""

import importlib.util
import numpy as np
import pandas as pd
import pytest

from api.market_data.regime_detection import detect_market_regimes
from api.market_data.forecasting import run_forecast
from api.market_data.router import router as market_router
from api.market_data.service import rebuild_market_intelligence_from_prices
from api.market_data.external_providers import (
    EIA_SERIES,
    FRED_SERIES,
    add_calculated_market_series,
    load_staged_market_csvs,
)
from api.market_data.stress_index import build_market_component_matrix, build_stress_index, classify_stress_level
from api.portfolio_risk.scenario_generator import build_scenario_matrix


def synthetic_market_prices(n_days=160):
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    rows = []
    asset_start = {
        "brent_oil": 80.0,
        "crude_oil": 75.0,
        "heating_oil_proxy": 2.8,
        "vix": 14.0,
        "sp500": 4800.0,
        "dxy": 102.0,
        "usd_inr": 83.0,
        "gold": 2050.0,
        "us_10y_yield": 42.0,
        "freight_proxy": 11.0,
        "jet_crack_spread": 22.0,
        "eia_crude_inventories": 430000.0,
        "opec_production": 27000.0,
        "global_pmi": 51.0,
        "iata_passenger_traffic": 102.0,
    }
    for asset, start in asset_start.items():
        values = [start]
        for i in range(1, n_days):
            drift = 0.0002
            shock = rng.normal(0, 0.004)
            if i > n_days - 30:
                if asset in {
                    "brent_oil",
                    "crude_oil",
                    "heating_oil_proxy",
                    "vix",
                    "dxy",
                    "usd_inr",
                    "gold",
                }:
                    shock += 0.012
                if asset in {"sp500", "freight_proxy"}:
                    shock -= 0.014
                if asset == "us_10y_yield":
                    shock += 0.008
            values.append(max(0.1, values[-1] * (1 + drift + shock)))
        for dt, value in zip(dates, values):
            rows.append({"date": dt, "asset": asset, "price": value})
    return pd.DataFrame(rows)


def test_stress_index_is_data_driven_bounded_and_directional():
    result = build_stress_index(synthetic_market_prices())
    history = result.history

    assert not history.empty
    assert history["stress_index"].between(0, 100).all()
    assert result.explained_variance_ratio > 0
    assert "vix_zscore" in result.available_components
    assert isinstance(result.pca_loadings, dict)
    assert history.iloc[-1]["stress_index"] > history.iloc[20]["stress_index"]


def test_stress_level_classification():
    assert classify_stress_level(10) == "Calm"
    assert classify_stress_level(35) == "Normal"
    assert classify_stress_level(55) == "Elevated"
    assert classify_stress_level(75) == "Stressed"
    assert classify_stress_level(95) == "Crisis"


def test_regime_detection_learns_market_states():
    stress_result = build_stress_index(synthetic_market_prices())
    regime_result = detect_market_regimes(
        stress_result.component_matrix,
        stress_result.history,
        n_regimes=4,
    )

    assert not regime_result.history.empty
    assert "regime_label" in regime_result.history.columns
    assert regime_result.history["regime_probability"].between(0, 1).all()
    assert len(regime_result.interpretation) >= 2
    assert set(regime_result.history["regime_label"])


def test_rebuild_market_intelligence_from_prices_without_persistence():
    result = rebuild_market_intelligence_from_prices(
        synthetic_market_prices(n_days=90),
        persist=False,
    )

    assert result["stress_rows"] > 0
    assert result["regime_rows"] > 0
    assert 0 <= result["latest_stress_index"] <= 100
    assert result["latest_stress_level"] in {
        "Calm",
        "Normal",
        "Elevated",
        "Stressed",
        "Crisis",
    }
    assert result["latest_regime_label"]
    assert "vix_zscore" in result["available_components"]


@pytest.mark.skipif(importlib.util.find_spec("statsmodels") is None or importlib.util.find_spec("arch") is None, reason="statsmodels and arch are required for V1-style forecasting")
def test_market_forecasting_outputs_required_fields():
    prices = synthetic_market_prices(n_days=120)

    arima = run_forecast(prices, model_type="arima", assets=["brent_oil"], horizon=5)
    var = run_forecast(prices, model_type="var", assets=["brent_oil", "dxy", "vix"], horizon=5)
    garch = run_forecast(prices, model_type="garch", assets=["brent_oil"], horizon=5)

    assert arima.model_name == "statsmodels ARIMA forecast"
    assert arima.forecast_horizon == 5
    assert len(arima.forecast_path["brent_oil"]) == 5
    assert arima.confidence_interval["brent_oil"]["upper"] >= arima.confidence_interval["brent_oil"]["lower"]
    assert arima.backtest_error is not None

    assert var.model_name == "statsmodels VAR forecast"
    assert set(var.input_series) >= {"brent_oil", "dxy", "vix"}
    assert all(len(path) == 5 for path in var.forecast_path.values())

    assert garch.model_name == "arch GARCH volatility forecast"
    assert garch.forecast_volatility is not None
    assert garch.forecast_volatility >= 0
    assert garch.volatility_regime in {"low", "normal", "elevated", "stress"}
    assert "volatility_clustering" in garch.assumptions


def test_market_intelligence_router_imports_without_pipeline_dependency():
    assert market_router.prefix == "/api/v1/market-intelligence"
    route_paths = {route.path for route in market_router.routes}
    assert "/api/v1/market-intelligence/rebuild" in route_paths
    assert "/api/v1/market-intelligence/refresh-live" in route_paths
    assert "/api/v1/market-intelligence/stress/latest" in route_paths
    assert "/api/v1/market-intelligence/stress/history" in route_paths
    assert "/api/v1/market-intelligence/regime/latest" in route_paths
    assert "/api/v1/market-intelligence/forecast" in route_paths


def test_free_provider_mappings_cover_market_monitor_sources():
    assert FRED_SERIES["brent_oil"].source_id == "DCOILBRENTEU"
    assert FRED_SERIES["crude_oil"].source_id == "DCOILWTICO"
    assert FRED_SERIES["sp500"].source_id == "SP500"
    assert FRED_SERIES["vix"].source_id == "VIXCLS"
    assert FRED_SERIES["dxy"].source_id == "DTWEXBGS"
    assert FRED_SERIES["us_10y_yield"].source_id == "DGS10"
    assert EIA_SERIES["jet_fuel_proxy"].source_id == "EER_EPJK_PF4_RGC_DPG"
    assert EIA_SERIES["eia_crude_inventories"].source_id == "WCESTUS1"


def test_calculated_jet_crack_spread_is_added_from_jet_and_crude_prices():
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    frame = pd.DataFrame(
        [
            {
                "date": dt,
                "asset": asset,
                "asset_name": asset,
                "source_id": asset,
                "price": price,
                "data_source": "test",
                "frequency": "daily",
                "units": "mixed",
                "return": np.nan,
                "rolling_volatility": np.nan,
            }
            for dt, jet, brent in zip(dates, [2.50, 2.60, 2.70], [80.0, 82.0, 84.0])
            for asset, price in [("jet_fuel_proxy", jet), ("brent_oil", brent)]
        ]
    )

    result = add_calculated_market_series(frame)
    spread = result[result["asset"] == "jet_crack_spread"].sort_values("date")

    assert len(spread) == 3
    assert spread.iloc[-1]["price"] == pytest.approx((2.70 * 42.0) - 84.0)
    assert spread.iloc[-1]["data_source"] == "calculated_market_series"


def test_staged_market_csv_loader_normalizes_manual_free_downloads(tmp_path):
    csv_path = tmp_path / "manual_sources.csv"
    csv_path.write_text(
        "date,asset,value,source_id,asset_name,data_source,frequency,units\n"
        "2024-01-31,global_pmi,50.4,JPM_GLOBAL_PMI,Global PMI,staged_csv:test,monthly,index\n"
        "2024-02-29,global_pmi,49.8,JPM_GLOBAL_PMI,Global PMI,staged_csv:test,monthly,index\n"
        "2024-01-31,opec_production,26650,JODI_OPEC,OPEC Production,staged_csv:test,monthly,thousand_barrels_per_day\n",
        encoding="utf-8",
    )

    frame, warnings = load_staged_market_csvs(tmp_path)

    assert warnings == []
    assert set(frame["asset"]) == {"global_pmi", "opec_production"}
    assert {"return", "rolling_volatility"}.issubset(frame.columns)
    assert frame["data_source"].eq("staged_csv:test").all()


def test_stress_components_include_new_manual_and_calculated_market_drivers():
    dates = pd.date_range("2024-01-01", periods=45, freq="D")
    rows = []
    assets = {
        "jet_crack_spread": np.linspace(20, 32, len(dates)),
        "eia_crude_inventories": np.linspace(430000, 455000, len(dates)),
        "opec_production": np.linspace(27000, 25500, len(dates)),
        "global_pmi": np.linspace(52, 47, len(dates)),
        "iata_passenger_traffic": np.linspace(105, 92, len(dates)),
    }
    for asset, values in assets.items():
        rows.extend({"date": dt, "asset": asset, "price": value} for dt, value in zip(dates, values))

    components, missing = build_market_component_matrix(pd.DataFrame(rows))

    expected = {
        "jet_crack_spread_zscore",
        "crude_inventory_build_zscore",
        "opec_production_cut_zscore",
        "global_pmi_weakness_zscore",
        "iata_traffic_loss_zscore",
    }
    assert expected.issubset(set(components.columns))
    assert expected.isdisjoint(set(missing))


def test_scenario_matrix_includes_expanded_market_drivers():
    matrix = build_scenario_matrix(synthetic_market_prices(n_days=90))

    assert "jet_crack_spread_change" in matrix.columns
    assert "crude_inventory_change" in matrix.columns
    assert "opec_production_change" in matrix.columns
    assert "global_pmi_change" in matrix.columns
    assert "iata_passenger_traffic_change" in matrix.columns


def test_no_v1_imports_in_migrated_market_files():
    files = [
        "api/market_data/stress_index.py",
        "api/market_data/regime_detection.py",
        "api/market_data/service.py",
        "api/market_data/router.py",
        "api/market_data/schemas.py",
        "api/market_data/external_providers.py",
        "api/market_data/market_data.py",
        "api/market_data/forecasting.py",
    ]
    forbidden = [
        "database.db_connection",
        "models.stress_index",
        "models.regime_detection",
        "pipelines.build_stress_regimes",
        "api.schemas_phase4",
        "CREDIT_RISK_PROJECT_V1",
    ]

    for file_path in files:
        text = open(file_path, encoding="utf-8").read()
        for pattern in forbidden:
            assert pattern not in text


"""Market and stress intelligence page."""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from web.api_client import ApiClient
from web.components.cards import bullet_list, render_section_header
from web.components.charts import apply_dark_chart_layout
from web.components.formatting import number, text
from web.components.layout import render_api_state, render_technical_json
from web.components.terminal import (
    action_grid,
    evidence_panel,
    render_terminal_kpi_strip,
    risk_driver_panel,
    terminal_panel,
)


DEFAULT_ASSETS = ["brent_oil", "crude_oil", "heating_oil_proxy", "vix", "sp500"]
FORECAST_MODELS = ["arima", "var", "garch"]
ASSET_LABELS = {
    "brent_oil": "Brent oil",
    "crude_oil": "Crude oil",
    "heating_oil_proxy": "Heating oil proxy",
    "vix": "VIX",
    "sp500": "S&P 500",
}


def _asset_label(asset: Any) -> str:
    return ASSET_LABELS.get(str(asset), str(asset).replace("_", " ").title())


def _price_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"])
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame["Asset"] = frame["asset"].map(_asset_label)
    return frame.dropna(subset=["date", "asset", "price"]).sort_values(["asset", "date"])


def _latest_price_rows(frame: pd.DataFrame) -> list[tuple[str, str, str | None]]:
    if frame.empty:
        return []
    rows = []
    for asset, asset_frame in frame.groupby("asset"):
        latest = asset_frame.sort_values("date").iloc[-1]
        rows.append((_asset_label(asset), number(latest.get("price"), 4), latest.get("date").strftime("%Y-%m-%d")))
    return rows


def _price_momentum_rows(frame: pd.DataFrame) -> list[tuple[str, str, str | None]]:
    if frame.empty:
        return []
    rows = []
    for asset, asset_frame in frame.groupby("asset"):
        series = asset_frame.sort_values("date")["price"].dropna()
        if len(series) < 2:
            rows.append((_asset_label(asset), "Insufficient history", "Change from earliest stored point"))
            continue
        start = float(series.iloc[0])
        end = float(series.iloc[-1])
        change = ((end / start) - 1.0) * 100 if start else 0.0
        rows.append((_asset_label(asset), f"{change:.2f}%", "Change across selected history"))
    return rows


def _market_brief(stress: dict | None, regime: dict | None) -> str:
    rows = [
        ("Stress level", text((stress or {}).get("stress_level")), "Latest backend stress index"),
        ("Stress index", number((stress or {}).get("stress_index"), 2), text((stress or {}).get("date"))),
        ("Market regime", text((regime or {}).get("regime_label")), "Latest regime classifier"),
        ("Regime confidence", number((regime or {}).get("regime_probability"), 3), "Backend probability"),
    ]
    return terminal_panel("Market Stress Brief", evidence_panel(rows), "Commodity and macro backdrop for fuel credit exposure")


def _correlation_heatmap(correlation_matrix: dict) -> None:
    if not correlation_matrix:
        return
    corr_df = pd.DataFrame(correlation_matrix).T
    if corr_df.empty:
        return
    corr_df.index = [_asset_label(item) for item in corr_df.index]
    corr_df.columns = [_asset_label(item) for item in corr_df.columns]
    fig = px.imshow(
        corr_df,
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        text_auto=".2f",
        aspect="auto",
    )
    apply_dark_chart_layout(fig, title="Market Correlation Heatmap")
    st.plotly_chart(fig, use_container_width=True)


def _volatility_driver_panel(volatility: dict, high_volatility_assets: list[str]) -> str:
    if not volatility:
        return terminal_panel(
            "Volatility Drivers",
            action_grid([("Awaiting factor output", "Run commodity factor analysis for rolling volatility signals.")]),
            "No volatility ranking available",
        )
    values = []
    numeric_values = []
    for value in volatility.values():
        try:
            numeric_values.append(abs(float(value)))
        except (TypeError, ValueError):
            continue
    max_value = max(numeric_values) if numeric_values else 1.0
    high_vol = {str(item) for item in high_volatility_assets}
    for asset, value in volatility.items():
        try:
            score = abs(float(value)) / max_value * 100 if max_value else 0.0
        except (TypeError, ValueError):
            score = 0.0
        values.append((_asset_label(asset), score, "risk" if asset in high_vol else "info"))
    return terminal_panel("Volatility Drivers", risk_driver_panel(values), "Relative rolling volatility across selected market series")


def _spread_panel(spreads: dict) -> str:
    rows = []
    for name, values in spreads.items():
        if not isinstance(values, dict):
            continue
        detail = ", ".join(f"{key.replace('_', ' ').title()}: {number(value, 4)}" for key, value in values.items())
        rows.append((str(name).replace("_", " ").title(), detail, "Backend spread analysis"))
    if not rows:
        return ""
    return terminal_panel("Spread Signals", evidence_panel(rows), "Commodity spread diagnostics")


def _forecast_summary(payload: dict, fallback_horizon: int) -> str:
    values = payload.get("forecast_value") or {}
    intervals = payload.get("confidence_interval") or {}
    rows = []
    for asset, value in values.items():
        interval = intervals.get(asset) or {}
        if interval:
            band = f"{number(interval.get('lower'), 6)} to {number(interval.get('upper'), 6)}"
        else:
            band = "Confidence band unavailable"
        rows.append((_asset_label(asset), number(value, 6), band))
    if not rows:
        rows.append(("Forecast output", "No estimate returned", f"{payload.get('forecast_horizon', fallback_horizon)} forecast steps"))
    return terminal_panel("Forecast Summary", evidence_panel(rows), "Backend estimate, not a guaranteed price")


def _forecast_path_chart(payload: dict) -> None:
    path = payload.get("forecast_path") or {}
    if not path:
        return
    forecast_df = pd.DataFrame(path)
    if forecast_df.empty:
        return
    forecast_df.index = range(1, len(forecast_df) + 1)
    forecast_df.index.name = "step"
    forecast_plot = forecast_df.reset_index().melt(id_vars="step", var_name="asset", value_name="forecast")
    forecast_plot["Asset"] = forecast_plot["asset"].map(_asset_label)
    forecast_fig = px.line(forecast_plot, x="step", y="forecast", color="Asset")
    apply_dark_chart_layout(forecast_fig, title="Forecast Path: Backend Estimate")
    st.plotly_chart(forecast_fig, use_container_width=True)


def render(client: ApiClient, context: dict) -> None:
    st.subheader("Market & Stress Intel")
    st.caption("Question answered: is the fuel and macro backdrop increasing short-term credit risk?")

    stress = client.latest_market_stress()
    regime = client.latest_market_regime()
    stress_payload = stress.data if stress.ok and stress.data else None
    regime_payload = regime.data if regime.ok and regime.data else None

    if stress_payload or regime_payload:
        render_terminal_kpi_strip(
            [
                ("Stress Index", number((stress_payload or {}).get("stress_index"), 2), text((stress_payload or {}).get("stress_level")), "watch"),
                ("Stress Date", text((stress_payload or {}).get("date")), "Latest market data date", "info"),
                ("Regime", text((regime_payload or {}).get("regime_label")), "Market classifier", "info"),
                ("Regime Confidence", number((regime_payload or {}).get("regime_probability"), 3), "Backend probability", "neutral"),
            ]
        )
        st.markdown(_market_brief(stress_payload, regime_payload), unsafe_allow_html=True)
    else:
        render_api_state(stress, "Market stress has not been built yet.")
        render_api_state(regime, "Market regime has not been built yet.")

    selected_assets = st.multiselect(
        "Market series",
        DEFAULT_ASSETS,
        default=DEFAULT_ASSETS,
        format_func=_asset_label,
        help="Stored market prices are retrieved through the FastAPI market-intelligence endpoint.",
    )
    limit_per_asset = st.slider("History per series", min_value=60, max_value=500, value=180, step=20)

    if not selected_assets:
        st.info("Select at least one market series.")
        return

    prices_result = client.recent_market_prices(selected_assets, limit_per_asset=limit_per_asset)
    if not render_api_state(prices_result, "No stored market prices found for the selected series."):
        return

    price_payload = prices_result.data or {}
    price_rows = price_payload.get("market_prices") or []
    price_df = _price_frame(price_rows)

    render_terminal_kpi_strip(
        [
            ("Series", str(len(selected_assets)), "Selected market inputs", "info"),
            ("Observations", str(price_payload.get("row_count", len(price_rows))), "Retrieved through API", "neutral"),
            ("Start Date", text(price_payload.get("min_date")), "Stored history begins", "neutral"),
            ("End Date", text(price_payload.get("max_date")), "Latest stored observation", "info"),
        ]
    )

    if price_df.empty:
        st.warning("The API returned price records, but no chartable rows after validation.")
        return

    price_fig = px.line(price_df, x="date", y="price", color="Asset")
    apply_dark_chart_layout(price_fig, title="Stored Market Price History")
    st.plotly_chart(price_fig, use_container_width=True)

    latest_col, momentum_col = st.columns(2)
    with latest_col:
        st.markdown(
            terminal_panel("Latest Price Signals", evidence_panel(_latest_price_rows(price_df)), "Most recent observation by selected series"),
            unsafe_allow_html=True,
        )
    with momentum_col:
        st.markdown(
            terminal_panel("Price Momentum", evidence_panel(_price_momentum_rows(price_df)), "Direction over the selected history window"),
            unsafe_allow_html=True,
        )

    factors_tab, forecast_tab, ledger_tab = st.tabs(["Commodity Factors", "Forecasts", "Price Ledger"])

    with factors_tab:
        render_section_header("Commodity Factor Analysis", "Volatility, correlation, and spread signals from the backend.")
        rolling_window = st.slider("Rolling volatility window", min_value=10, max_value=90, value=30, step=5)
        factors = client.commodity_factors(selected_assets, price_rows, rolling_window=rolling_window)
        if render_api_state(factors, "Commodity factor analysis is unavailable."):
            payload = factors.data or {}
            render_terminal_kpi_strip(
                [
                    ("Model", text(payload.get("model_name")), text(payload.get("model_version")), "info"),
                    ("High Vol Assets", str(len(payload.get("high_volatility_assets") or [])), "Latest rolling volatility flags", "watch"),
                    ("Window", str(rolling_window), "Trading observations", "neutral"),
                ]
            )
            st.markdown(
                _volatility_driver_panel(
                    payload.get("rolling_volatility") or {},
                    payload.get("high_volatility_assets") or [],
                ),
                unsafe_allow_html=True,
            )
            if payload.get("high_volatility_assets"):
                st.markdown(
                    "<div class='warning-callout'><strong>High volatility assets</strong>"
                    f"<p>{escape(', '.join(_asset_label(item) for item in payload['high_volatility_assets']))}</p></div>",
                    unsafe_allow_html=True,
                )
            _correlation_heatmap(payload.get("correlation_matrix") or {})
            spreads = payload.get("spread_analysis") or {}
            if spreads:
                st.markdown(_spread_panel(spreads), unsafe_allow_html=True)
            if payload.get("warnings"):
                st.markdown(bullet_list([str(item) for item in payload["warnings"]], "No factor warnings."), unsafe_allow_html=True)

    with forecast_tab:
        render_section_header("Backend Forecasts", "ARIMA, VAR, and GARCH outputs are estimates generated by the API.")
        model_type = st.selectbox("Forecast model", FORECAST_MODELS, index=0)
        horizon = st.slider("Forecast horizon", min_value=5, max_value=60, value=10, step=5)
        forecast_assets = selected_assets
        if model_type in {"arima", "garch"}:
            forecast_asset = st.selectbox("Forecast asset", selected_assets, index=0, format_func=_asset_label)
            forecast_assets = [forecast_asset]
        elif len(selected_assets) < 2:
            st.warning("VAR requires at least two selected market series.")

        run_forecast = st.button(
            "Run forecast",
            use_container_width=True,
            disabled=model_type == "var" and len(selected_assets) < 2,
        )
        if run_forecast:
            with st.spinner("Running backend forecast model..."):
                forecast = client.market_forecast(model_type, forecast_assets, price_rows, horizon=horizon)
            if render_api_state(forecast, "Forecast could not be generated."):
                payload = forecast.data or {}
                render_terminal_kpi_strip(
                    [
                        ("Model", text(payload.get("model_name")), text(payload.get("model_version")), "info"),
                        ("Horizon", str(payload.get("forecast_horizon", horizon)), "Forecast steps", "neutral"),
                        ("Backtest Error", number(payload.get("backtest_error"), 6), "If available", "watch"),
                        ("Volatility Regime", text(payload.get("volatility_regime")), "GARCH output", "info"),
                    ]
                )
                _forecast_path_chart(payload)
                st.markdown(_forecast_summary(payload, horizon), unsafe_allow_html=True)
                if payload.get("assumptions"):
                    render_technical_json("Model assumptions", payload["assumptions"])
                if payload.get("warnings"):
                    st.markdown(bullet_list([str(item) for item in payload["warnings"]], "No forecast warnings."), unsafe_allow_html=True)

    with ledger_tab:
        render_section_header("Price Ledger", "Analyst-readable price context without exposing raw storage rows.")
        st.markdown(
            terminal_panel(
                "Selected Market Data",
                evidence_panel(
                    [
                        ("Selected series", ", ".join(_asset_label(asset) for asset in selected_assets), "Dashboard request"),
                        ("Observation count", str(price_payload.get("row_count", len(price_rows))), "Backend response"),
                        ("Date range", f"{text(price_payload.get('min_date'))} to {text(price_payload.get('max_date'))}", "Stored market history"),
                        ("Presentation", "Charted signals and latest observations", "No raw database table"),
                    ]
                ),
                "Traceability for the chart and forecast request",
            ),
            unsafe_allow_html=True,
        )

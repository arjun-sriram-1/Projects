"""Scenario forecasts and Monte Carlo page."""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from web.api_client import ApiClient
from web.components.cards import bullet_list, render_section_header
from web.components.charts import apply_dark_chart_layout
from web.components.formatting import money, number, pct, text
from web.components.layout import render_api_state, render_technical_json
from web.components.terminal import (
    action_grid,
    evidence_panel,
    render_terminal_kpi_strip,
    terminal_panel,
)


SCENARIO_TYPES = ["baseline", "adverse", "severe"]
COPULA_TYPES = ["gaussian", "t_copula"]
HEDGE_TYPES = ["futures", "swap", "option", "collar", "fixed_price_contract"]
SCENARIO_LABELS = {
    "baseline": "Baseline",
    "adverse": "Adverse",
    "severe": "Severe",
    "t_copula": "t-Copula",
    "gaussian": "Gaussian",
    "fixed_price_contract": "Fixed price contract",
}


def _clean_label(value: Any) -> str:
    return SCENARIO_LABELS.get(str(value), str(value).replace("_", " ").title())


def _metric_rows(payload: dict) -> list[tuple[str, str, str, str]]:
    return [
        ("Expected Loss", money(payload.get("expected_loss")), "Mean simulated loss", "watch"),
        (
            "VaR 95 / 99",
            f"{money(payload.get('credit_var_95') or payload.get('var_95'))} / {money(payload.get('credit_var_99') or payload.get('var_99'))}",
            "Tail loss thresholds",
            "risk",
        ),
        (
            "ES 95 / 99",
            f"{money(payload.get('expected_shortfall_95'))} / {money(payload.get('expected_shortfall_99'))}",
            "Tail conditional loss",
            "risk",
        ),
        ("Copula", _clean_label(text(payload.get("copula_type"))), text(payload.get("tail_dependence_note")), "info"),
    ]


def _scenario_cards(scenarios: list[dict]) -> str:
    if not scenarios:
        return action_grid([("No scenarios returned", "Build data-driven market shocks in the backend before reviewing scenario forecasts.")])
    cards = []
    for item in scenarios:
        shocks = item.get("market_shocks") or {}
        shock_summary = ", ".join(f"{_clean_label(key)} {number(value, 3)}" for key, value in list(shocks.items())[:3])
        cards.append(
            "<div class='terminal-action-card'>"
            f"<strong>{escape(text(item.get('scenario_name'), 'Scenario'))}</strong>"
            f"<span>{escape(_clean_label(text(item.get('scenario_type'))))} | {escape(text(item.get('market_regime')))}</span>"
            f"<span>{escape(shock_summary or 'Shock details unavailable')}</span>"
            "</div>"
        )
    return f"<div class='terminal-action-grid'>{''.join(cards)}</div>"


def _scenario_detail_panel(detail: dict) -> str:
    rows = [
        ("Scenario", text(detail.get("scenario_name")), "Backend scenario library"),
        ("Type", _clean_label(text(detail.get("scenario_type"))), "Scenario class"),
        ("Quantile", number(detail.get("scenario_quantile"), 3), "Historical selection"),
        ("Regime", text(detail.get("market_regime")), "Market context"),
        ("Source range", f"{text(detail.get('source_start_date'))} to {text(detail.get('source_end_date'))}", "Market history"),
        ("Observations", text(detail.get("source_observations")), "Source sample"),
    ]
    shocks = detail.get("market_shocks") or {}
    shock_rows = [(_clean_label(key), number(value, 3), "Market shock") for key, value in shocks.items()]
    return terminal_panel("Scenario Detail", evidence_panel(rows + shock_rows), "Selected stress path and market movements")


def _distribution_panel(distribution: dict) -> str:
    if not distribution:
        return terminal_panel(
            "Loss Distribution Summary",
            action_grid([("No distribution returned", "Store or run a Monte Carlo simulation to inspect distribution diagnostics.")]),
            "Awaiting simulation diagnostics",
        )
    rows = [(str(key).replace("_", " ").title(), number(value, 4), "Simulation diagnostic") for key, value in distribution.items()]
    return terminal_panel("Loss Distribution Summary", evidence_panel(rows), "Backend diagnostics for the simulated loss distribution")


def _marginal_contribution_chart(marginal: dict) -> None:
    if not marginal:
        return
    marginal_df = pd.DataFrame(
        [{"Counterparty": str(key), "Contribution": value} for key, value in marginal.items()]
    ).sort_values("Contribution", ascending=True)
    fig = px.bar(marginal_df, x="Contribution", y="Counterparty", orientation="h")
    apply_dark_chart_layout(fig, title="Marginal Risk Contribution")
    st.plotly_chart(fig, use_container_width=True)


def _hedge_metric_panel(payload: dict) -> str:
    rows = [
        ("Unhedged exposure", money(payload.get("unhedged_exposure")), "Before hedge"),
        ("Hedge benefit", money(payload.get("hedge_benefit")), "Modeled reduction"),
        ("Hedged exposure", money(payload.get("hedged_exposure")), "After hedge"),
        ("EL reduction", money(payload.get("expected_loss_reduction")), "Expected loss impact"),
    ]
    return terminal_panel("Hedge Impact", evidence_panel(rows), "Backend hedge sensitivity result")


def _before_after_panel(metrics: dict) -> str:
    rows = []
    for key, value in metrics.items():
        label = str(key).replace("_", " ").title()
        display = pct(value) if "ratio" in str(key) or "rate" in str(key) else number(value, 4)
        rows.append((label, display, "Current sensitivity run"))
    return terminal_panel("Before / After Metrics", evidence_panel(rows), "Hedge impact explanation")


def _latest_data_panel(payload: dict) -> str:
    reference = payload.get("input_data_reference") or {}
    assumptions = payload.get("assumptions_reference") or {}
    rows = [
        ("Simulation data", text(reference.get("data_used") or reference.get("source") or "Latest backend simulation inputs"), "Model input"),
        ("Date range", text(reference.get("date_range") or reference.get("as_of_date") or "Latest stored run"), "Input lineage"),
        ("Assumptions stored", text(assumptions.get("created_at") or payload.get("created_at") or "Latest stored run"), "Model review"),
        ("Traceability", "Technical details available below", "Audit trail"),
    ]
    return terminal_panel("Latest Simulation Data Used", evidence_panel(rows), "Analyst-readable references for the latest stored simulation")


def render(client: ApiClient, context: dict) -> None:
    counterparty_id = int(context["counterparty_id"])
    st.subheader("Scenario & Forecasts")
    st.caption("Question answered: how does the facility behave under stressed market paths and tail loss simulations?")

    latest = client.latest_monte_carlo()
    if latest.ok and latest.data:
        render_terminal_kpi_strip(_metric_rows(latest.data))
    else:
        render_api_state(latest, "No stored Monte Carlo simulation found yet.")

    scenarios_tab, monte_carlo_tab, hedge_tab, data_tab = st.tabs(
        [
            "Scenarios",
            "Monte Carlo",
            "Hedging Sensitivity",
            "Data Used",
        ]
    )

    with scenarios_tab:
        render_section_header("Scenario Matrix", "Data-driven market shock scenarios available from the backend.")
        regime_filter = st.text_input("Optional regime filter", value="")
        scenarios = client.scenario_list(target_regime=regime_filter.strip() or None)
        if render_api_state(scenarios, "No data-driven scenarios available."):
            scenario_rows = scenarios.data.get("scenarios") or []
            st.markdown(
                terminal_panel("Scenario Library", _scenario_cards(scenario_rows), "Available forecast paths"),
                unsafe_allow_html=True,
            )
            if scenario_rows:
                selected = st.selectbox("Scenario detail", [text(item.get("scenario_name"), "Scenario") for item in scenario_rows])
                detail = next((item for item in scenario_rows if text(item.get("scenario_name"), "Scenario") == selected), None)
                if detail:
                    st.markdown(_scenario_detail_panel(detail), unsafe_allow_html=True)
                    render_technical_json("Market shocks", detail.get("market_shocks") or {})
                    render_technical_json("Model assumptions", detail.get("assumptions") or {})

    with monte_carlo_tab:
        render_section_header("Run Backend Simulation", "Configure tail-risk simulation without triggering heavy work on page load.")
        st.markdown("<div class='simulation-control-strip'>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            scenario_type = st.selectbox("Scenario type", SCENARIO_TYPES, index=1, format_func=_clean_label)
            simulations = st.number_input("Simulations", min_value=100, max_value=100000, value=5000, step=500)
        with col_b:
            copula_type = st.selectbox("Copula type", COPULA_TYPES, index=0, format_func=_clean_label)
            degrees = st.number_input("t-Copula degrees of freedom", min_value=3, max_value=100, value=5, step=1)
        with col_c:
            seed = st.number_input("Random seed", min_value=1, max_value=999999, value=42, step=1)
            include_context = st.checkbox("Use selected counterparty only", value=True)
        persist = st.checkbox("Store simulation result", value=True)
        st.markdown("</div>", unsafe_allow_html=True)
        if copula_type == "t_copula":
            st.markdown(
                "<div class='warning-callout'><strong>t-Copula tail dependence</strong>"
                "<p>This run asks the backend to model heavier joint tail behavior using the selected degrees of freedom.</p></div>",
                unsafe_allow_html=True,
            )
        if st.button("Run Monte Carlo", use_container_width=True):
            payload = {
                "scenario_type": scenario_type,
                "counterparty_ids": [counterparty_id] if include_context else None,
                "n_simulations": int(simulations),
                "random_seed": int(seed),
                "persist": persist,
                "copula_type": copula_type,
                "degrees_of_freedom": int(degrees),
            }
            with st.spinner("Running backend Monte Carlo simulation..."):
                result = client.run_monte_carlo(payload)
            if render_api_state(result, "Monte Carlo run returned no result."):
                st.success("Backend Monte Carlo simulation completed.")
                render_terminal_kpi_strip(_metric_rows(result.data))
                st.markdown(_distribution_panel(result.data.get("loss_distribution_summary") or {}), unsafe_allow_html=True)
                _marginal_contribution_chart(result.data.get("marginal_risk_contribution") or {})
                render_technical_json("Simulation result", result.data)

        if latest.ok and latest.data:
            st.markdown(_distribution_panel(latest.data.get("loss_distribution_summary") or {}), unsafe_allow_html=True)
            render_technical_json("Latest stored simulation details", latest.data)

    with hedge_tab:
        render_section_header("Hedge Sensitivity", "Estimate exposure and expected-loss impact using the backend hedging module.")
        latest_pd = client.latest_pd(counterparty_id)
        latest_loss = client.latest_loss(counterparty_id)
        default_pd = float((latest_pd.data or {}).get("final_pd") or (latest_loss.data or {}).get("probability_of_default") or 0.05)
        default_lgd = float((latest_loss.data or {}).get("predicted_lgd") or 0.45)
        default_exposure = float((latest_loss.data or {}).get("exposure_at_default") or 1_000_000.0)

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            exposure = st.number_input("Exposure", min_value=0.0, value=default_exposure, step=50_000.0)
            probability = st.slider("Probability of default", min_value=0.0, max_value=1.0, value=min(max(default_pd, 0.0), 1.0), step=0.01)
            lgd = st.slider("Loss given default", min_value=0.0, max_value=1.0, value=min(max(default_lgd, 0.0), 1.0), step=0.01)
        with col_b:
            hedge_type = st.selectbox("Hedge type", HEDGE_TYPES, index=0, format_func=_clean_label)
            hedge_notional = st.number_input("Hedge notional", min_value=0.0, value=exposure * 0.50, step=25_000.0)
            hedge_ratio = st.slider("Hedge ratio", min_value=0.0, max_value=1.0, value=0.50, step=0.05)
        with col_c:
            market_move = st.slider("Scenario market move", min_value=-1.0, max_value=1.0, value=-0.10, step=0.01)
            hedge_direction = st.selectbox("Hedge direction", ["long", "short"], index=0, format_func=_clean_label)
            reference_price = st.number_input("Reference price", min_value=0.0, value=100.0, step=1.0)

        if st.button("Calculate Hedge Sensitivity", use_container_width=True):
            payload = {
                "counterparty_id": counterparty_id,
                "exposure": exposure,
                "probability_of_default": probability,
                "loss_given_default": lgd,
                "hedge_type": hedge_type,
                "hedge_notional": hedge_notional,
                "hedge_ratio": hedge_ratio,
                "scenario_market_move": market_move,
                "reference_price": reference_price,
                "hedge_direction": hedge_direction,
            }
            result = client.hedge_sensitivity(payload)
            if render_api_state(result, "Hedge sensitivity returned no result."):
                payload = result.data
                st.markdown(_hedge_metric_panel(payload), unsafe_allow_html=True)
                before_after = payload.get("before_after_metrics") or {}
                if before_after:
                    st.markdown(_before_after_panel(before_after), unsafe_allow_html=True)
                    render_technical_json("Before / after metrics", before_after)
                if payload.get("warnings"):
                    st.markdown(bullet_list([str(item) for item in payload["warnings"]], "No hedge warnings."), unsafe_allow_html=True)

    with data_tab:
        render_section_header("Latest Simulation Data Used", "Analyst-readable references for the latest stored simulation.")
        if latest.ok and latest.data:
            st.markdown(_latest_data_panel(latest.data), unsafe_allow_html=True)
            render_technical_json("Input references", latest.data.get("input_data_reference") or {})
            render_technical_json("Assumptions reference", latest.data.get("assumptions_reference") or {})
        else:
            st.markdown(
                terminal_panel(
                    "Simulation Data Needed",
                    action_grid([("Run or store Monte Carlo", "Populate this view with model inputs, assumptions, and traceability references.")]),
                    "No stored simulation is available",
                ),
                unsafe_allow_html=True,
            )

"""Executive overview page."""

from __future__ import annotations

from html import escape

import streamlit as st

from web.api_client import ApiClient
from web.components.cards import bullet_list, data_summary_card, decision_panel, render_data_summary_grid
from web.components.formatting import money, number, pct, text
from web.components.kpi import badge, render_kpi_grid, status_kind


def _friendly_components(components) -> str:
    if not components:
        return "Latest available market stress inputs"
    names = {
        "oil_volatility_zscore": "oil volatility",
        "brent_return_zscore": "Brent return pressure",
        "heating_oil_return_zscore": "heating oil returns",
        "jet_fuel_return_zscore": "jet fuel proxy returns",
        "vix_zscore": "equity volatility",
        "sp500_return_zscore": "S&P 500 returns",
        "yield_spread_zscore": "yield spread",
        "credit_spread_zscore": "credit spread",
    }
    friendly = [names.get(str(component), str(component).replace("_", " ")) for component in components[:5]]
    suffix = " and related factors" if len(components) > 5 else ""
    return ", ".join(friendly) + suffix


def _first_sentence(value: str | None, fallback: str) -> str:
    clean = text(value, fallback)
    parts = clean.split(".")
    return parts[0].strip() + "." if len(parts) > 1 and parts[0].strip() else clean


def _date_only(value) -> str:
    raw = text(value)
    if raw == "-":
        return raw
    return raw.split("T")[0]


def _alert_cards(alerts: list[dict]) -> str:
    if not alerts:
        return """
        <div class="alert-card alert-card-ok">
          <div class="alert-title">No active alerts</div>
          <div class="alert-meta">The latest monitoring API returned no open early-warning alerts.</div>
        </div>
        """
    cards = []
    for alert in alerts[:5]:
        kind = status_kind(alert.get("severity"))
        cards.append(
            f"""
            <div class="alert-card alert-card-{escape(kind)}">
              <div class="alert-title">{escape(text(alert.get('category'), 'Monitoring alert'))}</div>
              <div class="data-summary-copy">{escape(text(alert.get('alert_reason'), 'No reason returned.'))}</div>
              <div class="alert-meta">Metric: {escape(text(alert.get('triggering_metric')))} | Value: {escape(number(alert.get('triggering_value'), 4))} | Source: {escape(text(alert.get('data_source')))}</div>
            </div>
            """
        )
    return "".join(cards)


def _posture_panel(decision_data: dict, pd_data: dict, loss_data: dict, stress_data: dict, simulation_data: dict) -> str:
    rows = [
        ("Policy score", number(decision_data.get("policy_score"), 2)),
        ("Limit haircut", pct(decision_data.get("limit_haircut"))),
        ("PD divergence", pct(pd_data.get("pd_divergence"))),
        ("Stress level", text(stress_data.get("stress_level"))),
        ("Credit VaR 95", money(decision_data.get("credit_var_95") or simulation_data.get("var_95"))),
        ("ES 95", money(decision_data.get("expected_shortfall_95") or simulation_data.get("expected_shortfall_95"))),
    ]
    items = "".join(
        f"""
        <div class="posture-item">
          <div class="posture-label">{escape(label)}</div>
          <div class="posture-value">{escape(value)}</div>
        </div>
        """
        for label, value in rows
    )
    return f"<div class='posture-grid'>{items}</div>"


def render(client: ApiClient, context: dict) -> None:
    counterparty_id = int(context["counterparty_id"])
    st.subheader("Executive Overview")

    alerts = client.latest_alerts()
    stress = client.latest_market_stress()
    regime = client.latest_market_regime()
    pd_result = client.latest_pd(counterparty_id)
    loss_result = client.latest_loss(counterparty_id)
    decision = client.latest_recommendation(counterparty_id)
    simulation = client.latest_monte_carlo()

    alert_data = alerts.data or {}
    stress_data = stress.data or {}
    regime_data = regime.data or {}
    pd_data = pd_result.data or {}
    loss_data = loss_result.data or {}
    decision_data = decision.data or {}
    simulation_data = simulation.data or {}

    decision_status = text(
        decision_data.get("approval_status") or decision_data.get("decision"),
        "No decision yet",
    )
    decision_help = _first_sentence(
        decision_data.get("recommendation_summary") or decision_data.get("risk_grade"),
        "Refresh the Credit Decision page after required backend outputs are available.",
    )

    render_kpi_grid([
        ("Credit Decision", decision_status, decision_help),
        ("Final PD", pct(pd_data.get("final_pd")), text(pd_data.get("classification_label"), "Latest model output")),
        ("Expected Loss", money(loss_data.get("expected_loss")), f"LGD {pct(loss_data.get('predicted_lgd'))}"),
        ("Market Stress", number(stress_data.get("stress_index"), 2), text(stress_data.get("stress_level"), "Latest stress index")),
        ("Regime", text(regime_data.get("regime_label")), f"Confidence {number(regime_data.get('regime_probability'), 3)}"),
        ("Alerts", str(alert_data.get("alert_count", 0)), f"{alert_data.get('high_count', 0)} high severity"),
        ("Portfolio VaR 99", money(simulation_data.get("var_99") or simulation_data.get("credit_var_99")), "Latest stored simulation"),
        ("Expected Shortfall 99", money(simulation_data.get("expected_shortfall_99")), "Latest stored simulation"),
    ])

    if not decision.ok or not decision_data:
        st.markdown(
            """
            <div class="next-action-strip">
              No formal credit decision is stored for this counterparty yet. Review PD/LGD/EAD and scenario outputs, then refresh the recommendation from the Credit Decision page.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if decision.ok and decision_data:
        snapshot = decision_panel(
            [
                ("Risk grade", text(decision_data.get("risk_grade"))),
                ("Recommended limit", money(decision_data.get("recommended_credit_limit"))),
                ("Recommended tenor", f"{text(decision_data.get('recommended_tenor_days'))} days"),
                ("Security", text(decision_data.get("recommended_security"))),
            ],
            summary=decision_help,
            status_kind=status_kind(decision_status),
        )
        drivers = bullet_list(decision_data.get("key_risk_drivers") or [], "No risk drivers returned.")
        mitigants = bullet_list(decision_data.get("mitigating_factors") or [], "No mitigating factors returned.")
    else:
        snapshot = decision_panel(
            [("Status", "No stored credit decision yet")],
            summary="Use the Credit Decision page to refresh the formal recommendation after required backend outputs are available.",
            status_kind="neutral",
        )
        drivers = bullet_list([], "No decision drivers available yet.")
        mitigants = bullet_list([], "No mitigating factors available yet.")

    st.markdown(
        f"""
        <div class="executive-split">
          <div class="executive-panel">
            <div class="executive-panel-title">Decision Snapshot</div>
            {badge(decision_status, status_kind(decision_status))}
            {snapshot}
            <div class="executive-panel-title" style="margin-top:.85rem;">Key Risk Drivers</div>
            {drivers}
            <div class="executive-panel-title" style="margin-top:.85rem;">Mitigating Factors</div>
            {mitigants}
          </div>
          <div class="executive-panel">
            <div class="executive-panel-title">Risk Posture</div>
            {_posture_panel(decision_data, pd_data, loss_data, stress_data, simulation_data)}
            <div class="executive-panel-title" style="margin-top:.9rem;">Active Alerts</div>
            {_alert_cards(alert_data.get('alerts') or [])}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Data Used")
    st.caption("Analyst summary of the data behind this page. Technical table names are intentionally hidden.")
    render_data_summary_grid([
        data_summary_card(
            "Market context",
            _friendly_components(stress_data.get("available_components") or []),
            text(stress_data.get("date"), "Latest available"),
            "Stress level and regime context",
        ),
        data_summary_card(
            "Credit model inputs",
            "Extracted financial metrics, ratios, market stress, and model feature contributions",
            _date_only(pd_data.get("created_at")),
            "Final PD and risk classification",
        ),
        data_summary_card(
            "Exposure and collateral inputs",
            "Trade exposure, collateral/security, tenor, utilization, LGD and EAD estimates",
            _date_only(loss_data.get("created_at")),
            "Expected loss and loss severity",
        ),
        data_summary_card(
            "Tail-risk simulation",
            f"{text(simulation_data.get('scenario'), 'Latest')} simulation with {text(simulation_data.get('number_of_simulations'), 'stored')} runs",
            _date_only(simulation_data.get("created_at")),
            "VaR, Expected Shortfall, and portfolio tail pressure",
        ),
    ])

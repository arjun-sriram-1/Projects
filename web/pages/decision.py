"""Credit recommendation page."""

from __future__ import annotations

from typing import Any

import streamlit as st

from web.api_client import ApiClient
from web.components.cards import bullet_list, render_section_header
from web.components.formatting import money, number, pct, text
from web.components.kpi import status_kind
from web.components.layout import render_technical_json
from web.components.terminal import (
    action_grid,
    decision_card,
    evidence_panel,
    render_terminal_kpi_strip,
    risk_driver_panel,
    terminal_panel,
)


def _date_only(value: Any) -> str:
    raw = text(value)
    return raw if raw == "-" else raw.split("T")[0]


def _clean_label(value: Any) -> str:
    return str(value).replace("_", " ").title()


def _decision_kind(value: Any) -> str:
    return status_kind(text(value))


def _required_outputs(pd_data: dict | None, loss: dict | None, ratios: dict | None) -> str:
    actions = [
        ("Latest PD", "Available from Quant & Monte Carlo" if pd_data else "Run or refresh probability of default."),
        ("Latest loss estimate", "Available from Quant & Monte Carlo" if loss else "Run LGD / EAD / expected loss."),
        ("Financial ratios", "Available from Financial Statements" if ratios else "Calculate ratios from accepted financials."),
        ("Credit recommendation", "Refresh this page once inputs are ready."),
    ]
    return terminal_panel("Required Backend Outputs", action_grid(actions), "The dashboard does not invent missing credit decisions")


def _recommendation_card(recommendation: dict, approval_status: str) -> str:
    rows = [
        ("Risk grade", text(recommendation.get("risk_grade"))),
        ("Recommended limit", money(recommendation.get("recommended_credit_limit"))),
        ("Recommended tenor", f"{text(recommendation.get('recommended_tenor_days'))} days"),
        ("Required security", text(recommendation.get("recommended_security"))),
        ("Expected loss", money(recommendation.get("expected_loss"))),
        ("Policy score", number(recommendation.get("policy_score"), 2)),
    ]
    rationale = (
        f"Backend recommends {approval_status} with "
        f"{money(recommendation.get('recommended_credit_limit'))}, "
        f"{text(recommendation.get('recommended_tenor_days'))} day tenor, and "
        f"{text(recommendation.get('recommended_security'))}."
    )
    return decision_card(approval_status, rows, rationale, _decision_kind(approval_status))


def _terms_panel(recommendation: dict, context: dict) -> str:
    requested_limit = float(context.get("requested_limit") or 0)
    recommended_limit = recommendation.get("recommended_credit_limit")
    rows = [
        ("Requested limit", money(requested_limit), "Header context"),
        ("Recommended limit", money(recommended_limit), "Backend recommendation"),
        ("Limit haircut", pct(recommendation.get("limit_haircut")), "Policy adjustment"),
        ("Recommended tenor", f"{text(recommendation.get('recommended_tenor_days'))} days", "Payment terms"),
        ("Required security", text(recommendation.get("recommended_security")), "Collateral / security condition"),
        ("Approval expiry", _date_only(recommendation.get("approval_expiry_date")), "If returned by backend"),
    ]
    return terminal_panel("Recommended Terms", evidence_panel(rows), "Credit facility terms for approval routing")


def _drivers_panel(recommendation: dict) -> str:
    drivers = recommendation.get("key_risk_drivers") or []
    mitigants = recommendation.get("mitigating_factors") or []
    body = (
        "<div class='terminal-panel-subtitle'>Key Risk Drivers</div>"
        + bullet_list([str(item) for item in drivers], "No key risk drivers returned by the backend.")
        + "<div class='terminal-panel-subtitle'>Mitigating Factors</div>"
        + bullet_list([str(item) for item in mitigants], "No mitigating factors returned by the backend.")
    )
    return terminal_panel("Decision Explanation", body, "Backend rationale for the recommended mandate")


def _model_inputs_panel(recommendation: dict, pd_data: dict | None, loss: dict | None) -> str:
    rows = [
        ("Final PD", pct(recommendation.get("probability_of_default")), text((pd_data or {}).get("classification_label"), "Decision input")),
        ("LGD", pct(recommendation.get("loss_given_default")), "Loss severity"),
        ("EAD", money(recommendation.get("exposure_at_default")), "Exposure at default"),
        ("Scenario EL", money(recommendation.get("scenario_expected_loss")), "Scenario input"),
        ("Credit VaR 95", money(recommendation.get("credit_var_95")), "Tail risk"),
        ("ES 95", money(recommendation.get("expected_shortfall_95")), "Tail loss"),
        ("Stored loss EL", money((loss or {}).get("expected_loss")), "Latest loss estimate"),
    ]
    return terminal_panel("Model Inputs", evidence_panel(rows), "Quant outputs feeding the final decision")


def _ratio_panel(ratios: dict | None) -> str:
    payload = ratios or {}
    rows = [
        ("Current ratio", number(payload.get("current_ratio"), 4), "Liquidity"),
        ("Quick ratio", number(payload.get("quick_ratio"), 4), "Liquidity"),
        ("Debt / EBITDA", number(payload.get("debt_to_ebitda"), 4), "Leverage"),
        ("Debt / equity", number(payload.get("debt_to_equity"), 4), "Leverage"),
        ("Interest coverage", number(payload.get("interest_coverage"), 4), "Coverage"),
        ("Operating margin", pct(payload.get("operating_margin")), "Profitability"),
    ]
    return terminal_panel("Financial Ratio Context", evidence_panel(rows), "Latest accepted ratios used by policy review")


def _policy_driver_panel(recommendation: dict) -> str:
    drivers = [
        ("Probability of default", _score(recommendation.get("probability_of_default")), "risk"),
        ("Loss given default", _score(recommendation.get("loss_given_default")), "risk"),
        ("Limit haircut", _score(recommendation.get("limit_haircut")), "watch"),
        ("Policy score", _policy_score(recommendation.get("policy_score")), "info"),
    ]
    return terminal_panel("Policy Driver Index", risk_driver_panel(drivers), "Relative pressure behind the mandate")


def _lineage_panel(recommendation: dict, pd_data: dict | None, loss: dict | None, ratios: dict | None) -> str:
    rows = [
        ("Financial statement / ratios", text((ratios or {}).get("fiscal_year"), "Latest available"), "Financial Statements"),
        ("PD model output", f"Final PD {pct((pd_data or {}).get('final_pd'))}", _date_only((pd_data or {}).get("created_at"))),
        ("LGD / EAD / expected loss", f"LGD {pct((loss or {}).get('predicted_lgd'))}; EAD {money((loss or {}).get('exposure_at_default'))}", _date_only((loss or {}).get("created_at"))),
        ("Credit recommendation", f"{text(recommendation.get('approval_status'))}; security {text(recommendation.get('recommended_security'))}", _date_only(recommendation.get("created_at"))),
    ]
    return terminal_panel("Decision Data Lineage", evidence_panel(rows), "Analyst-readable source trail for the recommendation")


def _score(value: Any) -> float:
    try:
        numeric = abs(float(value))
    except (TypeError, ValueError):
        return 0.0
    return numeric * 100 if numeric <= 1 else numeric


def _policy_score(value: Any) -> float:
    try:
        numeric = abs(float(value))
    except (TypeError, ValueError):
        return 0.0
    return min(numeric, 100.0)


def render(client: ApiClient, context: dict) -> None:
    counterparty_id = int(context["counterparty_id"])
    st.subheader("Credit Recommendation")
    st.caption("Question answered: what limit, tenor, and security should be approved for this counterparty?")

    top_cols = st.columns([1, 2])
    with top_cols[0]:
        if st.button("Refresh Recommendation", use_container_width=True):
            with st.spinner("Calling credit decision API..."):
                refresh = client.calculate_recommendation(counterparty_id)
            if refresh.ok:
                st.success("Recommendation refreshed from backend output.")
            else:
                st.error(f"Could not refresh recommendation: {refresh.error}")
    with top_cols[1]:
        st.caption("Backend output only. No UI formulas or manual credit decision overrides are applied.")

    recommendation_result = client.latest_recommendation(counterparty_id)
    pd_result = client.latest_pd(counterparty_id)
    loss_result = client.latest_loss(counterparty_id)
    ratios_result = client.latest_ratios(counterparty_id)

    recommendation = recommendation_result.data if recommendation_result.ok else None
    pd_data = pd_result.data if pd_result.ok else None
    loss = loss_result.data if loss_result.ok else None
    ratios = ratios_result.data if ratios_result.ok else None

    if not recommendation:
        st.warning("No stored credit recommendation found for this counterparty.")
        st.markdown(_required_outputs(pd_data, loss, ratios), unsafe_allow_html=True)
        return

    approval_status = text(recommendation.get("approval_status"))
    render_terminal_kpi_strip(
        [
            ("Approval Status", approval_status, "Formal backend decision", _decision_kind(approval_status)),
            ("Risk Grade", text(recommendation.get("risk_grade")), "Internal proxy grade", _decision_kind(approval_status)),
            ("Recommended Limit", money(recommendation.get("recommended_credit_limit")), "Backend recommendation", "info"),
            ("Recommended Tenor", f"{text(recommendation.get('recommended_tenor_days'))} days", "Payment terms", "neutral"),
            ("Required Security", _clean_label(text(recommendation.get("recommended_security"))), "Collateral / security", "watch"),
            ("Expected Loss", money(recommendation.get("expected_loss")), "Stored decision input", "risk"),
        ]
    )

    left_col, right_col = st.columns([0.95, 1.05])
    with left_col:
        st.markdown(_recommendation_card(recommendation, approval_status), unsafe_allow_html=True)
    with right_col:
        st.markdown(_terms_panel(recommendation, context), unsafe_allow_html=True)

    explain_col, driver_col = st.columns([1.05, 0.95])
    with explain_col:
        st.markdown(_drivers_panel(recommendation), unsafe_allow_html=True)
    with driver_col:
        st.markdown(_policy_driver_panel(recommendation), unsafe_allow_html=True)

    inputs_tab, data_tab, technical_tab = st.tabs(["Model Inputs", "Data Used", "Technical Details"])
    with inputs_tab:
        input_col, ratio_col = st.columns(2)
        with input_col:
            st.markdown(_model_inputs_panel(recommendation, pd_data, loss), unsafe_allow_html=True)
        with ratio_col:
            st.markdown(_ratio_panel(ratios), unsafe_allow_html=True)

    with data_tab:
        render_section_header("Data Used", "Clean lineage for the backend recommendation without exposing database table details.")
        st.markdown(_lineage_panel(recommendation, pd_data, loss, ratios), unsafe_allow_html=True)
        assumptions = recommendation.get("model_assumptions") or {}
        if assumptions:
            assumption_rows = [(_clean_label(key), text(value), "Decision assumption") for key, value in assumptions.items()]
            st.markdown(
                terminal_panel("Decision Assumptions", evidence_panel(assumption_rows), "Stored with backend recommendation"),
                unsafe_allow_html=True,
            )

    with technical_tab:
        render_technical_json(
            "Technical details",
            {
                "recommendation": recommendation,
                "pd": pd_data,
                "loss": loss,
                "ratios": ratios,
            },
        )

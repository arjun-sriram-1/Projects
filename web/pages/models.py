"""Quant model execution page."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from web.api_client import ApiClient, ApiResult
from web.components.cards import bullet_list, render_section_header
from web.components.charts import apply_dark_chart_layout
from web.components.formatting import money, number, pct, text
from web.components.layout import render_api_state, render_technical_json
from web.components.terminal import (
    action_grid,
    evidence_panel,
    render_terminal_kpi_strip,
    risk_driver_panel,
    terminal_panel,
    terminal_status_badge,
)


COLLATERAL_TYPES = ["unsecured", "letter_of_credit", "guarantee", "cash_deposit", "secured"]
MODEL_FIELDS = [
    ("Structural PD", "structural_pd", pct, "Structural model"),
    ("ML PD", "ml_pd", pct, "Machine-learning model"),
    ("Final PD", "final_pd", pct, "Policy blend"),
    ("Model confidence", "model_confidence", pct, "Backend score"),
    ("PD divergence", "pd_divergence", pct, "Model agreement"),
    ("Distance to default", "distance_to_default", lambda value: number(value, 4), "Structural input"),
    ("Market stress index", "market_stress_index", lambda value: number(value, 2), "Market overlay"),
]
LOSS_FIELDS = [
    ("Probability of default", "probability_of_default", pct, "PD input"),
    ("Predicted LGD", "predicted_lgd", pct, "Loss severity"),
    ("Exposure at default", "exposure_at_default", money, "Exposure engine"),
    ("Expected loss", "expected_loss", money, "PD x LGD x EAD"),
    ("Collateral strength", "collateral_strength", lambda value: number(value, 3), "Recovery input"),
    ("Liquidity score", "liquidity_score", lambda value: number(value, 3), "Repayment input"),
]


def _clean_label(value: Any) -> str:
    return str(value).replace("_", " ").title()


def _latest_metrics_id(client: ApiClient, counterparty_id: int) -> int | None:
    documents = client.counterparty_documents(counterparty_id)
    if not documents.ok or not documents.data:
        return None
    ordered = sorted(documents.data, key=lambda row: row.get("uploaded_at") or "", reverse=True)
    for document in ordered:
        status = client.document_status(int(document["id"]))
        metrics = (status.data or {}).get("financial_metrics") if status.ok else None
        if metrics and metrics.get("id"):
            return int(metrics["id"])
    return None


def _show_warning(result: ApiResult, label: str) -> None:
    if not result.ok:
        st.warning(f"{label}: {result.error}")


def _pd_kind(payload: dict) -> str:
    try:
        final_pd = float(payload.get("final_pd") or 0)
    except (TypeError, ValueError):
        final_pd = 0
    if final_pd >= 0.15:
        return "risk"
    if final_pd >= 0.08:
        return "watch"
    return "ok"


def _model_agreement_panel(payload: dict) -> str:
    structural = payload.get("structural_pd")
    ml = payload.get("ml_pd")
    final_pd = payload.get("final_pd")
    divergence = payload.get("pd_divergence")
    rows = [
        ("Structural PD", pct(structural), "Merton / structural estimate"),
        ("ML PD", pct(ml), "Feature-based estimate"),
        ("Final PD", pct(final_pd), "Downstream credit input"),
        ("Model divergence", pct(divergence), "Agreement check"),
    ]
    return terminal_panel("PD Model Agreement", evidence_panel(rows), "Structural and machine-learning model comparison")


def _model_detail_panel(payload: dict) -> str:
    rows = [(label, formatter(payload.get(field)), source) for label, field, formatter, source in MODEL_FIELDS]
    return terminal_panel("PD Model Diagnostics", evidence_panel(rows), "Stored backend prediction details")


def _loss_panel(payload: dict) -> str:
    rows = [(label, formatter(payload.get(field)), source) for label, field, formatter, source in LOSS_FIELDS]
    return terminal_panel("LGD / EAD / Expected Loss", evidence_panel(rows), "Latest stored backend loss estimate")


def _risk_driver_panel(pd_payload: dict, loss_payload: dict) -> str:
    drivers = [
        ("Final PD", _as_percent_score(pd_payload.get("final_pd")), "risk" if _as_percent_score(pd_payload.get("final_pd")) >= 8 else "watch"),
        ("PD divergence", _as_percent_score(pd_payload.get("pd_divergence")), "watch"),
        ("Predicted LGD", _as_percent_score(loss_payload.get("predicted_lgd")), "risk" if _as_percent_score(loss_payload.get("predicted_lgd")) >= 50 else "watch"),
        ("Utilization", _as_percent_score(loss_payload.get("utilization_rate")), "info"),
        ("Liquidity score", _as_percent_score(loss_payload.get("liquidity_score")), "info"),
    ]
    return terminal_panel("Quant Risk Drivers", risk_driver_panel(drivers), "Relative model signals used in credit sizing")


def _as_percent_score(value: Any) -> float:
    try:
        numeric = abs(float(value))
    except (TypeError, ValueError):
        return 0.0
    return numeric * 100 if numeric <= 1 else numeric


def _render_feature_contributions(contributions: dict) -> None:
    if not contributions:
        st.markdown(
            terminal_panel(
                "Feature Contributions",
                action_grid([("No contribution data", "The backend model did not return directional feature drivers for this run.")]),
                "Directional PD drivers",
            ),
            unsafe_allow_html=True,
        )
        return
    feature_df = pd.DataFrame(
        [{"Feature": _clean_label(key), "Contribution": value} for key, value in contributions.items()]
    ).sort_values("Contribution", key=lambda series: series.abs(), ascending=True)
    fig = px.bar(
        feature_df,
        x="Contribution",
        y="Feature",
        orientation="h",
        color="Contribution",
        color_continuous_scale=["#EF4444", "#8994A5", "#00E096"],
    )
    fig.update_layout(coloraxis_showscale=False, height=max(280, 42 * len(feature_df)))
    apply_dark_chart_layout(fig, title="PD Feature Contributions")
    st.plotly_chart(fig, use_container_width=True)


def _lineage_panel(payload: dict, title: str) -> str:
    reference = payload.get("input_data_reference") or {}
    assumptions = payload.get("model_assumptions") or {}
    rows = [
        ("Source", text(reference.get("source") or reference.get("data_source") or "Backend model input"), "Input reference"),
        ("Period", text(reference.get("date_range") or reference.get("as_of_date") or reference.get("model_date") or "Latest available"), "Input reference"),
        ("Model", text(payload.get("model_name")), text(payload.get("model_version"))),
        ("Assumptions", "Available" if assumptions else "Not returned", "Technical details"),
    ]
    return terminal_panel(title, evidence_panel(rows), "Model lineage without database internals")


def _divergence_warning(payload: dict) -> None:
    divergence = payload.get("pd_divergence")
    try:
        value = abs(float(divergence))
    except (TypeError, ValueError):
        return
    if value > 0.05:
        st.markdown(
            "<div class='warning-callout'><strong>Model disagreement above threshold</strong>"
            f"<p>Structural PD and ML PD differ by {pct(divergence)}. Analyst review is required before relying on the final PD.</p></div>",
            unsafe_allow_html=True,
        )


def render(client: ApiClient, context: dict) -> None:
    counterparty_id = int(context["counterparty_id"])
    st.subheader("Quant & Monte Carlo")
    st.caption("Question answered: what do the PD, LGD, EAD, and expected-loss engines imply for this facility?")

    pd_result = client.latest_pd(counterparty_id)
    loss_result = client.latest_loss(counterparty_id)
    pd_payload = pd_result.data or {}
    loss_payload = loss_result.data or {}

    if pd_result.ok and pd_payload or loss_result.ok and loss_payload:
        render_terminal_kpi_strip(
            [
                ("Final PD", pct(pd_payload.get("final_pd")), text(pd_payload.get("classification_label")), _pd_kind(pd_payload)),
                ("PD Model", text(pd_payload.get("model_name")), text(pd_payload.get("model_version")), "info"),
                ("Expected Loss", money(loss_payload.get("expected_loss")), "Latest stored estimate", "watch"),
                ("LGD / EAD", f"{pct(loss_payload.get('predicted_lgd'))} / {money(loss_payload.get('exposure_at_default'))}", "Backend loss model", "risk"),
            ]
        )
    else:
        render_api_state(pd_result, "No latest PD prediction found for this counterparty.")
        render_api_state(loss_result, "No latest LGD/EAD estimate found for this counterparty.")

    pd_tab, loss_tab, inputs_tab = st.tabs(["PD Model", "LGD / EAD / EL", "Data Used"])

    with pd_tab:
        render_section_header("Latest Probability of Default", "Structural and ML estimates are compared before final PD is used downstream.")
        if pd_result.ok and pd_payload:
            label = text(pd_payload.get("classification_label"), "Unclassified")
            st.markdown(terminal_status_badge(label, _pd_kind(pd_payload)), unsafe_allow_html=True)
            left_col, right_col = st.columns([1, 1])
            with left_col:
                st.markdown(_model_agreement_panel(pd_payload), unsafe_allow_html=True)
            with right_col:
                st.markdown(_model_detail_panel(pd_payload), unsafe_allow_html=True)
            _divergence_warning(pd_payload)
            render_section_header("Feature Contributions", "Directional drivers returned by the backend PD model.")
            _render_feature_contributions(pd_payload.get("feature_contributions") or {})
            if pd_payload.get("warnings"):
                st.markdown(bullet_list([str(item) for item in pd_payload["warnings"]], "No model warnings."), unsafe_allow_html=True)
        else:
            _show_warning(pd_result, "Latest PD unavailable")

        with st.expander("Run backend PD calculation"):
            horizon = st.number_input("Time horizon in years", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
            metrics_id = _latest_metrics_id(client, counterparty_id)
            st.caption(f"Latest financial metric set: {'found' if metrics_id else 'not found'}")
            if st.button("Calculate PD", use_container_width=True, disabled=metrics_id is None):
                result = client.calculate_pd(int(metrics_id), time_horizon_years=float(horizon))
                if result.ok:
                    st.success("Backend PD calculation completed and stored.")
                    render_technical_json("PD calculation response", result.data)
                else:
                    st.error(f"PD calculation failed: {result.error}")

    with loss_tab:
        render_section_header("Loss Engine", "Latest LGD, EAD, and expected loss rendered from stored backend outputs.")
        if loss_result.ok and loss_payload:
            left_col, right_col = st.columns([1, 1])
            with left_col:
                st.markdown(_loss_panel(loss_payload), unsafe_allow_html=True)
            with right_col:
                st.markdown(_risk_driver_panel(pd_payload, loss_payload), unsafe_allow_html=True)
            if loss_payload.get("ead_cap_applied"):
                st.markdown(
                    "<div class='warning-callout'><strong>EAD cap applied</strong><p>The backend capped exposure at default for this estimate.</p></div>",
                    unsafe_allow_html=True,
                )
            if loss_payload.get("warnings"):
                st.markdown(bullet_list([str(item) for item in loss_payload["warnings"]], "No loss model warnings."), unsafe_allow_html=True)
        else:
            _show_warning(loss_result, "Latest loss estimate unavailable")

        with st.expander("Run backend LGD / EAD / Expected Loss calculation"):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                invoice_amount = st.number_input("Invoice amount", min_value=0.0, value=1_000_000.0, step=50_000.0)
                fuel_volume = st.number_input("Fuel volume", min_value=0.0, value=50_000.0, step=1_000.0)
                fuel_price = st.number_input("Fuel price", min_value=0.0, value=2.50, step=0.05)
            with col_b:
                approved_limit = st.number_input("Approved credit limit", min_value=0.0, value=2_000_000.0, step=50_000.0)
                requested_limit = st.number_input("Requested credit limit", min_value=0.0, value=2_500_000.0, step=50_000.0)
                receivables = st.number_input("Outstanding receivables", min_value=0.0, value=250_000.0, step=25_000.0)
            with col_c:
                tenor = st.number_input("Payment tenor days", min_value=1, max_value=180, value=45, step=1)
                utilization = st.slider("Utilization rate", min_value=0.0, max_value=1.0, value=0.55, step=0.05)
                collateral_type = st.selectbox("Collateral type", COLLATERAL_TYPES, index=0, format_func=_clean_label)
            lc_flag = collateral_type == "letter_of_credit" or st.checkbox("Letter of credit flag")
            guarantee_flag = collateral_type == "guarantee" or st.checkbox("Guarantee flag")
            deposit_pct = st.slider("Deposit percentage", min_value=0.0, max_value=100.0, value=0.0, step=5.0)
            if st.button("Calculate LGD / EAD / EL", use_container_width=True):
                payload = {
                    "counterparty_id": counterparty_id,
                    "pd_prediction_id": pd_payload.get("id"),
                    "invoice_amount": invoice_amount,
                    "fuel_volume": fuel_volume,
                    "fuel_price": fuel_price,
                    "approved_credit_limit": approved_limit,
                    "requested_credit_limit": requested_limit,
                    "outstanding_receivables": receivables,
                    "payment_tenor_days": int(tenor),
                    "utilization_rate": utilization,
                    "collateral_type": collateral_type,
                    "letter_of_credit_flag": lc_flag,
                    "guarantee_flag": guarantee_flag,
                    "deposit_percentage": deposit_pct,
                }
                result = client.calculate_loss(payload)
                if result.ok:
                    st.success("Backend loss estimate completed and stored.")
                    render_technical_json("Loss calculation response", result.data)
                else:
                    st.error(f"Loss calculation failed: {result.error}")

    with inputs_tab:
        render_section_header("Data Used", "Analyst-readable model lineage without exposing database internals.")
        if pd_payload or loss_payload:
            col_a, col_b = st.columns(2)
            with col_a:
                if pd_payload:
                    st.markdown(_lineage_panel(pd_payload, "PD Input Lineage"), unsafe_allow_html=True)
                    render_technical_json("PD input references", pd_payload.get("input_data_reference") or {})
                    render_technical_json("PD assumptions", pd_payload.get("model_assumptions") or {})
            with col_b:
                if loss_payload:
                    st.markdown(_lineage_panel(loss_payload, "Loss Input Lineage"), unsafe_allow_html=True)
                    render_technical_json("Loss input references", loss_payload.get("input_data_reference") or {})
                    render_technical_json("Loss assumptions", loss_payload.get("model_assumptions") or {})
        else:
            st.markdown(
                terminal_panel(
                    "Model Inputs Needed",
                    action_grid(
                        [
                            ("Ingest financials", "Capture accepted accounting values before PD execution."),
                            ("Run PD and loss models", "Use the backend actions on this page once inputs are available."),
                        ]
                    ),
                    "No model input references returned by the backend yet",
                ),
                unsafe_allow_html=True,
            )

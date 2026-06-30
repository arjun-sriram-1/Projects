"""Model validation page."""

from __future__ import annotations

import json
from html import escape

import pandas as pd
import streamlit as st

from web.api_client import ApiClient
from web.components.cards import bullet_list, data_summary_card, render_data_summary_grid, render_section_header
from web.components.formatting import number, text
from web.components.kpi import badge, render_kpi_grid, status_kind
from web.components.layout import render_api_state, render_technical_json


DEFAULT_VALIDATION_PAYLOAD = {
    "predicted_pd": [0.01, 0.03, 0.08, 0.14, 0.22],
    "observed_default": [0, 0, 0, 1, 1],
    "predicted_lgd": [0.30, 0.42, 0.55, 0.70],
    "observed_lgd": [0.28, 0.45, 0.52, 0.76],
    "forecast_actual": [80.0, 82.0, 81.0, 84.0],
    "forecast_predicted": [79.0, 81.5, 82.0, 83.0],
}


def _metrics_frame(metrics: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Metric": metric.get("name"),
            "Value": number(metric.get("value"), 6),
            "Interpretation": metric.get("interpretation"),
        }
        for metric in metrics
    ])


def _validation_scope_cards(data: dict) -> list[str]:
    scope = data.get("validation_scope") or []
    assumptions = data.get("assumptions") or {}
    return [
        data_summary_card(
            "Validation scope",
            ", ".join(str(item) for item in scope) if scope else "Backend validation scope returned with report",
            text(data.get("created_at")),
            "Model review, sanity checks, and limitations.",
        ),
        data_summary_card(
            "Benchmark inputs",
            "Default deterministic sample or analyst-supplied benchmark arrays",
            "Current validation run",
            "PD, LGD, and forecast validation checks.",
        ),
        data_summary_card(
            "Assumptions",
            f"{len(assumptions)} assumption entries available" if isinstance(assumptions, dict) else "Assumptions returned by backend",
            "Stored with validation response",
            "Technical review and audit traceability.",
        ),
    ]


def _sanity_panel(checks: dict) -> str:
    if not checks:
        return ""
    rows = []
    for name, passed in checks.items():
        label = "Passed" if passed else "Review"
        rows.append(
            "<div class='validation-check-item'>"
            f"<span>{escape(str(name).replace('_', ' ').title())}</span>"
            f"{badge(label, status_kind('approved' if passed else 'elevated'))}"
            "</div>"
        )
    return "<div class='validation-check-grid'>" + "".join(rows) + "</div>"


def _limitations_panel(limitations: object) -> None:
    if isinstance(limitations, list):
        st.markdown(bullet_list([str(item) for item in limitations], "No limitations returned."), unsafe_allow_html=True)
    elif limitations:
        st.markdown(f"<div class='data-summary-card'><div class='data-summary-copy'>{escape(str(limitations))}</div></div>", unsafe_allow_html=True)
    else:
        st.info("No limitations returned by the backend validation report.")


def render(client: ApiClient, context: dict) -> None:
    st.subheader("Model Validation")
    st.caption("Runs the backend validation report builder using supplied benchmark arrays. Defaults are deterministic demo arrays.")

    control_col, guide_col = st.columns([1, 1])
    with control_col:
        use_defaults = st.checkbox("Use default validation sample", value=True)
        payload_text = st.text_area(
            "Validation payload JSON",
            value=json.dumps(DEFAULT_VALIDATION_PAYLOAD, indent=2),
            height=260,
            disabled=use_defaults,
        )
    with guide_col:
        render_section_header("Validation Input", "Use defaults for a deterministic demo or supply benchmark arrays for real validation.")
        render_data_summary_grid([
            data_summary_card("Default sample", "PD, LGD, and forecast arrays", "Deterministic demo input", "Functional validation workflow check."),
            data_summary_card("Custom sample", "Analyst supplied JSON payload", "Current run", "Real benchmark validation when available."),
        ])

    if st.button("Generate validation report", use_container_width=True):
        if use_defaults:
            payload = {}
        else:
            try:
                payload = json.loads(payload_text or "{}")
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON: {exc}")
                return
        result = client.model_validation_report(payload)
        if render_api_state(result, "Validation report returned no content."):
            data = result.data or {}
            render_kpi_grid([
                ("Model", text(data.get("model_name")), text(data.get("model_version"))),
                ("Scope Items", str(len(data.get("validation_scope") or [])), "Validation coverage"),
                ("Metrics", str(len(data.get("metrics") or [])), "Generated checks"),
                ("Created", text(data.get("created_at")), "Backend report timestamp"),
            ])
            render_data_summary_grid(_validation_scope_cards(data))

            metrics = data.get("metrics") or []
            if metrics:
                render_section_header("Validation Metrics", "Dense numeric model validation outputs from the backend.")
                st.dataframe(_metrics_frame(metrics), use_container_width=True, hide_index=True)

            checks = data.get("sanity_checks") or {}
            if checks:
                render_section_header("Sanity Checks", "Backend pass/review indicators for validation inputs and outputs.")
                st.markdown(_sanity_panel(checks), unsafe_allow_html=True)

            render_section_header("Limitations", "Known constraints returned by the backend report builder.")
            _limitations_panel(data.get("limitations") or [])

            render_technical_json("Model assumptions", data.get("assumptions") or {})

            report = data.get("markdown_report", "")
            if report:
                render_section_header("Markdown Report", "Formal validation report text generated by the backend.")
                st.markdown(report)


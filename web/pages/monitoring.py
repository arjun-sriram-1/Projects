"""Monitoring alerts page."""

from __future__ import annotations

import json
from html import escape

import pandas as pd
import streamlit as st

from web.api_client import ApiClient
from web.components.cards import bullet_list, render_section_header
from web.components.formatting import number, text
from web.components.kpi import badge, render_kpi_grid, status_kind
from web.components.layout import render_api_state, render_technical_json


def _alert_rows(alerts: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Severity": alert.get("severity"),
            "Category": alert.get("category"),
            "Reason": alert.get("alert_reason"),
            "Metric": alert.get("triggering_metric"),
            "Value": number(alert.get("triggering_value"), 4),
            "Threshold": number(alert.get("threshold"), 4),
            "Source": alert.get("data_source"),
            "Created": alert.get("created_at"),
        }
        for alert in alerts
    ])


def _severity_class(value: object) -> str:
    kind = status_kind(value)
    if kind == "risk":
        return "alert-card-risk"
    if kind == "watch":
        return "alert-card-watch"
    if kind == "ok":
        return "alert-card-ok"
    return "alert-card-info"


def _alert_card(alert: dict) -> str:
    severity = text(alert.get("severity"))
    severity_badge = badge(severity, status_kind(severity))
    category = text(alert.get("category"))
    reason = text(alert.get("alert_reason"))
    metric = text(alert.get("triggering_metric"))
    value = number(alert.get("triggering_value"), 4)
    threshold = number(alert.get("threshold"), 4)
    source = text(alert.get("data_source"))
    created = text(alert.get("created_at"))
    return f"""
    <div class='alert-card {_severity_class(severity)}'>
      <div class='alert-title'>{escape(category)} {severity_badge}</div>
      <div class='alert-meta'>{escape(reason)}</div>
      <div class='alert-meta'><strong>Metric:</strong> {escape(metric)} &nbsp; <strong>Value:</strong> {escape(value)} &nbsp; <strong>Threshold:</strong> {escape(threshold)}</div>
      <div class='alert-meta'><strong>Source:</strong> {escape(source)} &nbsp; <strong>Created:</strong> {escape(created)}</div>
    </div>
    """


def _alert_card_grid(alerts: list[dict]) -> str:
    body = "".join(_alert_card(alert) for alert in alerts)
    return f"<div class='monitoring-alert-grid'>{body}</div>"


def render(client: ApiClient, context: dict) -> None:
    st.subheader("Monitoring Alerts")
    alerts = client.latest_alerts()
    if not render_api_state(alerts, "No monitoring alerts are available."):
        return

    data = alerts.data or {}
    render_kpi_grid([
        ("Total Alerts", str(data.get("alert_count", 0)), "Latest backend alert run"),
        ("High", str(data.get("high_count", 0)), "High severity"),
        ("Medium", str(data.get("medium_count", 0)), "Medium severity"),
        ("Low", str(data.get("low_count", 0)), "Low severity"),
    ])

    rows = data.get("alerts", [])
    if rows:
        severity_options = sorted({row.get("severity") for row in rows if row.get("severity")})
        severity = st.multiselect("Severity filter", severity_options, default=severity_options)
        filtered = [row for row in rows if row.get("severity") in severity]
        render_section_header("Active Alerts", "Backend early-warning signals for the selected risk universe.")
        st.markdown(_alert_card_grid(filtered), unsafe_allow_html=True)
        render_section_header("Alert Ledger", "Dense monitoring records for audit review.")
        st.dataframe(_alert_rows(filtered), use_container_width=True, hide_index=True)
    else:
        st.markdown(
            "<div class='success-callout'><strong>No active alerts</strong>"
            "<p>The latest backend monitoring run did not return active alerts.</p></div>",
            unsafe_allow_html=True,
        )

    if data.get("warnings"):
        st.markdown(bullet_list([str(item) for item in data["warnings"]], "No monitoring warnings."), unsafe_allow_html=True)

    with st.expander("Run supplied alert analysis"):
        st.caption("Optional technical input for the backend alert analyzer. Leave blank to keep the stored backend alert run above.")
        payload_text = st.text_area("Optional alert source JSON", value="{}", height=120)
        if st.button("Analyze supplied alert sources", use_container_width=True):
            try:
                payload = json.loads(payload_text or "{}")
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON: {exc}")
            else:
                result = client.analyze_alerts(payload)
                if result.ok:
                    st.success("Alert analysis completed.")
                    render_technical_json("Alert analysis response", result.data)
                else:
                    st.error(f"Alert analysis failed: {result.error}")

"""Tests for shared dashboard UI components."""

from __future__ import annotations

import plotly.graph_objects as go

from web.components.cards import bullet_list, data_summary_card, decision_panel
from web.components.charts import apply_dark_chart_layout
from web.components.ingestion import analyst_label
from web.components.kpi import badge, kpi_card, status_kind
from web.components.terminal import (
    action_grid,
    compact_table,
    decision_card,
    evidence_panel,
    risk_driver_bar,
    scenario_matrix,
    terminal_kpi_card,
    terminal_panel,
    terminal_status_badge,
)


def test_kpi_card_escapes_backend_text():
    html = kpi_card("PD <script>", "8.1%", "LGD <b>bad</b>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>bad</b>" not in html
    assert "&lt;b&gt;bad&lt;/b&gt;" in html


def test_badge_escapes_label_and_maps_status():
    html = badge("Approved <x>")
    assert "status-ok" in html
    assert "&lt;x&gt;" in html
    assert status_kind("No decision yet") == "neutral"
    assert status_kind("Rejected") == "risk"


def test_data_summary_and_decision_panels_escape_values():
    card = data_summary_card("Market <ctx>", "VIX <raw>", "2026-06-12", "Stress <use>")
    panel = decision_panel([("Security", "LC <required>")], summary="Summary <raw>", status_kind="watch")
    bullets = bullet_list(["Driver <1>"], "None <empty>")
    assert "&lt;ctx&gt;" in card
    assert "&lt;raw&gt;" in card
    assert "decision-panel-watch" in panel
    assert "&lt;required&gt;" in panel
    assert "&lt;1&gt;" in bullets


def test_dark_plotly_layout_helper_applies_theme():
    fig = apply_dark_chart_layout(go.Figure(), title="Risk Chart")
    assert fig.layout.paper_bgcolor == "#111827"
    assert fig.layout.plot_bgcolor == "#111827"
    assert fig.layout.title.text == "Risk Chart"


def test_terminal_components_escape_values_and_apply_status_classes():
    kpi = terminal_kpi_card("PD <raw>", "8.8%", "Merton <model>", "risk")
    badge_html = terminal_status_badge("Approve <x>", "ok")
    panel = terminal_panel("Title <raw>", "Body is caller generated", subtitle="Sub <raw>")

    assert "&lt;raw&gt;" in kpi
    assert "&lt;model&gt;" in kpi
    assert "terminal-kpi-risk" in kpi
    assert "terminal-status-ok" in badge_html
    assert "&lt;x&gt;" in badge_html
    assert "&lt;raw&gt;" in panel


def test_terminal_table_decision_and_evidence_escape_values():
    table = compact_table(["Field <h>", "Value"], [["Revenue <r>", "$1M"]])
    decision = decision_card(
        "Approve with conditions <d>",
        [("Limit", "$8M <limit>")],
        rationale="Needs LC <reason>",
        kind="watch",
    )
    evidence = evidence_panel([("Ratio <label>", "4.2x <value>", "FY2025 <source>")])

    assert "&lt;h&gt;" in table
    assert "&lt;r&gt;" in table
    assert "terminal-decision-watch" in decision
    assert "&lt;d&gt;" in decision
    assert "&lt;limit&gt;" in decision
    assert "&lt;reason&gt;" in decision
    assert "&lt;label&gt;" in evidence
    assert "&lt;value&gt;" in evidence
    assert "&lt;source&gt;" in evidence


def test_terminal_risk_driver_scenario_and_action_components():
    risk = risk_driver_bar("Fuel <risk>", 145, "risk")
    scenario = scenario_matrix([
        {
            "scenario": "Severe <case>",
            "brent": "+25%",
            "dxy": "+8%",
            "vix": "+50%",
            "pd": "17.8%",
            "lgd": "58%",
            "expected_loss": "$1.03M",
            "limit": "$4M",
            "tenor": "LC only",
        }
    ])
    actions = action_grid([("Refresh <action>", "Calls backend <api>")])

    assert "width: 100%" in risk
    assert "&lt;risk&gt;" in risk
    assert "&lt;case&gt;" in scenario
    assert "&lt;action&gt;" in actions
    assert "&lt;api&gt;" in actions


def test_ingestion_field_labels_are_analyst_friendly():
    assert analyst_label("total_debt") == "Total debt"
    assert analyst_label("cash_and_equivalents") == "Cash and equivalents"
    assert analyst_label("custom_metric_name") == "Custom Metric Name"

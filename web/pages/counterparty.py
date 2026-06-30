"""Counterparty analysis landing page."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from web.api_client import ApiClient, ApiResult
from web.components.formatting import money, number, pct, text
from web.components.kpi import status_kind
from web.components.terminal import (
    action_grid,
    decision_card,
    evidence_panel,
    render_terminal_kpi_strip,
    terminal_panel,
)


def _data_or_none(result: ApiResult) -> Any:
    return result.data if result.ok else None


def _latest_document(documents: list[dict] | None) -> dict | None:
    if not documents:
        return None
    return sorted(documents, key=lambda row: row.get("uploaded_at") or "", reverse=True)[0]


def _metric(metrics: dict | None, field: str) -> Any:
    return (metrics or {}).get(field)


def _document_metrics(client: ApiClient, documents: list[dict] | None) -> tuple[dict | None, dict | None]:
    latest_doc = _latest_document(documents)
    if not latest_doc:
        return None, None
    status_result = client.document_status(int(latest_doc["id"]))
    if not status_result.ok:
        return latest_doc, None
    return status_result.data, (status_result.data or {}).get("financial_metrics")


def _workflow_status(
    documents: list[dict] | None,
    ratios: dict | None,
    pd_data: dict | None,
    loss: dict | None,
    recommendation: dict | None,
) -> list[tuple[str, bool, str]]:
    return [
        ("Financial statements", bool(documents), "Upload annual report or capture analyst-reviewed figures."),
        ("Ratio engine", bool(ratios), "Calculate liquidity, leverage, coverage, and profitability ratios."),
        ("Default model", bool(pd_data), "Run structural and ML probability of default models."),
        ("Loss estimate", bool(loss), "Calculate LGD, EAD, and expected loss from exposure inputs."),
        ("Credit terms", bool(recommendation), "Refresh backend recommendation after model outputs are ready."),
    ]


def _readiness_panel(statuses: list[tuple[str, bool, str]]) -> str:
    items = []
    for label, complete, detail in statuses:
        state = "Available" if complete else "Missing"
        items.append((label, state, detail))
    return evidence_panel(items)


def _next_actions(statuses: list[tuple[str, bool, str]]) -> str:
    missing = [(label, detail) for label, complete, detail in statuses if not complete]
    if not missing:
        return action_grid(
            [
                ("Review recommendation", "Inspect the final credit terms and rationale."),
                ("Ask AI analyst", "Request a grounded explanation of PD, security, tenor, or scenarios."),
                ("Generate memo", "Produce a credit memo from backend/RAG outputs."),
            ]
        )
    return action_grid([(label, detail) for label, detail in missing])


def _risk_driver_panel(recommendation: dict | None, stress: dict | None, pd_data: dict | None) -> str:
    drivers = []
    for item in (recommendation or {}).get("key_risk_drivers") or []:
        drivers.append(("Credit driver", str(item), "Recommendation output"))
    stress_level = (stress or {}).get("stress_level")
    if stress_level:
        drivers.append(("Market stress", str(stress_level), "Latest market stress index"))
    classification = (pd_data or {}).get("classification_label")
    if classification:
        drivers.append(("Default risk class", str(classification), "Latest PD model output"))
    if not drivers:
        drivers.append(("Risk drivers", "Not available", "Refresh backend model and recommendation outputs"))
    return evidence_panel(drivers[:5])


def _accounting_snapshot(metrics: dict | None) -> str:
    rows = [
        ("Revenue", money(_metric(metrics, "revenue")), "Latest financial statement"),
        ("EBITDA", money(_metric(metrics, "ebitda")), "Latest financial statement"),
        ("Total debt", money(_metric(metrics, "total_debt")), "Latest financial statement"),
        ("Cash", money(_metric(metrics, "cash_and_equivalents")), "Latest financial statement"),
    ]
    return evidence_panel(rows)


def _recommendation_card(recommendation: dict | None, counterparty_name: str) -> str:
    if not recommendation:
        return decision_card(
            "No recommendation yet",
            [
                ("Counterparty", counterparty_name),
                ("Next step", "Complete financials, PD, LGD/EAD, and scenario inputs"),
            ],
            rationale="The dashboard is waiting for backend outputs before displaying credit terms.",
            kind="neutral",
        )
    return decision_card(
        text(recommendation.get("approval_status"), "Recommendation available"),
        [
            ("Recommended limit", money(recommendation.get("recommended_credit_limit"))),
            ("Payment tenor", f"{text(recommendation.get('recommended_tenor_days'))} days"),
            ("Required security", text(recommendation.get("recommended_security"))),
            ("Risk grade", text(recommendation.get("risk_grade"))),
        ],
        rationale="Backend recommendation output. The dashboard displays it without recalculating credit terms.",
        kind=status_kind(recommendation.get("approval_status")),
    )


def _alert_summary(alerts: Any) -> str:
    if not alerts:
        return evidence_panel([("Monitoring alerts", "No active alert payload", "Latest monitoring API")])
    values = alerts if isinstance(alerts, list) else alerts.get("alerts") if isinstance(alerts, dict) else []
    count = len(values or [])
    return evidence_panel([("Monitoring alerts", f"{count} alert record(s)", "Latest monitoring API")])


def render(client: ApiClient, context: dict) -> None:
    counterparty_id = int(context["counterparty_id"])
    counterparty_name = text(context.get("counterparty"), "Selected counterparty")

    documents_result = client.counterparty_documents(counterparty_id)
    ratios_result = client.latest_ratios(counterparty_id)
    pd_result = client.latest_pd(counterparty_id)
    loss_result = client.latest_loss(counterparty_id)
    recommendation_result = client.latest_recommendation(counterparty_id)
    stress_result = client.latest_market_stress()
    regime_result = client.latest_market_regime()
    alerts_result = client.latest_alerts()

    documents = _data_or_none(documents_result)
    ratios = _data_or_none(ratios_result)
    pd_data = _data_or_none(pd_result)
    loss = _data_or_none(loss_result)
    recommendation = _data_or_none(recommendation_result)
    stress = _data_or_none(stress_result)
    regime = _data_or_none(regime_result)
    alerts = _data_or_none(alerts_result)

    if recommendation:
        counterparty_name = text(recommendation.get("counterparty_name"), counterparty_name)

    _, metrics = _document_metrics(client, documents if isinstance(documents, list) else None)

    st.subheader("Counterparty Credit Analysis")
    st.caption("Question answered: Is this customer safe to sell fuel to on credit?")

    render_terminal_kpi_strip(
        [
            ("Final PD", pct((pd_data or {}).get("final_pd")), text((pd_data or {}).get("classification_label"), "No PD yet"), status_kind((pd_data or {}).get("classification_label"))),
            ("Predicted LGD", pct((loss or {}).get("predicted_lgd")), "Latest backend loss estimate", "info"),
            ("Calculated EAD", money((loss or {}).get("exposure_at_default")), "Exposure at default", "info"),
            ("Expected Loss", money((loss or {}).get("expected_loss")), "PD x LGD x EAD from backend", "watch" if loss else "neutral"),
            ("Risk Grade", text((recommendation or {}).get("risk_grade")), text((recommendation or {}).get("approval_status"), "No recommendation yet"), status_kind((recommendation or {}).get("approval_status"))),
            (
                "Recommended Terms",
                (
                    f"{money((recommendation or {}).get('recommended_credit_limit'))} / "
                    f"{text((recommendation or {}).get('recommended_tenor_days'))}d / "
                    f"{text((recommendation or {}).get('recommended_security'))}"
                ),
                "Backend recommendation",
                status_kind((recommendation or {}).get("approval_status")),
            ),
        ]
    )

    left_col, middle_col, right_col = st.columns(3)
    with left_col:
        st.markdown(
            terminal_panel(
                "Accounting Brief Summary",
                _accounting_snapshot(metrics),
                "Latest source financial values for the selected counterparty.",
            ),
            unsafe_allow_html=True,
        )
    with middle_col:
        st.markdown(
            terminal_panel(
                "Risk Driver Index",
                _risk_driver_panel(recommendation, stress, pd_data),
                "Drivers are displayed from backend outputs only.",
            ),
            unsafe_allow_html=True,
        )
    with right_col:
        st.markdown(_recommendation_card(recommendation, counterparty_name), unsafe_allow_html=True)

    context_rows = [
        ("Market stress", text((stress or {}).get("stress_level"), "Unavailable"), text((stress or {}).get("date"), "Latest market stress")),
        ("Regime", text((regime or {}).get("regime_label"), "Unavailable"), text((regime or {}).get("date"), "Latest detected regime")),
        ("Requested limit", text(context.get("requested_limit"), "Not set"), "Analyst context"),
        ("Requested tenor", text(context.get("requested_tenor"), "Not set"), "Analyst context"),
    ]
    readiness = _workflow_status(
        documents if isinstance(documents, list) else None,
        ratios,
        pd_data,
        loss,
        recommendation,
    )

    lower_left, lower_right = st.columns([1, 1])
    with lower_left:
        st.markdown(
            terminal_panel("Market And Facility Context", evidence_panel(context_rows), "External context and requested terms."),
            unsafe_allow_html=True,
        )
    with lower_right:
        st.markdown(
            terminal_panel("Workflow Readiness", _readiness_panel(readiness), "Availability of backend records."),
            unsafe_allow_html=True,
        )

    st.markdown(
        terminal_panel("Monitoring Snapshot", _alert_summary(alerts), "Latest alert API status."),
        unsafe_allow_html=True,
    )

    st.markdown("#### Next Best Backend Step")
    st.markdown(_next_actions(readiness), unsafe_allow_html=True)

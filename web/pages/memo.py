"""Credit memo and reporting page."""

from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

from web.api_client import ApiClient
from web.components.cards import data_summary_card, render_data_summary_grid, render_section_header
from web.components.formatting import money, pct, text
from web.components.kpi import render_kpi_grid
from web.components.layout import render_api_state, render_technical_json


def _report_source_cards(decision: dict, pd_payload: dict, loss: dict) -> list[str]:
    return [
        data_summary_card(
            "Credit decision package",
            text(decision.get("decision"), "No latest decision returned"),
            text(decision.get("created_at")),
            "Memo recommendation and approval narrative.",
        ),
        data_summary_card(
            "PD model output",
            f"Final PD {pct(pd_payload.get('final_pd'))}; class {text(pd_payload.get('classification_label'))}",
            text(pd_payload.get("created_at")),
            "Risk grade and probability-of-default explanation.",
        ),
        data_summary_card(
            "Loss model output",
            f"Expected loss {money(loss.get('expected_loss'))}; LGD {pct(loss.get('predicted_lgd'))}",
            text(loss.get("created_at")),
            "Exposure, collateral, and expected-loss narrative.",
        ),
    ]


def _file_panel(title: str, files: list[tuple[str, object]]) -> str:
    rows = []
    for label, value in files:
        rows.append(
            "<div class='export-file-row'>"
            f"<span>{escape(label)}</span>"
            f"<strong>{escape(text(value))}</strong>"
            "</div>"
        )
    return f"<div class='export-result-panel'><div class='export-result-title'>{escape(title)}</div>{''.join(rows)}</div>"


def render(client: ApiClient, context: dict) -> None:
    counterparty_label = str(context.get("counterparty") or "")
    counterparty_id = int(context["counterparty_id"])
    st.subheader("Credit Memo / Reporting")

    decision = client.latest_recommendation(counterparty_id)
    loss = client.latest_loss(counterparty_id)
    pd_result = client.latest_pd(counterparty_id)
    decision_payload = decision.data or {}
    loss_payload = loss.data or {}
    pd_payload = pd_result.data or {}

    if decision.ok or loss.ok or pd_result.ok:
        render_kpi_grid([
            ("Decision", text(decision_payload.get("decision")), "Latest backend recommendation"),
            ("Final PD", pct(pd_payload.get("final_pd")), text(pd_payload.get("classification_label"))),
            ("Expected Loss", money(loss_payload.get("expected_loss")), "Latest stored loss estimate"),
        ])
        render_section_header("Report Source Summary", "Latest backend outputs used for memo and report generation.")
        render_data_summary_grid(_report_source_cards(decision_payload, pd_payload, loss_payload))

    memo_tab, export_tab, risk_report_tab = st.tabs(["Grounded Memo", "Memo Export", "Risk Report Export"])

    with memo_tab:
        render_section_header("Grounded Memo", "Generate memo text through the backend RAG service.")
        company = st.text_input("Company / counterparty name", value=counterparty_label)
        if st.button("Generate memo text", use_container_width=True):
            result = client.rag_memo(company)
            if render_api_state(result, "Memo service returned no content."):
                st.markdown("<div class='memo-output-panel'>", unsafe_allow_html=True)
                st.markdown(result.data.get("memo", ""))
                st.markdown("</div>", unsafe_allow_html=True)
                render_technical_json("Memo service response", result.data)

    with export_tab:
        render_section_header("Memo Export", "Create formal memo files from the backend reporting service.")
        default_question = f"Generate a credit memo for {counterparty_label} using the latest V2 credit risk outputs."
        question = st.text_area("Memo instruction", value=default_question, height=120)
        if st.button("Export DOCX / PDF memo", use_container_width=True):
            result = client.export_memo(question)
            if render_api_state(result, "Memo export returned no files."):
                st.success("Memo export completed.")
                st.markdown(
                    _file_panel(
                        "Generated memo files",
                        [("DOCX", result.data.get("docx")), ("PDF", result.data.get("pdf"))],
                    ),
                    unsafe_allow_html=True,
                )
                with st.expander("Memo preview", expanded=False):
                    st.markdown(result.data.get("memo", ""))
                render_technical_json("Memo export response", result.data)

    with risk_report_tab:
        render_section_header("Risk Report Export", "Create a PDF risk report from current backend portfolio/counterparty outputs.")
        report_company = st.text_input("Report company filter", value=counterparty_label, key="risk_report_company")
        if st.button("Export risk report PDF", use_container_width=True):
            safe_name = "".join(ch if ch.isalnum() else "_" for ch in (report_company.strip() or "portfolio"))
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/reports/{safe_name.lower()}_dashboard_{timestamp}.pdf"
            result = client.export_risk_report(report_company.strip() or None, output_file=output_file)
            if render_api_state(result, "Risk report export returned no file."):
                st.success("Risk report export completed.")
                render_kpi_grid([
                    ("Total Exposure", money(result.data.get("total_exposure")), text(result.data.get("source"))),
                    ("Expected Loss", money(result.data.get("total_expected_loss")), "Report aggregate"),
                    ("Average PD / LGD", f"{pct(result.data.get('avg_pd'))} / {pct(result.data.get('avg_lgd'))}", "Report aggregate"),
                ])
                st.markdown(
                    _file_panel("Generated risk report", [("PDF", result.data.get("report_file"))]),
                    unsafe_allow_html=True,
                )
                render_technical_json("Risk report response", result.data)

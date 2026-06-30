"""Financial statements review page."""

from __future__ import annotations

from typing import Any

import streamlit as st

from web.api_client import ApiClient, ApiResult
from web.components.cards import render_section_header
from web.components.formatting import money, number, pct, text
from web.components.ingestion import analyst_label, render_financial_ingestion_workflow
from web.components.layout import render_api_state, render_technical_json
from web.components.terminal import (
    action_grid,
    evidence_panel,
    render_terminal_kpi_strip,
    terminal_panel,
)


STATEMENT_GROUPS = {
    "Income Statement": [
        ("Revenue", "revenue"),
        ("EBITDA", "ebitda"),
        ("EBIT / operating income", "ebit"),
        ("Interest expense", "interest_expense"),
        ("Net income", "net_income"),
    ],
    "Balance Sheet": [
        ("Cash and equivalents", "cash_and_equivalents"),
        ("Current assets", "current_assets"),
        ("Total assets", "total_assets"),
        ("Current liabilities", "current_liabilities"),
        ("Total liabilities", "total_liabilities"),
        ("Total debt", "total_debt"),
        ("Shareholders equity", "shareholders_equity"),
    ],
    "Working Capital / Cash Flow": [
        ("Accounts receivable", "accounts_receivable"),
        ("Inventory", "inventory"),
        ("Accounts payable", "accounts_payable"),
        ("Operating cash flow", "operating_cash_flow"),
    ],
}

RATIO_GROUPS = {
    "Liquidity": [
        ("Current ratio", "current_ratio"),
        ("Quick ratio", "quick_ratio"),
        ("Cash ratio", "cash_ratio"),
        ("Working capital", "working_capital"),
    ],
    "Leverage": [
        ("Debt / equity", "debt_to_equity"),
        ("Debt / EBITDA", "debt_to_ebitda"),
        ("Liabilities / assets", "liabilities_to_assets"),
    ],
    "Coverage": [
        ("Interest coverage", "interest_coverage"),
    ],
    "Profitability": [
        ("Operating margin", "operating_margin"),
        ("Net margin", "net_margin"),
        ("Return on assets", "return_on_assets"),
        ("Return on equity", "return_on_equity"),
    ],
}

MONEY_FIELDS = {
    field
    for fields in STATEMENT_GROUPS.values()
    for _, field in fields
} | {"working_capital"}
PERCENT_FIELDS = {"operating_margin", "net_margin", "return_on_assets", "return_on_equity"}
CRITICAL_FIELDS = ["revenue", "ebitda", "total_assets", "total_debt", "shareholders_equity"]


def _latest_document(documents: list[dict]) -> dict | None:
    if not documents:
        return None
    return sorted(documents, key=lambda row: row.get("uploaded_at") or "", reverse=True)[0]


def _document_label(document: dict) -> str:
    filename = text(document.get("filename"), "Financial source")
    status = text(document.get("extraction_status"), "status pending")
    uploaded = text(document.get("uploaded_at"), "date unavailable")
    return f"{filename} | {status} | {uploaded}"


def _source_name(document: dict | None) -> str:
    if not document:
        return "Selected financial source"
    return text(document.get("filename"), "Financial source")


def _format_field(field: str, value: Any) -> str:
    if field in MONEY_FIELDS:
        return money(value)
    if field in PERCENT_FIELDS:
        return pct(value)
    return number(value, 2)


def _format_confidence(value: Any) -> str:
    formatted = number(value, 2)
    return formatted if formatted != "-" else "Pending"


def _clean_warning(value: Any) -> str:
    return analyst_label(str(value).replace("missing_", "").replace("field_", ""))


def _missing_fields(metrics: dict | None) -> list[str]:
    payload = metrics or {}
    explicit = payload.get("missing_critical_fields") or []
    if explicit:
        return [analyst_label(item) for item in explicit]
    return [analyst_label(field) for field in CRITICAL_FIELDS if payload.get(field) is None]


def _statement_panel(title: str, metrics: dict, fields: list[tuple[str, str]], source: str) -> str:
    rows = [(label, _format_field(field, metrics.get(field)), source) for label, field in fields]
    return terminal_panel(title, evidence_panel(rows), "Extracted or analyst-entered statement values")


def _ratio_panel(title: str, ratios: dict, fields: list[tuple[str, str]]) -> str:
    rows = [(label, _format_field(field, ratios.get(field)), "Backend ratio engine") for label, field in fields]
    return terminal_panel(title, evidence_panel(rows), "Calculated from accepted financial metrics")


def _source_audit(status: dict, metrics: dict | None, document: dict | None) -> str:
    metric_payload = metrics or {}
    source_status = text(status.get("extraction_status"), text(document.get("extraction_status") if document else None))
    uploaded_at = text(document.get("uploaded_at") if document else None)
    document_type = analyst_label(text(document.get("document_type") if document else None, "financial source"))
    rows = [
        ("Source file", _source_name(document), "Uploaded document"),
        ("Document type", document_type, "Backend classification"),
        ("Extraction status", source_status, "Document pipeline"),
        ("Uploaded at", uploaded_at, "Source lineage"),
        ("Fiscal period", text(metric_payload.get("fiscal_period"), "FY"), "Financial metrics"),
        ("Fiscal year", text(metric_payload.get("fiscal_year")), "Financial metrics"),
        ("Currency", text(metric_payload.get("currency"), "USD"), "Financial metrics"),
        ("Confidence", _format_confidence(metric_payload.get("extraction_confidence")), "Extractor score"),
    ]
    return terminal_panel("Source Audit", evidence_panel(rows), "Lineage for the selected financial source")


def _quality_review(metrics: dict | None) -> str:
    if not metrics:
        body = action_grid(
            [
                ("No metrics available", "Upload a PDF or capture manual financials for this counterparty."),
                ("Extraction pending", "Refresh after backend processing finishes if a PDF was just uploaded."),
            ]
        )
        return terminal_panel("Extraction Quality", body, "Awaiting accepted statement values")

    missing = _missing_fields(metrics)
    warnings = [_clean_warning(item) for item in metrics.get("extraction_warnings") or []]
    rows = [
        ("Critical fields", "Complete" if not missing else f"{len(missing)} missing", "Validation check"),
        ("Warnings", "None" if not warnings else f"{len(warnings)} flagged", "Extraction review"),
        ("Review status", "Ready for ratios" if not missing else "Analyst review required", "Dashboard control"),
    ]
    details = []
    if missing:
        details.append(("Missing fields", ", ".join(missing), "Required for credit analysis"))
    if warnings:
        details.append(("Warnings", ", ".join(warnings), "Extractor notes"))
    body = evidence_panel(rows + details)
    return terminal_panel("Extraction Quality", body, "Completeness checks before credit modeling")


def _ratio_readiness(client: ApiClient, ratios_result: ApiResult, metrics: dict | None) -> None:
    if ratios_result.ok and ratios_result.data:
        ratios = ratios_result.data
        render_section_header("Ratio Analysis", "Liquidity, leverage, coverage, and profitability from backend calculations.")
        col1, col2 = st.columns(2)
        group_items = list(RATIO_GROUPS.items())
        for index, (title, fields) in enumerate(group_items):
            with col1 if index % 2 == 0 else col2:
                st.markdown(_ratio_panel(title, ratios, fields), unsafe_allow_html=True)
        return

    render_section_header("Ratio Analysis", "Ratios appear here after backend calculation.")
    st.markdown(
        terminal_panel(
            "Ratio Readiness",
            action_grid(
                [
                    ("Calculate ratios", "Use the backend ratio engine once statement values are accepted."),
                    ("Review missing fields", "Complete revenue, EBITDA, assets, debt, and equity before modeling."),
                ]
            ),
            "No ratio set is currently available for this counterparty",
        ),
        unsafe_allow_html=True,
    )
    if not ratios_result.ok:
        st.caption(f"Latest ratio check: {ratios_result.error}")
    if metrics and st.button("Calculate / refresh ratios", use_container_width=True):
        result = client.calculate_ratios(int(metrics["id"]))
        if result.ok:
            st.success("Financial ratios calculated by backend.")
            render_technical_json("Ratio calculation response", result.data)
        else:
            st.error(f"Ratio calculation failed: {result.error}")


def render(client: ApiClient, context: dict) -> None:
    counterparty_id = int(context["counterparty_id"])
    st.subheader("Financial Statements")
    st.caption("Question answered: can the counterparty support the requested fuel credit facility from reported financial strength?")

    render_section_header(
        "Ingest Financial Data",
        "Upload source statements or capture analyst-reviewed figures through backend APIs.",
    )
    render_financial_ingestion_workflow(
        client,
        context,
        key_prefix="financial_page_ingestion",
        redirect_on_success=False,
    )

    documents_result = client.counterparty_documents(counterparty_id)
    if not render_api_state(documents_result, "No financial sources found for this counterparty."):
        return

    documents = documents_result.data or []
    latest_doc = _latest_document(documents)
    if not latest_doc:
        st.markdown(
            terminal_panel(
                "Financial Source Needed",
                action_grid(
                    [
                        ("Upload annual report", "Start PDF extraction from the ingestion controls above."),
                        ("Manual capture", "Enter analyst-reviewed line items when no PDF is available."),
                    ]
                ),
                "No source document is linked to this counterparty yet",
            ),
            unsafe_allow_html=True,
        )
        return

    doc_options = {_document_label(doc): doc for doc in documents}
    labels = list(doc_options)
    default_index = labels.index(_document_label(latest_doc)) if latest_doc else 0
    selected_label = st.selectbox("Financial source", labels, index=default_index)
    selected_document = doc_options[selected_label]
    selected_doc_id = int(selected_document["id"])

    status_result = client.document_status(selected_doc_id)
    if not render_api_state(status_result, "Financial source status unavailable."):
        return
    status = status_result.data or {}
    metrics = status.get("financial_metrics")
    missing = _missing_fields(metrics)
    status_text = text(status.get("extraction_status"), text(selected_document.get("extraction_status")))

    render_terminal_kpi_strip(
        [
            ("Source Status", status_text, "Document pipeline", status_text),
            ("Fiscal Year", text((metrics or {}).get("fiscal_year")), "Reported period", "info"),
            ("Currency", text((metrics or {}).get("currency"), "USD"), "Statement currency", "info"),
            ("Confidence", _format_confidence((metrics or {}).get("extraction_confidence")), "Extractor score", "neutral"),
            ("Critical Fields", "Complete" if not missing else f"{len(missing)} missing", "Credit model inputs", "ok" if not missing else "watch"),
        ]
    )

    audit_col, quality_col = st.columns(2)
    with audit_col:
        st.markdown(_source_audit(status, metrics, selected_document), unsafe_allow_html=True)
    with quality_col:
        st.markdown(_quality_review(metrics), unsafe_allow_html=True)

    if not metrics:
        return

    source = "Selected source"
    render_section_header("Statement Values", "Clean analyst labels for accepted financial statement inputs.")
    income_col, balance_col, cash_col = st.columns(3)
    columns = [income_col, balance_col, cash_col]
    for column, (title, fields) in zip(columns, STATEMENT_GROUPS.items()):
        with column:
            st.markdown(_statement_panel(title, metrics, fields, source), unsafe_allow_html=True)

    ratios_result = client.latest_ratios(counterparty_id)
    _ratio_readiness(client, ratios_result, metrics)

    st.markdown(
        terminal_panel(
            "Accounting Interpretation",
            evidence_panel(
                [
                    ("Leverage focus", "Debt, EBITDA, and equity drive facility sizing.", "Credit policy input"),
                    ("Liquidity focus", "Cash, current assets, and current liabilities shape short-tenor comfort.", "Underwriting input"),
                    ("Profitability focus", "Margins and net income inform repayment capacity.", "Risk model input"),
                    ("Data treatment", "Clean analyst labels only", "Dashboard presentation rule"),
                ]
            ),
            "How this page feeds the downstream risk framework",
        ),
        unsafe_allow_html=True,
    )

"""Shared financial data ingestion controls for the terminal workflow."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from web.api_client import ApiClient
from web.components.layout import render_technical_json


FIELD_LABELS = {
    "revenue": "Revenue",
    "ebitda": "EBITDA",
    "ebit": "EBIT / operating income",
    "net_income": "Net income",
    "cash_and_equivalents": "Cash and equivalents",
    "total_assets": "Total assets",
    "current_assets": "Current assets",
    "total_liabilities": "Total liabilities",
    "current_liabilities": "Current liabilities",
    "total_debt": "Total debt",
    "shareholders_equity": "Shareholders equity",
    "interest_expense": "Interest expense",
    "operating_cash_flow": "Operating cash flow",
    "accounts_receivable": "Accounts receivable",
    "accounts_payable": "Accounts payable",
    "inventory": "Inventory",
}


def analyst_label(field_name: str) -> str:
    """Return a business-friendly label for backend field names."""
    return FIELD_LABELS.get(str(field_name), str(field_name).replace("_", " ").title())


def _number_or_none(
    label: str,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    help_text: str | None = None,
    key: str,
) -> float | None:
    return st.number_input(
        label,
        min_value=min_value,
        max_value=max_value,
        value=None,
        step=1000.0,
        format="%.2f",
        help=help_text,
        key=key,
    )


def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def render_ingestion_notice() -> None:
    st.markdown(
        "<div class='terminal-ingest-note'><strong>Data ingestion</strong>"
        "<span>Upload source statements or enter analyst-reviewed financials. Values are stored through FastAPI and downstream calculations remain in backend services.</span></div>",
        unsafe_allow_html=True,
    )


def render_manual_capture(
    client: ApiClient,
    counterparty_id: int,
    *,
    form_key: str = "manual_financial_metrics_form",
    redirect_on_success: bool = False,
) -> bool:
    """Render manual financial capture controls and return True after a successful capture."""
    st.markdown(
        "<div class='warning-callout'><strong>Manual source</strong>"
        "<p>These values will be marked as analyst-entered financials and audited separately from PDF extraction.</p></div>",
        unsafe_allow_html=True,
    )

    with st.form(form_key, clear_on_submit=False):
        meta_col1, meta_col2, meta_col3 = st.columns([1, 1, 1])
        with meta_col1:
            fiscal_year = st.number_input("Fiscal year", min_value=1990, max_value=2100, value=2025, step=1, key=f"{form_key}_year")
        with meta_col2:
            fiscal_period = st.selectbox("Fiscal period", ["FY", "Q1", "Q2", "Q3", "Q4", "LTM"], index=0, key=f"{form_key}_period")
        with meta_col3:
            currency = st.text_input("Currency", value="USD", max_chars=3, key=f"{form_key}_currency")

        income_tab, balance_tab, liquidity_tab = st.tabs(["Income Statement", "Balance Sheet", "Liquidity / Coverage"])
        with income_tab:
            col1, col2, col3 = st.columns(3)
            with col1:
                revenue = _number_or_none("Revenue", min_value=0.0, key=f"{form_key}_revenue")
                ebitda = _number_or_none("EBITDA", key=f"{form_key}_ebitda")
            with col2:
                ebit = _number_or_none("EBIT / operating income", key=f"{form_key}_ebit")
                operating_margin_percent = _number_or_none(
                    "Operating margin %",
                    min_value=-100.0,
                    max_value=100.0,
                    help_text="Used by the backend to derive EBIT only when EBIT is not supplied.",
                    key=f"{form_key}_operating_margin",
                )
            with col3:
                interest_expense = _number_or_none("Interest expense", min_value=0.0, key=f"{form_key}_interest")
                net_income = _number_or_none("Net income", key=f"{form_key}_net_income")

        with balance_tab:
            col1, col2, col3 = st.columns(3)
            with col1:
                total_assets = _number_or_none("Total assets", min_value=0.0, key=f"{form_key}_total_assets")
                current_assets = _number_or_none("Current assets", min_value=0.0, key=f"{form_key}_current_assets")
            with col2:
                total_debt = _number_or_none("Total debt", min_value=0.0, key=f"{form_key}_total_debt")
                total_liabilities = _number_or_none("Total liabilities", min_value=0.0, key=f"{form_key}_total_liabilities")
            with col3:
                shareholders_equity = _number_or_none("Shareholders equity", key=f"{form_key}_equity")
                current_liabilities = _number_or_none("Current liabilities", min_value=0.0, key=f"{form_key}_current_liabilities")

        with liquidity_tab:
            col1, col2, col3 = st.columns(3)
            with col1:
                cash_and_equivalents = _number_or_none("Cash and equivalents", min_value=0.0, key=f"{form_key}_cash")
            with col2:
                accounts_receivable = _number_or_none("Accounts receivable", min_value=0.0, key=f"{form_key}_receivables")
            with col3:
                inventory = _number_or_none("Inventory", min_value=0.0, key=f"{form_key}_inventory")
            calculate_after_capture = st.checkbox("Calculate ratios after capture", value=True, key=f"{form_key}_ratios")

        submitted = st.form_submit_button("Capture manual financials", use_container_width=True)

    if not submitted:
        return False

    payload = _clean_payload(
        {
            "counterparty_id": counterparty_id,
            "fiscal_year": int(fiscal_year),
            "fiscal_period": fiscal_period,
            "currency": currency,
            "revenue": revenue,
            "ebitda": ebitda,
            "ebit": ebit,
            "operating_margin_percent": operating_margin_percent,
            "interest_expense": interest_expense,
            "net_income": net_income,
            "cash_and_equivalents": cash_and_equivalents,
            "accounts_receivable": accounts_receivable,
            "inventory": inventory,
            "current_assets": current_assets,
            "total_assets": total_assets,
            "current_liabilities": current_liabilities,
            "total_debt": total_debt,
            "total_liabilities": total_liabilities,
            "shareholders_equity": shareholders_equity,
            "created_by": "streamlit_dashboard",
        }
    )
    with st.spinner("Capturing manual financial metrics through the backend..."):
        result = client.create_manual_financial_metrics(payload)

    if not result.ok:
        st.error(f"Manual capture failed: {result.error}")
        return False

    metrics = (result.data or {}).get("metrics", {})
    st.success("Manual financial metrics captured for this counterparty.")
    render_technical_json("Manual capture response", result.data)

    if calculate_after_capture and metrics.get("id"):
        ratio_result = client.calculate_ratios(int(metrics["id"]))
        if ratio_result.ok:
            st.success("Financial ratios calculated by backend from the captured metrics.")
            render_technical_json("Ratio calculation response", ratio_result.data)
        else:
            st.error(f"Ratio calculation failed: {ratio_result.error}")

    if redirect_on_success:
        st.session_state.active_page = "2. Financial Statements"
    return True


def render_pdf_upload(
    client: ApiClient,
    counterparty_id: int,
    *,
    key_prefix: str = "pdf_upload",
    redirect_on_success: bool = False,
) -> bool:
    """Render PDF upload controls and return True after a successful upload."""
    uploaded_file = st.file_uploader("Annual report or financial statement PDF", type=["pdf"], key=f"{key_prefix}_file")
    document_type = st.selectbox(
        "Document type",
        ["Annual report", "Financial statement", "Credit pack"],
        index=0,
        key=f"{key_prefix}_type",
    )
    document_type_map = {
        "Annual report": "annual_report",
        "Financial statement": "financial_statement",
        "Credit pack": "credit_pack",
    }
    if st.button("Upload and extract", use_container_width=True, disabled=uploaded_file is None, key=f"{key_prefix}_button"):
        st.caption("Full annual reports may take 2-5 minutes because extraction currently runs synchronously in the backend.")
        with st.spinner("Uploading PDF and running backend extraction. Keep this page open until it completes..."):
            result = client.upload_document(
                uploaded_file,
                uploaded_file.name,
                counterparty_id=counterparty_id,
                document_type=document_type_map[document_type],
                created_by="streamlit_dashboard",
            )
        if result.ok:
            st.success("Document uploaded and extraction completed by backend.")
            render_technical_json("Upload response", result.data)
            if redirect_on_success:
                st.session_state.active_page = "2. Financial Statements"
            return True
        if result.error and "Read timed out" in result.error:
            st.error("Upload/extraction is still taking longer than the dashboard wait limit. Check the document list after backend processing finishes.")
        else:
            st.error(f"Upload failed: {result.error}")
    return False


def render_financial_ingestion_workflow(
    client: ApiClient,
    context: dict,
    *,
    key_prefix: str = "financial_ingestion",
    redirect_on_success: bool = False,
) -> bool:
    """Render the shared PDF/manual financial ingestion workflow."""
    counterparty_id = int(context["counterparty_id"])
    counterparty_name = context.get("counterparty", "Selected counterparty")
    st.markdown(
        f"""
        <div class="terminal-ingest-context">
          <span>Counterparty</span><strong>{escape(str(counterparty_name))}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_ingestion_notice()
    pdf_tab, manual_tab = st.tabs(["Upload PDF", "Manual entry"])
    with pdf_tab:
        pdf_success = render_pdf_upload(
            client,
            counterparty_id,
            key_prefix=f"{key_prefix}_pdf",
            redirect_on_success=redirect_on_success,
        )
    with manual_tab:
        manual_success = render_manual_capture(
            client,
            counterparty_id,
            form_key=f"{key_prefix}_manual",
            redirect_on_success=redirect_on_success,
        )
    return pdf_success or manual_success

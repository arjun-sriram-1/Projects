"""Streamlit dashboard shell for Fuel Credit Risk Platform V2.

All dashboard data comes from FastAPI endpoints. The UI displays backend outputs
and never recalculates core credit risk models.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from web.api_client import ApiClient
from web.components.ingestion import render_financial_ingestion_workflow
from web.components.kpi import status_kind
from web.components.layout import render_persistent_copilot, render_terminal_header
from web.config import config
from web.styles import apply_theme
from web.pages import (
    copilot,
    counterparty,
    decision,
    financials,
    market,
    models,
    scenario,
)

PAGES = {
    "1. Counterparty Analysis": counterparty.render,
    "2. Financial Statements": financials.render,
    "3. Market & Stress Intel": market.render,
    "4. Scenario & Forecasts": scenario.render,
    "5. Quant & Monte Carlo": models.render,
    "6. Credit Recommendation": decision.render,
    "7. AI Credit Analyst": copilot.render,
}

PAGE_META = {
    "1. Counterparty Analysis": {
        "title": "Counterparty Credit Analysis",
        "question": "Is this customer safe to sell fuel to on credit?",
    },
    "2. Financial Statements": {
        "title": "Financial Statements",
        "question": "Can the counterparty support the requested facility from reported financial strength?",
    },
    "3. Market & Stress Intel": {
        "title": "Market & Stress Intel",
        "question": "Is the fuel and macro backdrop increasing short-term credit risk?",
    },
    "4. Scenario & Forecasts": {
        "title": "Scenario & Forecasts",
        "question": "How does the facility behave under stressed market paths and tail loss simulations?",
    },
    "5. Quant & Monte Carlo": {
        "title": "Quant & Monte Carlo",
        "question": "What do the PD, LGD, EAD, and expected-loss engines imply for this facility?",
    },
    "6. Credit Recommendation": {
        "title": "Credit Recommendation",
        "question": "What limit, tenor, and security should be approved for this counterparty?",
    },
    "7. AI Credit Analyst": {
        "title": "AI Credit Analyst",
        "question": "What should the analyst ask next using the current credit workflow context?",
    },
}


@st.dialog("Ingest New Data")
def render_ingestion_dialog(client: ApiClient, context: dict) -> None:
    """Top-level data ingestion workflow for the selected counterparty."""
    success = render_financial_ingestion_workflow(
        client,
        context,
        key_prefix="top_level_ingestion",
        redirect_on_success=True,
    )
    if success:
        st.success("Financial data ingested. The workflow is ready to review on Financial Statements.")
        if st.button("Review Financial Statements", use_container_width=True):
            st.rerun()


def initialize_state() -> None:
    st.session_state.setdefault("selected_counterparty", "Phase 16 Golden Airways")
    st.session_state.setdefault("selected_counterparty_id", 180)
    st.session_state.setdefault("selected_date_range", "Latest available")
    st.session_state.setdefault("selected_segment", "Airline (Jet Fuel)")
    st.session_state.setdefault("selected_country", "United States")
    st.session_state.setdefault("requested_limit", "Not set")
    st.session_state.setdefault("requested_tenor", "Not set")
    st.session_state.setdefault("active_page", "1. Counterparty Analysis")


def _counterparty_label(counterparty: dict) -> str:
    name = counterparty.get("counterparty_name") or "Unnamed counterparty"
    counterparty_id = counterparty.get("id")
    counterparty_type = counterparty.get("counterparty_type") or "Unknown segment"
    country = counterparty.get("country") or "Unknown country"
    return f"{name} | ID {counterparty_id} | {counterparty_type} | {country}"


def render_sidebar(client: ApiClient) -> str:
    st.sidebar.title("RiskIntel Agent")
    st.sidebar.caption("Single-counterparty credit terminal")
    if st.session_state.active_page not in PAGES:
        st.session_state.active_page = "1. Counterparty Analysis"
    page = st.sidebar.radio(
        "Risk Framework",
        list(PAGES.keys()),
        index=list(PAGES.keys()).index(st.session_state.active_page),
        key="active_page",
    )
    st.sidebar.divider()

    counterparty_search = st.sidebar.text_input(
        "Search counterparties",
        value="",
        help="Searches backend counterparties by name. Leave blank to show the first 50.",
    )
    counterparties_result = client.counterparties(search=counterparty_search or None, limit=50)
    if counterparties_result.ok and counterparties_result.data:
        options = list(counterparties_result.data)
        labels = [_counterparty_label(row) for row in options]
        current_index = next(
            (
                index
                for index, row in enumerate(options)
                if int(row.get("id")) == int(st.session_state.selected_counterparty_id)
            ),
            0,
        )
        selected_label = st.sidebar.selectbox(
            "Counterparty",
            labels,
            index=current_index,
            help="Backend-backed counterparty context for all workflow pages.",
        )
        selected_counterparty = options[labels.index(selected_label)]
        st.session_state.selected_counterparty_id = int(selected_counterparty["id"])
        st.session_state.selected_counterparty = selected_counterparty.get("counterparty_name") or st.session_state.selected_counterparty
        st.session_state.selected_segment = selected_counterparty.get("counterparty_type") or st.session_state.selected_segment
        st.session_state.selected_country = selected_counterparty.get("country") or st.session_state.selected_country
    else:
        if not counterparties_result.ok:
            st.sidebar.caption("Counterparty selector unavailable; using manual context.")
        else:
            st.sidebar.caption("No counterparties matched; using manual context.")
        st.session_state.selected_counterparty = st.sidebar.text_input(
            "Counterparty label",
            value=st.session_state.selected_counterparty,
            help="Display label only. Backend calls use Counterparty ID.",
        )

    with st.sidebar.expander("Manual backend ID fallback", expanded=False):
        st.session_state.selected_counterparty_id = st.number_input(
            "Counterparty ID",
            min_value=1,
            value=int(st.session_state.selected_counterparty_id),
            step=1,
            help="Use this only when the selector is unavailable or you need a specific backend ID.",
        )
    st.session_state.selected_segment = st.sidebar.text_input(
        "Segment",
        value=st.session_state.selected_segment,
    )
    st.session_state.selected_country = st.sidebar.text_input(
        "Country",
        value=st.session_state.selected_country,
    )
    st.session_state.requested_limit = st.sidebar.text_input(
        "Requested limit",
        value=st.session_state.requested_limit,
    )
    st.session_state.requested_tenor = st.sidebar.text_input(
        "Requested tenor",
        value=st.session_state.requested_tenor,
    )
    st.session_state.selected_date_range = st.sidebar.selectbox(
        "Date range",
        ["Latest available", "FY2025", "Last 12 months", "Custom later"],
        index=0,
    )
    st.sidebar.caption("No backend formulas run in the dashboard.")
    return page


def main() -> None:
    st.set_page_config(page_title=config.page_title, layout=config.layout)
    initialize_state()
    apply_theme()

    client = ApiClient()
    health = client.health()
    api_status = "Healthy" if health.ok and health.data and health.data.get("status") == "healthy" else "Unavailable"
    api_kind = status_kind(api_status)

    page = render_sidebar(client)
    page_meta = PAGE_META.get(page, {"title": page, "question": "Backend data only; no dashboard-side credit calculations."})
    context = {
        "counterparty": st.session_state.selected_counterparty,
        "counterparty_id": int(st.session_state.selected_counterparty_id),
        "date_range": st.session_state.selected_date_range,
        "segment": st.session_state.selected_segment,
        "country": st.session_state.selected_country,
        "requested_limit": st.session_state.requested_limit,
        "requested_tenor": st.session_state.requested_tenor,
        "api_status": api_status,
        "active_page": page,
        "active_question": page_meta["question"],
    }
    render_terminal_header(
        st.session_state.selected_counterparty,
        st.session_state.selected_segment,
        st.session_state.selected_country,
        st.session_state.requested_limit,
        st.session_state.requested_tenor,
        status_label=f"API: {api_status}",
        status_kind=api_kind,
    )
    action_col, spacer_col = st.columns([0.2, 0.8])
    with action_col:
        if st.button("Ingest New Data", use_container_width=True):
            render_ingestion_dialog(client, context)

    main_col, copilot_col = st.columns([0.72, 0.28], gap="large")
    with main_col:
        st.markdown(
            f"""
            <div class="terminal-page-kicker">Risk Framework / {page_meta["title"]}</div>
            <div class="terminal-page-question">Question answered: {page_meta["question"]}</div>
            """,
            unsafe_allow_html=True,
        )
        PAGES[page](client, context)
    with copilot_col:
        render_persistent_copilot(context)


if __name__ == "__main__":
    main()



"""Reusable layout helpers."""

from __future__ import annotations

from html import escape

import streamlit as st

from web.api_client import ApiResult


def render_header(title: str, subtitle: str, status_label: str = "API status unknown", status_kind: str = "neutral") -> None:
    safe_kind = escape(str(status_kind))
    st.markdown(
        f"""
        <div class="main-header">
          <div>
            <p class="main-title">{escape(str(title))}</p>
            <div class="main-subtitle">{escape(str(subtitle))}</div>
          </div>
          <span class="status-badge status-{safe_kind}">{escape(str(status_label))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_terminal_header(
    counterparty: str,
    segment: str,
    country: str,
    requested_limit: str,
    requested_tenor: str,
    status_label: str = "API status unknown",
    status_kind: str = "neutral",
) -> None:
    """Render the terminal-style top controller strip for the underwriting workflow."""
    safe_kind = escape(str(status_kind))
    st.markdown(
        f"""
        <div class="terminal-header-strip">
          <div class="terminal-brand"><span class="terminal-brand-mark">&gt;_</span> RiskIntel Agent</div>
          <div class="terminal-counterparty-select">{escape(str(counterparty))}</div>
          <div class="terminal-meta-pill"><span>Segment:</span><strong>{escape(str(segment))}</strong></div>
          <div class="terminal-meta-pill"><span>Country:</span><strong>{escape(str(country))}</strong></div>
          <div class="terminal-meta-pill"><span>Requested Limit:</span><strong>{escape(str(requested_limit))}</strong></div>
          <div class="terminal-meta-pill"><span>Requested Tenor:</span><strong>{escape(str(requested_tenor))}</strong></div>
          <span class="status-badge status-{safe_kind}">{escape(str(status_label))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_context_bar(counterparty: str, date_range: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="context-bar">
          <strong>Counterparty:</strong> {escape(str(counterparty))} &nbsp; | &nbsp;
          <strong>Date range:</strong> {escape(str(date_range))}<br />
          <span class="context-note">{escape(str(note))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_persistent_copilot(context: dict) -> None:
    """Render a persistent right-side credit co-pilot rail without running model logic."""
    counterparty = context.get("counterparty", "Selected counterparty")
    requested_limit = context.get("requested_limit", "Not set")
    requested_tenor = context.get("requested_tenor", "Not set")
    active_page = context.get("active_page", "Risk Framework")
    active_question = context.get("active_question", "Backend data only; no dashboard-side credit calculations.")
    st.markdown(
        f"""
        <div class="terminal-copilot-rail">
          <div class="terminal-copilot-title">Live Credit Co-Pilot</div>
          <div class="terminal-copilot-message">
            Holding real-time context for <strong>{escape(str(counterparty))}</strong>. I monitor financial statements,
            Merton and ML model outputs, scenario paths, and recommendation evidence as each workflow page loads.
          </div>
          <div class="terminal-copilot-context">
            <span>Current view</span><strong>{escape(str(active_page))}</strong>
            <em>{escape(str(active_question))}</em>
          </div>
          <div class="terminal-copilot-presets">
            <div>Why is PD high?</div>
            <div>Why LC required?</div>
            <div>What if Brent rises?</div>
            <div>Why this tenor?</div>
          </div>
          <div class="terminal-copilot-foot">
            Requested facility: <strong>{escape(str(requested_limit))}</strong> / <strong>{escape(str(requested_tenor))}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_api_state(result: ApiResult, empty_message: str = "No data returned yet.") -> bool:
    if not result.ok:
        st.error(f"API unavailable: {result.error}")
        return False
    if result.data in (None, [], {}):
        st.info(empty_message)
        return False
    return True


def render_technical_json(label: str, payload) -> None:
    """Render technical JSON only inside a collapsed expander."""
    with st.expander(label, expanded=False):
        st.json(payload or {})

"""KPI and status display components."""

from __future__ import annotations

from html import escape

import streamlit as st


def kpi_card(label: str, value: str, help_text: str = "") -> str:
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{escape(str(label))}</div>
      <div class="kpi-value">{escape(str(value))}</div>
      <div class="kpi-help">{escape(str(help_text))}</div>
    </div>
    """


def render_kpi_grid(cards: list[tuple[str, str, str]]) -> None:
    """Render KPI cards without relying on one large markdown HTML block.

    Streamlit can occasionally show raw HTML when a large generated block is
    mixed with complex page layout. Rendering cards cell-by-cell keeps the KPI
    strip stable across pages.
    """
    if not cards:
        return
    max_columns = 4
    for start in range(0, len(cards), max_columns):
        row = cards[start:start + max_columns]
        columns = st.columns(len(row))
        for column, (label, value, help_text) in zip(columns, row):
            with column:
                st.markdown(kpi_card(label, value, help_text), unsafe_allow_html=True)


def status_kind(label: str | None) -> str:
    text = (label or "").lower()
    if any(word in text for word in ["healthy", "approved", "low", "stable", "completed"]):
        return "ok"
    if any(word in text for word in ["conditional", "watch", "elevated", "medium", "normal"]):
        return "watch"
    if any(word in text for word in ["reject", "high", "failed", "crisis", "error"]):
        return "risk"
    if any(word in text for word in ["info", "pending", "unknown"]):
        return "info"
    return "neutral"


def badge(label: str, kind: str | None = None) -> str:
    badge_kind = kind or status_kind(label)
    return f'<span class="status-badge status-{badge_kind}">{escape(str(label))}</span>'

"""Reusable card and panel components for the dashboard."""

from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st


def data_summary_card(title: str, detail: str, date_text: str, use: str) -> str:
    """Return escaped HTML for an analyst-friendly data lineage card."""
    return f"""
    <div class="data-summary-card">
      <div class="data-summary-title">{escape(str(title))}</div>
      <div class="data-summary-copy"><strong>Data:</strong> {escape(str(detail))}</div>
      <div class="data-summary-copy"><strong>Date / range:</strong> {escape(str(date_text))}</div>
      <div class="data-summary-copy"><strong>Used for:</strong> {escape(str(use))}</div>
    </div>
    """


def render_data_summary_grid(cards: Iterable[str]) -> None:
    body = "".join(cards)
    if body:
        st.markdown(f"<div class='data-summary-grid'>{body}</div>", unsafe_allow_html=True)


def decision_panel(rows: Iterable[tuple[str, str]], summary: str | None = None, status_kind: str = "neutral") -> str:
    """Return escaped HTML for a compact credit decision panel."""
    row_html = "".join(
        f"<div class='data-summary-copy'><strong>{escape(str(label))}:</strong> {escape(str(value))}</div>"
        for label, value in rows
    )
    summary_html = ""
    if summary:
        summary_html = f"<div class='data-summary-copy'><strong>Summary:</strong> {escape(str(summary))}</div>"
    return f"<div class='decision-panel decision-panel-{escape(status_kind)}'>{row_html}{summary_html}</div>"


def bullet_list(items: Iterable[str], empty: str) -> str:
    values = [str(item) for item in items if item]
    if not values:
        return f"<p class='data-summary-copy'>{escape(str(empty))}</p>"
    bullets = "".join(f"<li>{escape(value)}</li>" for value in values[:5])
    return f"<ul class='compact-bullet-list'>{bullets}</ul>"


def render_section_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<div class='section-subtitle'>{escape(str(subtitle))}</div>" if subtitle else ""
    st.markdown(
        f"<div class='section-header'><div class='section-title'>{escape(str(title))}</div>{subtitle_html}</div>",
        unsafe_allow_html=True,
    )

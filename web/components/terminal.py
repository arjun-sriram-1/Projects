"""Terminal-style UI components for the credit underwriting workflow."""

from __future__ import annotations

from html import escape
from typing import Iterable, Mapping, Sequence

import streamlit as st

from web.components.kpi import status_kind


VALID_KINDS = {"ok", "info", "watch", "risk", "neutral"}


def _kind(value: str | None) -> str:
    candidate = (value or "neutral").lower()
    return candidate if candidate in VALID_KINDS else status_kind(candidate)


def terminal_status_badge(label: str, kind: str | None = None) -> str:
    badge_kind = _kind(kind or label)
    return f'<span class="terminal-status-badge terminal-status-{badge_kind}">{escape(str(label))}</span>'


def terminal_kpi_card(label: str, value: str, helper: str = "", kind: str | None = None) -> str:
    card_kind = _kind(kind)
    helper_html = f'<div class="terminal-kpi-helper">{escape(str(helper))}</div>' if helper else ""
    return f"""
    <div class="terminal-kpi-card terminal-kpi-{card_kind}">
      <div class="terminal-kpi-label">{escape(str(label))}</div>
      <div class="terminal-kpi-value">{escape(str(value))}</div>
      {helper_html}
    </div>
    """


def render_terminal_kpi_strip(cards: Sequence[tuple[str, str, str] | tuple[str, str, str, str]]) -> None:
    body = []
    for card in cards:
        label, value, helper, *rest = card
        body.append(terminal_kpi_card(label, value, helper, rest[0] if rest else None))
    if body:
        st.markdown(f"<div class='terminal-kpi-strip'>{''.join(body)}</div>", unsafe_allow_html=True)


def terminal_panel(title: str, body: str, subtitle: str | None = None) -> str:
    subtitle_html = f'<div class="terminal-panel-subtitle">{escape(str(subtitle))}</div>' if subtitle else ""
    return f"""
    <div class="terminal-panel">
      <div class="terminal-panel-title">{escape(str(title))}</div>
      {subtitle_html}
      <div class="terminal-panel-body">{body}</div>
    </div>
    """


def risk_driver_bar(label: str, value: float | int | None, kind: str | None = None) -> str:
    try:
        percent = max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        percent = 0.0
    bar_kind = _kind(kind)
    return f"""
    <div class="terminal-risk-row">
      <span>{escape(str(label))}</span>
      <div class="terminal-risk-meter"><div class="terminal-risk-fill terminal-risk-{bar_kind}" style="width: {percent:.0f}%"></div></div>
      <strong>{percent:.0f}%</strong>
    </div>
    """


def risk_driver_panel(drivers: Iterable[tuple[str, float | int | None, str]]) -> str:
    return "".join(risk_driver_bar(label, value, kind) for label, value, kind in drivers)


def compact_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    header_html = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    row_html = []
    for row in rows:
        cells = "".join(f"<td>{escape(str(cell))}</td>" for cell in row)
        row_html.append(f"<tr>{cells}</tr>")
    return f"""
    <div class="terminal-table-wrap">
      <table class="terminal-compact-table">
        <thead><tr>{header_html}</tr></thead>
        <tbody>{''.join(row_html)}</tbody>
      </table>
    </div>
    """


def decision_card(
    decision: str,
    rows: Iterable[tuple[str, str]],
    rationale: str | None = None,
    kind: str | None = None,
) -> str:
    card_kind = _kind(kind or decision)
    rows_html = "".join(
        "<div class='terminal-decision-row'>"
        f"<span>{escape(str(label))}</span><strong>{escape(str(value))}</strong>"
        "</div>"
        for label, value in rows
    )
    rationale_html = ""
    if rationale:
        rationale_html = f"<div class='terminal-decision-rationale'>{escape(str(rationale))}</div>"
    return f"""
    <div class="terminal-decision-card terminal-decision-{card_kind}">
      <div class="terminal-decision-label">Credit Underwriting Status</div>
      <div class="terminal-decision-title">{escape(str(decision))}</div>
      {rows_html}
      {rationale_html}
    </div>
    """


def evidence_panel(items: Iterable[tuple[str, str, str | None]]) -> str:
    rows = []
    for label, value, source in items:
        source_html = f"<em>{escape(str(source))}</em>" if source else ""
        rows.append(
            "<div class='terminal-evidence-row'>"
            f"<span>{escape(str(label))}</span><strong>{escape(str(value))}</strong>{source_html}"
            "</div>"
        )
    return f"<div class='terminal-evidence-panel'>{''.join(rows)}</div>"


def scenario_matrix(rows: Iterable[Mapping[str, object]]) -> str:
    headers = ["Scenario", "Brent", "DXY", "VIX", "PD", "LGD", "EL", "Limit", "Tenor"]
    table_rows = []
    for row in rows:
        table_rows.append(
            [
                row.get("scenario", "-"),
                row.get("brent", "-"),
                row.get("dxy", "-"),
                row.get("vix", "-"),
                row.get("pd", "-"),
                row.get("lgd", "-"),
                row.get("expected_loss", "-"),
                row.get("limit", "-"),
                row.get("tenor", "-"),
            ]
        )
    return compact_table(headers, table_rows)


def action_grid(actions: Iterable[tuple[str, str]]) -> str:
    cards = "".join(
        "<div class='terminal-action-card'>"
        f"<strong>{escape(str(title))}</strong><span>{escape(str(description))}</span>"
        "</div>"
        for title, description in actions
    )
    return f"<div class='terminal-action-grid'>{cards}</div>"

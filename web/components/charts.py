"""Plotly helpers for dark dashboard charts."""

from __future__ import annotations

from typing import Any

DARK_PLOTLY_LAYOUT: dict[str, Any] = {
    "paper_bgcolor": "#111827",
    "plot_bgcolor": "#111827",
    "font": {"color": "#C1C7D0", "family": "Inter, system-ui, sans-serif"},
    "title": {"font": {"color": "#FFFFFF", "size": 16}},
    "xaxis": {
        "gridcolor": "#1E293B",
        "linecolor": "#1E293B",
        "zerolinecolor": "#1E293B",
        "tickfont": {"color": "#8994A5"},
        "title": {"font": {"color": "#C1C7D0"}},
    },
    "yaxis": {
        "gridcolor": "#1E293B",
        "linecolor": "#1E293B",
        "zerolinecolor": "#1E293B",
        "tickfont": {"color": "#8994A5"},
        "title": {"font": {"color": "#C1C7D0"}},
    },
    "legend": {"font": {"color": "#C1C7D0"}},
    "margin": {"l": 48, "r": 24, "t": 56, "b": 40},
}


def apply_dark_chart_layout(fig, *, title: str | None = None):
    """Apply the V2 dashboard dark chart style to a Plotly figure."""
    fig.update_layout(**DARK_PLOTLY_LAYOUT)
    if title:
        fig.update_layout(title=title)
    return fig


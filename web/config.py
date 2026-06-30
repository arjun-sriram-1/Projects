"""Configuration helpers for the Streamlit dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH, override=False)


def _api_base_url() -> str:
    return (
        os.getenv("V2_API_BASE_URL")
        or os.getenv("API_BASE_URL")
        or "http://localhost:8000"
    )


@dataclass(frozen=True)
class DashboardConfig:
    api_base_url: str = field(default_factory=_api_base_url)
    page_title: str = field(
        default_factory=lambda: os.getenv("V2_DASHBOARD_TITLE", "Fuel Credit Risk Platform V2")
    )
    layout: str = field(default_factory=lambda: os.getenv("V2_DASHBOARD_LAYOUT", "wide"))


config = DashboardConfig()


__all__ = ["PROJECT_ROOT", "ENV_PATH", "DashboardConfig", "config"]

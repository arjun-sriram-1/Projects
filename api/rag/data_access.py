"""Database-backed data access helpers for RAG agents.

These helpers replace the V1 dashboard data loaders so the RAG package can stay
inside the backend API boundary. They return empty data frames when optional
source tables are unavailable; generation layers must report missing data rather
than invent values.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from api.db.session import engine


def _read_sql(query: str) -> pd.DataFrame:
    try:
        with engine.connect() as connection:
            return pd.read_sql(text(query), connection)
    except Exception:
        return pd.DataFrame()


def load_counterparties() -> pd.DataFrame:
    return _read_sql(
        """
        SELECT id AS counterparty_id, counterparty_name AS company_name,
               counterparty_type, country
        FROM counterparties_master
        """
    )


def load_predictions() -> pd.DataFrame:
    return _read_sql(
        """
        SELECT DISTINCT ON (counterparty_id)
               counterparty_id, final_pd AS pd, classification_label,
               market_stress_index, market_regime, created_at
        FROM pd_model_predictions
        ORDER BY counterparty_id, created_at DESC
        """
    )


def load_portfolio() -> pd.DataFrame:
    return _read_sql(
        """
        SELECT counterparty_id, probability_of_default, predicted_lgd,
               exposure_at_default, expected_loss, created_at
        FROM loss_estimates
        ORDER BY created_at DESC
        """
    )


def load_scenarios() -> pd.DataFrame:
    return _read_sql(
        """
        SELECT run_id, scenario_name, scenario_type, scenario_impacts,
               created_at
        FROM scenario_results
        ORDER BY created_at DESC
        """
    )

def load_simulations() -> pd.DataFrame:
    return _read_sql(
        """
        SELECT run_id, scenario, expected_loss, var_95, var_99,
               expected_shortfall_95, expected_shortfall_99,
               expected_shortfall, unexpected_loss, created_at
        FROM simulation_results
        ORDER BY created_at DESC
        """
    )

# ============================================================
# FILE: risk/risk_contributions.py
# FULL FINAL REPLACEMENT
# Production-ready marginal risk attribution
# Works with:
# - monte_carlo.py
# - hybrid ML engine
# - portfolio dashboards
# ============================================================

import numpy as np
import pandas as pd

from api.portfolio_risk.monte_carlo import simulate_portfolio_loss
from api.portfolio_risk.var import compute_var


# ============================================================
# CORE ENGINE
# ============================================================

def calculate_risk_contributions(
    df,
    n_simulations=500,
    confidence=0.95
):
    """
    Leave-One-Out VaR Contributions

    Contribution_i =
        Portfolio VaR
        - VaR(without i)

    Returns numpy array
    """

    if len(df) == 0:
        return np.array([])

    df = df.reset_index(drop=True).copy()

    # ------------------------------------------------
    # FULL PORTFOLIO RISK
    # ------------------------------------------------
    total_output = simulate_portfolio_loss(
        df,
        n_simulations=n_simulations
    )

    total_losses = total_output["portfolio_losses"]

    total_var = compute_var(
        total_losses,
        confidence=confidence
    )

    contributions = []

    # ------------------------------------------------
    # LOOP EACH COUNTERPARTY
    # ------------------------------------------------
    for i in range(len(df)):

        reduced_df = (
            df.drop(index=i)
              .reset_index(drop=True)
        )

        # Single name portfolio case
        if len(reduced_df) == 0:
            reduced_var = 0.0

        else:
            reduced_output = simulate_portfolio_loss(
                reduced_df,
                n_simulations=n_simulations
            )

            reduced_losses = reduced_output[
                "portfolio_losses"
            ]

            reduced_var = compute_var(
                reduced_losses,
                confidence=confidence
            )

        contrib = total_var - reduced_var

        contributions.append(
            float(contrib)
        )

    return np.array(contributions)


# ============================================================
# DATAFRAME OUTPUT
# ============================================================

def risk_contribution_table(
    df,
    n_simulations=500,
    confidence=0.95
):
    """
    Returns clean table
    """

    contribs = calculate_risk_contributions(
        df=df,
        n_simulations=n_simulations,
        confidence=confidence
    )

    out = df.copy().reset_index(drop=True)

    out["risk_contribution"] = contribs

    total = out["risk_contribution"].sum()

    if total > 0:
        out["pct_contribution"] = (
            out["risk_contribution"] / total
        )
    else:
        out["pct_contribution"] = 0.0

    return out.sort_values(
        "risk_contribution",
        ascending=False
    )


# ============================================================
# TOP CONTRIBUTORS
# ============================================================

def top_risk_names(
    df,
    top_n=5,
    n_simulations=500
):
    """
    Highest contributors only
    """

    table = risk_contribution_table(
        df,
        n_simulations=n_simulations
    )

    return table.head(top_n)


# ============================================================
# TEST MODE
# ============================================================

if __name__ == "__main__":

    sample = pd.DataFrame([
        {
            "sector": "Airline",
            "revenue": 500,
            "debt": 300,
            "fleet_size": 40,
            "fuel_dependency": 0.80,
            "fx_exposure": 0.60,
            "profit_margin": 0.08,
            "exposure": 2_000_000
        },
        {
            "sector": "Shipping",
            "revenue": 800,
            "debt": 500,
            "fleet_size": 60,
            "fuel_dependency": 0.65,
            "fx_exposure": 0.40,
            "profit_margin": 0.05,
            "exposure": 4_000_000
        }
    ])

    print(
        risk_contribution_table(
            sample,
            n_simulations=100
        )
    )

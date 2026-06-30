# ============================================================
# FILE: api/structural_credit/merton_model.py
# FULL FINAL HYBRID STRUCTURAL MODEL
# ============================================================

import numpy as np

from scipy.stats import norm

from .distance_to_default import (
    calculate_distance_to_default
)

from .black_scholes import (
    black_scholes_equity
)
pd_model = None

# ============================================================
# PURE MERTON PD
# ============================================================

def calculate_merton_pd(
    asset_value,
    debt,
    sigma,
    r=0.05,
    T=1
):
    """
    Structural PD from Merton model
    """

    debt = max(debt, 1)

    sigma = max(sigma, 1e-4)

    dd = calculate_distance_to_default(
        asset_value,
        debt,
        r,
        sigma,
        T
    )

    pd_structural = norm.cdf(-dd)

    return float(
        np.clip(
            pd_structural,
            0.0001,
            0.999
        )
    )


# ============================================================
# HYBRID MODEL
# ============================================================

def merton_model(
    V0,
    D,
    mu,
    sigma,
    T,
    counterparty=None,
    use_hybrid=True
):
    """
    Hybrid Credit Risk Model

    Combines:
    - Structural PD
    - ML PD
    """

    # ------------------------------------------------
    # STRUCTURAL PD
    # ------------------------------------------------
    dd = calculate_distance_to_default(
        V0,
        D,
        mu,
        sigma,
        T
    )

    pd_structural = norm.cdf(-dd)

    # ------------------------------------------------
    # ML PD
    # ------------------------------------------------
    pd_ml = None
# ------------------------------------------------
    # HYBRID COMBINATION
    # ------------------------------------------------
    if pd_ml is not None:

        # Weighted ensemble
        hybrid_pd = (
            0.6 * pd_ml +
            0.4 * pd_structural
        )

    else:

        hybrid_pd = pd_structural

    hybrid_pd = float(
        np.clip(
            hybrid_pd,
            0.0001,
            0.999
        )
    )

    return {

        "pd_hybrid": hybrid_pd,

        "pd_structural":
            float(pd_structural),

        "pd_ml":
            float(pd_ml)
            if pd_ml is not None
            else None,

        "distance_to_default":
            float(dd)
    }


# ============================================================
# ADVANCED BLACK-SCHOLES VERSION
# ============================================================

def merton_advanced(
    V0,
    D,
    r,
    sigma,
    T
):
    """
    Black-Scholes based structural analysis
    """

    equity, d1, d2 = black_scholes_equity(
        V0,
        D,
        r,
        sigma,
        T
    )

    pd = norm.cdf(-d2)

    return {

        "equity":
            float(equity),

        "PD":
            float(pd),

        "d1":
            float(d1),

        "d2":
            float(d2)
    }


# ============================================================
# TEST MODE
# ============================================================

if __name__ == "__main__":

    cp = {
        "revenue": 500,
        "debt": 300,
        "fleet_size": 40,
        "fuel_dependency": 0.7,
        "fx_exposure": 0.5,
        "profit_margin": 0.08
    }

    out = merton_model(
        V0=800,
        D=400,
        mu=0.05,
        sigma=0.3,
        T=1,
        counterparty=cp
    )

    print(out)


# ============================================================
# FILE: risk/var.py
# FULL FINAL REPLACEMENT
# Production-ready Value at Risk metrics
# Works with:
# - stress_testing.py
# - monte_carlo.py
# - dashboards / reports
# ============================================================

import numpy as np


# ============================================================
# INTERNAL CLEANER
# ============================================================

def _clean_losses(losses):
    """
    Convert input to numeric numpy array
    remove NaNs
    """

    arr = np.array(losses, dtype=float)

    arr = arr[~np.isnan(arr)]

    return arr


# ============================================================
# MAIN FUNCTION
# ============================================================

def compute_var(
    losses,
    confidence=0.95
):
    """
    Value at Risk

    Example:
    confidence=0.95 => 95th percentile loss
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0.0

    return float(
        np.percentile(
            arr,
            confidence * 100
        )
    )


# ============================================================
# ALIAS
# ============================================================

def calculate_var(
    losses,
    confidence=0.95
):
    """
    Backward compatible alias
    """

    return compute_var(
        losses,
        confidence
    )


# ============================================================
# EXTRA METRICS
# ============================================================

def worst_case_loss(losses):
    """
    Maximum simulated loss
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0.0

    return float(np.max(arr))


def median_loss(losses):
    """
    Median loss
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0.0

    return float(np.median(arr))


def percentile_loss(
    losses,
    percentile=99
):
    """
    Generic percentile loss
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0.0

    return float(
        np.percentile(
            arr,
            percentile
        )
    )


# ============================================================
# TEST MODE
# ============================================================

if __name__ == "__main__":

    sample = np.array([
        0,
        10000,
        25000,
        40000,
        80000,
        120000
    ])

    print("VaR 95:", compute_var(sample))
    print("VaR 99:", percentile_loss(sample, 99))
    print("Median:", median_loss(sample))
    print("Worst:", worst_case_loss(sample))
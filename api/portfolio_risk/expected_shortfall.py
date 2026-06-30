# ============================================================
# FILE: risk/expected_shortfall.py
# FULL FINAL REPLACEMENT
# Backward compatible + production-ready
# Works with:
# - stress_testing.py
# - monte_carlo.py
# - risk analytics dashboard
# ============================================================

import numpy as np


# ============================================================
# INTERNAL CLEANER
# ============================================================

def _clean_losses(losses):
    """
    Convert input to clean numpy array
    """

    arr = np.array(losses, dtype=float)

    arr = arr[~np.isnan(arr)]

    return arr


# ============================================================
# CORE ES FUNCTION
# ============================================================

def calculate_expected_shortfall(
    losses,
    confidence=0.95
):
    """
    Expected Shortfall (CVaR)

    ES = average losses worse than VaR threshold
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0.0

    var_level = np.percentile(
        arr,
        confidence * 100
    )

    tail_losses = arr[
        arr >= var_level
    ]

    if len(tail_losses) == 0:
        return float(var_level)

    return float(
        np.mean(tail_losses)
    )


# ============================================================
# BACKWARD COMPATIBLE ALIAS
# ============================================================

def compute_expected_shortfall(
    losses,
    confidence=0.95
):
    """
    Legacy alias
    """

    return calculate_expected_shortfall(
        losses,
        confidence
    )


# ============================================================
# EXTRA ANALYTICS
# ============================================================

def tail_loss_count(
    losses,
    confidence=0.95
):
    """
    Number of losses in tail
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0

    var_level = np.percentile(
        arr,
        confidence * 100
    )

    return int(
        np.sum(arr >= var_level)
    )


def var_threshold(
    losses,
    confidence=0.95
):
    """
    Return VaR threshold used in ES
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
# TEST MODE
# ============================================================

if __name__ == "__main__":

    sample = np.array([
        0,
        10000,
        25000,
        40000,
        80000,
        120000,
        200000
    ])

    print("VaR threshold:", var_threshold(sample))
    print("Expected Shortfall:", calculate_expected_shortfall(sample))
    print("Tail Count:", tail_loss_count(sample))
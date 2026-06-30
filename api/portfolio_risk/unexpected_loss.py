# ============================================================
# FILE: risk/unexpected_loss.py
# FULL FINAL REPLACEMENT
# Production-ready Unexpected Loss metrics
# Works with:
# - stress_testing.py
# - monte_carlo.py
# - dashboards / reporting
# ============================================================

import numpy as np


# ============================================================
# INTERNAL CLEANER
# ============================================================

def _clean_losses(losses):
    """
    Convert to numeric array and remove NaNs
    """

    arr = np.array(losses, dtype=float)

    arr = arr[~np.isnan(arr)]

    return arr


# ============================================================
# MAIN FUNCTION
# ============================================================

def compute_unexpected_loss(losses):
    """
    Unexpected Loss = Std Dev of loss distribution
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0.0

    return float(np.std(arr))


# ============================================================
# ALIAS
# ============================================================

def calculate_unexpected_loss(losses):
    """
    Backward compatible alias
    """

    return compute_unexpected_loss(losses)


# ============================================================
# EXTRA METRICS
# ============================================================

def loss_variance(losses):
    """
    Variance of loss distribution
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0.0

    return float(np.var(arr))


def coeff_variation(losses):
    """
    Std / Mean
    """

    arr = _clean_losses(losses)

    if len(arr) == 0:
        return 0.0

    mean_val = np.mean(arr)

    if mean_val == 0:
        return 0.0

    return float(np.std(arr) / mean_val)


# ============================================================
# TEST MODE
# ============================================================

if __name__ == "__main__":

    sample = np.array([
        0,
        10000,
        25000,
        60000,
        90000
    ])

    print("Unexpected Loss:", compute_unexpected_loss(sample))
    print("Variance:", loss_variance(sample))
    print("Coeff Variation:", coeff_variation(sample))
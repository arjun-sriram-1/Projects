import numpy as np
def calculate_distance_to_default(V0, D, mu, sigma, T):
    """
    Distance to Default (DD)
    """
    numerator = np.log(V0 / D) + (mu - 0.5 * sigma**2) * T
    denominator = sigma * np.sqrt(T)
    return numerator / denominator 
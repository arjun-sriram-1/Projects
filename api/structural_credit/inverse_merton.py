import numpy as np
from scipy.stats import norm
from scipy.optimize import fsolve


def inverse_merton(E, D, r, T, sigma_E):
    """
    Solves for asset value (V) and asset volatility (sigma_A)
    from observed equity and equity volatility
    """

    def equations(x):
        V, sigma_A = x

        d1 = (np.log(V / D) + (r + 0.5 * sigma_A**2) * T) / (sigma_A * np.sqrt(T))
        d2 = d1 - sigma_A * np.sqrt(T)

        # Equation 1: Equity value
        eq1 = V * norm.cdf(d1) - D * np.exp(-r * T) * norm.cdf(d2) - E

        # Equation 2: Equity volatility
        eq2 = (V / E) * norm.cdf(d1) * sigma_A - sigma_E

        return [eq1, eq2]

    # Initial guesses
    V0 = E + D
    sigma_A0 = sigma_E

    solution = fsolve(equations, [V0, sigma_A0])

    V, sigma_A = solution

    return V, sigma_A  

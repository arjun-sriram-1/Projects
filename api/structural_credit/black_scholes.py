import numpy as np
from scipy.stats import norm

def compute_d1(V0, D, r, sigma, T):
    return (np.log(V0 / D) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

def compute_d2(d1, sigma, T):
    return d1 - sigma * np.sqrt(T)

def black_scholes_equity(V0, D, r, sigma, T):
    d1 = compute_d1(V0, D, r, sigma, T)
    d2 = compute_d2(d1, sigma, T)

    equity = V0 * norm.cdf(d1) - D * np.exp(-r * T) * norm.cdf(d2)

    return equity, d1, d2
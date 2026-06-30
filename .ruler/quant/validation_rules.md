# Validation Rules

Minimum sanity checks:

- Higher leverage should not reduce PD.
- Lower liquidity should not reduce PD.
- Lower interest coverage should not reduce PD.
- Higher asset volatility should not reduce PD.
- Higher asset value should not increase PD.
- Stronger collateral should not increase LGD.
- Higher EAD should not reduce Expected Loss, all else equal.
- Adverse scenarios should not usually be safer than base scenarios.
- Expected Shortfall should be greater than or equal to VaR.

Required tests by module:

- financial ratio formula tests
- Merton sensitivity tests
- LGD bounds and collateral-direction tests
- EAD cap and tenor tests
- scenario non-hardcoding tests
- Monte Carlo output shape and reproducibility tests
- credit recommendation sanity tests
- API smoke tests for exposed routes


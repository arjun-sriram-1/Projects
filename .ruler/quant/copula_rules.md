# Copula Rules

Use these rules only for portfolio default dependence and portfolio loss simulation.

Scope:

- Copulas are for portfolio default dependence only.
- Do not use copulas for single-counterparty PD.
- Single-name PD must come from structural, ML, or policy-supported credit models.

Allowed model roles:

- Gaussian copula: baseline dependence model.
- t-Copula: tail-dependence model for stressed portfolio default clustering.

Required copula outputs:

- model_name
- model_version
- copula_type
- correlation_matrix_source
- degrees_of_freedom for t-Copula
- simulation_count
- random_seed when supplied
- portfolio_loss_distribution
- VaR
- Expected Shortfall
- tail_dependence_note
- assumptions
- warnings

t-Copula requirements:

- Use t-Copula only for portfolio-level dependence and tail-risk analysis.
- Degrees of freedom must be explicit and documented.
- Lower degrees of freedom imply stronger tail dependence.
- t-Copula results should be compared against Gaussian baseline when exposed to users.

Validation:

- Correlation matrices must be symmetric and positive semidefinite or repaired with a documented method.
- Higher PD, LGD, or EAD should not reduce expected loss all else equal.
- Expected Shortfall should be greater than or equal to VaR.
- Stressed/tail dependence should not look safer than Gaussian baseline without explanation.

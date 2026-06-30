# Quant Rules

Core definitions:

- PD = probability of default.
- LGD = loss given default.
- EAD = exposure at default.
- Expected Loss = `PD * LGD * EAD`.

Required model separation:

- Structural PD: Merton/distance-to-default.
- ML PD: cross-check, preferably logistic regression baseline.
- LGD: Random Forest regressor where ML is used.
- EAD: trade exposure logic, not the same as credit limit.

Credit decision outputs:

- recommended_credit_limit
- recommended_tenor_days
- recommended_security
- risk_grade
- approval_status
- key_risk_drivers
- model_version

Do not confuse risk score with PD, LGD with total loss, or EAD with credit limit.


## Full Quantitative Methodology Coverage

For any quantitative modelling design, implementation, refactor, review, or bug fix, also load:

- `.ruler/quant/quantitative_model_rules_full.md`

That file is the lossless V2 copy of V1 `quantitative_agents.md`. The smaller quant rule files are task-specific routing helpers, not replacements for the full methodology when numerical model behavior is being changed.

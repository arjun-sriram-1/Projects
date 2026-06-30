# api/portfolio_risk/AGENTS.md

Load this before broader API rules for Monte Carlo, copula, VaR, ES, EL/UL, and portfolio concentration work.

Task matrix:

| Task | Required rules |
|---|---|
| Portfolio metric feature | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/quant_rules.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/build_feature.md` |
| Copula or tail-dependence feature | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/copula_rules.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/build_feature.md` |
| Scenario or simulation refactor | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/scenario_model_rules.md`, `.ruler/core/migration.md`, `.ruler/prompts/refactor.md` |
| Bug fix | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/bug_fix.md` |
| Tests | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/testing.md` |

Rules:

- Expected Loss is `PD * LGD * EAD`.
- Copulas are for portfolio default dependence only.
- Gaussian copula is the baseline; t-Copula is for tail-dependence analysis.
- Simulations must expose simulation count, random seed, VaR, ES, and loss distribution.




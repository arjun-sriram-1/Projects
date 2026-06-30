# api/structural_credit/AGENTS.md

Use for Merton, distance-to-default, structural PD, and sensitivity tests.

Task matrix:

| Task | Required rules |
|---|---|
| Structural PD feature | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/quant_rules.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/build_feature.md` |
| Refactor | `.ruler/core/migration.md`, `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/quant_rules.md`, `.ruler/prompts/refactor.md` |
| Bug fix | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/bug_fix.md` |

Rules:

- Higher leverage or asset volatility must not reduce PD.
- Higher asset value must not increase PD.
- Outputs must include distance to default, structural PD, assumptions, and model version.



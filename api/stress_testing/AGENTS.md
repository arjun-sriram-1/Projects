# api/stress_testing/AGENTS.md

Use for historical scenarios, stress impact, market regimes, and scenario APIs.

Task matrix:

| Task | Required rules |
|---|---|
| Scenario feature | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/scenario_model_rules.md`, `.ruler/data/data_rules.md`, `.ruler/prompts/build_feature.md` |
| Forecast-driven scenario feature | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/forecasting_rules.md`, `.ruler/quant/scenario_model_rules.md`, `.ruler/prompts/build_feature.md` |
| Hedging sensitivity scenario | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/hedging_rules.md`, `.ruler/quant/scenario_model_rules.md`, `.ruler/prompts/build_feature.md` |
| Refactor | `.ruler/core/migration.md`, `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/scenario_model_rules.md`, `.ruler/prompts/refactor.md` |
| Tests | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/testing.md` |

Rules:

- Do not hardcode shocks such as oil +20% or FX +10%.
- Scenario values must come from historical quantiles, regimes, bootstrapping, or model forecasts.




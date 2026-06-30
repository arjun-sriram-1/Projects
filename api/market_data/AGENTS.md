# api/market_data/AGENTS.md

Use for market data ingestion, external providers, stress index, regimes, and forecasting.

Task matrix:

| Task | Required rules |
|---|---|
| Market data feature | `.ruler/data/data_rules.md`, `.ruler/api/api_rules.md`, `.ruler/prompts/build_feature.md` |
| Forecasting feature | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/forecasting_rules.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/build_feature.md` |
| Regime or stress feature | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/scenario_model_rules.md`, `.ruler/data/data_rules.md`, `.ruler/prompts/build_feature.md` |
| Refactor | `.ruler/core/migration.md`, `.ruler/prompts/refactor.md` |
| Tests | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/testing.md` |

Rules:

- Market values must be traceable to a provider, stored data, or documented sample data.
- Forecasts are probabilistic and must include assumptions and warnings.
- Do not hardcode shocks as if they are historical or forecasted market data.


# api/machine_learning/AGENTS.md

Use for ML PD, LGD, clustering, anomaly detection, feature engineering, and training metadata.

Task matrix:

| Task | Required rules |
|---|---|
| ML feature/model work | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/quant_rules.md`, `.ruler/quant/validation_rules.md`, `.ruler/data/data_rules.md` |
| Training/refactor | `.ruler/core/migration.md`, `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/prompts/refactor.md` |
| Tests | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/testing.md` |

Rules:

- ML PD is a cross-check, not the only source of truth.
- LGD must remain bounded from 0 to 1.
- Synthetic labels require documented label-generation logic and `data_source`.



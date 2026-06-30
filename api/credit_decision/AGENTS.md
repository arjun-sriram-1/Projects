# api/credit_decision/AGENTS.md

Use for final credit recommendation, tenor, collateral, risk grade, approval status, and credit memo grounding data.

Task matrix:

| Task | Required rules |
|---|---|
| Decision feature | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/quant_rules.md`, `.ruler/api/database_rules.md`, `.ruler/prompts/build_feature.md` |
| Refactor | `.ruler/core/migration.md`, `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/prompts/refactor.md` |
| Tests | `.ruler/quant/quantitative_model_rules_full.md`, `.ruler/quant/validation_rules.md`, `.ruler/prompts/testing.md` |

Rules:

- The final recommendation must be rules-based or model-based from stored outputs.
- Required outputs: credit limit, tenor, security, risk grade, approval status, risk drivers, model version.
- RAG may explain this output but must not independently decide it.



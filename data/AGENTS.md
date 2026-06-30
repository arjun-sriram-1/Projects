# data/AGENTS.md

Use for raw data, uploads, processed datasets, synthetic data, saved models, vector stores, and reports.

Task matrix:

| Task | Required rules |
|---|---|
| Data ingestion/storage | `.ruler/data/data_rules.md` |
| Model or vector artifact paths | `.ruler/data/data_rules.md`, `.ruler/core/migration.md` |
| Synthetic data | `.ruler/data/data_rules.md`, `.ruler/quant/validation_rules.md` |

Rules:

- Never mix real and synthetic rows without a `data_source` field.
- Do not commit secrets or private uploaded documents.


# Backend Guardrails

- Do not break existing V1 behavior during migration.
- Do not silently fill missing critical financial fields.
- Do not mix real and synthetic data without `data_source`.
- Do not let the LLM create final numeric recommendations.
- Do not rename database tables during folder migration unless explicitly approved.
- Do not add new dependencies without checking `.ruler/core/tech_stack.md`.


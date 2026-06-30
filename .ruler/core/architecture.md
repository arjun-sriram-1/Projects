# Architecture Rules

V2 target structure:

```text
api/       FastAPI backend, services, quant modules, RAG backend
web/       Streamlit dashboard and API clients
data/      raw, uploads, processed datasets, model artifacts, vector stores, reports
database/  SQL schema and migration notes
docs/      human documentation and V1 references
tests/     V2 test suite
.ruler/    token-efficient AI governance
```

Boundaries:

- Keep business logic outside route files.
- Keep dashboard logic outside backend model code.
- Keep core quant formulas in quant/domain modules.
- Keep generated artifacts under `data/`, not source packages.
- Use module `AGENTS.md` files for local routing; closest rule wins.

Do not introduce enterprise complexity unless it directly improves the student project's functionality, testability, or explainability.


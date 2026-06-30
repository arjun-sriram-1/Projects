# api/AGENTS.md

Backend agents should load only the rules needed for the touched module.

Task matrix:

| Task | Required rules |
|---|---|
| New or changed FastAPI endpoint | `.ruler/api/api_rules.md`, `.ruler/prompts/build_feature.md` |
| Database model/session/schema work | `.ruler/api/database_rules.md`, `.ruler/api/guardrails.md` |
| Backend refactor | `.ruler/api/api_rules.md`, `.ruler/core/migration.md`, `.ruler/prompts/refactor.md` |
| Backend bug fix | `.ruler/api/guardrails.md`, `.ruler/prompts/bug_fix.md` |
| Backend tests | `.ruler/prompts/testing.md` |

Route to a closer module AGENTS.md when present.

Important module routes:

| Area | Closest rule router |
|---|---|
| `api/market_data/` forecasting, regimes, stress index | `api/market_data/AGENTS.md` |
| `api/monitoring/` early warning and alerts | `api/monitoring/AGENTS.md` |
| `api/portfolio_risk/` copula, Monte Carlo, VaR, ES | `api/portfolio_risk/AGENTS.md` |

Backend boundaries:

- Routers validate HTTP input and call services.
- Services contain workflow/business orchestration.
- Quant formulas belong in quant modules, not routers.
- RAG explanation belongs in `api/rag/`, not credit decision services.



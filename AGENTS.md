# AGENTS.md

Purpose: route AI coding agents to the smallest useful rule set.

Do not load every rule file. Identify the affected area, then read the closest
module AGENTS.md and only the listed `.ruler` files for the task type.

Default routing:

| Area | Next file |
|---|---|
| `api/` | `api/AGENTS.md` |
| `api/portfolio_risk/` | `api/portfolio_risk/AGENTS.md` |
| `api/structural_credit/` | `api/structural_credit/AGENTS.md` |
| `api/machine_learning/` | `api/machine_learning/AGENTS.md` |
| `api/market_data/` | `api/market_data/AGENTS.md` |
| `api/monitoring/` | `api/monitoring/AGENTS.md` |
| `api/stress_testing/` | `api/stress_testing/AGENTS.md` |
| `api/credit_decision/` | `api/credit_decision/AGENTS.md` |
| `api/rag/` | `api/rag/AGENTS.md` |
| `web/` | `web/AGENTS.md` |
| `data/` | `data/AGENTS.md` |
| `deployment/`, Docker, env templates | `.ruler/deployment/deployment_rules.md` |

Global rules:

- Preserve V1 behavior while migrating into V2.
- Treat `../CREDIT_RISK_PROJECT_V1` as read-only reference.
- Do not copy `.env`, generated reports, model artifacts, or vector indexes unless explicitly approved.
- Do not let AI invent credit decisions or numerical risk outputs.
- For business context, read `.ruler/core/project_identity.md` only when the task affects workflow, credit decisions, or user-facing methodology.
- For full V1 ruler parity audits, read `.ruler/core/v1_full_rule_index.md`; do not load full V1 mirrors by default.




# api/monitoring/AGENTS.md

Use for early warning, alerts, anomaly monitoring, and risk deterioration workflows.

Task matrix:

| Task | Required rules |
|---|---|
| Alert feature | `.ruler/monitoring/alert_rules.md`, `.ruler/api/api_rules.md`, `.ruler/prompts/build_feature.md` |
| Alert database work | `.ruler/monitoring/alert_rules.md`, `.ruler/api/database_rules.md`, `.ruler/prompts/build_feature.md` |
| Monitoring refactor | `.ruler/monitoring/alert_rules.md`, `.ruler/core/migration.md`, `.ruler/prompts/refactor.md` |
| Bug fix | `.ruler/monitoring/alert_rules.md`, `.ruler/prompts/bug_fix.md` |
| Tests | `.ruler/monitoring/alert_rules.md`, `.ruler/prompts/testing.md` |

Rules:

- Alerts must include severity, category, reason, triggering value, and source.
- Alert methodology belongs in services, not routers or dashboard pages.
- Do not create alerts from missing or invented data.

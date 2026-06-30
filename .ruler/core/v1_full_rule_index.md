# V1 Full Rule Index

Use this index only when a task requires full V1 governance context, full feature parity review, or a rule-gap audit.

Do not load these full files for ordinary feature work unless the closest module `AGENTS.md` or the user explicitly asks for full V1 ruler coverage.

Full V1 rule mirrors available in V2:

| V1 ruler | V2 full-rule mirror | Use when |
|---|---|---|
| `agents.md` | `.ruler/core/agents_rules_full.md` | Broad architecture, agent behavior, governance, and cross-module reasoning. |
| `project_features.md` | `.ruler/core/project_features_full.md` | Feature completeness, feature parity, business capability audits. |
| `project_explanation.md` | `.ruler/core/project_explanation_full.md` | Deep business-methodology explanations and end-to-end workflow reasoning. |
| `quantitative_agents.md` | `.ruler/quant/quantitative_model_rules_full.md` | Quantitative modelling design, implementation, refactor, review, or bug fix. |

Routing rule:

- Start with the closest module `AGENTS.md`.
- Load small modular `.ruler` files first.
- Load a full V1 mirror only when exact V1 rule coverage matters for the task.
- For quantitative model changes, `.ruler/quant/quantitative_model_rules_full.md` is mandatory.

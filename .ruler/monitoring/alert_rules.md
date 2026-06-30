# Monitoring And Alert Rules

Use these rules only for early warning, alerts, anomaly monitoring, and risk deterioration work.

Purpose:

- Early warning flags deteriorating counterparties before default.
- Alerts must be explainable and tied to stored data, model outputs, market stress, or scenario results.

Allowed alert sources:

- PD threshold breach
- LGD or expected loss deterioration
- exposure or concentration breach
- stress loss breach
- portfolio VaR or Expected Shortfall breach
- market stress or volatility deterioration
- z-score anomaly
- Isolation Forest or anomaly model output when available
- payment delay or operational warning when stored data exists

Required alert outputs:

- alert_id when persisted
- counterparty_id when counterparty-specific
- severity
- category
- alert_reason
- triggering_metric
- triggering_value
- threshold or comparison_baseline
- data_source
- created_at
- model_version or rule_version

Rules:

- Do not create unexplained alerts.
- Do not invent news, payment delay, or market data.
- Thresholds must come from config, policy, or database settings.
- Alert logic belongs in monitoring services, not dashboard pages.
- Dashboard and API layers should display alerts, not own the alert methodology.

Validation:

- Inject abnormal data and confirm the correct alert is triggered.
- Normal data should not create high-severity alerts.
- Missing data should produce warnings or no alert, not fabricated values.
- Alert severity should be deterministic for the same inputs and thresholds.

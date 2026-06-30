# Database Rules

Use PostgreSQL-friendly schemas and SQLAlchemy-compatible design.

Important tables include:

- counterparties_master
- uploaded_documents
- extracted_financials
- financial_ratios
- market_prices
- market_features
- macro_indicators
- geopolitical_index or geopolitical_stress_index
- market_regimes
- model_predictions
- scenario_results
- simulation_results
- credit_recommendations
- ai_credit_memos
- audit_logs

Every model output table should include:

- model_name
- model_version
- run_id
- created_at
- input_data_reference
- assumptions_reference

Traceability requirement:

credit recommendation -> scenario/model output -> PD/LGD/EAD -> ratios -> extracted financials -> source document and market data.


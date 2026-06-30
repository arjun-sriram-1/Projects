# Fuel Trade Credit Risk Engine - Interview Guide

## 1. One-Minute Project Pitch

This project is an AI-augmented credit risk platform for fuel trade finance. The core business question is: can a fuel supplier safely extend trade credit to an airline, shipping company, trader, or distributor, and under what credit limit, tenor, collateral, and monitoring conditions?

The system does not let AI invent credit decisions. It uses a deterministic data pipeline: financial statement extraction, ratio calculation, market stress and regime detection, PD modeling, LGD/EAD/expected loss calculation, scenario analysis, Monte Carlo portfolio simulation, and finally a rules-based credit recommendation. AI is used as an explanation and memo layer over stored model outputs.

## 2. Architecture

- Frontend: `frontend/index.html`, `frontend/app.js`, and `frontend/styles.css` provide the main HTML dashboard served by FastAPI.
- Legacy dashboard: `web/app.py` is a Streamlit dashboard with the same workflow pages.
- API: `api/main.py` exposes FastAPI routes for documents, financial analysis, market intelligence, credit risk, scenarios, credit decisions, memos, monitoring, and copilot.
- Database: PostgreSQL schema lives in `database/schema.sql`.
- Models and engines: financial ratios, PD, LGD/EAD/EL, stress index, market regimes, Monte Carlo, credit policy, and memo generation are separated into domain modules.
- Data flow: uploaded financials and market data are transformed into model outputs; model outputs are persisted with run IDs, versions, assumptions, warnings, and input references for auditability.

## 3. End-to-End Workflow

1. A user uploads an annual report/PDF or enters financials manually.
2. The system stores the counterparty and document metadata.
3. Financial line items are extracted into structured financial metrics.
4. Financial ratios are calculated using deterministic formulas.
5. Market data is ingested from market/fuel/macro sources and converted into stress and regime signals.
6. PD is estimated using a Merton structural model anchored to financials, with an ML/logistic proxy cross-check.
7. Trade exposure terms are captured, and LGD/EAD/expected loss are calculated.
8. Scenarios and Monte Carlo simulations estimate portfolio tail risk.
9. A rules-based decision engine recommends limit, tenor, security, risk grade, and approval status.
10. AI memo/copilot features explain the stored results without inventing unsupported numbers.

## 4. Key Formulas and Interview Talking Points

- Current ratio = current assets / current liabilities.
- Quick ratio = cash plus receivables / current liabilities, or current assets minus inventory / current liabilities when direct quick assets are unavailable.
- Cash ratio = cash / current liabilities.
- Working capital = current assets - current liabilities.
- Debt to equity = total debt / shareholders equity.
- Debt to EBITDA = total debt / EBITDA.
- Liabilities to assets = total liabilities / total assets.
- Interest coverage = EBIT / interest expense.
- Operating margin = EBIT / revenue.
- Net margin = net income / revenue.
- ROA = net income / total assets.
- ROE = net income / shareholders equity.
- Structural PD uses Merton distance-to-default: the model compares asset value proxy against a debt threshold under asset volatility.
- Final PD = 65% structural PD + 35% ML/proxy PD, with distress floors for negative equity or liabilities exceeding assets.
- LGD is collateral-aware: stronger LC/cash deposit/guarantee lowers severity, while unsecured exposure, country risk, and longer tenor increase severity.
- EAD = outstanding receivables + expected drawdown, capped by approved/requested limit when available.
- Expected drawdown = invoice exposure * utilization rate * max(1, tenor / 30).
- Expected loss = PD * LGD * EAD.
- Recommended limit = base limit * (1 - policy haircut).
- Policy haircut is driven by PD, LGD, market stress, liquidity, leverage, interest coverage, tenor, VaR/ES, model disagreement, and collateral strength.

## 5. Table Dictionary

### market_prices

Stores raw and enriched market/fuel/macro price observations.

- `id`: primary key.
- `date`: observation timestamp.
- `price`: observed price/value.
- `asset`: normalized asset key, such as `brent_oil`, `vix`, `dxy`, `jet_fuel_proxy`.
- `ticker`: market ticker or provider symbol.
- `source_id`: provider-specific series ID.
- `asset_name`: human-readable asset name.
- `data_source`: provider, such as yfinance, FRED, EIA, or Alpha Vantage.
- `frequency`: daily, monthly, weekly, etc.
- `units`: unit of measurement.
- `return`: calculated return/change for the asset.
- `rolling_volatility`: rolling volatility for risk/stress features.
- `created_at`: insert timestamp.

### market_features

Stores summarized statistical features per asset.

- `id`: primary key.
- `asset`: normalized asset key.
- `ticker`: ticker/provider symbol.
- `source_id`: provider series ID.
- `data_source`: data provider.
- `mu`: average return/drift.
- `sigma`: volatility estimate.
- `latest_price`: most recent observed value.
- `created_at`: insert timestamp.

### macro_indicators

Stores macro series mirrored from providers.

- `id`: primary key.
- `date`: observation timestamp.
- `indicator`: macro variable name, such as CPI, yield spread, rates, or high-yield spread.
- `value`: observed indicator value.
- `source_id`: provider series ID.
- `data_source`: provider.
- `frequency`: observation frequency.
- `units`: unit of measurement.
- `return`: calculated percentage/log change.
- `rolling_volatility`: volatility of the indicator change.
- `created_at`: insert timestamp.

### counterparties_master

Master record for every borrower/counterparty.

- `id`: primary key.
- `counterparty_name`: unique company/customer name.
- `counterparty_type`: airline, trader, marine, distributor, etc.
- `country`: country of operation or risk domicile.
- `created_at`: creation timestamp.

### uploaded_documents

Tracks uploaded PDFs and processing status.

- `id`: primary key.
- `counterparty_id`: link to `counterparties_master`.
- `filename`: uploaded file name.
- `file_path`: server path where the file is stored.
- `document_type`: annual report, financial statement, etc.
- `file_size_bytes`: file size.
- `uploaded_at`: upload timestamp.
- `processed_at`: extraction completion timestamp.
- `extraction_status`: pending, processing, completed, or failed.
- `extraction_error`: error message if extraction failed.
- `created_by`: uploader/user identifier.
- `updated_at`: last update timestamp.

### financial_metrics_extracted

Stores structured financial statement line items extracted from PDFs or manual entry.

- `id`: primary key.
- `uploaded_document_id`: source document.
- `counterparty_id`: company.
- `fiscal_year`: reporting year.
- `fiscal_period`: FY, Q1, Q2, etc.
- `revenue`: sales/top-line income.
- `cost_of_goods_sold`: direct cost of goods/services.
- `operating_expenses`: operating expense base.
- `ebitda`: earnings before interest, tax, depreciation, and amortization.
- `ebit`: operating profit after depreciation/amortization.
- `interest_expense`: debt interest cost.
- `net_income`: bottom-line profit.
- `cash_and_equivalents`: cash and near-cash assets.
- `short_term_investments`: liquid investments.
- `accounts_receivable`: customer receivables.
- `inventory`: inventory balance.
- `other_current_assets`: other short-term assets.
- `current_assets`: total short-term assets.
- `ppe_gross`: gross property, plant, and equipment.
- `accumulated_depreciation`: depreciation deducted from PPE.
- `ppe_net`: net property, plant, and equipment.
- `intangible_assets`: non-physical assets.
- `goodwill`: goodwill balance.
- `total_assets`: total asset base.
- `accounts_payable`: supplier payables.
- `short_term_debt`: debt due within one year.
- `current_portion_long_term_debt`: long-term debt due soon.
- `other_current_liabilities`: other short-term liabilities.
- `current_liabilities`: total short-term liabilities.
- `long_term_debt`: debt due after one year.
- `total_debt`: short-term plus long-term debt.
- `other_long_term_liabilities`: other long-term obligations.
- `total_liabilities`: total obligations.
- `shareholders_equity`: book equity.
- `retained_earnings`: accumulated retained profit.
- `operating_cash_flow`: cash from operations.
- `investing_cash_flow`: cash from investing activity.
- `financing_cash_flow`: cash from financing activity.
- `free_cash_flow`: cash left after capex/operations.
- `currency`: reporting currency.
- `extraction_confidence`: extraction confidence from 0 to 1.
- `missing_critical_fields`: JSON list of missing important fields.
- `original_text_references`: JSON references back to source text.
- `extraction_warnings`: JSON warnings from extraction.
- `source_document_id`: source document reference.
- `created_at`: creation timestamp.
- `updated_at`: update timestamp.

### financial_ratios

Stores formula-versioned ratios derived from `financial_metrics_extracted`.

- `id`: primary key.
- `counterparty_id`: company.
- `uploaded_document_id`: source document.
- `financial_metrics_id`: source financial metrics row; unique one-to-one link.
- `fiscal_year`: reporting year.
- `fiscal_period`: reporting period.
- `currency`: reporting currency.
- `current_ratio`: liquidity coverage from current assets/current liabilities.
- `quick_ratio`: short-term liquidity excluding inventory.
- `cash_ratio`: most conservative liquidity ratio.
- `working_capital`: current assets minus current liabilities.
- `debt_to_equity`: leverage relative to book equity.
- `debt_to_ebitda`: leverage relative to cash earnings.
- `liabilities_to_assets`: balance-sheet solvency pressure.
- `interest_coverage`: EBIT/interest expense debt service capacity.
- `operating_margin`: operating profitability.
- `net_margin`: after-tax profitability.
- `return_on_assets`: profit generated by assets.
- `return_on_equity`: profit generated by equity.
- `formula_version`: version of ratio formulas.
- `calculation_date`: calculation timestamp.
- `input_data_reference`: source row reference.
- `missing_inputs`: JSON of missing inputs by ratio.
- `calculation_warnings`: JSON warnings, such as derived total debt.
- `created_at`: creation timestamp.
- `updated_at`: update timestamp.

### stress_index_history

Stores daily market stress index outputs.

- `id`: primary key.
- `date`: stress date.
- `stress_index`: 0-100 stress score.
- `stress_level`: Calm, Normal, Elevated, Stressed, or Crisis.
- `pc1_score`: PCA first principal component score.
- `explained_variance_ratio`: variance explained by PC1.
- `pca_loadings`: JSON loadings by component.
- `top_positive_drivers`: JSON strongest positive stress drivers.
- `top_negative_drivers`: JSON offsetting/negative drivers.
- `component_values`: JSON z-score components used that day.
- `available_components`: JSON list of available inputs.
- `missing_components`: JSON list of unavailable inputs.
- `model_version`: stress model version.
- `data_source`: source table/process.
- `created_at`: creation timestamp.
- `updated_at`: update timestamp.

### market_regime_history

Stores learned market regime labels.

- `id`: primary key.
- `date`: regime date.
- `regime_id`: cluster/state ID.
- `regime_label`: Stable Market, Commodity Stress, USD Stress, Risk-Off, Crisis, etc.
- `regime_probability`: confidence/probability of the regime assignment.
- `regime_characteristics`: JSON cluster interpretation.
- `feature_values`: JSON stress component values.
- `model_version`: regime model version.
- `data_source`: data/process source.
- `created_at`: creation timestamp.
- `updated_at`: update timestamp.

### pd_model_predictions

Stores probability-of-default model outputs.

- `id`: primary key.
- `run_id`: unique model run identifier.
- `counterparty_id`: company.
- `financial_metrics_id`: source financial data.
- `financial_ratios_id`: source ratio data.
- `model_name`: model display name.
- `model_version`: model version.
- `structural_pd`: Merton-style PD.
- `ml_pd`: logistic/trained ML cross-check PD.
- `final_pd`: blended final PD.
- `classification_label`: internal grade A, BBB, BB, B, or CCC.
- `model_confidence`: confidence derived from model agreement.
- `model_disagreement`: whether structural and ML PD diverge materially.
- `pd_divergence`: absolute PD difference.
- `distance_to_default`: Merton distance-to-default.
- `asset_value_proxy`: asset value used by structural model.
- `debt_threshold`: debt/default threshold.
- `asset_volatility`: estimated asset volatility.
- `risk_free_rate`: rate used in structural formula.
- `time_horizon_years`: PD horizon, usually one year.
- `commodity_sensitivity_score`: fuel/commodity vulnerability.
- `fx_sensitivity_score`: FX/USD vulnerability.
- `macro_sensitivity_score`: broad macro vulnerability.
- `market_stress_index`: latest stress score included.
- `market_regime`: latest regime included.
- `feature_contributions`: JSON ML/logistic feature contributions.
- `model_assumptions`: JSON assumptions and diagnostics.
- `input_data_reference`: JSON lineage to source rows.
- `warnings`: JSON model warnings.
- `created_at`: run timestamp.

### trade_exposures

Stores requested or tested trade credit exposure terms.

- `id`: primary key.
- `counterparty_id`: company.
- `invoice_amount`: invoice amount if known.
- `fuel_volume`: fuel quantity.
- `fuel_price`: unit fuel price.
- `approved_credit_limit`: existing approved limit.
- `requested_credit_limit`: new requested limit.
- `outstanding_receivables`: existing unpaid receivables.
- `payment_tenor_days`: payment term length.
- `utilization_rate`: expected utilization of invoice/limit.
- `collateral_type`: unsecured, letter of credit, guarantee, cash deposit, secured collateral.
- `letter_of_credit_flag`: explicit LC flag.
- `guarantee_flag`: explicit guarantee flag.
- `deposit_percentage`: cash deposit percentage.
- `counterparty_type`: business segment.
- `country_risk_score`: country risk input.
- `seniority_score`: recovery seniority input.
- `notes`: analyst notes.
- `created_at`: creation timestamp.

### loss_estimates

Stores LGD, EAD, and expected loss outputs.

- `id`: primary key.
- `run_id`: unique run identifier.
- `counterparty_id`: company.
- `pd_prediction_id`: linked PD result.
- `trade_exposure_id`: linked exposure terms.
- `model_name`: model name.
- `model_version`: model version.
- `probability_of_default`: PD used.
- `predicted_lgd`: estimated loss severity.
- `exposure_at_default`: estimated exposure if default occurs.
- `expected_loss`: PD * LGD * EAD.
- `collateral_strength`: normalized collateral protection score.
- `liquidity_score`: liquidity input if available.
- `ead_cap_applied`: whether EAD was capped by limit.
- `expected_drawdown`: expected additional exposure.
- `invoice_exposure`: invoice amount or fuel volume * fuel price.
- `model_assumptions`: JSON formulas and assumptions.
- `input_data_reference`: JSON lineage.
- `warnings`: JSON warnings.
- `created_at`: run timestamp.

### scenario_results

Stores scenario-level portfolio risk outputs.

- `id`: primary key.
- `run_id`: unique scenario run.
- `scenario_name`: human-readable scenario.
- `scenario_type`: base, adverse, severe, etc.
- `model_name`: scenario/Monte Carlo model name.
- `model_version`: model version.
- `expected_loss`: scenario expected portfolio loss.
- `var_95`: 95% credit VaR.
- `var_99`: 99% credit VaR.
- `expected_shortfall_95`: average loss beyond 95% VaR.
- `expected_shortfall_99`: average loss beyond 99% VaR.
- `expected_shortfall`: compatibility field, usually ES95.
- `unexpected_loss`: loss volatility/std deviation.
- `max_loss`: maximum simulated loss.
- `scenario_inputs`: JSON market shock/scenario inputs.
- `scenario_impacts`: JSON adjusted PD/LGD/EAD by counterparty.
- `input_data_reference`: JSON source rows.
- `assumptions_reference`: JSON model assumptions.
- `number_of_counterparties`: portfolio size.
- `number_of_simulations`: simulation count.
- `random_seed`: reproducibility seed.
- `created_at`: run timestamp.

### simulation_results

Stores Monte Carlo simulation outputs, linked to scenario results.

- `id`: primary key.
- `run_id`: unique simulation run.
- `scenario`: scenario type/name.
- `scenario_result_id`: linked `scenario_results` row.
- `model_name`: simulation model name.
- `model_version`: model version.
- `expected_loss`: mean simulated loss.
- `var_95`: 95% credit VaR.
- `var_99`: 99% credit VaR.
- `expected_shortfall_95`: tail average beyond 95% VaR.
- `expected_shortfall_99`: tail average beyond 99% VaR.
- `expected_shortfall`: compatibility expected shortfall field.
- `unexpected_loss`: standard deviation of losses.
- `avg_defaults`: average simulated default count.
- `max_defaults`: maximum simulated default count.
- `number_of_simulations`: simulation count.
- `random_seed`: reproducibility seed.
- `loss_distribution_summary`: JSON min/p50/p75/p90/p95/p99/max/mean/std.
- `marginal_risk_contribution`: JSON contribution share by counterparty.
- `default_correlation`: copula/default dependence assumption.
- `input_data_reference`: JSON source rows.
- `assumptions_reference`: JSON assumptions and diagnostics.
- `created_at`: run timestamp.

### monte_carlo_runs

Older/simple Monte Carlo summary table kept for compatibility.

- `run_id`: primary key.
- `avg_loss`: average loss.
- `max_loss`: maximum loss.
- `min_loss`: minimum loss.
- `avg_defaults`: average default count.
- `max_defaults`: maximum default count.
- `anomaly_flags_triggered`: number of anomaly flags.
- `n_simulations`: number of simulations.
- `created_at`: run timestamp.

### credit_recommendations

Stores final rules-based credit recommendations.

- `id`: primary key.
- `run_id`: unique decision run.
- `counterparty_id`: company.
- `model_name`: decision engine name.
- `model_version`: decision engine version.
- `probability_of_default`: final PD used.
- `loss_given_default`: LGD used.
- `exposure_at_default`: EAD used.
- `expected_loss`: PD * LGD * EAD.
- `scenario_expected_loss`: scenario loss if available.
- `credit_var_95`: 95% VaR if available.
- `expected_shortfall_95`: ES95 if available.
- `recommended_credit_limit`: final proposed limit.
- `recommended_tenor_days`: final proposed payment tenor.
- `recommended_security`: required security/collateral.
- `risk_grade`: internal grade A/BBB/BB/B/CCC.
- `approval_status`: approved, conditional, secured, reject/prepay only.
- `policy_score`: aggregate policy risk score.
- `limit_haircut`: percentage haircut applied to base limit.
- `key_risk_drivers`: JSON explanation of main risks.
- `mitigating_factors`: JSON explanation of positives.
- `model_assumptions`: JSON policy rules and diagnostics.
- `input_data_reference`: JSON linked PD/loss/scenario/ratio rows.
- `warnings`: JSON missing-data or model warnings.
- `created_at`: run timestamp.

### ai_credit_memos

Stores grounded memo outputs.

- `id`: primary key.
- `run_id`: memo run ID.
- `counterparty_id`: company.
- `credit_recommendation_id`: linked decision row.
- `model_name`: memo model/agent name.
- `model_version`: memo version.
- `memo_text`: generated credit memo.
- `input_data_reference`: JSON source model rows.
- `assumptions_reference`: JSON assumptions.
- `warnings`: JSON warnings or missing-data notes.
- `created_at`: memo timestamp.

### historical_training_dataset

Stores auditable model training rows.

- `id`: primary key.
- `run_id`: training dataset run.
- `counterparty_id`: linked company if available.
- `counterparty_name`: company name.
- `fiscal_year`: reporting year.
- `counterparty_type`: segment.
- `country`: country.
- `data_source`: origin, such as uploaded financials, fallback dataset, or counterfactual augmentation.
- Financial ratio fields: `current_ratio`, `quick_ratio`, `cash_ratio`, `working_capital`, `debt_to_equity`, `debt_to_ebitda`, `liabilities_to_assets`, `interest_coverage`, `operating_margin`, `net_margin`, `return_on_assets`, `return_on_equity`.
- Market fields: `market_stress_index`, `market_regime`, `oil_volatility`, `fuel_return`, `dxy_return`, `vix_level`, `sp500_return`.
- Exposure fields: `country_risk_score`, `payment_tenor_days`, `collateral_type`, `letter_of_credit_flag`, `guarantee_flag`, `deposit_percentage`, `exposure_size`.
- Labels: `proxy_default_risk_score`, `proxy_default_label`, `proxy_lgd_label`.
- Audit fields: `feature_payload`, `label_logic`, `input_data_reference`, `created_at`.

### model_training_runs

Stores model training metadata.

- `id`: primary key.
- `run_id`: unique training run.
- `model_name`: model name.
- `model_version`: version.
- `model_type`: PD, LGD, etc.
- `algorithm`: algorithm used.
- `training_rows`: total rows used.
- `train_rows`: training split size.
- `test_rows`: test split size.
- `target_column`: target label.
- `feature_columns`: JSON list of features.
- `artifact_path`: saved model artifact path.
- `feature_importance`: JSON feature importances.
- `input_data_reference`: JSON source references.
- `assumptions_reference`: JSON assumptions.
- `created_at`: training timestamp.

### model_validation_results

Stores validation metrics and sanity checks.

- `id`: primary key.
- `run_id`: validation run.
- `model_training_run_id`: linked training run.
- `model_name`: model name.
- `model_version`: version.
- `validation_type`: holdout, backtest, sanity check, etc.
- `metrics`: JSON metrics such as AUC, accuracy, RMSE, MAE, etc.
- `sanity_checks`: JSON directional/business-rule checks.
- `train_start_year`: training window start.
- `train_end_year`: training window end.
- `test_start_year`: test window start.
- `test_end_year`: test window end.
- `assumptions_reference`: JSON validation assumptions.
- `created_at`: validation timestamp.

## 6. How to Explain Design Choices

- I separated raw inputs, engineered features, model outputs, recommendations, and AI explanations into separate tables so every number has lineage.
- I used run IDs and model versions because credit risk systems must be auditable and reproducible.
- I stored JSON assumptions/warnings because many financial and market inputs may be missing, proxied, or derived.
- I used transparent formulas for ratios and expected loss so the decision logic can be explained to a credit officer.
- I used a structural PD model as an anchor and ML as a cross-check to avoid black-box-only credit decisions.
- I used scenario analysis and Monte Carlo because point estimates like expected loss do not show tail risk.
- I made AI read from stored outputs only, so it explains decisions rather than fabricating credit numbers.

## 7. Strong Interview Answer

"This is a fuel trade credit risk engine. It evaluates whether we should extend credit to a counterparty and recommends limit, tenor, and security. The pipeline starts with financial statement ingestion, stores extracted financial metrics, calculates ratios, builds market stress and regime indicators from fuel/macro data, estimates PD using a Merton structural model plus ML cross-check, calculates LGD/EAD/expected loss from collateral and exposure terms, runs scenario and Monte Carlo tail-risk analysis, and finally applies a rules-based credit policy to produce a recommendation. The important design principle is auditability: every output table stores model version, run ID, source references, assumptions, and warnings. AI is only used to summarize and explain grounded data; it is not the source of the credit numbers."


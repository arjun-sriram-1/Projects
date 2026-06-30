# Free Source CSV Schemas

These schemas define the Phase 2 CSV contract for free-source model calibration.
The files are staging inputs only; they do not affect the current app until
future import and training scripts read them.

## 1. company_financials.csv

Location:

```text
data/external/free_sources/sec_financials/company_financials.csv
```

Purpose:

Historical company financial statements and ratios for PD model training.

Required columns:

| Column | Type | Description |
|---|---|---|
| `company_id` | string | Stable source identifier such as CIK, ticker, or custom ID. |
| `company_name` | string | Company legal or display name. |
| `ticker` | string | Market ticker when available. |
| `cik` | string | SEC CIK when available. |
| `fiscal_year` | integer | Fiscal year. |
| `period_end_date` | date | Statement period end date. |
| `currency` | string | Reporting currency. |
| `industry` | string | Industry or sector label. |
| `country` | string | Country or domicile. |
| `revenue` | float | Revenue. |
| `ebitda` | float | EBITDA. |
| `ebit` | float | EBIT. |
| `interest_expense` | float | Interest expense. |
| `net_income` | float | Net income. |
| `cash_and_equivalents` | float | Cash and equivalents. |
| `accounts_receivable` | float | Receivables. |
| `inventory` | float | Inventory. |
| `current_assets` | float | Current assets. |
| `current_liabilities` | float | Current liabilities. |
| `total_assets` | float | Total assets. |
| `total_debt` | float | Total debt. |
| `total_liabilities` | float | Total liabilities. |
| `shareholders_equity` | float | Shareholders equity. |
| `operating_cash_flow` | float | Operating cash flow. |
| `free_cash_flow` | float | Free cash flow. |
| `data_source` | string | Source name, such as `sec_xbrl`, `manual_csv`, or `synthetic`. |

Optional precomputed columns:

- `current_ratio`
- `quick_ratio`
- `cash_ratio`
- `working_capital`
- `debt_to_equity`
- `debt_to_ebitda`
- `liabilities_to_assets`
- `interest_coverage`
- `operating_margin`
- `net_margin`
- `return_on_assets`
- `return_on_equity`

## 2. market_context.csv

Location:

```text
data/external/free_sources/market/market_context.csv
```

Purpose:

Historical market and macro context aligned by date for PD/scenario calibration.

Required columns:

| Column | Type | Description |
|---|---|---|
| `date` | date | Observation date. |
| `brent_oil` | float | Brent price or index. |
| `crude_oil` | float | WTI/crude price or index. |
| `heating_oil_proxy` | float | Heating oil proxy. |
| `jet_fuel_proxy` | float | Jet fuel proxy when available. |
| `vix` | float | Equity volatility/fear index. |
| `sp500` | float | S&P 500 level or return input. |
| `dxy` | float | USD index. |
| `gold` | float | Gold price/index. |
| `us_10y_yield` | float | 10-year yield. |
| `us_2y_yield` | float | 2-year yield. |
| `yield_curve_spread` | float | 10Y-2Y or similar spread. |
| `cpi_index` | float | CPI or inflation index. |
| `freight_proxy` | float | Freight/trade proxy. |
| `data_source` | string | Source name, such as `fred`, `eia`, `yfinance`, or `manual_csv`. |

Optional columns:

- `stress_index`
- `market_regime`
- `recession_flag`
- `high_yield_spread`
- `country_risk_score`

## 3. default_labels.csv

Location:

```text
data/external/free_sources/default_labels/default_labels.csv
```

Purpose:

Default or proxy-default labels for PD model training.

Required columns:

| Column | Type | Description |
|---|---|---|
| `company_id` | string | Same identifier used in `company_financials.csv`. |
| `company_name` | string | Company name. |
| `label_date` | date | Date of default/distress event or label observation. |
| `default_label` | integer | `1` for default/proxy default, `0` for non-default. |
| `default_type` | string | `bankruptcy`, `missed_payment`, `distress_proxy`, `going_concern`, `non_default`, etc. |
| `label_horizon_months` | integer | Prediction horizon represented by the label, usually `12`. |
| `source_reference` | string | Filing, URL, source file, or note. |
| `data_source` | string | Source name. |

Optional columns:

- `bankruptcy_chapter`
- `delisting_flag`
- `going_concern_flag`
- `restructuring_flag`
- `rating_downgrade_flag`

## 4. recovery_proxy.csv

Location:

```text
data/external/free_sources/recovery_proxy/recovery_proxy.csv
```

Purpose:

Recovery-rate or LGD proxy data for LGD and collateral calibration.

Required columns:

| Column | Type | Description |
|---|---|---|
| `company_id` | string | Company or exposure identifier. |
| `company_name` | string | Company name. |
| `default_date` | date | Default/distress date. |
| `facility_id` | string | Loan/facility/exposure identifier when available. |
| `collateral_type` | string | `unsecured`, `letter_of_credit`, `cash_deposit`, `guarantee`, `secured_collateral`, etc. |
| `seniority` | string | Seniority label. |
| `exposure_at_default` | float | EAD. |
| `recovery_amount` | float | Amount recovered. |
| `recovery_rate` | float | Recovery rate from `0` to `1`. |
| `lgd` | float | LGD from `0` to `1`; if missing, future scripts can compute `1 - recovery_rate`. |
| `country` | string | Country or jurisdiction. |
| `data_source` | string | Source name. |

Optional columns:

- `resolution_date`
- `days_to_recovery`
- `legal_cost`
- `write_off_amount`
- `guarantor_type`

## 5. trade_exposure_history.csv

Location:

```text
data/external/free_sources/trade_exposure_history/trade_exposure_history.csv
```

Purpose:

Historical trade credit behavior for EAD/utilization and policy calibration.

Required columns:

| Column | Type | Description |
|---|---|---|
| `company_id` | string | Company identifier. |
| `company_name` | string | Company name. |
| `observation_date` | date | Observation date. |
| `invoice_amount` | float | Invoice amount. |
| `fuel_volume` | float | Fuel volume when available. |
| `fuel_price` | float | Fuel unit price when available. |
| `approved_credit_limit` | float | Approved limit. |
| `requested_credit_limit` | float | Requested limit. |
| `outstanding_receivables` | float | Current receivables. |
| `payment_tenor_days` | integer | Payment tenor. |
| `utilization_rate` | float | Limit utilization from `0` to `1`. |
| `collateral_type` | string | Security/collateral type. |
| `letter_of_credit_flag` | integer | `1` if LC exists, else `0`. |
| `guarantee_flag` | integer | `1` if guarantee exists, else `0`. |
| `deposit_percentage` | float | Cash deposit percentage. |
| `days_past_due` | integer | Days past due, if any. |
| `default_or_writeoff_flag` | integer | `1` if default/writeoff occurred, else `0`. |
| `realized_ead` | float | Observed exposure at default or peak exposure. |
| `data_source` | string | Source name. |

Optional columns:

- `payment_date`
- `due_date`
- `write_off_amount`
- `recovery_amount`
- `country_risk_score`
- `counterparty_type`

## Validation Rules

- Every file must include `data_source`.
- Use blank cells for unknown numeric values; do not use text like `N/A` in numeric columns.
- Use `0`/`1` for binary flags.
- Use decimals for rates: `0.25`, not `25%`.
- Keep raw files unchanged; future importers should write cleaned files to `data/processed/calibration/`.


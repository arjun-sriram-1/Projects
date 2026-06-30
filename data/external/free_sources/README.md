# Free Source Calibration Data

This folder is the staging area for free historical datasets used to calibrate
PD, LGD, EAD, collateral, scenario, and correlation assumptions.

It is intentionally separate from the existing application pipeline. Dropping
CSV files here does not change model behavior until import/training scripts are
run in later phases.

## Folders

- `sec_financials/`: public-company financial statements and ratios from SEC data.
- `market/`: market, fuel, macro, FX, rates, and stress-context time series.
- `default_labels/`: default, bankruptcy, distress, or proxy-default labels.
- `recovery_proxy/`: recovery-rate or LGD proxy observations.
- `trade_exposure_history/`: utilization, receivables, invoice, tenor, collateral, and exposure history.

## Rules

- Keep real and synthetic rows distinguishable with `data_source`.
- Do not store API keys, secrets, private uploads, or paid/licensed datasets here.
- Prefer raw source files in these folders and cleaned outputs in `data/processed/calibration/`.
- Dates should use ISO format: `YYYY-MM-DD`.
- Monetary values should be numeric and expressed in the row currency.


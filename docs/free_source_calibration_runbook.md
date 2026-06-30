# Free Source Calibration Runbook

This runbook explains the clean calibration pipeline added after Phase 1 and
Phase 2. It does not replace the current app workflow. It only creates optional
artifacts that the live models use when available.

## What This Adds

Scripts:

```powershell
python -m api.scripts.download_free_calibration_data
python -m api.scripts.generate_synthetic_trade_history
python -m api.scripts.build_free_calibration_datasets
python -m api.scripts.train_free_calibration_models
python -m api.scripts.validate_free_calibration_models
python -m api.scripts.inspect_calibration_artifacts
python -m api.scripts.run_free_calibration_pipeline
```

Optional artifacts:

```text
data/models/historical_pd_model.pkl
data/models/historical_lgd_model.pkl
data/models/calibrated_ead_model.pkl
data/models/pd_blend_config.json
data/models/collateral_strength_config.json
data/models/scenario_multiplier_config.json
data/models/default_correlation_config.json
```

Reports:

```text
data/reports/calibration/dataset_build_summary.json
data/reports/calibration/training_summary.json
data/reports/calibration/validation_report.json
data/reports/calibration/artifact_manifest.json
data/reports/calibration/synthetic_trade_history_summary.json
```

## Download Free Sources

Light public download:

```powershell
python -m api.scripts.download_free_calibration_data --all-light --start-year 2020
```

Includes:

- SEC quarterly Financial Statement Data Set ZIPs
- World Bank selected indicators
- yfinance market proxies

Large SEC companyfacts bulk ZIP:

```powershell
python -m api.scripts.download_free_calibration_data --sec-companyfacts
```

This can be very large. Use only when you want a bulk source archive.

## Build Datasets

```powershell
python -m api.scripts.build_free_calibration_datasets
```

Outputs:

```text
data/processed/calibration/pd_training_dataset.csv
data/processed/calibration/lgd_training_dataset.csv
data/processed/calibration/ead_training_dataset.csv
```

By default, the builder may create transparent proxy default labels from
financial distress when explicit default labels are missing. To require only
explicit labels:

```powershell
python -m api.scripts.build_free_calibration_datasets --no-proxy-labels
```

## Phase 6: Generate Synthetic Trade Recovery History

```powershell
python -m api.scripts.generate_synthetic_trade_history --rows 5000 --seed 42 --overwrite
```

This creates realistic but explicitly synthetic rows in:

```text
data/external/free_sources/recovery_proxy/recovery_proxy.csv
data/external/free_sources/trade_exposure_history/trade_exposure_history.csv
data/reports/calibration/synthetic_trade_history_summary.json
```

The generator models collateral type, seniority, country risk, payment tenor,
exposure at default, recovery amount, legal cost, days to recovery, and LGD.
Every row has `data_source = synthetic_phase6_trade_recovery`, so the model
governance reports can distinguish these rows from real internal observations.

## Phase 7: Train LGD And Collateral Calibration

```powershell
python -m api.scripts.build_free_calibration_datasets
python -m api.scripts.train_free_calibration_models
python -m api.scripts.validate_free_calibration_models
python -m api.scripts.inspect_calibration_artifacts
```

This creates:

```text
data/models/historical_lgd_model.pkl
data/models/collateral_strength_config.json
```

Because the phase 6 trade file also includes realized EAD fields, the existing
trainer may also create:

```text
data/models/calibrated_ead_model.pkl
```

That EAD artifact is useful for pipeline completeness, but it should still be
treated as synthetic/proxy calibrated until real utilization and exposure-at-
default history is supplied.

## Phase 8: Activate EAD Cross-Check

When `data/models/calibrated_ead_model.pkl` exists, the live loss engine keeps
the transparent formula path:

```text
EAD = min(limit, outstanding_receivables + expected_drawdown)
```

and blends it with the trained EAD artifact as a cross-check. The cap by
approved/requested limit remains active, so the trained artifact cannot create
an impossible exposure above the credit limit. Validation reports include MAE,
RMSE, mean actual EAD, mean predicted EAD, and median absolute error.

## Phase 9: Calibrate PD Blend Weights

The training script now writes calibrated structural/ML blend weights to:

```text
data/models/pd_blend_config.json
```

If explicit `structural_pd` and `ml_pd` backtest columns are present, it uses
those. Otherwise, it derives structural PD from the Merton-style financial
inputs and derives ML PD from the trained historical PD artifact plus the
interpretable logistic proxy. It then grid-searches the structural weight that
minimizes Brier score against the available default/proxy-default labels.

## Phase 10: Calibrate Scenario Stress Multipliers

The training script now calibrates:

```text
data/models/scenario_multiplier_config.json
```

It estimates:

- `pd_stress_coefficient` from high-vs-low market stress default/proxy-default rates
- `lgd_stress_coefficient` from high-vs-low stress LGD observations
- `ead_commodity_coefficient` and `ead_commodity_cap` from high-vs-low commodity-price utilization/EAD behavior

The live Monte Carlo engine already reads this config. Its assumptions output
now reports the actual calibrated coefficients used in the run.

## Phase 11: Calibrate Default Correlation

The training script now calibrates:

```text
data/models/default_correlation_config.json
```

It estimates base default correlation from year-level default/proxy-default
clustering and derives stress/VIX coefficients from how default rates move
across higher-stress periods. This replaces the previous purely default
correlation settings while keeping min/max guardrails.

## Phase 12: Frontend Model Transparency

The backend exposes calibration governance through:

```text
GET /api/v1/calibration/status
```

The Quant & Monte Carlo page now shows a Calibration Transparency panel with:

- active artifacts
- PD blend weights
- PD/LGD/EAD validation metrics
- scenario and correlation calibration methods
- readiness flags
- synthetic/proxy data notes

## Phase 13: Final Interview And Production Guide

The full calibration story is documented in:

```text
CALIBRATION_PHASES_FINAL_GUIDE.md
```

Use that file to explain what was implemented, which data is real, which data is
synthetic/proxy, which artifacts are active, and how to defend the limitations
in an interview.

## Train Artifacts

```powershell
python -m api.scripts.train_free_calibration_models
```

Training is safe:

- If enough data exists, artifacts are written.
- If not enough data exists, the report explains why training was skipped.
- The current application still works either way.

## Phase 4: Validate Artifacts

```powershell
python -m api.scripts.validate_free_calibration_models
```

This creates:

```text
data/reports/calibration/validation_report.json
```

The validation report includes:

- PD feature coverage
- label balance
- Brier score, AUC, and log loss
- calibration bins comparing predicted PD to observed/proxy default rate
- year-by-year sanity checks when period dates are available
- clear missing-data reasons for LGD and EAD

Important: the current free-source PD report is an in-sample proxy-label
validation report. It is useful for sanity checks and interviews, but it is not
a bank-grade observed-default backtest until real default history is supplied.

## Phase 5: Inspect Runtime Artifacts

```powershell
python -m api.scripts.inspect_calibration_artifacts
```

This creates:

```text
data/reports/calibration/artifact_manifest.json
```

The manifest records which optional model/config artifacts exist, where they
are stored, SHA-256 hashes, modified times, runtime use, and fallback behavior.
It is an audit/governance layer and does not mutate model behavior.

## Run Everything

```powershell
python -m api.scripts.run_free_calibration_pipeline --download --all-light --start-year 2020
```

The full runner now performs:

```text
download -> build datasets -> train artifacts -> validate artifacts -> write manifest
```

To include phase 6 synthetic trade history in the runner:

```powershell
python -m api.scripts.run_free_calibration_pipeline --generate-synthetic-trades --synthetic-trade-rows 5000
```

For faster local runs:

```powershell
python -m api.scripts.run_free_calibration_pipeline --skip-validation
python -m api.scripts.run_free_calibration_pipeline --skip-manifest
```

## Live Pipeline Integration

The current app keeps its existing workflow:

```text
financials -> ratios -> PD -> LGD/EAD/EL -> scenarios -> recommendation
```

The live model code now checks optional calibration artifacts:

- PD still uses the existing structural + ML flow.
- If `historical_pd_model.pkl` exists, the trained model is used as the ML cross-check.
- If `pd_blend_config.json` exists, calibrated blend weights replace the default `0.65 / 0.35`.
- If `historical_lgd_model.pkl` exists, LGD uses the trained artifact as a cross-check.
- If `collateral_strength_config.json` exists, collateral scores are read from data.
- If scenario/correlation configs exist, Monte Carlo stress multipliers and default correlation use them.
- If any artifact is missing or invalid, the old hardcoded fallback remains active.

## Important Limitation

Free public data can improve feature calibration, market context, and proxy
labels. True corporate defaults, trade receivable behavior, and recoveries are
usually proprietary. The free-source pipeline is therefore a precision upgrade,
not a full replacement for bank/internal data.

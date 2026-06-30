# Calibration Phases Final Guide

This document explains what the 13 calibration phases added to the credit risk
project and how to explain them in an interview.

## One-Line Summary

The project started as a formula-driven credit risk workflow and was upgraded
into a fallback-safe, data-calibrated credit decision engine with historical
financial data, synthetic trade recovery data, trained artifacts, validation
reports, runtime governance, and frontend model transparency.

## Core Credit Flow

```text
counterparty financials
-> financial ratios
-> market stress and regime context
-> structural PD and ML PD
-> blended final PD
-> LGD, EAD, and expected loss
-> Monte Carlo portfolio loss simulation
-> credit recommendation
```

The calibration work does not remove this flow. It adds optional artifacts that
the live pipeline uses when available. If an artifact is missing or invalid, the
existing fallback logic still works.

## Phase Rundown

| Phase | What Was Implemented | Main Output |
|---|---|---|
| 1 | Created clean external/processed/model/report folders | `data/external/free_sources`, `data/processed/calibration` |
| 2 | Defined CSV contracts for free-source calibration data | `docs/free_source_csv_schemas.md` |
| 3 | Downloaded free SEC, World Bank, and market data; trained historical PD | `historical_pd_model.pkl` |
| 4 | Added validation reports for PD/LGD/EAD artifacts | `validation_report.json` |
| 5 | Added runtime artifact registry and governance manifest | `artifact_manifest.json` |
| 6 | Generated realistic synthetic trade/recovery history | `recovery_proxy.csv`, `trade_exposure_history.csv` |
| 7 | Trained LGD and collateral calibration from recovery rows | `historical_lgd_model.pkl`, `collateral_strength_config.json` |
| 8 | Activated calibrated EAD as a live cross-check | `calibrated_ead_model.pkl` used in loss engine |
| 9 | Calibrated structural/ML PD blend weights | `pd_blend_config.json` |
| 10 | Calibrated scenario stress multipliers | `scenario_multiplier_config.json` |
| 11 | Calibrated default correlation | `default_correlation_config.json` |
| 12 | Added frontend calibration transparency | Quant page calibration panel |
| 13 | Added final documentation and interview explanation | This guide |

## Active Artifacts

```text
data/models/historical_pd_model.pkl
data/models/historical_lgd_model.pkl
data/models/calibrated_ead_model.pkl
data/models/pd_blend_config.json
data/models/collateral_strength_config.json
data/models/scenario_multiplier_config.json
data/models/default_correlation_config.json
```

These are summarized by:

```text
data/reports/calibration/artifact_manifest.json
```

The frontend reads the same governance data through:

```text
GET /api/v1/calibration/status
```

## Current Calibration Results

PD:

```text
Training rows: 157,029
Structural / ML blend: 40% / 60%
Calibrated blend Brier score: about 0.2101
Structural-only Brier score: about 0.2908
ML-only Brier score: about 0.2465
```

LGD:

```text
Training rows: 5,000 synthetic/proxy recovery rows
Train/test MAE: about 0.1132
Train/test RMSE: about 0.1465
```

EAD:

```text
Training rows: 5,000 synthetic/proxy trade rows
Validation MAE: about $301.9K
Validation RMSE: about $664.0K
```

Scenario stress:

```text
PD stress coefficient: 0.030
LGD stress coefficient: 0.010
EAD commodity coefficient: 0.005
EAD commodity cap: 0.150
```

Default correlation:

```text
Base correlation: about 0.0636
Stress coefficient: about 0.0482
VIX stress coefficient: 0.0050
Correlation bounds: 0.0300 to 0.5500
```

## What Is Real, Proxy, And Synthetic

Real/free public data:

- SEC quarterly financial statement datasets
- World Bank macro indicators
- yfinance market proxies
- market stress and commodity signals derived from public market history

Proxy labels:

- PD default labels are based on transparent financial distress rules when real
  observed default labels are not available.
- This is acceptable for a student/research project, but not a final bank model.

Synthetic/proxy data:

- LGD and EAD training use phase 6 synthetic trade recovery rows.
- Each row is tagged with `data_source = synthetic_phase6_trade_recovery`.
- These rows model plausible credit behavior: collateral type, country risk,
  tenor, recovery amount, legal cost, days to recovery, write-off amount, and
  exposure at default.

Not yet real/internal:

- Observed bank defaults
- Real recovery collections
- Real write-offs
- Actual utilization at default
- Contract-level collateral enforcement outcomes

## Interview Explanation

Use this explanation:

> I built a credit risk decision engine for jet fuel trade credit. The original
> workflow calculated financial ratios, structural Merton PD, LGD/EAD, expected
> loss, Monte Carlo risk, and credit recommendations. Then I added a calibration
> layer so the system no longer relies only on hardcoded assumptions.
>
> For PD, I used free SEC financial statement data and public market data to
> build a historical training dataset. The system now combines Merton structural
> PD with a trained ML PD cross-check, and the structural/ML blend weights are
> calibrated by minimizing Brier score.
>
> For LGD and EAD, public data does not contain internal recoveries or exposure
> at default, so I created transparent synthetic trade recovery history. I marked
> every row as synthetic and used it to train LGD/EAD artifacts and collateral
> recovery mappings. This makes the pipeline complete while clearly separating
> proxy calibration from real bank calibration.
>
> I also added validation reports, artifact manifests, model readiness checks,
> and a frontend transparency panel so a reviewer can see which models are
> active, which data sources were used, and where fallback logic still applies.

## How To Defend The Limitations

If asked whether this is production-ready, say:

> The architecture is production-style, but the labels are not production-grade
> until internal default, recovery, and utilization history is supplied. I
> designed it so real data can replace the synthetic/proxy CSVs without changing
> the live application flow.

If asked why synthetic LGD/EAD data is used, say:

> Free public sources do not publish trade-level recoveries, write-offs, and EAD.
> Rather than hiding that gap, I made it explicit. Synthetic rows are tagged,
> documented, validated separately, and can be replaced by real internal rows.

If asked what the biggest improvement was, say:

> The biggest improvement is governance. The system now has model artifacts,
> validation metrics, runtime manifests, fallback logic, and frontend
> transparency. It can explain not just the answer, but which model produced it
> and how reliable that model is.

## Commands

Run the full local calibration pipeline:

```powershell
python -m api.scripts.run_free_calibration_pipeline
```

Generate synthetic trade recovery rows:

```powershell
python -m api.scripts.generate_synthetic_trade_history --rows 5000 --seed 42 --overwrite
```

Validate artifacts:

```powershell
python -m api.scripts.validate_free_calibration_models
```

Inspect runtime artifacts:

```powershell
python -m api.scripts.inspect_calibration_artifacts
```

## Final Status

The current system is fallback-safe and interview-ready. PD uses real public
financial and market data. LGD/EAD use transparent synthetic/proxy trade data.
Scenario and correlation assumptions are calibrated from available historical
signals. The UI now exposes model readiness, validation metrics, artifacts, and
limitations instead of hiding them.

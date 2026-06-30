# V1 To V2 Migration Map

Status: Implementation through Phase 8 is migrated into V2 and regression-tested. V1 remains read-only reference code.

V1 reference:

```text
D:\ARJUN\Arjun\Jet Fuel Trade Risk\CREDIT_RISK_PROJECT_V1
```

V2 active project:

```text
D:\ARJUN\Arjun\Jet Fuel Trade Risk\CREDIT_RISK_PROJECT_V2
```

## Migration Principles

- V1 remains read-only.
- Migrate one functional slice at a time.
- Before moving a file, check its imports, file path constants, model artifacts, vector artifacts, and tests.
- Do not copy `.env`, generated memo files, model artifacts, FAISS indexes, uploaded documents, or processed datasets unless explicitly approved.
- Prefer V2 path conventions immediately. Do not preserve old hardcoded paths such as `models/ml/*.pkl` or `rag/data/*.faiss`.
- Use compatibility wrappers only when needed to preserve behavior during staged migration.
- Run focused tests after every migration slice.

## High-Risk Dependencies Found In V1

### Hardcoded ML Artifacts

These must move to `data/models/` in V2 and be read through central settings, not hardcoded strings:

| V1 reference | V2 target |
|---|---|
| `models/ml/pd_model.pkl` | `data/models/pd_model.pkl` |
| `models/ml/lgd_model.pkl` | `data/models/lgd_model.pkl` |
| `models/ml/cluster_model.pkl` | `data/models/cluster_model.pkl` |
| `models/ml/cluster_scaler.pkl` | `data/models/cluster_scaler.pkl` |
| `models/ml/anomaly_model.pkl` | `data/models/anomaly_model.pkl` |
| `models/ml/anomaly_scaler.pkl` | `data/models/anomaly_scaler.pkl` |
| `models/ml/training_metadata.pkl` | `data/models/training_metadata.pkl` |
| `models/ml/historical_pd_model.pkl` | `data/models/historical_pd_model.pkl` |
| `models/ml/historical_lgd_model.pkl` | `data/models/historical_lgd_model.pkl` |

Known V1 files that reference these:

- `models/ml/default_model.py`
- `models/ml/lgd_model.py`
- `models/ml/clustering.py`
- `models/ml/anomaly_detection.py`
- `models/credit/pd_model.py`
- `models/credit/loss_model.py`
- `historical_training/train_pd_model.py`
- `historical_training/train_lgd_model.py`
- `pipelines/train.py`
- `pipelines/populate_model_predictions.py`

Migration requirement:

- Create V2 settings/path helpers before moving these modules.
- Update imports and path constants to use `api/core/config.py` or a dedicated artifact path helper.
- Do not copy artifacts during code migration unless the user approves.

### Hardcoded RAG Vector Artifacts

These must move to `data/vector_store/` in V2:

| V1 reference | V2 target |
|---|---|
| `rag/data/counterparty_index.faiss` | `data/vector_store/counterparty_index.faiss` |
| `rag/data/counterparty_metadata.pkl` | `data/vector_store/counterparty_metadata.pkl` |
| `rag/data/stress_index.faiss` | `data/vector_store/stress_index.faiss` |
| `rag/data/stress_metadata.pkl` | `data/vector_store/stress_metadata.pkl` |
| `rag/data/montecarlo_index.faiss` | `data/vector_store/montecarlo_index.faiss` |
| `rag/data/montecarlo_metadata.pkl` | `data/vector_store/montecarlo_metadata.pkl` |
| `rag/data/policy_index.faiss` | `data/vector_store/policy_index.faiss` |
| `rag/data/policy_metadata.pkl` | `data/vector_store/policy_metadata.pkl` |

Known V1 files that reference these:

- `rag/retriever/counterparty_retriever.py`
- `rag/retriever/stress_retriever.py`
- `rag/retriever/montecarlo_retriever.py`
- `rag/retriever/policy_retriever.py`
- `rag/embeddings/build_counterparty_embeddings.py`
- `rag/embeddings/build_stress_embeddings.py`
- `rag/embeddings/build_montecarlo_embeddings.py`
- `rag/embeddings/build_policy_embeddings.py`
- `tests/test_index.py`

Migration requirement:

- Centralize vector-store paths before migrating retrievers.
- Avoid import-time FAISS loading where possible; lazy-load indexes so tests and API startup do not fail when artifacts are absent.

### Backend Imports Dashboard Helpers

V1 has backend/RAG/reporting code importing `dashboard.components.database`, which should not continue in V2.

Known files:

- `api/rag_routes.py`
- `rag/agents/credit_committee_agent.py`
- `reporting/report_generator.py`
- `risk_monitoring/alert_engine.py`

Migration requirement:

- Move shared SQL query helpers into backend/shared or service modules.
- In V2, `web/` may call backend APIs or API clients, but backend code must not import `web/`.

### SQLAlchemy Base Duplication

V1 has:

- `database/db_connection.py` defining `Base`
- `models/phase2_orm.py` defining its own `Base`

Migration requirement:

- V2 should use a single declarative base in `api/db/base.py`.
- ORM models should import `Base` from `api/db/base.py`.
- This should be handled early because many tests and services depend on ORM models.

## Target Module Mapping

### Core And Database

| V1 path | V2 target | Notes |
|---|---|---|
| `database/db_connection.py` | `api/db/session.py` | Preserve `engine`, `SessionLocal`, `get_db`; read `DB_URL` from env. |
| `models/phase2_orm.py` | `api/db/models.py` or domain `models.py` files | Split later if needed; first migrate intact with unified `Base`. |
| `database/schema.sql` | `database/schema.sql` | Copy with no schema rename in first slice. |
| `verify_schema.py` | `api/scripts/verify_schema.py` | Update imports to V2 db session. |
| `config/` | `api/core/` | Inspect before copying; migrate only active settings. |

Recommended first implementation slice:

```text
api/db/base.py
api/db/session.py
api/db/models.py
database/schema.sql
api/scripts/verify_schema.py
tests/test_phase1_setup.py
```

### Documents And Financials

| V1 path | V2 target | Import updates |
|---|---|---|
| `ingestion/pdf_parser.py` | `api/documents/pdf_parser.py` | Update route/service imports from `ingestion` to `api.documents`. |
| `api/routes_phase2.py` | `api/documents/router.py` | Update DB and ORM imports. |
| `api/schemas_phase2.py` | `api/documents/schemas.py` | Keep response models close to router. |
| `analytics/financial_ratios.py` | `api/shared/financial_ratios.py` | Pure formula module; good early migration candidate. |
| `analytics/financial_ratio_service.py` | `api/financials/service.py` | Update ORM import to V2 db models. |
| `api/routes_phase3.py` | `api/financials/router.py` | Update service/schema imports. |
| `api/schemas_phase3.py` | `api/financials/schemas.py` | Keep with financials domain. |

Important dependencies:

- `financial_ratio_service.py` imports `analytics.financial_ratios` and `models.phase2_orm`.
- `routes_phase3.py` imports `analytics.financial_ratio_service`, `database.db_connection`, and `models.phase2_orm`.
- Migrate DB/ORM before this slice.

### Market Data And Intelligence

| V1 path | V2 target | Notes |
|---|---|---|
| `models/market/*.py` | `api/market_data/` | Separate providers, calculations, and services if practical. |
| `models/stress_index.py` | `api/market_data/stress_index.py` or `api/stress_testing/stress_index.py` | Keep PCA logic quant-auditable. |
| `models/regime_detection.py` | `api/market_data/regime_detection.py` | Preserve model version constants. |
| `pipelines/fetch_market_data.py` | `api/scripts/fetch_market_data.py` | Update paths to V2 data folders. |
| `pipelines/fetch_external_market_data.py` | `api/scripts/fetch_external_market_data.py` | Update imports. |
| `pipelines/build_stress_regimes.py` | `api/scripts/build_stress_regimes.py` | Imports stress/regime modules and db engine. |
| `api/routes_phase4.py` | `api/market_data/router.py` | Thin route only. |
| `api/schemas_phase4.py` | `api/market_data/schemas.py` | Domain schemas. |

Path hazards:

- Many pipelines write to `data/raw/*.csv` and `data/processed/*.csv`.
- In V2, keep these paths but centralize them through settings later.

### Credit Risk Models

| V1 path | V2 target | Notes |
|---|---|---|
| `models/credit/pd_model.py` | `api/machine_learning/pd_model.py` or `api/credit_decision/pd_model.py` | Contains historical model artifact dependency. |
| `models/credit/pd_service.py` | `api/machine_learning/pd_service.py` | Uses ORM financial data. |
| `models/credit/loss_model.py` | `api/machine_learning/loss_model.py` | Contains LGD artifact dependency and EAD/EL logic. |
| `models/credit/loss_service.py` | `api/machine_learning/loss_service.py` | Persists model predictions/loss estimates. |
| `models/structural/*` | `api/structural_credit/` | Merton imports old ML default model; refactor carefully. |
| `models/ml/*` | `api/machine_learning/legacy_proxy/` or `api/machine_learning/` | Move after artifact paths are centralized. |
| `historical_training/*` | `api/machine_learning/training/` | Preserve transparent proxy-label logic. |
| `api/routes_phase5.py` | `api/machine_learning/router.py` | PD route. |
| `api/routes_phase6.py` | `api/machine_learning/loss_router.py` or `api/credit_decision/loss_router.py` | LGD/EAD/EL route. |
| `api/schemas_phase5.py` | `api/machine_learning/schemas.py` | Merge carefully with loss schemas. |
| `api/schemas_phase6.py` | `api/machine_learning/loss_schemas.py` | Keep clear PD/LGD/EAD separation. |

Path hazards:

- `models/credit/pd_model.py` uses `PROJECT_ROOT / "models" / "ml" / "historical_pd_model.pkl"`.
- `models/credit/loss_model.py` uses `PROJECT_ROOT / "models" / "ml" / "historical_lgd_model.pkl"`.
- `models/ml/default_model.py`, `lgd_model.py`, `clustering.py`, `anomaly_detection.py` use string paths under `models/ml/`.

Migration requirement:

- Do not migrate these until `api/core/config.py` or artifact-path helper exists.

### Scenario, Portfolio, And Risk Metrics

| V1 path | V2 target | Notes |
|---|---|---|
| `simulation/scenario_generator.py` | `api/stress_testing/scenario_generator.py` | Preserve no-hardcoded-scenario behavior. |
| `simulation/monte_carlo.py` | `api/portfolio_risk/monte_carlo.py` | Preserve seed, simulation count, VaR/ES outputs. |
| `simulation/phase7_service.py` | `api/portfolio_risk/service.py` or `api/stress_testing/service.py` | Orchestrates scenarios + simulation. |
| `simulation/stress_testing.py` | `api/stress_testing/engine.py` | Check for old Monte Carlo imports. |
| `risk/expected_loss.py` | `api/portfolio_risk/expected_loss.py` | Note dependency on old `models.ml.lgd_model`. |
| `risk/unexpected_loss.py` | `api/portfolio_risk/unexpected_loss.py` | Pure metric likely easy. |
| `risk/var.py` | `api/portfolio_risk/var.py` | Pure metric likely easy. |
| `risk/expected_shortfall.py` | `api/portfolio_risk/expected_shortfall.py` | Pure metric likely easy. |
| `risk/risk_contributions.py` | `api/portfolio_risk/risk_contributions.py` | Imports old simulation and VaR. |
| `models/copula/*` | `api/portfolio_risk/copula/` | Preserve portfolio-only usage. |
| `api/routes_phase7.py` | `api/portfolio_risk/router.py` | Thin route. |
| `api/schemas_phase7.py` | `api/portfolio_risk/schemas.py` | Domain schemas. |

### Credit Decision

| V1 path | V2 target | Notes |
|---|---|---|
| `decision_engine/credit_decision_engine.py` | `api/credit_decision/engine.py` | Pure decision logic; preserve rules and model version. |
| `decision_engine/credit_decision_service.py` | `api/credit_decision/service.py` | Uses SQL and memo grounding data. |
| `risk/credit_policy.py` | `api/credit_decision/credit_policy.py` | Check overlap with formal recommendation engine. |
| `api/routes_phase8.py` | `api/credit_decision/router.py` | Thin route. |
| `api/schemas_phase8.py` | `api/credit_decision/schemas.py` | Domain schemas. |

Important rule:

- The formal recommendation source remains `credit_recommendations`.
- RAG must explain this output, not independently create a recommendation.

### RAG And Memo

| V1 path | V2 target | Notes |
|---|---|---|
| `rag/agents/*` | `api/rag/agents/` | Remove dashboard imports from backend agents. |
| `rag/retriever/*` | `api/rag/retriever/` | Update vector paths to `data/vector_store/`; lazy-load indexes. |
| `rag/embeddings/*` | `api/rag/embeddings/` or `api/scripts/` | Generates vector artifacts; update output paths. |
| `rag/ingestion/*` | `api/rag/ingestion/` | Uses DB and document utils. |
| `rag/exports/*` | `api/reporting/exports/` or `api/rag/exports/` | Memo export functions. |
| `rag/llm/*` | `api/rag/llm/` | Uses langchain-ollama. |
| `rag/prompts/*` | `api/rag/prompts/` | Prompt templates. |
| `rag/documents/policy/*.txt` | `docs/policy/` or `data/raw/policy/` | Policy source docs, not vector artifacts. |
| `api/rag_routes.py` | `api/rag/router.py` | Remove dependency on dashboard database helper. |

Path hazards:

- Retrievers load FAISS and pickle files at import time from `rag/data/`.
- Embedding builders write FAISS/pickle outputs to `rag/data/`.

Migration requirement:

- Do not migrate RAG until data/vector path config exists.
- Convert retrievers to handle missing indexes clearly.

### Web Dashboard

| V1 path | V2 target | Notes |
|---|---|---|
| `dashboard/app.py` | `web/app.py` | Update imports to `web.pages` and `web.components`. |
| `dashboard/pages/*` | `web/pages/` | Migrate after backend API stabilizes. |
| `dashboard/components/*` | `web/components/` | Database helper should become API client or backend shared helper. |
| `dashboard/assets/custom.css` | `web/assets/custom.css` | Update theme path. |

Migration requirement:

- Dashboard should not be migrated before backend core APIs are stable.
- Replace direct SQL/dashboard DB access with API client calls over time.

### Pipelines And Scripts

| V1 path | V2 target | Notes |
|---|---|---|
| `pipelines/*.py` | `api/scripts/` | Update imports and paths slice by slice. |
| `reporting/*.py` | `api/reporting/` | Remove dashboard database imports. |
| `risk_monitoring/*.py` | `api/monitoring/` | Remove dashboard database imports. |

Path hazards:

- Most scripts assume project root relative paths.
- Many write to `data/raw/` or `data/processed/`.

Migration requirement:

- Migrate scripts after their target domain modules exist.

### Tests

| V1 path | V2 target | Notes |
|---|---|---|
| `tests/test_phase1_setup.py` | `tests/test_phase1_setup.py` | First test to migrate with DB/core. |
| `tests/test_phase2_pdf_extraction.py` | `tests/test_documents.py` | After documents slice. |
| `tests/test_phase3_financial_ratios.py` | `tests/test_financials.py` | After ratios slice. |
| `tests/test_phase4_market_intelligence.py` | `tests/test_market_data.py` | After market slice. |
| `tests/test_phase5_pd_models.py` | `tests/test_pd_models.py` | After PD slice. |
| `tests/test_phase6_loss_engine.py` | `tests/test_loss_engine.py` | After LGD/EAD/EL slice. |
| `tests/test_phase7_scenario_monte_carlo.py` | `tests/test_portfolio_risk.py` | After scenario/MC slice. |
| `tests/test_phase8_credit_decision.py` | `tests/test_credit_decision.py` | After decision slice. |
| `tests/test_credit_copilot.py`, `test_agents.py`, `test_retrieval.py`, `test_index.py` | RAG tests | After RAG path refactor. |

Test migration rule:

- Update imports to V2 paths in the same slice as implementation migration.
- Keep V1 tests as behavior references.

## Files Not To Copy Automatically

Do not copy without explicit approval:

- `CREDIT_RISK_PROJECT_V1\.env`
- `credit_memo.pdf`
- `credit_memo.docx`
- `models/ml/*.pkl`
- `rag/data/*.faiss`
- `rag/data/*.pkl`
- `data/processed/*.csv`
- uploaded documents under `data/uploads/`
- `database/__pycache__/`

Potentially copy later with approval:

- `data/raw/counterparties_master.csv`
- `data/raw/market_data.csv`
- `data/synthetic/credit_profiles.csv`
- `rag/documents/policy/*.txt`
- selected processed sample datasets for demo reproduction

## Recommended Next Implementation Slice

### Phase 3: Core DB And Package Bootstrapping

Purpose:

- Establish V2 import foundation before migrating feature code.

Copy/refactor:

```text
V1 database/db_connection.py
-> V2 api/db/session.py

V1 models/phase2_orm.py
-> V2 api/db/models.py

New:
-> V2 api/db/base.py
-> V2 api/core/config.py

V1 database/schema.sql
-> V2 database/schema.sql

V1 verify_schema.py
-> V2 api/scripts/verify_schema.py
```

Required import rewrites:

```text
from database.db_connection import engine, SessionLocal, get_db
-> from api.db.session import engine, SessionLocal, get_db

from models.phase2_orm import ...
-> from api.db.models import ...
```

Recommended compatibility wrappers for transition:

```text
database/db_connection.py
models/phase2_orm.py
```

In V2 these wrappers may re-export from the new modules only if needed by partially migrated tests.

Validation:

- Compile migrated Python files.
- Add/import smoke test for `api.db.session` and `api.db.models`.
- Do not require live PostgreSQL unless testing DB connection explicitly.

## First Five Migration Slices

1. Core DB and package bootstrapping.
2. Documents and financial extraction.
3. Financial ratios.
4. Market data, stress index, and regimes.
5. PD/LGD/EAD model paths and services.

RAG and dashboard should wait until backend and artifact paths are stable.
## Completed Migration Ledger

- Phase 1: V2 skeleton, governance routing, baseline files.
- Phase 2: migration map and dependency hazards documented.
- Phase 3: core DB/package bootstrapping, unified SQLAlchemy base, V2 settings.
- Phase 3.5: V2 `.gitignore` for secrets, caches, generated outputs, model/vector artifacts.
- Phase 4: documents/PDF extraction migrated to `api/documents/`.
- Phase 5: financial ratios and financial data services migrated to `api/financials/` and `api/shared/`.
- Phase 6: market data, stress index, and regime foundation migrated to `api/market_data/`.
- Phase 7: PD and structural credit foundation migrated to `api/machine_learning/` and `api/structural_credit/`.
- Phase 8: LGD/EAD/Expected Loss migrated to `api/machine_learning/loss_*` with optional LGD artifact path moved to `data/models/historical_lgd_model.pkl`.
- Phase 9: portfolio scenario generation, Monte Carlo, VaR, ES, unexpected loss, and scenario-analysis router migrated to `api/portfolio_risk/`.
- Phase 10: credit decision engine, grounded memo service, policy helper, and credit-decision router migrated to `api/credit_decision/`.
- Phase 11A: RAG code structure, agents, retrievers, prompts, exports, ingestion scripts, and RAG router migrated to `api/rag/`; vector artifacts and private documents were not copied.
- Phase 11B: RAG local fallback behavior tested; empty retrieval explicitly reports missing support data and copilot/router tests use monkeypatched local handlers only.
- Phase 11C: RAG copilot/memo/credit-decision agents integrated with stored V2 credit recommendation services; prompts hardened to forbid independent limits, grades, approval statuses, and unsupported numeric claims.
- Phase 11D Option A: test-only tiny RAG corpus validates FAISS/metadata retrieval using pytest temp paths only; no V1 policy docs or vector artifacts copied.
- Phase 11D Option B: approved plain-text policy documents copied to `data/rag_documents/policy/`; no FAISS/PKL vector artifacts copied.
- Phase 12A: reporting/export utilities migrated to `api/reporting/` and RAG memo exporters hardened for V2 report paths; tests write only to pytest temp paths.
- Phase 12B: memo export service integrated with grounded V2 memo builder and explicit output path handling; tests write only to pytest temp paths.
- Phase 12C: reporting/export API routes added under `api/reporting/router.py`; route tests monkeypatch output services and leave no generated files.
- Phase 13: V2 FastAPI app entrypoint added at `api/main.py`; migrated routers registered without requiring live DB access at import time.

Current verification:

```text
python -m compileall api tests
pytest tests\test_phase1_setup.py tests\test_documents.py tests\test_financials.py tests\test_market_data.py tests\test_pd_models.py tests\test_loss_engine.py tests\test_portfolio_risk.py tests\test_credit_decision.py tests\test_rag_migration.py tests\test_rag_behavior.py tests\test_rag_credit_integration.py tests\test_rag_tiny_corpus.py tests\test_rag_policy_docs.py tests\test_reporting_exports.py tests\test_memo_export_service.py tests\test_reporting_router.py tests\test_api_main.py -q
95 passed
```

Artifact rule still active: no `.pkl`, `.faiss`, uploaded documents, generated reports, or `.env` files were copied from V1.














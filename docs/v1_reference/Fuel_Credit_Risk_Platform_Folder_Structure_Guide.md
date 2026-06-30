# Fuel Credit Risk Platform - Folder Structure Guide



fuel-credit-risk-platform/
│
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
│
├── .ruler/
│   ├── core/
│   │   ├── project_context.md
│   │   ├── architecture.md
│   │   ├── tech_stack.md
│   │   └── adapter_pattern.md
│   ├── api/
│   │   ├── api_rules.md
│   │   ├── database_rules.md
│   │   └── backend_guardrails.md
│   ├── web/
│   │   ├── frontend_rules.md
│   │   └── frontend_guardrails.md
│   ├── quant/
│   │   ├── quant_model_rules.md
│   │   └── quant_guardrails.md
│   ├── rag/
│   │   ├── rag_rules.md
│   │   └── rag_guardrails.md
│   ├── deployment/
│   │   ├── deployment_rules.md
│   │   └── deployment_guardrails.md
│   └── prompts/
│       ├── build_feature.md
│       ├── bug_fix.md
│       ├── refactor.md
│       ├── code_review.md
│       └── testing.md
│
├── api/
│   ├── AGENTS.md
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── main.py
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── logging.py
│   │   ├── constants.py
│   │   └── exceptions.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   │
│   ├── data_connectors/
│   │   ├── AGENTS.md
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── service.py
│   │   ├── schemas.py
│   │   ├── router.py
│   │   ├── market_providers/
│   │   │   ├── base.py
│   │   │   ├── yahoo_finance.py
│   │   │   ├── stooq.py
│   │   │   └── fred.py
│   │   ├── document_extractors/
│   │   │   ├── base.py
│   │   │   ├── local_pdf.py
│   │   │   ├── pdfplumber_extractor.py
│   │   │   └── llama_cloud.py
│   │   ├── llm_providers/
│   │   │   ├── base.py
│   │   │   ├── ollama.py
│   │   │   └── bedrock.py
│   │   ├── embedding_providers/
│   │   │   ├── base.py
│   │   │   ├── sentence_transformers.py
│   │   │   └── bedrock_embeddings.py
│   │   ├── storage_providers/
│   │   │   ├── base.py
│   │   │   ├── local_storage.py
│   │   │   └── s3_storage.py
│   │   └── manual_entry/
│   │       ├── counterparty_entry.py
│   │       ├── exposure_entry.py
│   │       ├── financial_entry.py
│   │       └── invoice_entry.py
│   │
│   ├── shared/
│   │   ├── financial_ratios.py
│   │   ├── market_calculations.py
│   │   ├── risk_metrics.py
│   │   ├── feature_pipeline.py
│   │   └── utilities.py
│   │
│   ├── counterparties/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── market_data/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── structural_credit/
│   │   ├── AGENTS.md
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── merton.py
│   │   └── distance_to_default.py
│   │
│   ├── machine_learning/
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── inference.py
│   │   ├── pd_model.py
│   │   ├── lgd_model.py
│   │   ├── clustering.py
│   │   └── anomaly_detection.py
│   │
│   ├── portfolio_risk/
│   │   ├── AGENTS.md
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── copula.py
│   │   ├── monte_carlo.py
│   │   ├── expected_loss.py
│   │   ├── unexpected_loss.py
│   │   ├── var.py
│   │   ├── expected_shortfall.py
│   │   └── concentration.py
│   │
│   ├── stress_testing/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── scenarios.py
│   │   └── engine.py
│   │
│   ├── rag/
│   │   ├── AGENTS.md
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   ├── prompt_builder.py
│   │   └── ingestion.py
│   │
│   ├── reporting/
│   │   ├── service.py
│   │   ├── router.py
│   │   ├── credit_memo.py
│   │   └── pdf_generator.py
│   │
│   ├── monitoring/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   ├── router.py
│   │   └── alerts.py
│   │
│   ├── scripts/
│   │   ├── ingest_market_data.py
│   │   ├── ingest_counterparties.py
│   │   ├── upload_documents.py
│   │   ├── build_features.py
│   │   ├── train_models.py
│   │   ├── run_simulations.py
│   │   └── build_rag_index.py
│   │
│   └── tests/
│       ├── test_data_connectors.py
│       ├── test_counterparties.py
│       ├── test_market_data.py
│       ├── test_merton.py
│       ├── test_ml_models.py
│       ├── test_portfolio_risk.py
│       ├── test_stress_testing.py
│       └── test_rag.py
│
├── web/
│   ├── AGENTS.md
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   └── theme.py
│   │
│   ├── api_client/
│   │   ├── client.py
│   │   ├── data_connectors.py
│   │   ├── counterparties.py
│   │   ├── market.py
│   │   ├── portfolio.py
│   │   ├── stress.py
│   │   ├── rag.py
│   │   └── reports.py
│   │
│   ├── pages/
│   │   ├── 1_Executive_Dashboard.py
│   │   ├── 2_Data_Loading.py
│   │   ├── 3_Counterparty_Risk.py
│   │   ├── 4_Market_Data.py
│   │   ├── 5_Portfolio_Analytics.py
│   │   ├── 6_Monte_Carlo.py
│   │   ├── 7_Stress_Testing.py
│   │   ├── 8_Anomaly_Monitor.py
│   │   ├── 9_AI_Copilot.py
│   │   └── 10_Credit_Memo.py
│   │
│   ├── components/
│   │   ├── charts.py
│   │   ├── tables.py
│   │   ├── cards.py
│   │   ├── filters.py
│   │   ├── uploaders.py
│   │   └── layout.py
│   │
│   ├── utils/
│   │   ├── formatting.py
│   │   ├── session_state.py
│   │   └── error_handler.py
│   │
│   └── tests/
│       ├── test_api_client.py
│       ├── test_components.py
│       └── test_pages.py
│
├── data/
│   ├── raw/
│   ├── uploads/
│   ├── processed/
│   ├── models/
│   ├── vector_store/
│   └── reports/
│
└── docs/
    ├── methodology.md
    ├── architecture.md
    ├── adapter_pattern.md
    ├── api_reference.md
    └── deployment.md
```






## Root Level

| Folder/File | Meaning | What goes inside |
|---|---|---|
| `AGENTS.md` | Main Codex routing file | Tells Codex which `.ruler` files to read based on task |
| `README.md` | Project overview | Setup, project purpose, architecture summary, run commands |
| `.env.example` | Env template | DB URL, provider names, API keys placeholders |
| `.gitignore` | Git ignore rules | Ignore `.env`, models, cache, logs, large data |
| `docker-compose.yml` | Multi-service runner | Runs API, web, PostgreSQL together |
| `.ruler/` | AI governance/rules | Project rules, prompts, guardrails |
| `api/` | Backend application | FastAPI, DB, models, ML, RAG, simulations |
| `web/` | Frontend application | Streamlit dashboard and API clients |
| `data/` | Shared data storage | Raw files, uploads, processed data, models |
| `docs/` | Human documentation | Methodology, architecture, deployment notes |

## .ruler

| Folder/File | Meaning | What goes inside |
|---|---|---|
| `.ruler/core/` | Global project rules | Project context, architecture, tech stack |
| `project_context.md` | Business context | What the project does and who uses it |
| `architecture.md` | System design | Data flow, backend/frontend flow, modules |
| `tech_stack.md` | Approved tools | FastAPI, Streamlit, PostgreSQL, sklearn, FAISS, Ollama |
| `adapter_pattern.md` | External provider rules | How to add Yahoo, Bedrock, LlamaCloud, S3, etc. |
| `.ruler/api/` | Backend rules | FastAPI, SQLAlchemy, Pydantic standards |
| `api_rules.md` | API standards | Routers, services, schemas, dependency injection |
| `database_rules.md` | DB standards | Tables, migrations, naming, relationships |
| `backend_guardrails.md` | Backend restrictions | What Codex must not break |
| `.ruler/web/` | Frontend rules | Streamlit layout and chart standards |
| `frontend_rules.md` | UI standards | Pages, components, API calls, Plotly usage |
| `frontend_guardrails.md` | UI restrictions | No backend logic inside `web/` |
| `.ruler/quant/` | Quant model rules | Credit risk model rules |
| `quant_model_rules.md` | Model methodology | Merton, GBM, GARCH, Copula, Monte Carlo, VaR, ES |
| `quant_guardrails.md` | Quant restrictions | Do not replace approved risk formulas randomly |
| `.ruler/rag/` | RAG rules | Retrieval and LLM rules |
| `rag_rules.md` | RAG design | Chunking, embeddings, FAISS, prompts, context rules |
| `rag_guardrails.md` | RAG restrictions | Prevent hallucination, require retrieved context |
| `.ruler/deployment/` | Deployment rules | Docker/AWS rules |
| `deployment_rules.md` | Infra standards | EC2, Docker, env vars, logging |
| `deployment_guardrails.md` | Deployment restrictions | No paid services by default |
| `.ruler/prompts/` | Reusable Codex prompts | Build, debug, refactor, test templates |

## api

| Folder/File | Meaning | What goes inside |
|---|---|---|
| `api/AGENTS.md` | Backend Codex rules | Points Codex to backend `.ruler` files |
| `api/Dockerfile` | Backend container | FastAPI Docker setup |
| `api/requirements.txt` | Backend dependencies | FastAPI, SQLAlchemy, sklearn, FAISS, etc. |
| `api/alembic.ini` | Alembic config | Migration config |
| `api/main.py` | FastAPI entry point | App creation and router registration |

### api/core

| File | Meaning | What goes inside |
|---|---|---|
| `config.py` | App settings | DB URL, active providers, model paths |
| `dependencies.py` | Dependency injection | DB session, provider registry, services |
| `logging.py` | Logging setup | App logs and formatting |
| `constants.py` | Global constants | Risk thresholds, default values |
| `exceptions.py` | Error handling | Custom API exceptions |

### api/db and api/alembic

| Folder/File | Meaning | What goes inside |
|---|---|---|
| `db/base.py` | SQLAlchemy registry | Imports all models for migrations |
| `db/session.py` | DB connection | Engine, SessionLocal |
| `db/init_db.py` | DB initializer | Create base tables/seed setup |
| `alembic/env.py` | Migration runner | Alembic database migration config |
| `alembic/versions/` | Migration files | Auto/manual DB schema changes |

### api/data_connectors

| Folder/File | Meaning | What goes inside |
|---|---|---|
| `base.py` | Common adapter interfaces | Abstract provider classes |
| `registry.py` | Provider selector | Chooses Yahoo/Ollama/S3/etc. from config |
| `service.py` | Connector orchestrator | Calls adapters and returns normalized data |
| `schemas.py` | Connector schemas | Upload/manual/API request models |
| `router.py` | Connector endpoints | Upload PDF, ingest market data, manual entry |
| `market_providers/` | Market data adapters | Yahoo, Stooq, FRED |
| `document_extractors/` | PDF extraction adapters | Local PDF, pdfplumber, LlamaCloud |
| `llm_providers/` | LLM adapters | Ollama, Bedrock |
| `embedding_providers/` | Embedding adapters | Sentence Transformers, Bedrock embeddings |
| `storage_providers/` | File storage adapters | Local storage, S3 |
| `manual_entry/` | Manual input handlers | Counterparty, exposure, financial, invoice entry |

### api/shared

| File | Meaning | What goes inside |
|---|---|---|
| `financial_ratios.py` | Ratio calculations | Leverage, margins, liquidity |
| `market_calculations.py` | Market math | Returns, volatility, correlations |
| `risk_metrics.py` | Risk formulas | EL, UL, VaR, Expected Shortfall |
| `feature_pipeline.py` | Feature builder | Converts raw data into ML/model inputs |
| `utilities.py` | Helpers | Formatting, date handling, common functions |

## Backend Feature Modules

| Folder | Meaning | Core files and functionality |
|---|---|---|
| `counterparties/` | Counterparty profiles | Models, schemas, CRUD, services, APIs |
| `market_data/` | Market data storage | Brent, WTI, FX, volatility, market features |
| `structural_credit/` | Merton model | Distance-to-default and structural PD |
| `machine_learning/` | ML models | PD, LGD, clustering, anomaly detection |
| `portfolio_risk/` | Portfolio analytics | Copula, Monte Carlo, EL, VaR, ES |
| `stress_testing/` | Stress engine | Fuel shock, FX shock, combined shock |
| `rag/` | AI copilot backend | Retrieval, vector store, prompts |
| `reporting/` | Reports and memos | Credit memo and PDF generation |
| `monitoring/` | Alerts | PD, LGD, anomaly and concentration alerts |

## Common Feature Files

| File | Meaning | What goes inside |
|---|---|---|
| `models.py` | SQLAlchemy models | Database tables |
| `schemas.py` | Pydantic schemas | Request/response validation |
| `crud.py` | DB operations | Queries and persistence |
| `service.py` | Business logic | Feature workflows |
| `router.py` | FastAPI routes | API endpoints |
| `AGENTS.md` | Module-specific rules | Heavy module guidance |

## api/scripts

| File | Meaning | What goes inside |
|---|---|---|
| `ingest_market_data.py` | Market ingestion runner | Pull external market data |
| `ingest_counterparties.py` | Counterparty loader | Load airline/shipping datasets |
| `upload_documents.py` | Document upload script | Load PDFs into RAG |
| `build_features.py` | Feature builder | Generate model datasets |
| `train_models.py` | ML training script | Train PD/LGD models |
| `run_simulations.py` | Simulation runner | Monte Carlo execution |
| `build_rag_index.py` | RAG index builder | Create FAISS indexes |

## api/tests

| File | Meaning | What goes inside |
|---|---|---|
| `test_data_connectors.py` | Adapter tests | Validate provider outputs |
| `test_counterparties.py` | Counterparty tests | CRUD and scoring checks |
| `test_market_data.py` | Market tests | Ingestion and analytics checks |
| `test_merton.py` | Structural model tests | PD and DTD validation |
| `test_ml_models.py` | ML tests | Predictions and loading |
| `test_portfolio_risk.py` | Portfolio tests | EL, VaR, ES checks |
| `test_stress_testing.py` | Stress tests | Scenario validation |
| `test_rag.py` | RAG tests | Retrieval validation |

## web

| Folder/File | Meaning | What goes inside |
|---|---|---|
| `web/AGENTS.md` | Frontend Codex rules | Frontend instructions |
| `web/Dockerfile` | Frontend container | Streamlit Docker setup |
| `web/requirements.txt` | Frontend dependencies | Streamlit, Plotly, requests |
| `web/app.py` | Streamlit entry | Main dashboard |
| `config/` | Frontend settings | Theme and API config |
| `api_client/` | Backend callers | API wrappers |
| `pages/` | Dashboard pages | User-facing screens |
| `components/` | UI components | Charts, cards, tables |
| `utils/` | Frontend helpers | Formatting and state |
| `tests/` | Frontend tests | Component and page tests |

### web/pages

| File | Meaning | What goes inside |
|---|---|---|
| `1_Executive_Dashboard.py` | Main dashboard | KPIs and portfolio summary |
| `2_Data_Loading.py` | Data input page | Uploads and ingestion |
| `3_Counterparty_Risk.py` | Counterparty page | PD/LGD analysis |
| `4_Market_Data.py` | Market dashboard | Oil, FX and volatility charts |
| `5_Portfolio_Analytics.py` | Portfolio page | EL, VaR, ES |
| `6_Monte_Carlo.py` | Simulation page | Loss distributions |
| `7_Stress_Testing.py` | Stress page | Scenario analysis |
| `8_Anomaly_Monitor.py` | Monitoring page | Risk alerts |
| `9_AI_Copilot.py` | RAG page | Chat assistant |
| `10_Credit_Memo.py` | Memo page | Generate reports |

## data

| Folder | Meaning | What goes inside |
|---|---|---|
| `raw/` | Original data | CSVs and downloaded files |
| `uploads/` | User uploads | PDFs and documents |
| `processed/` | Clean datasets | Features and transformed data |
| `models/` | Saved models | Joblib/PKL files |
| `vector_store/` | RAG storage | FAISS indexes |
| `reports/` | Generated reports | PDFs and exports |

## docs

| File | Meaning | What goes inside |
|---|---|---|
| `methodology.md` | Model explanation | Quant and ML methodology |
| `architecture.md` | System explanation | System design |
| `adapter_pattern.md` | Adapter documentation | How to add providers |
| `api_reference.md` | API docs | Endpoint catalog |
| `deployment.md` | Deployment guide | Local, Docker, AWS |

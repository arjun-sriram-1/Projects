```text
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



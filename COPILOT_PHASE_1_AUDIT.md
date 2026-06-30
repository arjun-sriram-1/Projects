# Copilot Phase 1 Audit

## Purpose

This audit documents how the current AI copilot works and what Phase 2 needs to add so the bot can answer project-specific questions accurately, casually, and with traceable evidence.

## Current Runtime Path

Frontend entry point:

- `frontend/app.js`
- The browser posts user questions to `POST /api/copilot`.
- When a counterparty/page is selected, the frontend includes `counterparty_id`, `counterparty_name`, `page`, and `visible_metrics`.

Backend entry point:

- `api/rag/router.py`
- `POST /api/copilot` receives `CopilotRequest`.
- If selected app context is present, it builds a `GroundedCopilotContext` from SQL tables through `api/rag/grounded_context.py`.
- The request is then routed through `api/rag/agents/master_router.py`.

## Current Answer Modes

### Grounded SQL fast mode

Controlled by:

- `COPILOT_USE_LLM=False`
- Default in `api/core/config.py`

Behavior:

- Uses `build_grounded_fallback_answer()`.
- Reads selected counterparty, financials, ratios, PD, loss, recommendation, scenario, simulation, stress, regime, and market prices from SQL.
- Produces a deterministic explanatory answer.
- Adds source table names at the end.

Strength:

- Safer than a raw LLM because it does not invent live counterparty numbers.

Weakness:

- It is mostly a handcrafted narrative, not a full formula/data lineage engine.
- It does not have a structured field catalog.
- It cannot reliably answer every combination of "where did this field come from, how was it calculated, what model was used, and what limitation applies?"

### Ollama/Qwen RAG mode

Controlled by:

- `COPILOT_USE_LLM=True`
- `OLLAMA_MODEL`, default `qwen2.5:3b`
- `OLLAMA_URL`, default `http://localhost:11434`

Behavior:

- Retrieves vector context with `retrieve_context(query)`.
- Combines retrieved context with SQL/UI context.
- Sends a prompt to the Ollama model.

Strength:

- More flexible than the handcrafted fallback.

Weakness:

- Qwen only performs well if the retrieved context is complete and specific.
- Current prompts are formal and role-based.
- There is no mandatory machine-readable formula catalog.
- There is no deterministic trace tool for calculations such as final PD, LGD, EAD, expected loss, limit haircut, or PCA stress.

## Current Prompt Style

Main prompts:

- `api/rag/agents/prompts.py`
- `api/rag/llm/prompt_templates.py`

Current tone:

- Formal credit analyst.
- Structured sections such as "Risk Overview", "Financial Risks", "Market Risks".

Desired tone:

- Casual, direct, and interview-friendly by default.
- Still precise and grounded.
- Example target style: "Yep, this number comes from PD x LGD x EAD. The project is basically translating default risk into a dollar loss estimate."

## Current Grounded SQL Sources

The selected-counterparty context currently reads:

- `counterparties_master`
- `uploaded_documents`
- `financial_metrics_extracted`
- `financial_ratios`
- `pd_model_predictions`
- `loss_estimates`
- `trade_exposures`
- `credit_recommendations`
- `scenario_results`
- `simulation_results`
- `stress_index_history`
- `market_regime_history`
- `market_prices`

This is a strong base for live answers.

## Current Calculation Coverage

Already visible in code:

- Expected loss: `EL = PD * LGD * EAD`
- Final PD: calibrated blend of structural PD and ML PD
- Stress index: PCA-based market stress score from market component values
- Risk grade: mapped from PD bands
- Credit recommendation: policy haircut applied to requested/approved limit/EAD base
- LGD: collateral-aware business logic blended with trained LGD artifact when available
- EAD: trade exposure/drawdown logic blended with calibrated EAD artifact when available

Missing as reusable copilot assets:

- Field-by-field explanations
- Formula IDs
- Input/output dependency graph
- Real/proxy/synthetic/calibrated data labels
- Model artifact descriptions
- Interview explanation snippets
- Informal tone profile

## Main Problem

The copilot currently mixes three different things:

1. Live SQL context
2. Older document/vector retrieval
3. LLM generation

But it does not yet have a canonical project brain. This makes Qwen look weak because it has to infer project truth from partial context.

The fix is not just "use a bigger model." The fix is:

1. Build structured knowledge catalogs.
2. Make formula/data lineage deterministic.
3. Give Qwen verified context.
4. Let Qwen only handle the final conversational wording.

## Phase 2 Deliverables Added

The following knowledge files are added under `data/knowledge/`:

- `field_catalog.json`
- `formula_catalog.json`
- `model_catalog.json`
- `pipeline_graph.json`
- `source_catalog.json`
- `tone_profile.json`

These are intentionally static for now. Later phases can add loaders, endpoint access, retrieval indexing, and tests.

## Recommended Next Phase

Phase 3 should add a small backend loader module:

- `api/copilot/knowledge.py`

It should load the JSON catalogs and expose lookups by:

- field name
- formula ID
- model ID
- source table
- pipeline stage

Phase 4 should add a formula trace engine that can answer:

- "How is expected loss calculated?"
- "Where does final PD come from?"
- "How does PCA stress affect the final recommendation?"
- "What data points feed the credit decision?"


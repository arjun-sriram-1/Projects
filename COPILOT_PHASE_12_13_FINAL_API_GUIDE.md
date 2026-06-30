# Copilot Phase 12-13 Final API Guide

## What Was Finalized

Phase 12 finalizes the backend API surface for the project-aware copilot.

Phase 13 adds the integration polish layer: readiness checks, capability discovery, catalog listing, page-specific suggestions, and a clear free-resource operating model.

## Free Resource Policy

The copilot uses:

- Local JSON knowledge catalogs in `data/knowledge/`
- Local project docs and source code
- Local TF-IDF retrieval
- Deterministic formula and PCA trace tools
- Optional local Ollama/Qwen when `COPILOT_USE_LLM=True`

It does not require paid APIs.

## Main Endpoints

### Health

`GET /api/v1/copilot/health`

Returns:

- Knowledge catalog status
- Retrieval status
- Configured local Ollama model
- Supported answer modes
- Capabilities
- Free-resource confirmation

### Capabilities

`GET /api/v1/copilot/capabilities`

Returns a compact map of the copilot API surface.

### Query

`POST /api/v1/copilot/query`

Main grounded answer endpoint.

Example:

```json
{
  "question": "How is final PD calculated?",
  "style": "casual_precise",
  "use_llm": false,
  "values": {
    "structural_pd": 0.02,
    "ml_pd": 0.10
  }
}
```

The response includes:

- `answer`
- `route`
- `trace`
- `market_trace`
- `sources`
- `retrieved_context`
- `uses_paid_resources`

### Route

`POST /api/v1/copilot/route`

Classifies the question before answer generation.

Example intents:

- `formula_trace`
- `market_pca_explanation`
- `data_lineage`
- `model_explanation`
- `credit_decision_explanation`
- `interview_explanation`

### Trace

`POST /api/v1/copilot/trace`

Runs deterministic formula tracing.

Useful targets:

- `final_pd`
- `expected_loss`
- `risk_grade`
- `recommended_credit_limit`
- `structural_pd`
- `stress_index`
- `pc1_score`

### Market Impact

`POST /api/v1/copilot/market-impact`

Explains how a market factor moves through:

```text
market_prices -> z-scored components -> PCA PC1 -> stress_index -> PD/scenario/decision context
```

### Catalog Lists

```text
GET /api/v1/copilot/fields
GET /api/v1/copilot/formulas
GET /api/v1/copilot/models
GET /api/v1/copilot/pipeline
GET /api/v1/copilot/sources
```

These make the copilot's project knowledge inspectable.

### Suggestions

`GET /api/v1/copilot/suggestions?page=models`

Returns default and page-specific questions for the UI.

## Frontend Integration

The frontend now prefers:

```text
POST /api/v1/copilot/query
```

and falls back to:

```text
POST /api/copilot
```

if needed.

The UI also shows source chips and metric-level explain buttons for key risk outputs.

## Interview Explanation

You can explain the completed copilot like this:

> I did not rely on Qwen as the source of truth. I built a project-aware copilot layer around it. The backend has structured field, formula, model, source, and pipeline catalogs. It also has deterministic formula trace tools and a PCA market-factor trace. The local retriever searches project docs and code for free, and Qwen is optional: it only writes the final natural-language explanation after receiving grounded context.


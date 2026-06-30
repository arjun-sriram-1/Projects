# api/rag/AGENTS.md

Use for retrieval, AI copilot, grounded memo generation, vector stores, prompt building, and LLM providers.

Task matrix:

| Task | Required rules |
|---|---|
| RAG feature | `.ruler/rag/rag_rules.md`, `.ruler/rag/guardrails.md`, `.ruler/prompts/build_feature.md` |
| RAG bug fix | `.ruler/rag/guardrails.md`, `.ruler/prompts/bug_fix.md` |
| Memo work | `.ruler/rag/rag_rules.md`, `.ruler/api/database_rules.md` |
| Tests | `.ruler/prompts/testing.md` |

Rules:

- Numerical claims must come from SQL, model output, uploaded documents, market tables, or scenario results.
- If data is missing, say it is missing.
- Do not let the LLM create final credit limits or risk grades.




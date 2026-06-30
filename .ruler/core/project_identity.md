# Project Identity

This is an AI-augmented trade finance credit risk system for fuel suppliers,
resellers, commodity traders, and trade finance teams evaluating jet fuel and
marine fuel counterparties on credit terms.

The system must answer:

> Can we safely extend fuel trade credit to this counterparty, and if yes, under what credit limit, tenor, collateral/security, and risk conditions?

Core workflow:

1. Upload or enter counterparty financial data.
2. Extract structured financial statement fields.
3. Calculate ratios from stored financials.
4. Ingest market, macro, commodity, and stress data.
5. Estimate PD, LGD, and EAD separately.
6. Generate data-driven scenarios and Monte Carlo portfolio metrics.
7. Store a rules/model-based credit recommendation.
8. Let AI explain stored outputs and generate grounded memos.

Non-negotiable:

- AI explains and assists; it does not decide final limits.
- Every important output must be traceable to stored data, model output, uploaded documents, or market data.
- V1 reference docs live in `docs/v1_reference/`; load them only when deeper context is needed.
- Full V1 rule mirrors are indexed in `.ruler/core/v1_full_rule_index.md`; use them only for full parity audits or explicit full-context requests.



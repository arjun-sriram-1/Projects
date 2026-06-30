# Migration Rules

V1 is reference-only:

```text
../CREDIT_RISK_PROJECT_V1
```

V2 is the active project:

```text
../CREDIT_RISK_PROJECT_V2
```

Migration rules:

- Do not edit V1.
- Do not copy `.env`, generated reports, model artifacts, vector indexes, or uploaded private documents without explicit approval.
- Do not move code and change behavior in the same step unless unavoidable.
- Migrate one functional slice at a time.
- Preserve imports with compatibility wrappers until tests pass.
- Do not delete old compatibility paths until all references are updated and tested.
- Run focused tests after each slice.

Preferred migration order:

1. Governance and skeleton.
2. Core config and database session.
3. Financial extraction and ratios.
4. Market data, stress index, and regimes.
5. PD, LGD, EAD, and expected loss.
6. Scenarios, Monte Carlo, VaR, and ES.
7. Credit decision engine.
8. RAG and memo layer.
9. Web dashboard.
10. Artifact path cleanup.


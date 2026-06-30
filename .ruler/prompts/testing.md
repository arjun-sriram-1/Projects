# Testing Prompt

Choose the smallest useful test scope:

- changed unit tests first
- module tests next
- API smoke tests for route changes
- full test suite only when the migration slice is broad

Required coverage themes:

- financial ratio formulas and divide-by-zero behavior
- Merton sensitivity
- LGD bounds and collateral direction
- EAD cap and tenor behavior
- scenario non-hardcoding
- Monte Carlo reproducibility and output shape
- credit recommendation sanity
- RAG grounding for memo/Q&A

Report:

- command run
- pass/fail result
- important failures
- tests not run and why


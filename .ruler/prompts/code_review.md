# Code Review Prompt

Review priorities:

1. Bugs or broken workflow behavior.
2. Credit risk, quant, RAG, or auditability violations.
3. Missing tests for changed behavior.
4. Unsafe migration or import breakage.
5. Maintainability issues.

Report findings first, ordered by severity.

Each finding should include:

- file and line reference
- why it matters
- suggested fix

If no issues are found, state that clearly and mention residual test gaps.


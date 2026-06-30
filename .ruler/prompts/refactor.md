# Refactor Prompt

Refactor goal:

- Improve V2 structure while preserving V1 behavior.

Rules:

- Move one functional slice at a time.
- Do not change formulas or business decisions during pure refactor.
- Use compatibility wrappers until imports and tests are updated.
- Keep old paths until replacement paths pass tests.
- Update imports deliberately; avoid broad blind rewrites.

Every refactor report should include:

- files changed
- old path to new path mapping
- compatibility wrappers added
- tests run
- remaining migration debt


# Bug Fix Prompt

Before fixing:

- Reproduce or inspect the failing path.
- Load the closest module `AGENTS.md`.
- Load only the relevant guardrail and task rule files.

Fix rules:

- Keep the change minimal.
- Preserve existing behavior outside the bug.
- Add or update a regression test when practical.
- Do not perform broad refactors as part of a bug fix.

After fixing:

- Run the smallest relevant test first.
- Report any tests that could not be run.


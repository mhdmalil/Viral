# Skill: Code Review

## Purpose
Perform a genuine self-review pass before considering significant work complete — catching
issues a first draft commonly misses.

## When This Skill Applies
Step 9 of the master workflow, before any non-trivial change is declared done.

## Review Checklist
- **Correctness**: does the diff actually do what was intended, including edge cases?
- **Regressions**: could this change break something else that shares the touched code?
- **Duplication**: was existing logic/component reinvented instead of reused?
- **Unnecessary dependencies**: did this pull in anything not clearly justified? (cross-check
  `performance`)
- **Performance**: any obvious inefficiency introduced? (cross-check `performance`)
- **Accessibility**: still holds up? (cross-check `accessibility`)
- **Security**: no secrets, no unvalidated input, no weakened auth checks (cross-check `security`)
- **Platform/stack compatibility**: does this follow the conventions and constraints of the
  detected stack (see `platform-expert` and `docs/PROJECT_CONTEXT.md`)?
- **Maintainability**: is the code reasonably clear to a future reader, named sensibly, and
  consistent with surrounding style?
- **Debug code removed**: no leftover `console.log`/debug output, commented-out dead code, or
  temporary test scaffolding left in the diff

## Process
1. Re-read the diff as if reviewing someone else's pull request, not your own work.
2. Check it against the acceptance criteria defined in the PLAN step.
3. Check it against each item above, not just the ones most relevant to the task's main goal.
4. Fix what needs fixing before presenting the work as complete.

## Anti-Patterns to Avoid
- Reviewing only the "interesting" part of the diff and skipping incidental changes.
- Treating code review as optional for small changes that still touch shared/critical code.
- Leaving debug output or commented-out code in because "it's harmless."

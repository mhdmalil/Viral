# Skill: Debugging

## Purpose
Fix bugs through a disciplined root-cause process — never by randomly rewriting large amounts of
code and hoping the symptom goes away.

## When This Skill Applies
Any bug report, unexpected behavior, or failing test/functionality.

## Process
1. **Reproduce** — confirm the exact conditions that trigger the issue before attempting a fix.
   If it can't be reproduced, say so rather than guessing at a fix.
2. **Isolate** — narrow down which component/file/function is actually responsible, using the
   smallest reliable test case.
3. **Identify root cause** — understand *why* it happens, not just *where* the symptom appears.
   A fix that addresses the symptom but not the cause tends to resurface elsewhere.
4. **Smallest safe fix** — implement the minimal change that addresses the root cause. Resist
   the urge to refactor surrounding code while fixing an unrelated bug.
5. **Test** — verify the fix resolves the original reproduction case.
6. **Verify no regression** — check that the fix didn't break adjacent functionality, especially
   anything sharing the code path that was touched.

## Checklist
- The actual root cause is understood and stated, not just assumed
- The fix is scoped to the root cause, not a broad rewrite
- The original reproduction steps now pass
- Related/adjacent functionality was re-checked for regressions
- If the root cause reveals a broader pattern of risk elsewhere, that's flagged (not silently
  fixed everywhere without discussion, unless trivial and clearly in scope)

## Anti-Patterns to Avoid
- Rewriting a large chunk of a file speculatively because "this might fix it."
- Fixing the symptom (e.g., suppressing an error) without understanding why it occurred.
- Declaring a bug fixed without actually reproducing and re-testing the original issue.
- Introducing a new dependency or major refactor as a bug fix when a small, targeted change
  would do.

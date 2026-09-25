# Skill: Requirements Analysis

## Purpose
Turn a user request — especially a loosely worded one — into a precise, boundaries-aware
implementation scope before writing code.

## When This Skill Applies
Every non-trivial request. This is Step 1/Step 3 of the master workflow.

## Core Principles
- A request is not just "what to add" — it also implicitly defines what must NOT change.
  Make that boundary explicit.
- Ambiguity should be resolved by picking the most reasonable interpretation and stating the
  assumption, not by silently guessing or by stalling on a clarifying question when one isn't
  truly necessary.
- Scope creep is a failure mode even when the extra work is "an improvement." Flag ideas
  separately; don't fold them into the change uninvited.

## Turn Every Significant Request Into
1. **Requested changes** — concrete, specific list
2. **Things that must remain unchanged** — explicit, not assumed
3. **Affected files** — from `project-architecture` inspection
4. **Dependencies/integrations touched, if any**
5. **Assumptions made** — stated plainly so they can be corrected
6. **Risks** — what could break, what's uncertain
7. **Acceptance criteria** — how you and the user will know this is actually done and correct

## Anti-Patterns to Avoid
- Silently expanding scope ("while I was in there I also refactored...").
- Modifying unrelated functionality because it was nearby in the same file.
- Treating a vague request as license to redesign rather than to solve the stated problem.
- Asking multiple clarifying questions when a reasonable default would do — state the
  assumption and proceed instead.

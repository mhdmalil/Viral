# Skill: Project Memory

## Purpose
Use `docs/` as the project's persistent memory across sessions, so context isn't rebuilt from
scratch (or reinvented) every time the agent is invoked.

## When This Skill Applies
At the start of any session (skim relevant docs), and at the end of any session that produced a
meaningful change (update relevant docs). Always applies alongside `documentation`.

## Core Principles
- `docs/` is authoritative project memory, not a nice-to-have. Read it before assuming you need
  to re-derive architecture or integration knowledge from scratch.
- Never invent project information to fill in a doc. If you don't know something, inspect the
  code to find out, or leave the section explicitly marked as unknown/TODO.
- If a doc contradicts the actual codebase, the codebase is correct — fix the doc, don't work
  around the contradiction silently.
- Update docs in the same session as the change that made them stale, not "later."

## Read Before Significant Work
- `docs/PROJECT_CONTEXT.md` — what this project is and its constraints
- `docs/ARCHITECTURE.md` — structure and data flow
- `docs/DESIGN_SYSTEM.md` — before any UI work
- `docs/INTEGRATIONS.md` — before touching anything that could be connected to something external
- `docs/DECISIONS.md` — to avoid re-litigating settled choices
- `docs/TODO.md` — to check if this work was already flagged/planned

## Update After Meaningful Work
- `docs/CHANGELOG.md` — always, with a dated entry: what changed, in which files, why, and what
  was verified.
- `docs/ARCHITECTURE.md` / `docs/DESIGN_SYSTEM.md` / `docs/INTEGRATIONS.md` — if the change
  altered structure, visual system, or an integration.
- `docs/DECISIONS.md` — if a non-obvious choice was made that a future session would benefit
  from understanding (why this approach and not another).
- `docs/TODO.md` — add anything consciously deferred; remove/check off anything resolved.

## Anti-Patterns to Avoid
- Writing speculative/aspirational documentation ("this should eventually...") into files meant
  to describe current reality — put that in `TODO.md` instead.
- Letting docs drift silently out of sync with the code.
- Re-discovering the same architecture from scratch every session because docs were never read.

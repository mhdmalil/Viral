# Skill: Project Architecture

## Purpose
Understand the existing codebase's real structure before changing anything in it. This skill
exists to prevent blind edits that break things the agent didn't know were connected.

## When This Skill Applies
Any task that touches more than a single isolated file, and any task in an unfamiliar part of
the codebase — load this before Step 3 (PLAN) of the master workflow in `AGENTS.md`.

## Core Principles
- Read before you write. Inspect the actual files involved, not just the ones named in the
  request — check what includes/imports/renders them and what they in turn depend on.
- Prefer the smallest safe change over a rewrite, even if a rewrite feels cleaner.
- Treat `docs/ARCHITECTURE.md` as a starting map, not ground truth — verify against the code,
  and correct the doc if it's stale.
- Understand data flow, not just file structure: where does the data/content driving this UI
  or logic actually come from, and what else reads or writes it?

## Inspection Checklist (adapt to the detected stack)
- What renders/serves the page, screen, or endpoint in question, end to end?
- What components/sections/modules compose it, and in what order?
- What shared/reusable pieces (snippets, partials, hooks, utilities) does it pull in — and who
  else uses those same shared pieces? (Changing a shared piece can affect unrelated screens.)
- What data sources feed it (CMS fields, database, API response, local state, config)?
- What JS/CSS is scoped to this area vs. global?
- What build step, if any, transforms these files before they ship?
- Are there feature flags, A/B tests, or conditional rendering paths that change behavior?

## Before Significant Edits, Identify
1. Affected files (direct edits)
2. Files that depend on the affected files (blast radius)
3. Integrations/dependencies in play (cross-reference `docs/INTEGRATIONS.md`)
4. Risks — what's most likely to break, and how you'd notice if it did
5. Proposed implementation — the smallest change that satisfies the requirement

## Anti-Patterns to Avoid
- Editing a shared component/snippet for a one-off need instead of scoping the change.
- Assuming a file is unused without checking references to it.
- Restructuring folders/naming "while I'm in here" without it being part of the request.
- Trusting a comment or old doc over what the code actually does right now.

## Output of This Skill
A short, concrete map of what you're about to touch and why, feeding directly into the PLAN step.

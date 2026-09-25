# Skill: Documentation

## Purpose
Keep project documentation in `docs/` (and relevant in-code comments) accurate, useful, and
honest about what is and isn't known.

## When This Skill Applies
Alongside `project-memory`, whenever meaningful architecture, integrations, design decisions,
constraints, or implementation choices are created or changed.

## Core Principles
- Document what actually exists and actually happened — never document guesses or intentions as
  if they were facts.
- Prefer structured, scannable docs (tables, headings, checklists) over long prose.
- A doc that's wrong is worse than no doc — if you're not confident something is accurate,
  verify it against the code before writing it down, or mark it clearly as unverified.
- In-code comments should explain *why*, not restate *what* the code already says.

## What to Document
- **Architecture**: structure and data flow that isn't obvious from file names alone
- **Integrations**: anything external the project depends on
- **Design decisions**: non-obvious choices, and the trade-off that was accepted
- **Setup requirements**: anything a new contributor/agent session would need to know to work
  safely (env vars needed, local dev quirks, required accounts/tools)
- **Constraints**: brand, legal, performance, or technical limits future work must respect
- **Known issues**: things that are broken, fragile, or intentionally left incomplete

## Anti-Patterns to Avoid
- Copying boilerplate documentation that doesn't reflect this specific project.
- Writing docs once and never revisiting them as the code changes.
- Over-documenting trivial, self-explanatory code at the expense of documenting the
  non-obvious parts that actually need it.

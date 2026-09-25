# Skill: Design System

## Purpose
Maintain one coherent visual language across the project instead of accumulating parallel,
inconsistent design systems over time.

## When This Skill Applies
Any UI work — before adding a new color, spacing value, component, or pattern.

## Core Principles
- First identify what already exists (`docs/DESIGN_SYSTEM.md` + actual code inspection) before
  introducing anything new.
- Reuse existing variables/tokens/components wherever practical, even if a slightly different
  value would look marginally better in isolation — consistency compounds, one-offs don't.
- If something genuinely needs to be new (no existing token/component fits), add it as a proper
  addition to the system (named, documented) — not as an inline one-off value.

## Maintain Consistency Across
- Typography (families, sizes, weights, line-height)
- Spacing (use the established scale, don't introduce arbitrary pixel values)
- Color (semantic tokens over raw hex values where the project already has them)
- Buttons and form controls (variants, sizing, states)
- Borders, radii, shadows
- Imagery treatment and aspect ratios
- Iconography (one icon set/style, not several mixed together)
- Animation timing/easing

## Before Adding Anything New, Check
1. Does an existing token/component already do this?
2. Is a near-equivalent close enough to reuse instead of forking?
3. If truly new, where does it belong in the system so future work can reuse it too?

## Anti-Patterns to Avoid
- Hardcoding a color/spacing value that duplicates an existing token under a different name.
- Building a second button/card/form component because the first one was "hard to find."
- Letting a single page's design drift from the system "just this once."
- Updating `docs/DESIGN_SYSTEM.md` only sometimes, causing it to fall out of sync.

# Skill: UI/UX

## Purpose
Produce interface work that feels premium, intentional, and considered — not generic
AI-default output — while staying consistent with the project's established design language.

## When This Skill Applies
Any task that touches user-facing interface, copy in the UI, layout, or interaction design.

## Core Principles
- Consult `docs/DESIGN_SYSTEM.md` and the actual rendered product before designing anything new.
  Reuse existing patterns; don't invent a parallel visual language.
- Hierarchy and restraint communicate quality more reliably than decoration.
- Every interactive element needs a considered state model, not just a default appearance.

## Avoid (unless the existing design system genuinely uses it deliberately)
- Generic AI-looking interfaces (default shadcn-esque cards with no distinct point of view)
- Excessive rounded corners applied uniformly regardless of context
- Unnecessary gradients or drop shadows used as decoration rather than to convey depth/state
- Random decorative elements with no functional or brand purpose
- Inconsistent spacing that doesn't map to a scale
- Poor typographic hierarchy (too many weights/sizes, low contrast, cramped line-height)
- Visual clutter — competing focal points on one screen

## For Premium / Considered Brands, Prioritize
- Generous, deliberate whitespace
- A small, disciplined type scale with real hierarchy
- High-quality imagery treated consistently (crop ratios, color treatment)
- Sophisticated, uncluttered layouts
- Restrained interaction — motion and feedback that confirm actions without showy excess

## States to Consider for Every Interactive Element
- Default / hover / active / focus (keyboard-visible) / loading / error / empty / disabled

## Anti-Patterns to Avoid
- Designing in isolation from the existing product — creating a component that looks good alone
  but clashes with everything around it.
- Skipping empty/error/loading states because the happy path was the only one considered.
- Treating "premium" as "more effects" instead of "more intentional."

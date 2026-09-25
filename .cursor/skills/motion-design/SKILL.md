# Skill: Motion Design

## Purpose
Use animation that feels sophisticated and intentional while staying restrained, performant,
and respectful of user preferences.

## When This Skill Applies
Any task introducing or modifying transitions, animations, or scroll/interaction-driven motion.

## Core Principles
- Motion should clarify — indicate state change, guide attention, provide feedback — not
  decorate for its own sake.
- Prefer `transform` and `opacity` for animated properties; they're compositor-friendly and
  avoid layout thrash. Avoid animating `width`/`height`/`top`/`left`/box-shadow spread on a
  frequent basis.
- Keep durations and easing consistent with whatever motion language already exists in the
  project (`docs/DESIGN_SYSTEM.md`).
- Always respect `prefers-reduced-motion` — provide a reduced/no-motion fallback, not just a
  faster version of the same animation.

## Acceptable Technologies (pick the lightest that fits)
- CSS transitions/animations for simple, discrete state changes
- GSAP for complex, sequenced, or scroll-driven timelines where CSS becomes unwieldy
- Framer Motion (in React contexts) when the project already uses React and needs
  declarative, interruption-safe animation

## Avoid
- Layout thrashing (animating properties that trigger reflow)
- Excessive or omnipresent animation that makes the interface feel busy or slow
- Unnecessary continuous/looping effects that burn CPU/battery for no functional reason
- Animation that delays or obstructs navigation, form submission, or reading content
- Animation that measurably damages performance (check against `performance` skill budgets)

## Checklist Before Shipping Motion
- Does it still feel good with `prefers-reduced-motion: reduce` honored (reduced or removed)?
- Does it run smoothly on a mid-range mobile device, not just a dev machine?
- Does it interrupt/cancel gracefully if triggered again before finishing?
- Is the duration/easing consistent with the rest of the product?

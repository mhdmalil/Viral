# Skill: Accessibility

## Purpose
Ensure interfaces are usable by people using assistive technology, keyboard navigation, or with
visual/motor/cognitive differences — as a baseline requirement, not an add-on.

## When This Skill Applies
Any frontend change. Accessibility is never traded off against visual design — a design that
requires inaccessible markup needs a different implementation, not a lower bar.

## Core Principles
- Semantic HTML first — native elements (`button`, `a`, `label`, form elements, landmark
  elements) carry accessibility behavior for free; don't reach for ARIA to patch a div that
  should have been the right element.
- Everything operable by mouse/touch must also be operable by keyboard alone.
- Don't rely on color alone to convey meaning or state.
- Respect user preferences (`prefers-reduced-motion`, `prefers-color-scheme`, text zoom) rather
  than overriding them.

## Checklist
- Semantic HTML used for structure (headings, lists, landmarks, buttons vs. links used correctly)
- All interactive elements are keyboard-reachable and operable (Tab order is logical, no
  keyboard traps)
- Visible focus states are present and not suppressed (`outline: none` without a real
  replacement is a violation)
- Form fields have associated `<label>`s (or equivalent accessible name), and errors are
  announced/associated with the field
- ARIA is used only where semantic HTML can't express the pattern, and used correctly (wrong
  ARIA is worse than none)
- Color contrast meets at least WCAG AA for text and meaningful UI elements
- Images/icons convey meaning via alt text or `aria-label`; purely decorative images are marked
  as such (`alt=""`, `aria-hidden`)
- Motion respects `prefers-reduced-motion`
- Content reflows/zooms without loss of functionality (avoid fixed pixel constraints that break
  at 200% zoom)

## Anti-Patterns to Avoid
- Building custom interactive widgets (dropdowns, modals, tabs) without keyboard and
  screen-reader support when a native or accessible pattern would have worked.
- Removing focus outlines for aesthetic reasons without providing a visible alternative.
- Using placeholder text as a substitute for a real label.
- Treating accessibility as a final "pass" instead of building it in from the start.

# Skill: Performance

## Purpose
Treat production performance as a first-class requirement on every change, not an afterthought
checked only when something feels slow.

## When This Skill Applies
Every task with any runtime footprint — Step 6 of the master workflow, but the mindset applies
from Step 3 (PLAN) onward.

## Core Principle
Before adding anything, ask: **"Is this actually necessary?"** Prefer existing code, native
platform functionality, CSS, and lightweight JavaScript before adding a new dependency, script,
or asset. Never sacrifice production performance just to make something visually impressive.

## Areas to Actively Consider
- **Rendering**: server-side/templating rendering cost, avoiding unnecessary re-renders
- **DOM size**: avoid excessive nesting/node count, especially in repeated list items
- **JavaScript**: execution cost, bundle size, code-splitting/lazy-loading non-critical code,
  avoiding blocking the main thread
- **CSS**: avoid unused/duplicated styles, avoid expensive selectors at scale
- **Images**: correct dimensions (no oversized source images scaled down by CSS), modern
  formats, compression, lazy loading below the fold, explicit width/height to avoid layout shift
- **Fonts**: subset where possible, appropriate `font-display` strategy, avoid excessive weights
- **Third-party scripts**: audit what's already loaded before adding more; defer/async where
  safe; remove scripts that are no longer used
- **Network requests**: minimize count and payload size, avoid waterfalls, cache where sensible
- **3D/animation**: see `3d-web` and `motion-design` skills for specific budgets
- **Bundle size**: check the actual delta a new dependency adds, not just its stated feature value
- **Render-blocking resources**: minimize what blocks first paint/LCP

## Checklist Before Calling a Change Done
- No unjustified new dependency, library, script, or asset was added
- Images are appropriately sized/compressed/lazy-loaded
- No obvious layout shift introduced (missing dimensions on media)
- New JS doesn't block rendering unnecessarily
- Third-party scripts weren't added or loaded more eagerly than needed
- The change was reasoned about in terms of Core-Web-Vitals-equivalent metrics (loading,
  interactivity, visual stability) for the target platform

## Anti-Patterns to Avoid
- Adding a full library for one small utility that could be written directly.
- Loading a third-party script synchronously in `<head>` without justification.
- Shipping full-resolution source images instead of optimized, correctly sized assets.
- Treating performance as something to check only if the user explicitly asks.

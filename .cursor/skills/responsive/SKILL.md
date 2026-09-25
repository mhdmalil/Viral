# Skill: Responsive Design

## Purpose
Ensure every frontend change works correctly across the full range of real device widths, not
just the viewport the agent happens to preview.

## When This Skill Applies
Any change to layout, components, typography, or spacing that renders in a browser.

## Core Principles
- Design and test mobile, tablet, and desktop — never assume desktop-only correctness implies
  mobile correctness, or vice versa.
- Never fix a desktop layout problem in a way that creates mobile overflow, and never fix mobile
  by breaking desktop.
- Use fluid, relative techniques (flex/grid, relative units, `min()`/`max()`/`clamp()` where
  supported) over a pile of fixed breakpoint overrides when practical.

## Check At Minimum These Widths
- 320px, 375px, 390px, 430px (small to large phones)
- 768px (tablet)
- 1024px (small laptop / landscape tablet)
- 1280px, 1440px+ (desktop and large desktop)

## Checklist
- No horizontal scroll/overflow at any checked width
- Text remains readable (no cramped line-length extremes at either end)
- Touch targets are large enough on mobile (roughly 44x44px minimum)
- Images scale and crop sensibly rather than distorting or overflowing
- Navigation/menus have a working mobile pattern, not just a shrunk desktop version
- Tables/grids/wide content don't force page-level horizontal scroll — they scroll internally
  or reflow
- Content order makes sense when layout reflows (not just visually repositioned via CSS in a way
  that breaks reading/tab order)

## Anti-Patterns to Avoid
- Testing only the breakpoint mentioned in the request and assuming the rest "probably work."
- Using `!important` overrides to patch one breakpoint, causing a new problem at another.
- Fixed pixel widths on containers that should be fluid.

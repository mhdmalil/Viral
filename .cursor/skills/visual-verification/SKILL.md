# Skill: Visual Verification

## Purpose
Confirm that frontend work actually looks and behaves correctly in the rendered output — not
just that the source code looks correct on paper.

## When This Skill Applies
Step 8 of the master workflow, for any task with a visible frontend effect.

## Core Principle
Source code correctness does not guarantee visual correctness. CSS cascade, browser quirks,
real content lengths, and real image dimensions routinely produce surprises that only show up
when actually rendered. Never skip this step for a UI-affecting change.

## What to Check
- Spacing and alignment against the design system's scale
- Typography rendering (real content, not lorem ipsum where avoidable — check long/short/empty
  content cases)
- Image cropping and aspect ratio handling with real image dimensions
- Overflow behavior (no unexpected scrollbars, no clipped content)
- Button and interactive element sizing/placement
- Hover/active/focus/loading/error/empty/disabled states, not just the default state
- Responsive behavior across the breakpoints listed in the `responsive` skill
- Animation/motion — does it look and feel right in motion, not just "should work" in code
- Overall visual consistency with the rest of the product

## For 3D/WebGL Work, Additionally Check
- Loading state and timing
- Interaction/controls feel correct and intuitive
- Frame rate/performance while actually interacting, not just at rest
- Mobile fallback actually triggers and looks acceptable

## Method
- Prefer actually rendering the change (dev server, preview environment, or browser tooling
  available in this environment) over reasoning about it purely from source.
- Check at more than one breakpoint and more than one content-length scenario.
- When something looks off, trace it back to source and fix at the root cause, not with a
  one-off visual patch that masks the underlying issue.

## Anti-Patterns to Avoid
- Declaring a UI task "done" based only on reading the diff.
- Checking only the exact scenario in the request and skipping adjacent states (empty, long
  content, error).
- Ignoring a visual regression elsewhere on the page introduced by a shared-component change.

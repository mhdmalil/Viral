# Skill: Testing / QA

## Purpose
Verify that changes actually work — in practice, not just in theory — before declaring a task
complete.

## When This Skill Applies
Step 7 of the master workflow, for every non-trivial change.

## Core Principle
"It should work" based on reading the code is not the same as "it works." Wherever the
environment allows, actually run/exercise the affected functionality before calling it done.

## Test the Relevant Areas
- The specific functionality that was changed, directly
- Desktop and mobile behavior for anything frontend-visible
- Navigation and any routing affected
- Forms: submission, validation, error states
- Cart/checkout or equivalent core transactional flow, if touched even indirectly
- Any other product functionality that shares code paths with the change
- Console for JavaScript errors introduced by the change
- Network tab / requests for new errors, failed calls, or unexpected payloads
- Links related to the change for breakage
- Edge cases: empty states, very long content, unusual input, slow network if relevant
- Regressions in adjacent features that share a component, snippet, or utility with the change

## Checklist
- The originally requested behavior is confirmed working
- No new console/network errors were introduced
- Mobile and desktop were both checked for frontend changes
- At least one edge case beyond the happy path was checked
- Shared components/utilities were re-checked for regressions elsewhere they're used

## Anti-Patterns to Avoid
- Testing only the exact scenario described in the request and nothing adjacent.
- Skipping mobile testing for a change that will render on mobile.
- Declaring "done" without actually exercising the change in a running environment when one is
  available.

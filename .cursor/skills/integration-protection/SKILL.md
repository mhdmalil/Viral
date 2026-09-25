# Skill: Integration Protection

## Purpose
Guarantee that existing integrations, apps, APIs, tracking, and payment-related functionality
are never silently broken by unrelated work. This is the operational enforcement of the
"Existing Project Protection" rules in `AGENTS.md`.

## When This Skill Applies
Always load this alongside `project-architecture` before any edit that could plausibly touch
shared infrastructure — Step 4 of the master workflow.

## Core Rule
Existing integrations are protected by default. Never remove, disconnect, replace, or silently
alter one unless the user explicitly requested that specific change.

## Before Changing Anything, Identify (cross-reference `docs/INTEGRATIONS.md`)
- Third-party apps / plugins / app embeds
- APIs and webhooks (both directions)
- Analytics and tracking scripts
- Forms and their handlers
- Payment-related functionality
- Metafields / metaobjects / custom data fields
- External services (email, search, CDN, recommendations, etc.)
- Configuration/environment dependencies

## Process
1. Before editing, check whether the affected files/areas appear in `docs/INTEGRATIONS.md` or
   show signs of being wired to something external (SDK calls, embed snippets, webhook
   handlers, tracking pixels, payment SDK usage).
2. If the change doesn't require touching any of these, proceed normally, but stay alert while
   editing shared files.
3. If the change **does** require touching one of these, stop and explain to the user, before
   making the change: what's affected, why it needs to change, and what the impact/risk is.
4. After the change, verify the affected integration(s) still function — don't just assume the
   surrounding code still works because it wasn't directly edited.
5. Update `docs/INTEGRATIONS.md` if anything about an integration's status or wiring changed.

## Anti-Patterns to Avoid
- Removing a script tag, embed, or webhook handler because it "looked unused" without verifying.
- Changing a shared utility/snippet that a tracking or payment integration also relies on,
  without checking that dependency first.
- Silently swallowing or redirecting a webhook payload while implementing an unrelated feature.
- Assuming an integration still works post-change without any verification.

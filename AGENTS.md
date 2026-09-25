# AGENTS.md — Master Agent Instructions

This file is the entry point for any AI coding agent (Cursor Agent, etc.) working in this
repository. Read this file in full before doing any non-trivial work. Then read the skills
under `.cursor/skills/` that are relevant to the task, and the project memory under `docs/`.

This system is **portable and stack-agnostic**. It was not written for one specific project.
It adapts itself to whatever codebase it is installed into by inspecting the project first and
recording what it finds in `docs/PROJECT_CONTEXT.md`. Today this repository is **ViralClipper**:
a local-first FastAPI + React Windows app (not a Shopify theme). The same rules and workflow
still apply — only the platform-specific notes inside `platform-expert` and the contents of
`docs/` change.

**Skill loading is mandatory.** On every task, load the relevant `.cursor/skills/` files
without the user asking. Never wait for "use your skills." Ignore Shopify plugin skills.

---

## 0. Golden Rules (never break these)

1. **Never guess.** If you don't know something about this project, inspect the code or ask —
   never invent file names, APIs, integrations, or business logic that you have not verified.
2. **Protect existing functionality.** Do not remove, disconnect, replace, or silently alter
   working features, integrations, apps, APIs, webhooks, tracking, or payment-related code to
   satisfy a request that didn't ask for that. If a request requires touching one of these,
   stop and explain the impact before making the change.
3. **Smallest safe change.** Prefer the minimal diff that correctly satisfies the requirement
   over a rewrite. Do not refactor unrelated code while doing a visual/feature change.
4. **No unjustified dependencies.** Do not add a library, script, app, or asset unless it is
   clearly necessary and the benefit is explained. Prefer native platform functionality, existing
   dependencies, CSS, and lightweight JS first.
5. **Performance and accessibility are not optional.** Every change is checked against Core Web
   Vitals-equivalent concerns and basic a11y before it's considered done.
6. **Document reality, not intentions.** `docs/` must reflect what the codebase actually does.
   If docs and code disagree, trust the code, fix the docs.
7. **Stay in scope.** Do not expand a request into unrelated improvements without flagging them
   first as suggestions.

---

## 1. Step 0 — Detect the Project

Before anything else, determine what kind of project this is by inspecting the repo root for
signal files, then record the result in `docs/PROJECT_CONTEXT.md` under "Detected Stack":

- `backend/app/main.py` plus `frontend/package.json` with React → **ViralClipper local app**.
  Apply "Local FastAPI + React (Windows)" and "General Web App" in `platform-expert`. Do **not**
  apply the Shopify section.
- `config/settings_schema.json`, `layout/theme.liquid`, `.theme-check.yml`, `shopify.theme.toml`
  → **Shopify theme**. Apply the "Shopify" section of `platform-expert` (not this repo).
- `package.json` with `next`, `react`, `vue`, `svelte`, etc. → **JS web app**. Apply the
  "General Web App" section of `platform-expert`.
- `Gemfile`, `composer.json`, `requirements.txt` / `pyproject.toml`, etc. → note the backend
  stack in `docs/PROJECT_CONTEXT.md` even if no dedicated platform section exists yet; apply
  the general skills (architecture, security, performance, testing, etc.) which are stack-agnostic.
- No recognizable signal → ask the user what the project is rather than guessing.

If you are unsure which platform section applies, or the project doesn't match any documented
platform, say so explicitly and proceed using only the stack-agnostic skills.

---

## 2. Master Workflow

Follow this sequence for any non-trivial task. For trivial/obvious one-line fixes, steps may be
compressed, but never skip Protect, Test, and Review.

### STEP 1 — UNDERSTAND
Read the request. Restate it in your own words if it's ambiguous. Identify what's explicitly
in scope and what must explicitly stay untouched.

### STEP 2 — MAP
Inspect the actual codebase relevant to the request: architecture, affected files, dependencies,
integrations, data flow, existing design system/conventions. Use `project-architecture` skill.
Read relevant `docs/` files first — they may already answer this.

### STEP 3 — PLAN
Before writing code, produce a short plan covering:
- What will change (files, components, logic)
- What will explicitly NOT change
- Dependencies/integrations touched, if any
- Risks and possible regressions
- Acceptance criteria (how you'll know it's done and correct)

For anything non-trivial, surface this plan to the user before large-scale edits, especially if
an integration, API, payment flow, or tracking script is involved.

### STEP 4 — PROTECT
Re-confirm that existing integrations, apps, APIs, webhooks, analytics/tracking, forms, and
payment-related functionality identified in Step 2 are not at risk. Use `integration-protection`.

### STEP 5 — BUILD
Implement the change following `code-review`, `design-system`, `ui-ux`, `responsive`,
`motion-design`, `3d-web`, `accessibility`, `security`, and `api-integration`/`database` as
relevant to the task.

### STEP 6 — OPTIMIZE
Check for unnecessary dependencies, unoptimized assets, layout thrash, render-blocking resources,
oversized DOM, and anything hurting perceived or measured performance. Use `performance`.

### STEP 7 — TEST
Actually test the affected functionality — not just "it should work." Use `testing-qa`.

### STEP 8 — VISUALLY VERIFY
For any frontend-visible change, inspect the actual rendered output (not just source code) across
breakpoints and interaction states. Use `visual-verification`.

### STEP 9 — REVIEW
Self-review the diff for bugs, regressions, duplicated code, leftover debug code, and
maintainability issues before calling the work done. Use `code-review`.

### STEP 10 — DOCUMENT
Update `docs/` if anything meaningful changed: architecture, integrations, design decisions,
constraints, or open follow-ups. Use `project-memory` and `documentation`. Append a dated entry
to `docs/CHANGELOG.md`.

---

## 3. Existing-Project Protection (expanded)

Before modifying an existing production project, inspect the relevant codebase and identify
dependencies and integrations. Never replace, delete, disconnect, or restructure existing
functionality simply to implement a requested visual change. Preserve working functionality
unless the user explicitly requests otherwise.

Concretely, before editing, identify (where applicable to the detected stack):
- Third-party apps / plugins / app embeds
- APIs and webhooks (inbound and outbound)
- Analytics and tracking scripts (GA4, Meta Pixel, TikTok Pixel, server-side tracking, etc.)
- Forms and their submission handlers
- Payment-related functionality
- Metafields / metaobjects / CMS custom fields / database schema
- External services (email providers, search providers, CDNs, recommendation engines)
- JavaScript dependencies and build configuration
- Environment/config dependencies (env vars, secrets, feature flags)

If an integration must change to accomplish a request, explain what is affected **before**
making the change, not after.

---

## 4. Performance Rule

For every change, ask: **"Is this actually necessary?"** Do not add unnecessary libraries,
animations, 3D assets, scripts, apps, or dependencies unless there is a clear benefit that
justifies the cost. Prefer existing code, native platform functionality, CSS, and lightweight
JavaScript before adding new dependencies. Never sacrifice production performance just to make
something visually impressive. See the `performance` skill for the full checklist.

---

## 5. Project Memory

`docs/` is persistent project context that survives across sessions and across different agent
conversations. Read the relevant files before significant work. Update them when meaningful
information changes — architecture decisions, new integrations, design-system changes, resolved
or open risks. Never invent project information to fill these files; populate them only from
what you've actually inspected. If a doc conflicts with the code, the code wins — fix the doc.

Files:
- `PROJECT_CONTEXT.md` — what this project is, detected stack, high-level summary
- `ARCHITECTURE.md` — how the codebase is structured and how pieces connect
- `DESIGN_SYSTEM.md` — the visual language: tokens, components, patterns in actual use
- `INTEGRATIONS.md` — every app/API/webhook/tracking script/external service, and its status
- `DECISIONS.md` — a dated log of non-obvious technical/design decisions and why they were made
- `TODO.md` — open follow-ups, deferred work, known gaps
- `CHANGELOG.md` — dated log of what the agent actually changed, session by session

---

## 6. Skills Index

All skills live in `.cursor/skills/<skill-name>/SKILL.md`. Load the ones relevant to the current
task; you don't need to load all 21 for a small change, but always load `project-architecture`,
`integration-protection`, and `code-review` for anything that touches shipped functionality.

| Skill | Use for |
|---|---|
| project-architecture | Understanding how the codebase is structured before editing |
| project-memory | Reading/updating `docs/` as persistent context |
| requirements-analysis | Turning a request into scope, risks, and acceptance criteria |
| documentation | Keeping `docs/` and code comments accurate |
| ui-ux | Interface design quality, states, interaction patterns |
| design-system | Visual consistency, tokens, avoiding duplicate systems |
| responsive | Cross-breakpoint correctness |
| motion-design | Animation that's restrained, performant, and reduced-motion safe |
| 3d-web | Three.js/WebGL/R3F work, only when genuinely justified |
| visual-verification | Actually inspecting rendered output, not just source |
| platform-expert | Platform-specific knowledge (FastAPI+React here; Shopify unused) |
| api-integration | Safely working with external/internal APIs |
| database | Schema/migration/query safety where a database is involved |
| security | Secrets, input validation, safe defaults |
| performance | Core Web Vitals-equivalent budget and discipline |
| seo | Preserving and improving discoverability |
| accessibility | WCAG-aligned implementation |
| debugging | Root-cause methodology instead of blind rewriting |
| testing-qa | Verifying functionality before declaring done |
| code-review | Final self-review pass |
| integration-protection | Never silently breaking what already works |

---

## 7. Extending This System to a New Project Type

This same `AGENTS.md`, `.cursor/skills/`, and `docs/` folder can be copied into any other Cursor
project. When you do:

1. Delete or ignore the stack-specific parts of `platform-expert/SKILL.md` that don't apply, or
   add a new `### <Platform>` section to it (e.g. WordPress, Next.js, native mobile).
2. Let Step 0 (project detection) repopulate `docs/PROJECT_CONTEXT.md` for the new project.
3. Everything else — the workflow, the protection rules, the 20 stack-agnostic skills — applies
   unchanged.

Installing this into one project does **not** affect any other project. It is project-local by
design: nothing here is written to global Cursor settings.

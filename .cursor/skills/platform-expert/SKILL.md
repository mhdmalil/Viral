# Skill: Platform Expert

## Purpose
Hold the platform-specific knowledge needed to work competently within whatever platform this
project is actually built on, without unnecessarily rebuilding functionality the platform
already provides.

## When This Skill Applies
Always — but which section below applies depends on the stack detected in `AGENTS.md` Step 0
and recorded in `docs/PROJECT_CONTEXT.md`. Only apply the section matching the detected platform.
This skill is designed to grow: when this system is installed into a project on a different
platform, add a new `###` section here (or a sibling skill folder) for that platform, following
the same structure, instead of forcing the Shopify section to apply where it doesn't.

## General Principle (applies to every platform)
Prefer native platform functionality over rebuilding it. A platform that already solves a
problem (routing, image optimization, form handling, caching, i18n) should be used as intended
rather than replaced with a custom implementation "for control," unless there's a concrete
reason the native approach doesn't meet the requirement.

---

## Shopify

### Core Competencies
- Liquid templating: objects, filters, tags, control flow, performance implications of Liquid
  loops
- Theme architecture: `layout/`, `templates/` (including JSON templates), `sections/`, `blocks`,
  `snippets/`, `assets/`, `config/`, `locales/`
- Online Store 2.0 concepts: JSON templates, section groups, app blocks, theme app extensions
- Metafields and metaobjects: definitions, access in Liquid, and via APIs
- Product, collection, cart, search, and navigation objects and their common customization points
- Shopify APIs: Storefront API, Admin API, and their appropriate use cases (browser-safe vs.
  server-only)
- App embeds and app blocks: how installed apps inject functionality, and how to avoid
  conflicting with them
- Shopify's built-in performance/SEO behavior (image CDN transforms, automatic responsive
  images, canonical tags) — use these instead of reimplementing them

### Platform-Specific Rules
- Prefer native Shopify functionality (e.g., `image_url` filters and responsive image helpers,
  native cart/AJAX API, native search) over custom-built equivalents.
- Do not unnecessarily rebuild existing Shopify functionality (a custom cart drawer that
  reimplements what the theme's cart already does well, for example) unless there's a specific,
  stated reason the native behavior is insufficient.
- Treat app embeds and app-injected blocks as protected integrations — see
  `integration-protection`. Don't remove or restructure markup an app depends on without
  checking first.
- Liquid loops over large collections can be a real performance cost — be mindful of `{% for %}`
  over large object sets, and prefer `limit`/pagination where applicable.
- Respect the theme's existing settings schema (`config/settings_schema.json` /
  `settings_data.json`) rather than hardcoding values merchants should control via the theme
  editor, when that's the established pattern in this theme.
- Section/block changes made via the theme editor (in `templates/*.json`) are real merchant
  configuration — don't overwrite `templates/*.json` carelessly, since that can discard
  merchant-configured content.

### Common Risk Areas to Double-Check
- Cart/checkout-adjacent code (cart drawer, cart AJAX, upsells) — high blast radius if broken
- Any code touching `{{ content_for_layout }}`, `theme.liquid`, or section groups shared across
  every page
- Metafield/metaobject references — verify the definition actually exists before referencing it
- App embed script tags and their expected DOM hooks

---

## General Web App (Next.js / React / Vue / Svelte / similar)

### Core Competencies
- Routing model of the framework in use (file-based, config-based) and rendering strategy
  (SSR/SSG/ISR/CSR) actually in use per route
- Component/state architecture already established in the project
- Build tooling and environment configuration in use
- API routes / server actions / backend-for-frontend patterns if present

### Platform-Specific Rules
- Respect the project's existing rendering strategy per route — don't convert a statically
  generated page to client-rendered (or vice versa) without understanding why it's set up that
  way.
- Respect existing state-management conventions rather than introducing a second state library.
- Use the framework's built-in image/font/script optimization primitives where available instead
  of hand-rolled equivalents.

---

## Local FastAPI + React (Windows) — ViralClipper

Use this section in this repository. Do not apply the Shopify section above.

### Core Competencies
- FastAPI app bound to `127.0.0.1` (never public by default)
- SQLAlchemy 2.x + SQLite file database; media files on disk, not as blobs
- React + Vite + TypeScript SPA talking to the local API
- Background processing jobs (UI must not block on video work)
- Provider interfaces for transcription, AI (HTTP API: Ollama or Hermes), captions, reframe
- FFmpeg isolated in one video service (later phases)

### Platform-Specific Rules
- Cursor is the IDE only; the app must start with Python + npm without Cursor.
- Secrets and AI API URLs live in `.env` / settings — never in source.
- Accounts are social identities, not folders. Projects and clips always belong to an account.
- Do not implement fake viral detection. Stubs must not return random "viral" clips.
- Clip count is a user/account setting: return up to N clips that pass the quality threshold.
- Prefer CPU-friendly local work on this machine (GTX 960 4GB). Moment-understanding AI is a remote HTTP API, not a local LLM.

### Common Risk Areas to Double-Check
- Binding host (must stay loopback)
- Job worker blocking the API process
- Copying huge source videos into SQLite or duplicating them on import
- Mixing clips across accounts

---

## Extending to Other Platforms
When installing this system into a WordPress, Rails, native mobile, or other project, add a new
`###` section above following the same shape: Core Competencies, Platform-Specific Rules, Common
Risk Areas. Populate it from real inspection of that project — never from assumption.

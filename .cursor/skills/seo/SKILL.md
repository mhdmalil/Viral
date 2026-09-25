# Skill: SEO

## Purpose
Preserve and improve discoverability with every change — never regress existing SEO
functionality as a side effect of an unrelated fix.

## When This Skill Applies
Any change to page structure, metadata, routing/URLs, or content templates.

## Core Principles
- Never remove or weaken existing SEO functionality (meta tags, structured data, canonical URLs,
  sitemaps, redirects) without explicit approval — even if it's incidental to the main request.
- Semantic HTML is itself an SEO foundation — use headings, landmarks, and elements for their
  actual meaning, not just their default styling.
- Don't create duplicate-content or broken-URL situations when changing routing/templates.

## Checklist
- Title tags and meta descriptions are present and accurate for changed/new pages
- Heading hierarchy is logical (one clear H1, nested subheadings — not chosen for font size)
- Structured data (schema.org / JSON-LD, or platform-native equivalent) is preserved or added
  where relevant (products, articles, breadcrumbs, etc., as applicable)
- Canonical URLs are correct, especially on filtered/paginated/variant pages
- Internal linking isn't broken by the change (no new orphaned pages, no broken links introduced)
- Images have meaningful alt text (not decorative-only, not keyword-stuffed)
- New/changed URLs are indexable unless intentionally excluded, and old URLs redirect properly
  if a path changes
- Page load performance isn't regressed (SEO and performance are linked — see `performance`)

## Anti-Patterns to Avoid
- Removing a canonical tag or structured data block while refactoring a template.
- Changing a URL structure without setting up redirects from the old paths.
- Using headings purely for visual size rather than document structure.
- Leaving alt text empty or generic ("image123.jpg") on meaningful content images.

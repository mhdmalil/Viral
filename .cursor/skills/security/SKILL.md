# Skill: Security

## Purpose
Protect secrets, credentials, and customer data, and avoid introducing common vulnerability
classes, in every change regardless of how small it seems.

## When This Skill Applies
Every task. Security is not opt-in for "security-related" tasks only — check it on every change
that touches input handling, configuration, credentials, or user data.

## Core Principles
- Secrets (API keys, tokens, passwords, credentials) live in secure configuration/environment
  variables — never hardcoded in source, never logged, never committed.
- All untrusted input (user input, query params, webhook payloads, third-party API responses)
  is validated and sanitized before use — never trusted implicitly.
- Least privilege: don't request or store more access/data than the task actually needs.
- Customer data (PII, payment-related info, order/account data) is handled with extra care and
  never exposed in logs, error messages, or client-side code unnecessarily.

## Checklist
- No hardcoded secrets/keys/tokens anywhere in the diff
- No secrets in client-side/browser-exposed code
- User/external input is validated (type, format, range) before use
- Output is properly escaped in its context (HTML, SQL, shell, URL) to prevent injection
- Error messages shown to users don't leak internal details (stack traces, query text, secrets)
- New environment variables/secrets are documented (name only, never value) in
  `docs/INTEGRATIONS.md`
- Auth/authorization checks aren't weakened or bypassed by the change
- Third-party scripts added to the frontend are from trusted sources and scoped appropriately

## Common Vulnerability Classes to Actively Guard Against
- Injection (SQL, command, template/HTML)
- Cross-site scripting (unescaped user content rendered into HTML)
- Insecure direct object references (trusting client-supplied IDs without authorization checks)
- Exposed secrets in source, client bundles, or logs
- Missing input validation on webhook/API payloads

## Anti-Patterns to Avoid
- "Temporarily" hardcoding a key to test something, then forgetting to remove it.
- Trusting a webhook payload's contents without verifying its signature/origin where supported.
- Disabling a security check to unblock a feature instead of fixing the underlying friction.

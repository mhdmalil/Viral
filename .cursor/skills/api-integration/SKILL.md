# Skill: API Integration

## Purpose
Work with internal and external APIs safely — without guessing at behavior, breaking existing
consumers, or mishandling credentials.

## When This Skill Applies
Any task that calls, modifies, or depends on an API — internal endpoints, third-party services,
or platform-provided APIs.

## Core Principles
- Before changing how an API is used, identify: the endpoint, the authentication method, the
  data flow in both directions, related webhooks, existing consumers, and current error handling.
- Use official documentation as the source of truth. Never invent endpoints, parameters,
  response shapes, or undocumented behavior — verify or ask instead of guessing.
- Treat every API call as something that can fail: handle timeouts, error responses, and
  rate limits explicitly rather than assuming the happy path.
- Changing a shared API contract (request/response shape, required fields) can break other
  consumers — check `docs/ARCHITECTURE.md` and `docs/INTEGRATIONS.md` for who else depends on it.

## Before Changing an API-Dependent Feature
1. Identify the exact endpoint(s) and method(s) in use
2. Identify the authentication/authorization mechanism and where credentials are stored
3. Trace the full data flow: request construction → call → response handling → what consumes
   the result
4. Identify related webhooks or async callbacks
5. Identify current error handling and whether it's adequate for the change
6. Check for other consumers of the same endpoint/contract

## Checklist
- Credentials/keys are never hardcoded or logged (see `security` skill)
- Errors and edge cases (timeout, 4xx, 5xx, malformed response, rate limit) are handled, not
  just the success path
- Retries/backoff are used where appropriate, not naive infinite retry loops
- Response data is validated/sanitized before use, not trusted blindly
- Changes to shared contracts are checked against other known consumers first
- New integrations are recorded in `docs/INTEGRATIONS.md`

## Anti-Patterns to Avoid
- Assuming an API's behavior from its name instead of checking documentation or actual responses.
- Silently changing a request/response contract that other code depends on.
- Swallowing errors silently instead of surfacing or logging them appropriately.

# Skill: Database

## Purpose
Handle schema, queries, and data changes safely in any project that uses a database (this may
not apply to a pure Shopify theme, but applies fully if the project has a backend/app layer).

## When This Skill Applies
Any task touching schema, migrations, queries, or stored data.

## Core Principles
- Understand the existing schema and relationships before altering them — a change to one table
  can silently affect unrelated features via foreign keys, joins, or shared queries.
- Migrations should be additive and reversible where possible; avoid destructive changes
  (dropping columns/tables, irreversible data transforms) without explicit user approval.
- Query performance matters — check that new queries use appropriate indexes and don't introduce
  N+1 patterns, especially in loops.
- Data integrity constraints (foreign keys, unique constraints, not-null) should be respected
  and not worked around in application code to avoid "just this once."

## Before Making Changes, Consider
- Current schema and relationships
- Existing indexes and query patterns that touch the affected tables
- Migration path (can it be applied without downtime? is it reversible?)
- Data integrity constraints already in place
- Backup/rollback plan for anything destructive
- Query performance impact at realistic data volume, not just on an empty/small dataset

## Checklist
- Migrations are additive/reversible unless destructive change was explicitly requested
- New queries are checked against indexes / explained for performance where it matters
- No raw string concatenation for queries (parameterized queries only — see `security`)
- Data integrity constraints preserved, not bypassed
- Any destructive change is called out explicitly and confirmed before executing

## Anti-Patterns to Avoid
- Making a destructive schema change without explicit approval.
- Writing a query that works today but will degrade badly as the table grows.
- Bypassing an application-level validation with a direct database write "just to fix this one
  record."

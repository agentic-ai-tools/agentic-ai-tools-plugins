---
description: Migration safety and tenant isolation rules for Postgres schemas - expand and contract, lock-safe DDL, and tenant columns
globs: ["**/*.sql"]
---

# Migration safety

- Expand, then contract: a release adds columns, tables, or indexes that the previous code version can ignore; a later release removes what is no longer read. A rollback never needs a down-migration.
- Every migration is compatible with the code version currently running, because the migration runs before the new code is live.
- Avoid long locks on tables that serve requests: add columns nullable or with a constant default, create indexes `CONCURRENTLY` in a migration that disables its transaction (`-- flyway:executeInTransaction=false`), and add constraints `NOT VALID` then `VALIDATE` them separately.
- Set `lock_timeout` and `statement_timeout` at the top of a migration that touches a busy table, so it fails fast instead of blocking traffic.
- Never drop a table, a column, or data in the same release that stops using it. Deleting data is a reviewed change with a backup or restore point named in the pull request.
- Every table that holds tenant data has a non-null `tenant_id` column, included in its indexes and unique constraints, so a tenant filter is cheap and a cross-tenant duplicate is impossible.
- Grant the application role only the privileges it needs. The migration role owns the schema; the application role does not run DDL.
- Keep bodies and secrets out of rows that are widely read: store a reference or a hash, never raw keys, tokens, or large content.

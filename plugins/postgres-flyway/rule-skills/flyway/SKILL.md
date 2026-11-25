---
name: flyway
description: Flyway migration and Postgres schema conventions. Use when reading or editing **/*.sql.
---

# Flyway and Postgres

- Versioned migrations are `V<n>__<snake_case_description>.sql`. One logical change per migration.
- Forward-only: never edit, reorder, or delete a migration that is merged or has run against a shared database. Fix it with a new migration.
- Changes are additive. Removing or renaming a column the running code reads takes two releases: stop reading it, then drop it.
- Repeatable `R__` migrations are not allowed by default. They are allowed only for idempotent views or functions, with a pull request note, and never for table DDL.
- No demo data in versioned migrations. Reference rows that are part of the product schema are allowed. Local seeds live outside the migrations and never run against a shared database.
- History table stays `flyway_schema_history`. Do not enable `outOfOrder`.
- `snake_case` for tables, columns, indexes, and constraints. Primary keys are `UUID PRIMARY KEY DEFAULT gen_random_uuid()`. Timestamps are `TIMESTAMPTZ`, stored in UTC.
- Every foreign key declares `ON DELETE` explicitly. Index the foreign keys used in lookups, in the same migration.
- Every durable table has `COMMENT ON TABLE`.
- Store references and hashes, never raw keys, tokens, or card data.
- The migrations ship as a migrations image on GHCR. Services run that image before they start and never own competing DDL (no `create_all`, no Alembic).

---
name: add-store-query
description: Add a database query to the store port and every store adapter, using raw SQL with named parameters. Use when a service needs to read or write Postgres.
---

# Add a store query

1. Add the method to the store `Protocol` with domain types in and out.
2. Write a failing test against the in-memory store, then implement it there.
3. Implement it in each SQL adapter (psycopg, and the RDS Data API where the service has one) with the same SQL text and named parameters. Never build SQL with f-strings or `%` formatting of values.
4. The schema comes from the published Flyway migrations. If the query needs a new column or table, add the migration in the repository that owns the schema first.
5. Run the store tests against a real Postgres migrated by the migrations image.

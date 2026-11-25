---
description: Layers, ports and adapters, problem+json errors, untrusted input, and idle-safe rules for FastAPI services
globs: ["app/**/*.py", "src/**/*.py"]
---

# Service design

Layers: `api/` holds thin FastAPI routers (parse, authorize, call a service, shape the response). `services/` holds one function per use case, which owns the transaction. `domain/` holds Pydantic schemas, validation, naming rules, and errors. Ports are `typing.Protocol` classes, and adapters implement one port for one provider.

- A router never runs SQL or calls a vendor SDK. A service never imports FastAPI.
- Domain code never imports a vendor type: no boto3 client, Restate context, or Strands agent outside an adapter.
- Each port has an in-memory adapter for tests. A factory picks the adapter from settings, and a FastAPI dependency (`Annotated[..., Depends(...)]`) hands it to routers.
- Every route sets `response_model`. Request bodies are Pydantic models, never a raw `dict`. JSON field names match the published contract.
- Errors are RFC 9457 `application/problem+json` with a stable `code` the contract lists. Services raise the one domain error type, and one handler renders it. Never raise `HTTPException`. Never put stack traces or exception class names in `detail`.
- Creates return `201`. Asynchronous jobs return `202` and a pollable resource.
- Untrusted input (user, model, internet): check the size before parsing, check the content rather than the declared type, `yaml.safe_load` with limits, and never fetch a user-supplied URL from a component that can reach the database. Model output is parsed into a Pydantic schema and rejected when it does not fit.
- One ASGI app runs under uvicorn locally and Mangum on Lambda. Asynchronous work has its own handler module that calls the same services.
- Idle-safe: `/health/live` never touches the database, no connection pool is held between invocations, and no scheduled job queries Postgres.
- The API owns feature flags. Clients never decide on their own.

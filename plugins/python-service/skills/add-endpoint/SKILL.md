---
name: add-endpoint
description: Add a FastAPI endpoint to a service, test first, with a Pydantic response model and problem+json errors. Use when asked to add or change an HTTP route.
---

# Add an endpoint

1. Find the operation in the published contract (OpenAPI and fixtures). If it is missing, the contract changes first, in the contracts repository.
2. Write the failing test with `httpx` against the app: the success status, the response body matching the fixture, and every error status the contract lists, each as `application/problem+json` with its `code`.
3. Add or reuse the request and response models in `domain/`. Field names match the contract.
4. Add the use case in `services/` as one function that takes the ports it needs. It raises the domain problem error, never `HTTPException`.
5. Add the route in `api/`: `response_model` set, `status_code` set (`201` for a create, `202` for a job), dependencies through `Annotated[..., Depends(...)]`. The route only parses, authorizes, calls the service, and returns.
6. Run the formatter, linter, and tests until clean.

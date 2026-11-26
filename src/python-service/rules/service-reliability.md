---
description: Reliability rules for FastAPI services - timeouts, retries, idempotency, circuit breakers, degradation, and visible failure
globs: ["app/**/*.py", "src/**/*.py"]
---

# Service reliability

- Every client (httpx, boto3, database, workflow, model) has an explicit timeout shorter than the caller's remaining time. A request path's timeouts add up to less than its entry point's limit.
- Retry only idempotent operations, only on timeouts, 5xx, and 429, with exponential backoff and full jitter, at most 3 attempts, inside the caller's timeout. Never retry other 4xx.
- An operation a client or a queue can repeat takes an idempotency key, or is idempotent by its natural id. Asynchronous invocations that can run twice are safe to run twice.
- A dependency that has a fallback sits behind a circuit breaker: a short timeout, open after consecutive failures, a half-open probe on real traffic. The fallback keeps the record in the system of record so nothing is lost.
- When an optional dependency fails, the operation continues with less and says so in the response.
- Asynchronous work ends `complete` or `failed`. Work that can be lost in flight is recognised as failed on read once it is older than its handler's timeout, not by a scheduler.
- Liveness never touches the database. No connection pool or scheduled job keeps a scale-to-zero database awake.
- Emit rate, errors, and a latency histogram for every route and outbound dependency, so SLOs can be measured.
- Each failure path has a test with an adapter fake that times out, returns 5xx, or throttles.

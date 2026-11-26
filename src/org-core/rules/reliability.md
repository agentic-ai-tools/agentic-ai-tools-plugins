---
description: Reliability baseline for every Agentic AI Tools repository - SLOs, alerts with runbooks, rollback, and idle-safe operations
alwaysApply: true
---

# Reliability baseline

- User journeys have service level objectives. Alerts page on error-budget burn over a long and a short window, with a minimum event count, never on a single failure or a resource threshold.
- An alert is not turned on until its runbook exists. Use the `add-runbook` skill.
- Every change says how it is rolled back. A change that cannot be rolled back says so and gets a second reviewer.
- Every outbound call has a timeout shorter than its caller's. Retry only idempotent operations, with exponential backoff and jitter, inside the caller's timeout.
- Asynchronous work ends visibly as complete or failed. Never leave it pending forever.
- Scale-to-zero systems stay idle-safe: no health check, probe, or timer that keeps a serverless database or service awake.

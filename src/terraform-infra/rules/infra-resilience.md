---
description: Resilience and edge security rules for infrastructure - backups, deletion protection, alarms with runbooks, quotas, and WAF
globs: ["**/*.tf", "**/*.tfvars"]
---

# Infrastructure resilience

- Stateful resources state their recovery: point-in-time restore with a set retention for databases, versioning with noncurrent-version expiry for object stores, and deletion protection in production.
- Name the recovery point and recovery time objectives for each data store in the repository's docs, and keep them achievable with what the code creates.
- Every alarm's description links to its runbook in `docs/runbooks/`. An alarm without a runbook is not created.
- Page only on SLO burn rate over a long and a short window, with a minimum event count, so a scale-to-zero system never pages on idle. Resource thresholds raise tickets, not pages.
- Never create a health check, probe, or scheduled rule that keeps a serverless database or service awake.
- Check the account's quotas before reserving Lambda concurrency or raising a throttle, and record what each workload reserves.
- Log groups have retention. Asynchronous invocations set their retry count and failure destination on purpose.
- Public entry points sit behind AWS WAF with managed rule groups and a rate limit, and APIs have route throttling. CDN distributions send security headers.
- Prefer multiple availability zones where it costs nothing extra. A single-region or single-zone design is a recorded, accepted risk.

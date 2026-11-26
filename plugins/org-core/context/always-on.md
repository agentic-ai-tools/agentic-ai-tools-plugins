# Development practice

- Follow test-driven development. Add or update a failing test for the behavior, make it pass, then refactor with the tests green.
- Run the repository's formatter and linter before every commit, and fix everything they report. Never commit with known format or lint failures. The commands are in the repository's `AGENTS.md`.
- When an agent wrote or co-wrote a commit, end the commit message with that agent's `Co-Authored-By` trailer. A pull request body says it was generated with the agent.
- Secrets never go into commits, examples, fixtures, logs, or Terraform: no tokens, passwords, keys, or `.env` files. Use the platform's secret store and reference it. If a secret is missing, stop and say so. Do not invent one.
- `AGENTS.md` holds only facts about its own repository. A rule that applies to more than one repository belongs in a plugin in `agentic-ai-tools-plugins`.

# Git workflow

- Never make changes on `main`. Do not commit or push to `main`.
- Create a new branch from the latest `main`, do the work there, and open a pull request into `main`. Every change goes through a pull request.
- Never force-push to any branch: no `git push --force`, no `--force-with-lease`, no rewriting published history.
- Never copy another repository's code or SQL into this one. Depend on its published release.
- Do not switch a sibling repository off its current branch. Point at it with the repository's documented path variable instead.

# Reliability baseline

- User journeys have service level objectives. Alerts page on error-budget burn over a long and a short window, with a minimum event count, never on a single failure or a resource threshold.
- An alert is not turned on until its runbook exists. Use the `add-runbook` skill.
- Every change says how it is rolled back. A change that cannot be rolled back says so and gets a second reviewer.
- Every outbound call has a timeout shorter than its caller's. Retry only idempotent operations, with exponential backoff and jitter, inside the caller's timeout.
- Asynchronous work ends visibly as complete or failed. Never leave it pending forever.
- Scale-to-zero systems stay idle-safe: no health check, probe, or timer that keeps a serverless database or service awake.

# Security baseline

- A change that adds a repository, a trust boundary (a new caller, network path, identity, or data crossing tenants or accounts), a model, tool, agent, or retrieval source, or an external dependency that handles data or runs code, updates the threat model in the same pull request. Use the `threat-model` skill.
- Defence in depth: a chain of threats that can reach a critical impact is broken by at least two independent controls on different layers and detected on one. An instruction to a model is never a control.
- Treat model output as untrusted input from whoever controls any text that reached the model.
- Deny by default and grant least privilege: IAM actions, network paths, tokens, and tool access are added when needed, scoped to the task.
- GitHub Actions are pinned to full commit SHAs with the version in a comment. Every repository runs Semgrep and Dependabot on pull requests and on `main`.
- A Critical or High scanner finding fails the build. Suppress a finding only inline with its reason (`nosemgrep: <rule> -- <reason>`), and say so in the pull request.
- Fix vulnerabilities within 7 days for Critical, 30 for High, 90 for Medium, and at the next change for Low, counted from triage. A finding that cannot meet its deadline is recorded as a risk with an owner and an expiry.
- A leaked secret is rotated first and investigated second.

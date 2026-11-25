---
description: TDD, lint before commit, commit attribution, and secrets for every Agentic AI Tools repository
alwaysApply: true
---

# Development practice

- Follow test-driven development. Add or update a failing test for the behavior, make it pass, then refactor with the tests green.
- Run the repository's formatter and linter before every commit, and fix everything they report. Never commit with known format or lint failures. The commands are in the repository's `AGENTS.md`.
- When an agent wrote or co-wrote a commit, end the commit message with that agent's `Co-Authored-By` trailer. A pull request body says it was generated with the agent.
- Secrets never go into commits, examples, fixtures, logs, or Terraform: no tokens, passwords, keys, or `.env` files. Use the platform's secret store and reference it. If a secret is missing, stop and say so. Do not invent one.
- `AGENTS.md` holds only facts about its own repository. A rule that applies to more than one repository belongs in a plugin in `agentic-ai-tools-plugins`.

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

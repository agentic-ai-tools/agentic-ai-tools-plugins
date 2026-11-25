---
description: Branch, commit, and pull request rules for every Agentic AI Tools repository
alwaysApply: true
---

# Git workflow

- Never make changes on `main`. Do not commit or push to `main`.
- Create a new branch from the latest `main`, do the work there, and open a pull request into `main`. Every change goes through a pull request.
- Never force-push to any branch: no `git push --force`, no `--force-with-lease`, no rewriting published history.
- Never copy another repository's code or SQL into this one. Depend on its published release.
- Do not switch a sibling repository off its current branch. Point at it with the repository's documented path variable instead.

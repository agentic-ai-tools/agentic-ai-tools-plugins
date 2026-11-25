---
description: Read an OKF v0.3 bundle from its indexes and open only the concepts a task needs
alwaysApply: true
---

# Read the bundle, not the tree

When the repository is an Open Knowledge Format v0.3 bundle (its root `index.md` sets `okf_version`), `index.md` at the root is the entry point.

- Read the root index, then the directory `index.md` for the group the task needs.
- Open a concept only when its one-line description matches the task.
- Do not read the whole tree to answer a narrow question.
- `index.md` and `log.md` are not concepts. A Markdown file with no `type` is not a concept.
- Link to a Decision instead of restating it.

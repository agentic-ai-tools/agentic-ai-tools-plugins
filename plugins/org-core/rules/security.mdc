---
description: Security baseline for every Agentic AI Tools repository - threat models, layered defences, supply chain, and vulnerability deadlines
alwaysApply: true
---

# Security baseline

- A change that adds a repository, a trust boundary (a new caller, network path, identity, or data crossing tenants or accounts), a model, tool, agent, or retrieval source, or an external dependency that handles data or runs code, updates the threat model in the same pull request. Use the `threat-model` skill.
- Defence in depth: a chain of threats that can reach a critical impact is broken by at least two independent controls on different layers and detected on one. An instruction to a model is never a control.
- Treat model output as untrusted input from whoever controls any text that reached the model.
- Deny by default and grant least privilege: IAM actions, network paths, tokens, and tool access are added when needed, scoped to the task.
- GitHub Actions are pinned to full commit SHAs with the version in a comment. Every repository runs Semgrep and Dependabot on pull requests and on `main`.
- A Critical or High scanner finding fails the build. Suppress a finding only inline with its reason (`nosemgrep: <rule> -- <reason>`), and say so in the pull request.
- Fix vulnerabilities within 7 days for Critical, 30 for High, 90 for Medium, and at the next change for Low, counted from triage. A finding that cannot meet its deadline is recorded as a risk with an owner and an expiry.
- A leaked secret is rotated first and investigated second.

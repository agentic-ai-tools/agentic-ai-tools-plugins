# Changelog

## Unreleased

- `feature-spec` 0.3.0: every `plan` prompt and the `plan-spec` skill carry a decision gate. Planning stops and asks the user when the design or spec leaves a gap, or when the plan would contradict, supersede, or add an ADR. Before asking about an ADR change, the agent lists its blast radius across the design repository and weighs cost against benefit with a recommendation. ADR changes are their own design pull request, merged before the code.
- `okf-design` 0.2.0: `check_okf.py` decodes JSON escapes in quoted frontmatter values, and skips links in nested and `~~~` code fences.
- `python-service` 0.2.1, `terraform-infra` 0.2.1, `feature-spec` 0.2.0: Claude Code hooks run `python3`, or `python` where there is no `python3`, so they work on stock macOS. `on_edit.py` runs a `python` tool command with its own interpreter.
- `feature-spec` 0.2.0: fixes from the d3-forge-api trial. New `claim`, `claims`, and `release` commands keep a shared record of in-flight work on `origin` (`refs/feature-specs/claims/`), and every plan prompt tells its session to use them. New `ship` command sets a spec and its children to `implemented`. `plan` keeps references of any file type, says where sibling repositories are, prints `repo@version` prerequisites from `x-fs-depends-on`, warns when specs in one wave share files or when spec files differ from `origin/main`, and asks for a red-then-green checkpoint. Child specs made without `--prompt-file` link to the parent's prompt log. `deprecate` accepts a replacement in the same spec. A new `docs/index.md` lists the OKF documents already in `docs/`. `design` lists context repositories such as contracts, and prefers table rows and headings for `role:`. Skills: blocking questions before drafting, a wave self-check, rules for parent specs and draft edits, and a ship step. `spec-reviewer` gains `INCONSISTENT` and `CONTRACT` and reviews a parent with its children. `spec-context` reads contracts.
- `feature-spec` 0.1.0: new plugin. Skills `write-spec` and `plan-spec`, agents `spec-context` and `spec-reviewer`, `spec_tool.py` (ID reservation on `origin`, OKF indexes, check, deprecate, plan waves), and a hook that checks edited specs.
- Build: `src/_shared/scripts/` holds scripts several plugins use, such as `on_edit.py`. The build copies each one into every plugin whose `hooks.yaml` runs it. Generated output is unchanged.
- `org-core` 0.2.0: always-on security and reliability baselines. Skill `threat-model` writes STRIDE and STRIDE-AI threat models as OKF concepts from a template, including attack chains and layered defences, and `check_threat_model.py` checks the format, scores, chain rule, and residual risk. Skill `add-runbook`.
- `genai-app` 0.1.0: new plugin for repositories that call models. Model security and model call reliability rules, skill `add-model-call`.
- `python-service` 0.2.0: service security and service reliability rules.
- `react-portal` 0.2.0: web security and resilience rule.
- `postgres-flyway` 0.2.0: migration safety and tenant isolation rule.
- `terraform-infra` 0.2.0: infrastructure resilience and edge security rule.
- The repository is public under the MIT license. The README covers installing the plugins outside Agentic AI Tools.

## 2026-11-25

- `org-core` 0.1.0, `python-service` 0.1.0, `react-portal` 0.1.0, `postgres-flyway` 0.1.0, `terraform-infra` 0.1.0, `okf-design` 0.1.0: first release, taken from the MCP Wizard `AGENTS.md` and `.cursor/rules` files and the `d3-forge-design` engineering standards.

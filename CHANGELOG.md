# Changelog

## Unreleased

- `feature-spec` 0.1.0: new plugin. Skills `write-spec` and `plan-spec`, agents `spec-context` and `spec-reviewer`, `spec_tool.py` (ID reservation on `origin`, OKF indexes, check, deprecate, plan waves), and a hook that checks edited specs.
- `org-core` 0.2.0: always-on security and reliability baselines. Skill `threat-model` writes STRIDE and STRIDE-AI threat models as OKF concepts from a template, including attack chains and layered defences, and `check_threat_model.py` checks the format, scores, chain rule, and residual risk. Skill `add-runbook`.
- `genai-app` 0.1.0: new plugin for repositories that call models. Model security and model call reliability rules, skill `add-model-call`.
- `python-service` 0.2.0: service security and service reliability rules.
- `react-portal` 0.2.0: web security and resilience rule.
- `postgres-flyway` 0.2.0: migration safety and tenant isolation rule.
- `terraform-infra` 0.2.0: infrastructure resilience and edge security rule.
- The repository is public under the MIT license. The README covers installing the plugins outside Agentic AI Tools.

## 2026-11-25

- `org-core` 0.1.0, `python-service` 0.1.0, `react-portal` 0.1.0, `postgres-flyway` 0.1.0, `terraform-infra` 0.1.0, `okf-design` 0.1.0: first release, taken from the MCP Wizard `AGENTS.md` and `.cursor/rules` files and the `d3-forge-design` engineering standards.

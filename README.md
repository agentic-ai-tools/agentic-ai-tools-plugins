# agentic-ai-tools-plugins

Coding-agent plugins from [Agentic AI Tools](https://agenticaitools.org) for Claude Code and Cursor. One plugin per stack, written once in `src/` and built into each agent's format.

This repository is public. Anyone can install these plugins. Some plugins (`org-core`, `react-portal`, `okf-design`) encode Agentic AI Tools' own conventions and are most useful in our repositories. Others, such as `python-service`, `postgres-flyway`, and `terraform-infra`, work in any project that uses that stack.

## Use these plugins in your own project

**Claude Code:**

```text
/plugin marketplace add agentic-ai-tools/agentic-ai-tools-plugins
/plugin install python-service@agentic-ai-tools
```

**Cursor:** add `https://github.com/agentic-ai-tools/agentic-ai-tools-plugins` as a plugin marketplace in Cursor's settings, then install the plugins you want.

Hooks run commands on your machine when the agent edits files. Every hook runs only a local formatter, linter, or checker (`ruff`, `oxlint`, `terraform fmt`, the `feature-spec` checker), makes no network call, and reads no secret. The `feature-spec` skill `write-spec` (not its hook) pushes a ref under `refs/feature-specs/` to `origin` to reserve each spec ID, and `spec_tool.py claim` and `release` push and delete refs under `refs/feature-specs/claims/` to share in-flight work between agents. Its source is in `src/<plugin>/scripts/`, or `src/_shared/scripts/` for a script several plugins use. Read it before you install.

## Plugins

| Plugin | For | Contains |
| --- | --- | --- |
| `org-core` | Every repository | Always-on rules: branching, pull requests, TDD, lint before commit, attribution, secrets, the security baseline, the reliability baseline. Skills `threat-model` (STRIDE and STRIDE-AI, with a checker) and `add-runbook` |
| `python-service` | FastAPI services and lifecycle modules | Python, service-layer, service security, and service reliability rules. Skills `add-endpoint`, `add-port`, `add-store-query`. Hook: `ruff format` and `ruff check` on edited Python files |
| `react-portal` | Portals and SPAs | UI foundations and web security rules. Skills `add-page`, `add-data-table`. Hook: `oxlint` on edited files |
| `postgres-flyway` | Schema repositories and modules that own a schema | Flyway and Postgres, and migration safety rules |
| `terraform-infra` | Bootstrap and infrastructure repositories | Terraform and infrastructure resilience rules. Hook: `terraform fmt` on edited files |
| `okf-design` | OKF design bundles | Read and author rules. Skill `okf-check` |
| `genai-app` | Repositories that call models | Model security (STRIDE-AI: prompt injection, output handling, excessive agency, leakage, poisoning, provenance, spend) and model call reliability rules. Skill `add-model-call` |
| `feature-spec` | Every repository that keeps feature specifications | Skill `write-spec` writes a spec from a prompt as an OKF concept in `docs/features/`, with citable item IDs (`FS-012.3.1`) reserved on `origin` so parallel agents never collide, context from the matching design repository, questions for anything missing, a consistency review that deprecates contradicted items, and decomposition into child specs. Skill `plan-spec` prints plan-mode prompts in parallel waves, warns about shared files, and has agents claim their work on `origin` so parallel sessions see each other. Agents `spec-context` (Haiku) and `spec-reviewer` (Sonnet). Hook: checks edited specs |

## Install in an Agentic AI Tools repository

**Claude Code.** Commit this to the repository's `.claude/settings.json`, enabling `org-core` plus the stack plugins it needs:

```json
{
  "extraKnownMarketplaces": {
    "agentic-ai-tools": {
      "source": { "source": "github", "repo": "agentic-ai-tools/agentic-ai-tools-plugins" }
    }
  },
  "enabledPlugins": {
    "org-core@agentic-ai-tools": true,
    "python-service@agentic-ai-tools": true,
    "feature-spec@agentic-ai-tools": true
  }
}
```

By hand: `claude plugin marketplace add agentic-ai-tools/agentic-ai-tools-plugins`, then `claude plugin install <plugin>@agentic-ai-tools`.

**Cursor.** On a team plan, import this repository once as the team marketplace and distribute `org-core` to everyone. Without one, each developer adds this repository as a plugin marketplace in Cursor's settings and installs the plugins their repository's `AGENTS.md` lists.

## Change a plugin

Edit only `src/<plugin>/`. Never edit `plugins/` or the marketplace files by hand: they are generated and committed, and CI fails when they differ from a fresh build.

```bash
python -m pip install -e ".[dev]"
python scripts/build.py            # regenerate plugins/ and both marketplaces
python -m pytest                   # build tests, hook tests, Claude validator when installed
python -m ruff format . && python -m ruff check .
```

A source plugin holds:

```text
src/<plugin>/
  plugin.yaml          name, version, description
  rules/*.md           frontmatter: description, and exactly one of alwaysApply: true or globs
  skills/<name>/       SKILL.md (frontmatter: name, description) and any files it uses
  agents/*.md          frontmatter: name, description
  scripts/             helper scripts for hooks, copied unchanged
  hooks.yaml           after-edit, session-start, before-shell, stop: a list of {command}
  mcp.yaml             MCP servers by name, no credentials
```

In a hook `command`, `{root}` is the plugin's install folder. The build writes `"${CLAUDE_PLUGIN_ROOT}"` for Claude Code and `.` for Cursor. Anything with no mapping for both agents fails the build.

Bump the plugin's `version` in `plugin.yaml` with every change and add a line to [CHANGELOG.md](CHANGELOG.md). A rule change that would fail existing repositories is a major version.

## How each agent gets it

| Source | Claude Code | Cursor |
| --- | --- | --- |
| `alwaysApply` rule | `context/always-on.md`, printed by a `SessionStart` hook | `rules/*.mdc`, `alwaysApply: true` |
| `globs` rule | A skill in `rule-skills/`, which only the Claude manifest names | `rules/*.mdc` with `globs` |
| `skills/` | `skills/` | `skills/` |
| `hooks.yaml` | `hooks/hooks.json` | `hooks/cursor.json`, named by the Cursor manifest |
| `mcp.yaml` | `.mcp.json` | `mcp.json` |

A path in a Cursor manifest replaces Cursor's folder discovery, so Cursor never loads the Claude-only `rule-skills/` or `hooks/hooks.json`. A `skills` path in a Claude manifest adds to the default `skills/`, which `claude plugin validate` confirms.

## Not yet verified

- **Cursor hooks.** Cursor's hook reference page was unavailable. Still to check: the `afterFileEdit` stdin field (the runner reads `file_path`), and whether hooks run from the plugin folder (the Cursor commands use `./scripts/...`). Check both in Cursor before the first release.
- **`python` on PATH.** The Python hooks call `python`. On machines where only `python3` exists, they fail to start.

## Contributing

Issues and pull requests are welcome. A pull request changes `src/` and includes the regenerated `plugins/` output from `python scripts/build.py`.

## License

[MIT](LICENSE)

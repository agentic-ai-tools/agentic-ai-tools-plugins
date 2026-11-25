# agentic-ai-tools-plugins

The `agentic-ai-tools` plugin marketplace for Claude Code and Cursor. Plugins are written once in `src/<plugin>/` and `scripts/build.py` generates `plugins/` and both marketplace files. Design: ADR-029 and `engineering/agent-plugins.md` in `d3-forge-design`.

## Commands

```bash
python -m pip install -e ".[dev]"
python scripts/build.py          # regenerate; commit the result with the source change
python scripts/build.py --check  # what CI runs
python -m pytest
python -m ruff format . && python -m ruff check .
```

## Repository rules

- Edit only `src/`, `scripts/`, and `tests/`. Never edit `plugins/`, `.claude-plugin/`, or `.cursor-plugin/` by hand.
- Bump the plugin's `version` and add a `CHANGELOG.md` line with every plugin change.
- A hook runs only local tools already in the target repository's toolchain. It makes no network call and reads no secret. `mcp.yaml` carries no credentials.

## Plugins

`org-core`, `python-service`.

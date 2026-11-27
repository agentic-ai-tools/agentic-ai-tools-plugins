---
name: plan-spec
description: Turn an approved feature specification into ready-to-paste prompts for the coding tool's native plan mode, ordered into waves so independent child specs can be planned and built in parallel. Use when asked to plan, or to start implementing, a feature spec such as FS-012.
---

# Plan a feature specification

The argument is a spec ID such as `FS-012`. If none is given, run `python <plugin>/scripts/spec_tool.py index` and ask which one to plan. `<plugin>/scripts/spec_tool.py` is `<this skill's folder>/../../scripts/spec_tool.py`.

Run `python <plugin>/scripts/spec_tool.py plan FS-NNN` from the repository root, and show the user its output unchanged.

- If it refuses because the spec or a child is not approved, or because the check fails, report that. Offer to finish the spec with the `write-spec` skill. Do not plan around it.
- Each prompt is meant for a fresh session in native plan mode: `/plan` or Shift+Tab in Claude Code, Plan mode in Cursor.
- Specs in the same wave do not depend on each other. Offer to start them in parallel sessions or worktrees. Start a wave only once the waves before it are planned.
- If the user asks you to plan one of them in this session, enter plan mode and use that spec's prompt as the request.

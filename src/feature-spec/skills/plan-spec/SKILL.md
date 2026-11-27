---
name: plan-spec
description: Turn an approved feature specification into ready-to-paste prompts for the coding tool's native plan mode, ordered into waves so independent child specs can be planned and built in parallel, with shared claims on origin so parallel agents see each other's work. Use when asked to plan, or to start implementing, a feature spec such as FS-012.
---

# Plan a feature specification

The argument is a spec ID such as `FS-012`. If none is given, run `ST index` and ask which one to plan. `ST` means `python <plugin>/scripts/spec_tool.py`, where `<plugin>/scripts/spec_tool.py` is `<this skill's folder>/../../scripts/spec_tool.py`.

Run `ST plan FS-NNN` from the repository root, and show the user its output unchanged.

- If it refuses because the spec or a child is not approved, or because the check fails, report that. Offer to finish the spec with the `write-spec` skill. Do not plan around it.
- If it starts with a WARNING that the spec files differ from `origin/main`, tell the user to merge the spec pull request before starting sessions from `main`. A session started from `main` would not find the files.
- Each prompt is meant for a fresh session in native plan mode: `/plan` or Shift+Tab in Claude Code, Plan mode in Cursor.
- Specs in the same wave do not depend on each other. But if the wave lists **shared files**, building them in parallel will conflict. Offer to build those one after another, each branch based on the one before, or ask the user for a merge order. Otherwise, offer parallel sessions or worktrees. Start a wave only once the waves before it are planned.
- If an **external prerequisite** such as `acme-contracts@v0.1.0` is listed, check that it is released before wave 1 starts.
- If the user asks you to plan one of them in this session, enter plan mode and use that spec's prompt as the request.

## Design gaps and decisions

Every prompt ends with a decision gate, and it applies in this session too. Stop and ask the user, before planning further, when:

- the design or the spec leaves a gap that the plan would fill with its own choice, such as who owns a data store, which contract to use, or a security or cost trade-off;
- the plan would contradict, supersede, or narrow an existing decision record (ADR);
- the plan needs a decision that no ADR records.

Never decide it yourself and never edit an ADR from a plan. Before asking about an ADR change:

1. **Blast radius.** Search the design repository for the ADR's ID and title. List every ADR, design document, contract, spec, and repository that cites or builds on it, what each would have to change, and what is already built on it.
2. **Cost and benefit.** Weigh the work and risk of the change across that radius against what it gains and what keeping the current decision costs. Recommend one option.
3. **Ask** with those facts, offering: fit the plan to the current decision, change the ADR, or write a new ADR. Up to four questions at a time, with AskUserQuestion where it exists.

An ADR change or a new ADR is its own pull request in the design repository, merged before the code that depends on it. If the answer changes the spec, update it with the `write-spec` skill and run `ST plan` again.

## Shared work claims

Agents building in parallel keep a shared record of their work on `origin`, under `refs/feature-specs/claims/`. Every prompt tells its session to do this. Before offering parallel sessions, run `ST claims` and show the user any existing claim or `OVERLAP` line.

- `ST claims` lists who is building which spec, on which branch, and which files, and flags files named by two claims.
- `ST claim FS-NNN --files <files>` claims a spec before writing code. It fails if another agent already claims that spec.
- `ST release FS-NNN` removes the claim once the pull request merges. A claim older than its branch's merge is stale. Release it after checking with the user.

When the last pull request for the feature is ready, run `ST ship FS-NNN` (see the `write-spec` skill).

## Known environment issues

- If GitHub Packages refuses the `gh` CLI token for npm ("does not match expected scopes"), point the tests at a local checkout of the package's repository at the released tag, through an environment variable, instead of the registry. Pin the exact version in CI.

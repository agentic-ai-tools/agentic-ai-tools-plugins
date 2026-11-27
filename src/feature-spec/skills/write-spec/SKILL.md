---
name: write-spec
description: Write a feature specification from a prompt, stored with the repository that implements it as an OKF concept in docs/features/ with citable item IDs, context from the matching design repository, questions to the user for anything missing, a consistency review that deprecates contradicted items, and decomposition into child specs when it is too large to plan at once. Use when asked to write, draft, or spec a feature.
---

# Write a feature specification

The user's prompt is the argument given with this skill. If there is none, ask for it.

`ST` below means `python <plugin>/scripts/spec_tool.py`, where `<plugin>` is two folders up from this file. Run every command from the root of the repository the feature is built in. A spec only covers work done in that repository.

Scripts do everything that is deterministic. Do not hand-edit IDs, index files, or deprecation markers.

## Steps

1. **Log the prompt.** If the prompt contains a secret or a credential, stop and ask the user to remove it, because the prompt log is committed. Otherwise, write the prompt verbatim to a temporary file. Pick a short title, then run `ST new --title "<title>" --prompt-file <file>`. This reserves the next `FS-NNN` on `origin`, creates the spec from the template and the prompt log, and updates the indexes. If it fails because the repository is offline or has no origin, tell the user. Never make up an ID.
2. **Find the design.** Run `ST design`. If it prints `design: none`, ask the user where the design or planning repository is, or whether there is one.
3. **Gather context.** Hand the prompt, the design path, the repository name, and the `role:` lines to the `spec-context` agent. Use what it returns, and do not read the design repository yourself unless it reports a gap.
4. **Read the existing specs.** Run `ST index`. Open an existing spec only when an item in the index bears on this one.
5. **Draft.** Fill in every section of the spec file. Keep the headings exactly as they are.
   - Section 1 cites design documents as code, `` `<design-repo>:path.md` ``, and never as links. Put the requirement or decision ID the spec serves in `x-fs-requirement`.
   - Each requirement is one testable statement: `- **FS-NNN.3.n** ...`. Each acceptance criterion names the requirements it verifies: `- **FS-NNN.6.n** Verifies FS-NNN.3.1. ...`.
   - Number new items after the highest number used so far. Never renumber or delete an item. An item that is no longer wanted gets deprecated.
   - Work that belongs to another repository goes under Out of scope as "spec in `<repository>`".
   - Set `description` to one sentence, then run `ST reindex`.
6. **Split it if it is too big.** Split when there are more than about 8 requirements, more than one deployable component, or parts that could be built in parallel. Run `ST new --parent FS-NNN --title "<child 1>" --title "<child 2>" ... --prompt-file <file>`. The parent keeps sections 1 and 2 and the feature-level acceptance criteria. Each child gets its own requirements and sets `x-fs-depends-on` on any sibling it needs first, so that independent children can be planned in parallel. List the children in the parent's section 7.
7. **Ask instead of guessing.** Write each missing or ambiguous point under Open questions. Ask the user about them, up to four at a time (with AskUserQuestion where it exists), then fold each answer into the spec and remove the question. Repeat until the section reads exactly `None.`
8. **Review for consistency.** Give the spec path and the output of `ST index` to the `spec-reviewer` agent.
   - For each `CONTRADICTS` finding, show the user both items. If they agree, run `ST deprecate <new item> <old item>` and say why in section 9.
   - For each `OVERLAPS` finding, cite the other item.
   - Handle `AMBIGUOUS` and `UNTESTABLE` findings as in step 7.
9. **Check.** Run `ST check` and fix every line it prints until it exits 0. After a pull request, `ST check --base origin/main` also reports items deleted since `main`.
10. **Approve.** Set `x-fs-status: approved` only when the user says so. `ST check` then also requires no TODO to be left. To plan the spec, use the `plan-spec` skill.

## Statuses

`draft` is being written. `approved` is ready to plan. `implemented` means it has shipped. `superseded` means every item in it has been deprecated.

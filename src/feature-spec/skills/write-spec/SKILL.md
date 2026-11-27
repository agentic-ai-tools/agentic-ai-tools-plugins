---
name: write-spec
description: Write a feature specification from a prompt, stored with the repository that implements it as an OKF concept in docs/features/ with citable item IDs, context from the matching design and contracts repositories, questions to the user for anything missing, a consistency review, and decomposition into child specs when it is too large to plan at once. Use when asked to write, draft, or spec a feature.
---

# Write a feature specification

The user's prompt is the argument given with this skill. If there is none, ask for it.

`ST` below means `python <plugin>/scripts/spec_tool.py`, that is, `python <this skill's folder>/../../scripts/spec_tool.py`. Run every command from the root of the repository the feature is built in. A spec only covers work done in that repository.

Scripts do everything that is deterministic. Do not hand-edit IDs, index files, or deprecation markers. The plugin's edit hook runs `ST check` on each edited spec. If the hook did not run, because the plugin is not installed, run `ST check` yourself after each edit.

## Steps

1. **Log the prompt.** If the prompt contains a secret or a credential, stop and ask the user to remove it, because the prompt log is committed. Otherwise, write the prompt verbatim to a temporary file. Pick a short title, then run `ST new --title "<title>" --prompt-file <file>`. This reserves the next `FS-NNN` on `origin`, creates the spec from the template and the prompt log, and updates the indexes. If it fails because the repository is offline or has no origin, tell the user. Never make up an ID.
2. **Find the context.** Run `ST design`. It prints the design repository, a `context:` line for each other sibling repository it found (contracts, for example), and `role:` lines. If it prints `design: none`, ask the user where the design or planning repository is, or whether there is one. Add any other repository the prompt names.
3. **Gather context.** Hand the prompt, the design path, every context path, the repository name, and the `role:` lines to the `spec-context` agent. Use what it returns, and do not read those repositories yourself unless it reports a gap.
4. **Read the existing specs.** Run `ST index`. Open an existing spec only when an item in the index bears on this one.
5. **Ask blocking questions first.** If a gap or conflict from step 3 would change the structure of the spec, or every child of it (who owns a data store, which contract version to pin, a requirement the design contradicts), ask the user now, before drafting. Up to four at a time, with AskUserQuestion where it exists.
6. **Draft.** Fill in every section of the spec file. Keep the headings exactly as they are.
   - Section 1 cites design and contract files as code, `` `<repo>:path/file.ext` ``, and never as links. Any file type is fine, for example `` `acme-contracts:openapi/api.yaml` ``. Put the requirement or decision ID the spec serves in `x-fs-requirement`.
   - Section 4 names, as code, every file the work edits, for example `` `app/main.py` ``. `plan` uses these names to warn when parallel specs touch the same file.
   - Each requirement is one testable statement: `- **FS-NNN.3.n** ...`. Each acceptance criterion names the requirements it verifies: `- **FS-NNN.6.n** Verifies FS-NNN.3.1. ...`.
   - Number new items after the highest number used so far. Never renumber an item. A draft item's text may be rewritten until the spec first merges to `main`. After that, an item that is wrong or no longer wanted gets deprecated (step 9).
   - Work that belongs to another repository goes under Out of scope as "spec in `<repository>`".
   - A prerequisite released by another repository goes in `x-fs-depends-on` as `<repo>@<version>`, for example `acme-contracts@v0.1.0`.
   - Set `description` to one sentence, then run `ST reindex`.
7. **Split it if it is too big.** Split when there are more than about 8 requirements, more than one deployable component, or parts that could be built in parallel. Run `ST new --parent FS-NNN --title "<child 1>" --title "<child 2>" ...` with no `--prompt-file`: children link to the parent's prompt log. Give a child its own `--prompt-file` only when a later prompt changes it.
   - The parent keeps sections 1 and 2 and the feature-level acceptance criteria. It may hold no requirements of its own. Its criteria verify the children's requirements (`Verifies FS-002.3.1 ...`), and must not repeat a criterion a child already has.
   - Each child gets its own requirements and sets `x-fs-depends-on` on any sibling it needs first, so that independent children can be planned in parallel. List the children in the parent's section 7.
8. **Self-check, then ask.** For each acceptance criterion, check that every route, file, or behaviour it uses exists by its wave in section 7. A criterion that needs a later sibling belongs to the parent or to that sibling. Then write each missing or ambiguous point under Open questions. Ask the user, fold each answer into the spec, and remove the question. Repeat until the section reads exactly `None.`
9. **Review for consistency.** Give the spec paths (the parent and every child) and the output of `ST index` to the `spec-reviewer` agent.
   - `CONTRADICTS <new> <old>`: an older spec outside this set. Show the user both items. If they agree, run `ST deprecate <new item> <old item>` and say why in section 9. A replacement inside the same spec works the same way: add the new item with the next number, then deprecate the old one.
   - `INCONSISTENT` and `CONTRACT`: fix the draft in place. Never deprecate for these.
   - `OVERLAPS`: cite the other item. If a parent's criterion repeats a child's, remove it from the parent.
   - `AMBIGUOUS` and `UNTESTABLE`: handle as in step 8.
10. **Check.** Run `ST check` and fix every line it prints until it exits 0. After a pull request, `ST check --base origin/main` also reports items deleted since `main`.
11. **Approve.** Set `x-fs-status: approved` only when the user says so. `ST check` then also requires no TODO to be left. To plan the spec, use the `plan-spec` skill.
12. **Ship.** In the last pull request that implements the spec, after every acceptance criterion has a passing test, run `ST ship FS-NNN`. It sets the spec and all its children to `implemented` and adds a changelog line to each.

## Statuses

`draft` is being written. `approved` is ready to plan. `implemented` means it has shipped (set by `ST ship`). `superseded` means every item in it has been deprecated.

## Known environment issues

- In Git Bash on Windows, long heredocs (a few KB) fail with `unexpected EOF while looking for matching`. Write a long script to a file and run the file.
- To count a session's tokens, use the transcript whose id matches the scratchpad folder's session id. The task-output folder can carry a different id.

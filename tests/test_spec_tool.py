from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

# reservations are commits; give them an identity and keep a developer's signing config out
os.environ.update(
    GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
    GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="commit.gpgsign", GIT_CONFIG_VALUE_0="false",
)  # fmt: skip

sys.dont_write_bytecode = True  # keep src/ free of __pycache__
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC / "feature-spec/scripts"))
sys.path.insert(0, str(SRC / "okf-design/skills/okf-check"))
import check_okf  # noqa: E402
import spec_tool as st  # noqa: E402

BODY = """
# {id} Example

Original prompt: [{id} prompt](prompts/{id}.md).

## 1. Context

Customers need it. Design: `acme-design:products/x.md`.

## 2. Scope

### In scope

- The thing.

### Out of scope

- Billing, spec in `acme-billing`.

## 3. Requirements

- **{id}.3.1** The service stores the thing.
- **{id}.3.2** The service returns the thing.

## 4. Design

A table and an endpoint.

## 5. Security and reliability

Tenant from the token.

## 6. Acceptance criteria

- **{id}.6.1** Verifies {id}.3.1 and {id}.3.2. A stored thing is returned.

## 7. Decomposition and dependencies

None.

## 8. Open questions

None.

## 9. Deprecations

None.

## 10. Changelog

- 2026-11-26: created.
"""


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_repo(tmp: Path, name: str = "acme-api", origin: Path | None = None) -> Path:
    if origin is None:
        origin = tmp / "origin.git"
        git(tmp, "init", "--bare", "-q", str(origin))
    repo = tmp / name
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "remote", "add", "origin", str(origin))
    return repo


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path)


def new(root: Path, *titles: str, parent: str = "") -> list[Path]:
    prompt = (
        root.parent / f"{root.name}-prompt.txt"
    )  # one per clone: the race test runs two at once
    prompt.write_text("Build the thing. ```code``` and [a](b).\n", encoding="utf-8")
    return st.cmd_new(root, list(titles), prompt, parent)


def fill(path: Path, status: str = "approved", depends: str = "[]", parent: str = "") -> None:
    sid = path.name[:6]
    text = path.read_text(encoding="utf-8")
    head = text[: text.index("\n---\n", 4) + 5]
    head = head.replace("x-fs-status: draft", f"x-fs-status: {status}")
    head = head.replace(
        "TODO: one sentence that says what this feature lets someone do.", "Does it."
    )
    head = head.replace("x-fs-depends-on: []", f"x-fs-depends-on: {depends}")
    path.write_text(head + BODY.replace("{id}", sid), encoding="utf-8")
    st.cmd_reindex(path.parents[2])


def test_new_writes_okf_docs_that_pass_both_checkers(repo: Path) -> None:
    paths = new(repo, "First thing")
    assert [p.name for p in paths] == ["FS-001-first-thing.md"]
    assert (repo / "docs/features/prompts/FS-001.md").exists()
    assert st.UNION_ATTR in (repo / ".gitattributes").read_text(encoding="utf-8")
    assert st.check_all(repo) == []
    assert check_okf.check(repo / "docs") == []


def test_ids_never_collide_across_clones(tmp_path: Path) -> None:
    a = make_repo(tmp_path, "a")
    b = make_repo(tmp_path, "b", origin=tmp_path / "origin.git")
    (tmp_path / "a" / "x").mkdir()  # make the two trees differ
    with ThreadPoolExecutor(2) as pool:
        got = list(pool.map(lambda r: new(r, "One", "Two", "Three"), [a, b]))
    ids = [p.name[:6] for paths in got for p in paths]
    assert len(set(ids)) == 6
    assert sorted(ids) == [f"FS-00{n}" for n in range(1, 7)]


def test_new_fails_without_origin(tmp_path: Path) -> None:
    repo = tmp_path / "solo"
    repo.mkdir()
    git(repo, "init", "-q")
    with pytest.raises(st.ToolError, match="only online"):
        new(repo, "Nope")


def test_approved_spec_passes_and_its_rules_are_enforced(repo: Path) -> None:
    (path,) = new(repo, "Thing")
    fill(path)
    assert st.check_all(repo) == []
    text = path.read_text(encoding="utf-8")
    broken = (
        text.replace("None.\n\n## 9.", "Who owns it?\n\n## 9.")
        .replace("A stored thing", "TODO a stored thing")
        .replace("Verifies FS-001.3.1 and FS-001.3.2.", "Cites FS-009.3.1.")
        .replace("- **FS-001.3.2**", "- **FS-001.4.2**")
    )
    path.write_text(broken, encoding="utf-8")
    problems = "\n".join(st.check_all(repo))
    assert "Open questions 'None.'" in problems
    assert "no TODO left" in problems
    assert "reference FS-009.3.1 does not exist" in problems
    assert "criterion FS-001.6.1 cites no requirement" in problems
    assert "requirement FS-001.3.1 has no acceptance criterion" in problems
    assert "item FS-001.4.2 must start with FS-001.3." in problems


def test_deprecate_marks_both_specs(repo: Path) -> None:
    old, newer = new(repo, "Old", "Newer")
    fill(old)
    fill(newer)
    st.cmd_deprecate(repo, "FS-002.3.1", ["FS-001.3.1"])
    assert "> Deprecated by [FS-002.3.1](FS-002-newer.md)" in old.read_text(encoding="utf-8")
    assert "x-fs-deprecates: [FS-001.3.1]" in newer.read_text(encoding="utf-8")
    specs, _ = st.load_specs(repo)
    assert specs["FS-001"].items["FS-001.3.1"].deprecated_by == "FS-002.3.1"
    # FS-001.6.1 still cites the deprecated FS-001.3.1, so FS-001.3.2 keeps its criterion
    assert st.check_all(repo) == []
    assert "  FS-001.3.1 " not in st.cmd_index(repo)
    with pytest.raises(st.ToolError, match="already deprecated"):
        st.cmd_deprecate(repo, "FS-002.3.2", ["FS-001.3.1"])
    newer.write_text(
        newer.read_text(encoding="utf-8").replace("[FS-001.3.1]", "[]"), encoding="utf-8"
    )
    assert any("does not list it" in p for p in st.check_all(repo))


def test_index_drift_is_reported_and_reindex_fixes_it(repo: Path) -> None:
    (path,) = new(repo, "Thing")
    fill(path)
    path.write_text(
        path.read_text(encoding="utf-8").replace("Does it.", "Does more."), encoding="utf-8"
    )
    assert any("index description differs" in p for p in st.check_all(repo))
    st.cmd_reindex(repo)
    assert st.check_all(repo) == []


def test_base_reports_deleted_items(repo: Path) -> None:
    (path,) = new(repo, "Thing")
    fill(path)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "x")
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("- **FS-001.3.2** The service returns the thing.\n", ""))
    assert any("item FS-001.3.2 deleted since HEAD" in p for p in st.check_all(repo, "HEAD"))


def test_hook_path_filter(repo: Path, tmp_path: Path) -> None:
    (path,) = new(repo, "Thing")
    path.write_text(path.read_text(encoding="utf-8").replace("type: Capability", "type: X"))
    assert st.cmd_check(repo, [str(tmp_path / "README.md")], None) == []
    assert any("type must be Capability" in p for p in st.cmd_check(repo, [str(path)], None))


def test_plan_orders_children_into_waves(repo: Path) -> None:
    (parent,) = new(repo, "Parent")
    a, b, c = new(repo, "A", "B", "C", parent="FS-001")
    for p in (parent, a, c):
        fill(p)
    fill(b, depends="[FS-002]")
    out = st.cmd_plan(repo, "FS-001")
    assert out.index("## Wave 1") < out.index("### FS-002") < out.index("### FS-004")
    assert out.index("## Wave 2") < out.index("### FS-003")
    assert "Requirements to implement: FS-003.3.1, FS-003.3.2" in out
    assert "References: acme-design:products/x.md" in out
    assert "Parent spec: FS-001" in out
    c.write_text(c.read_text(encoding="utf-8").replace("status: approved", "status: draft"))
    with pytest.raises(st.ToolError, match="not approved: FS-004"):
        st.cmd_plan(repo, "FS-001")


def test_plan_rejects_cycles(repo: Path) -> None:
    (parent,) = new(repo, "Parent")
    a, b = new(repo, "A", "B", parent="FS-001")
    fill(parent)
    fill(a, depends="[FS-003]")
    fill(b, depends="[FS-002]")
    with pytest.raises(st.ToolError, match="cycle"):
        st.cmd_plan(repo, "FS-001")


def test_design_found_from_agents_md_and_by_sibling_name(tmp_path: Path) -> None:
    root = tmp_path / "acme-api"
    root.mkdir()
    design = tmp_path / "acme-design"
    (design / "eng").mkdir(parents=True)
    (design / "eng/map.md").write_text("| `acme-api` | the API |\n", encoding="utf-8")
    assert st.find_design(root) == design
    assert "eng/map.md:1: | `acme-api` | the API |" in st.cmd_design(root)
    other = tmp_path / "plans"
    other.mkdir()
    (root / "AGENTS.md").write_text("Design: in `plans-design`.\n", encoding="utf-8")
    assert st.find_design(root) == design  # named folder missing, falls back to sibling
    (tmp_path / "plans-design").mkdir()
    assert st.find_design(root) == tmp_path / "plans-design"
    assert st.cmd_design(tmp_path / "plans") == "design: none"


def test_parent_criteria_may_cite_child_requirements_and_sections(repo: Path) -> None:
    (parent,) = new(repo, "Parent")
    (child,) = new(repo, "Child", parent="FS-001")
    (other,) = new(repo, "Other")
    for p in (parent, child, other):
        fill(p)
    text = parent.read_text(encoding="utf-8")
    text = text.replace(
        "- **FS-001.3.1** The service stores the thing.\n"
        "- **FS-001.3.2** The service returns the thing.\n",
        "Held by the child specs.\n",
    ).replace("Verifies FS-001.3.1 and FS-001.3.2.", "Verifies FS-002.3.1.")
    parent.write_text(text.replace("Customers need it.", "See FS-002.4."), encoding="utf-8")
    assert st.check_all(repo) == []
    out = st.cmd_plan(repo, "FS-001")
    assert out.index("## Integration") > out.index("### FS-002")
    assert "acceptance criteria: FS-001.6.1" in out
    parent.write_text(
        parent.read_text(encoding="utf-8").replace("FS-002.3.1.", "FS-003.3.1. See FS-002.11."),
        encoding="utf-8",
    )
    problems = "\n".join(st.check_all(repo))
    assert "criterion FS-001.6.1 cites no requirement" in problems  # FS-003 is not a child
    assert "reference FS-002.11 does not exist" in problems


def test_reservation_does_not_publish_the_hostname(repo: Path) -> None:
    import socket

    new(repo, "Thing")
    log = subprocess.run(
        ["git", "--git-dir", str(repo.parent / "origin.git"), "log", "--format=%B",
         "refs/feature-specs/FS-001"],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    assert "reserve FS-001 Thing" in log
    assert socket.gethostname() not in log


def test_child_without_prompt_links_the_parent_prompt(repo: Path) -> None:
    new(repo, "Parent")
    (child,) = st.cmd_new(repo, ["Child"], None, "FS-001")
    (grandchild,) = st.cmd_new(repo, ["Grandchild"], None, "FS-002")
    assert not (repo / "docs/features/prompts/FS-002.md").exists()
    assert "(prompts/FS-001.md)" in grandchild.read_text(encoding="utf-8")
    assert "FS-002" not in (repo / "docs/features/prompts/index.md").read_text(encoding="utf-8")
    assert st.check_all(repo) == []
    with pytest.raises(st.ToolError, match="--prompt-file is required"):
        st.cmd_new(repo, ["Orphan"], None, "")


def test_new_keeps_existing_docs_in_docs_index(repo: Path) -> None:
    (repo / "docs").mkdir()
    (repo / "docs/threat-model.md").write_text(
        '---\ntype: Reference\ntitle: "Threat model"\ndescription: "STRIDE rows."\n---\n\n# TM\n',
        encoding="utf-8",
    )
    new(repo, "Thing")
    index = (repo / "docs/index.md").read_text(encoding="utf-8")
    assert "* [Threat model](threat-model.md) - STRIDE rows." in index
    assert "features/index.md" in index
    assert check_okf.check(repo / "docs") == []


def test_plan_carries_contracts_externals_shared_files_and_branch_warning(repo: Path) -> None:
    (repo.parent / "acme-contracts").mkdir()
    (parent,) = new(repo, "Parent")
    a, b = new(repo, "A", "B", parent="FS-001")
    fill(parent, depends="[acme-contracts@v0.1.0]")
    for p in (a, b):
        fill(p)
        text = p.read_text(encoding="utf-8").replace(
            "Design: `acme-design:products/x.md`.",
            "Design: `acme-design:products/x.md`, contract `acme-contracts:openapi/api.yaml`, "
            "see `https://example.com/a.html`.",
        )
        p.write_text(
            text.replace("A table and an endpoint.", "Edits `app/main.py`, pins `v0.1.0`.")
        )
    assert st.check_all(repo) == []
    out = st.cmd_plan(repo, "FS-001")
    assert "References: acme-contracts:openapi/api.yaml, acme-design:products/x.md" in out
    assert "acme-contracts is a sibling checkout at ../acme-contracts." in out
    assert "acme-design was not found next to this repository" in out
    assert "External prerequisites, released before this wave: acme-contracts@v0.1.0" in out
    assert "Shared files in wave 1: `app/main.py` (FS-002, FS-003)" in out
    assert "`v0.1.0` (" not in out and "https" not in out
    assert out.startswith("# Planning prompts for FS-001\n\nWARNING: the spec files differ")
    assert "red-then-green" in out and "claims`" in out and "release FS-002`" in out
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "x")
    git(repo, "push", "-q", "origin", "HEAD:main")
    git(repo, "fetch", "-q", "origin")
    assert "WARNING" not in st.cmd_plan(repo, "FS-001")
    (repo / "docs/features/notes.md").write_text("new\n", encoding="utf-8")
    assert "WARNING" not in st.cmd_plan(repo, "FS-001")  # not one of the planned specs
    assert st.off_main(repo, ["docs/features/notes.md"])  # untracked is not on main either


def test_deprecate_within_the_same_spec(repo: Path) -> None:
    (path,) = new(repo, "Thing")
    fill(path)
    text = path.read_text(encoding="utf-8").replace(
        "- **FS-001.3.2** The service returns the thing.\n",
        "- **FS-001.3.2** The service returns the thing.\n"
        "- **FS-001.3.3** The service returns the thing fast.\n",
    )
    path.write_text(text.replace("and FS-001.3.2.", "FS-001.3.2 and FS-001.3.3."))
    st.cmd_deprecate(repo, "FS-001.3.3", ["FS-001.3.2"])
    text = path.read_text(encoding="utf-8")
    assert "> Deprecated by [FS-001.3.3](FS-001-thing.md)" in text
    assert "x-fs-deprecates: [FS-001.3.2]" in text
    assert st.check_all(repo) == []
    with pytest.raises(st.ToolError, match="itself"):
        st.cmd_deprecate(repo, "FS-001.3.1", ["FS-001.3.1"])


def test_ship_marks_the_family_implemented(repo: Path) -> None:
    (parent,) = new(repo, "Parent")
    (child,) = new(repo, "Child", parent="FS-001")
    fill(parent)
    fill(child, status="draft")
    with pytest.raises(st.ToolError, match="not approved: FS-002"):
        st.cmd_ship(repo, "FS-001")
    fill(child)
    assert st.cmd_ship(repo, "FS-001") == ["FS-001", "FS-002"]
    for p in (parent, child):
        text = p.read_text(encoding="utf-8")
        assert "x-fs-status: implemented" in text
        assert text.rstrip().endswith(": implemented.")
    assert st.check_all(repo) == []


def test_claims_are_shared_exclusive_and_released(tmp_path: Path) -> None:
    import socket

    a = make_repo(tmp_path, "a")
    b = make_repo(tmp_path, "b", origin=tmp_path / "origin.git")
    assert st.cmd_claims(b) == ["no claims"]
    st.cmd_claim(a, "FS-002", ["app/main.py", "app/x.py"])
    with pytest.raises(st.ToolError, match="FS-002 is already claimed: FS-002 on"):
        st.cmd_claim(b, "FS-002", ["app/y.py"])
    st.cmd_claim(b, "FS-003", ["app/main.py"])
    seen = st.cmd_claims(b)
    assert any(c.startswith("FS-002 on ") and c.endswith("app/main.py, app/x.py") for c in seen)
    assert "OVERLAP app/main.py: FS-002, FS-003" in seen
    assert socket.gethostname() not in "\n".join(seen)
    st.cmd_release(a, ["FS-002"])
    assert [c[:6] for c in st.cmd_claims(b)] == ["FS-003"]


def test_design_lists_context_repos_and_prefers_role_rows(tmp_path: Path) -> None:
    root = tmp_path / "acme-web-api"
    root.mkdir()
    (tmp_path / "acme-contracts").mkdir()
    (tmp_path / "acme-web").mkdir()  # a prefix folder nothing names
    design = tmp_path / "acme-design"
    design.mkdir()
    (design / "a.md").write_text(
        "Check acme-web-api with gh repo list.\n| `acme-web-api` | the API |\n", encoding="utf-8"
    )
    (root / "AGENTS.md").write_text("Run `..` from `.`; uses `acme-contracts`.\n", encoding="utf-8")
    out = st.cmd_design(root)
    assert f"context: {tmp_path / 'acme-contracts'}" in out
    assert out.count("context:") == 1
    assert "| `acme-web-api` | the API |" in out and "gh repo list" not in out


def test_cli_new_child_without_prompt_and_ship(repo: Path) -> None:
    (parent,) = new(repo, "Parent")
    assert st.main(["--root", str(repo), "new", "--title", "Child", "--parent", "FS-001"]) == 0
    fill(parent)
    fill(next((repo / "docs/features").glob("FS-002-*.md")))
    assert st.main(["--root", str(repo), "ship", "FS-001"]) == 0
    assert st.main(["--root", str(repo), "ship", "FS-001"]) == 1  # already implemented

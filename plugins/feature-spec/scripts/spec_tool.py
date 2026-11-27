"""Feature specification tool: allocate IDs, check, deprecate, index, plan, ship, and claim specs.

Specs are OKF v0.3 concepts in docs/features/FS-NNN-<slug>.md. Standard library only.

usage: spec_tool.py [--root DIR] <command> ...
  new --title T [--title T2 ...] [--prompt-file F] [--parent FS-n]
  design | reindex | index
  check [paths...] [--base REF]
  deprecate NEW_ITEM OLD_ITEM [OLD_ITEM ...]
  plan FS-n
  ship FS-n
  claim FS-n --files F [F ...] | claims | release FS-n [FS-m ...]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

FEATURES = Path("docs/features")
PROMPTS = FEATURES / "prompts"
TEMPLATE = Path(__file__).resolve().parent.parent / "skills/write-spec/template.md"
REF_NS = "refs/feature-specs"
CLAIMS = f"{REF_NS}/claims"
MAX_TRIES = 20
UNION_ATTR = "docs/features/**/index.md merge=union"

HEADINGS = [
    "Context",
    "Scope",
    "Requirements",
    "Design",
    "Security and reliability",
    "Acceptance criteria",
    "Decomposition and dependencies",
    "Open questions",
    "Deprecations",
    "Changelog",
]
REQ, CRIT, OPEN = 3, 6, 8
STATUSES = {"draft", "approved", "implemented", "superseded"}
FINAL = {"approved", "implemented"}

SPEC_FILE = re.compile(r"^(FS-\d{3,})-[a-z0-9-]+\.md$")
ITEM = re.compile(r"^\s*(?:[-*]\s+)?\*\*(FS-\d{3,}(?:\.\d+)+)\*\*\s*(.*)$")
DEPRECATED = re.compile(r"^\s*>\s*Deprecated by \[?(FS-\d{3,}(?:\.\d+)+)")
REF = re.compile(r"\bFS-\d{3,}(?:\.\d+)*")
HEADING = re.compile(r"^## (\d+)\. (.+)$")
REPO_REF = re.compile(r"`([\w.-]+):([^`\s/][^`\s]*\.\w+)`")  # not scheme://
CODE_PATH = re.compile(r"`([\w./-]+\.\w+)`")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
INDEX_LINE = re.compile(r"^\*\s+\[[^\]]*\]\(([^)]+)\)\s+-\s+(.+)$")


class ToolError(Exception):
    pass


# ---------- parsing ----------


def split_frontmatter(text: str) -> tuple[dict, list[str], str]:
    """Return (meta, raw frontmatter lines, body). Flat keys, inline lists, JSON-quoted strings."""
    if not text.startswith("---\n"):
        return {}, [], text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, [], text
    lines = text[4:end].splitlines()
    meta: dict = {}
    for line in lines:
        key, sep, value = line.partition(":")
        if not sep or line.startswith((" ", "-", "#")):
            continue
        meta[key.strip()] = parse_value(value.strip())
    return meta, lines, text[end + 5 :]


def parse_value(value: str) -> object:
    if value.startswith("[") and value.endswith("]"):
        return [parse_value(v.strip()) for v in value[1:-1].split(",") if v.strip()]
    if value.startswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value.strip('"')
    return value.strip("'")


def code_free(lines: list[str]) -> list[tuple[int, str]]:
    """Lines outside fenced code blocks, with their index."""
    out, fence = [], ""
    for i, line in enumerate(lines):
        m = re.match(r"^\s*(`{3,}|~{3,})", line)
        if m and (not fence or m.group(1).startswith(fence)):
            fence = "" if fence else m.group(1)
            continue
        if not fence:
            out.append((i, line))
    return out


@dataclass
class Item:
    id: str
    section: int
    text: str
    deprecated_by: str | None = None


@dataclass
class Spec:
    path: Path
    rel: str
    meta: dict
    body: str
    headings: list[tuple[int, str]] = field(default_factory=list)
    items: dict[str, Item] = field(default_factory=dict)
    dup_items: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.meta.get("x-fs-id", ""))

    def section_text(self, number: int) -> str:
        m = re.search(rf"^## {number}\. .*?$(.*?)(?=^## \d+\. |\Z)", self.body, re.M | re.S)
        return m.group(1).strip() if m else ""

    def active(self, section: int) -> list[Item]:
        return [i for i in self.items.values() if i.section == section and not i.deprecated_by]


def parse_spec(path: Path, root: Path) -> Spec:
    meta, _, body = split_frontmatter(path.read_text(encoding="utf-8"))
    spec = Spec(path, path.relative_to(root).as_posix(), meta, body)
    lines = body.splitlines()
    section, current = 0, None
    for _, line in code_free(lines):
        if h := HEADING.match(line):
            section, current = int(h.group(1)), None
            spec.headings.append((section, h.group(2).strip()))
            continue
        if line.startswith("#"):
            current = None
            continue
        if m := ITEM.match(line):
            current = Item(m.group(1), section, m.group(2))
            if current.id in spec.items:
                spec.dup_items.append(current.id)
            spec.items[current.id] = current
        elif current and (d := DEPRECATED.match(line)):
            current.deprecated_by = d.group(1)
        elif current and line.startswith((" ", "\t")) and line.strip():
            current.text += " " + line.strip()
        elif line.strip():
            current = None
    return spec


def load_specs(root: Path) -> tuple[dict[str, Spec], list[str]]:
    specs: dict[str, Spec] = {}
    problems: list[str] = []
    for path in sorted((root / FEATURES).glob("FS-*.md")):
        spec = parse_spec(path, root)
        if spec.id in specs:
            problems.append(f"{spec.rel}: duplicate id {spec.id}, also in {specs[spec.id].rel}")
            continue
        specs[spec.id or path.stem] = spec
    return specs, problems


def spec_of(ref: str) -> str:
    return ref.split(".")[0]


def number(spec_id: str) -> int:
    return int(spec_id.split("-")[1])


# ---------- git ----------


def git(root: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args], input=stdin, capture_output=True, text=True
    )


def remote_numbers(root: Path) -> set[int]:
    res = git(root, "ls-remote", "origin", f"{REF_NS}/*")
    if res.returncode:
        raise ToolError(
            "cannot list reserved IDs on origin; an ID is allocated only online.\n" + res.stderr
        )
    return {int(m) for m in re.findall(rf"{REF_NS}/FS-(\d+)$", res.stdout, re.M)}


def reserve(root: Path, count: int, title: str) -> list[str]:
    """Reserve IDs by creating refs on origin; creating a ref that exists is rejected."""
    local = {
        number(m.group(1))
        for p in (root / FEATURES).glob("FS-*.md")
        if (m := SPEC_FILE.match(p.name))
    }
    nxt = max(local | remote_numbers(root), default=0) + 1
    got: list[str] = []
    for _ in range(MAX_TRIES * count):
        if len(got) == count:
            break
        spec_id = f"FS-{nxt:03d}"
        note = f"reserve {spec_id} {title}\n\n{secrets.token_hex(8)} {os.getpid()} {time.time_ns()}"
        if push_new_ref(root, f"{REF_NS}/{spec_id}", note):
            got.append(spec_id)
        nxt += 1
    if len(got) < count:
        raise ToolError(f"gave up after {MAX_TRIES * count} tries; reserved {got}")
    return got


def push_new_ref(root: Path, ref: str, message: str) -> bool:
    """Create ref on origin; False if it already exists. Creation is atomic on the remote."""
    tree = git(root, "mktree", stdin="")
    if tree.returncode:
        raise ToolError(tree.stderr)
    # GitHub rejects refs to blobs. A parentless commit never fast-forwards over another
    # one, so a push to a ref that already exists is always rejected.
    commit = git(root, "commit-tree", tree.stdout.strip(), "-m", message)
    if commit.returncode:
        raise ToolError(commit.stderr)
    push = git(root, "push", "--quiet", "origin", f"{commit.stdout.strip()}:{ref}")
    if push.returncode == 0:
        return True
    if git(root, "ls-remote", "--exit-code", "origin", ref).returncode:
        raise ToolError(f"could not push {ref} to origin:\n{push.stderr}")
    return False


# ---------- writing ----------


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60].strip("-") or "feature"


def fence_for(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def prompt_log(spec_id: str, title: str, spec_name: str, prompt: str, created: str) -> str:
    fence = fence_for(prompt)
    head = {
        "type": "Reference",
        "title": f"{spec_id} prompt",
        "description": f"The prompt that started {spec_id} {title}, recorded verbatim.",
    }
    meta = "".join(f"{k}: {json.dumps(v)}\n" for k, v in head.items())
    return (
        f"---\n{meta}tags: [feature-spec, prompt]\nx-fs-id: {spec_id}\n"
        f'x-fs-created: "{created}"\n---\n\n# {spec_id} prompt\n\n'
        f"Spec: [{spec_id} {title}](../{spec_name})\n\n"
        f"{fence}text\n{prompt.rstrip()}\n{fence}\n"
    )


def ensure_union_merge(root: Path) -> None:
    attrs = root / ".gitattributes"
    text = attrs.read_text(encoding="utf-8") if attrs.exists() else ""
    if UNION_ATTR not in text.splitlines():
        write(attrs, text + ("" if not text or text.endswith("\n") else "\n") + UNION_ATTR + "\n")


def cmd_new(
    root: Path, titles: list[str], prompt_file: Path | None, parent: str = ""
) -> list[Path]:
    """A child made without a prompt file links to its root ancestor's prompt log."""
    if prompt_file is None and not parent:
        raise ToolError("--prompt-file is required unless --parent is given")
    prompt = prompt_file.read_text(encoding="utf-8") if prompt_file else ""
    if prompt_file and not prompt.strip():
        raise ToolError("the prompt is empty")
    specs = load_specs(root)[0]
    if parent and parent not in specs:
        raise ToolError(f"parent {parent} does not exist")
    created = dt.date.today().isoformat()
    template = TEMPLATE.read_text(encoding="utf-8")
    paths = []
    for spec_id, title in zip(reserve(root, len(titles), titles[0]), titles, strict=True):
        name = f"{spec_id}-{slugify(title)}.md"
        values = {
            "id": spec_id,
            "title": title,
            "title_json": json.dumps(title),
            "repo": root.name,
            "parent": parent,
            "created": created,
            "prompt_id": spec_id if prompt else root_spec(parent, specs),
        }
        text = template
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        write(root / FEATURES / name, text)
        if prompt:
            write(
                root / PROMPTS / f"{spec_id}.md", prompt_log(spec_id, title, name, prompt, created)
            )
        paths.append(root / FEATURES / name)
    ensure_union_merge(root)
    cmd_reindex(root)
    return paths


def index_line(name: str, label: str, description: str) -> str:
    return f"* [{label.replace('[', '(').replace(']', ')')}]({name}) - {description}"


def cmd_reindex(root: Path) -> None:
    specs, _ = load_specs(root)
    lines = [
        "# Feature specifications",
        "",
        "Prompt logs: [prompts/index.md](prompts/index.md)",
        "",
    ]
    for sid in sorted(specs, key=number):
        s = specs[sid]
        lines.append(
            index_line(
                s.path.name, f"{sid} {s.meta.get('title', '')}", str(s.meta.get("description", ""))
            )
        )
    write(root / FEATURES / "index.md", "\n".join(lines) + "\n")
    plines = ["# Feature specification prompts", ""]
    for path in sorted((root / PROMPTS).glob("FS-*.md"), key=lambda p: number(p.stem)):
        meta, _, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        plines.append(
            index_line(
                path.name, str(meta.get("title", path.stem)), str(meta.get("description", ""))
            )
        )
    write(root / PROMPTS / "index.md", "\n".join(plines) + "\n")
    docs_index = root / "docs/index.md"
    entry = index_line(
        "features/index.md",
        "Feature specifications",
        "Feature specifications for this repository, with citable item IDs.",
    )
    if not docs_index.exists():
        lines = []
        for doc in sorted((root / "docs").glob("*.md")):
            meta = split_frontmatter(doc.read_text(encoding="utf-8"))[0]
            if doc.name != "index.md" and meta.get("title") and meta.get("description"):
                lines.append(index_line(doc.name, str(meta["title"]), str(meta["description"])))
        body = "\n".join([*lines, entry])
        write(docs_index, f'---\nokf_version: "0.3"\n---\n\n# Documentation\n\n{body}\n')
    elif "features/index.md" not in (t := docs_index.read_text(encoding="utf-8")):
        write(docs_index, t.rstrip("\n") + f"\n{entry}\n")


# ---------- check ----------


def index_entries(index: Path) -> dict[str, str]:
    if not index.exists():
        return {}
    out = {}
    for line in index.read_text(encoding="utf-8").splitlines():
        if m := INDEX_LINE.match(line.strip()):
            out[m.group(1)] = m.group(2).strip()
    return out


def check_links(rel: str, path: Path, body: str) -> list[str]:
    problems = []
    for _, line in code_free(body.splitlines()):
        for target in LINK.findall(line):
            if re.match(r"^([a-z][a-z0-9+.-]*:|#)", target):
                continue
            if not (path.parent / target.split("#")[0]).exists():
                problems.append(f"{rel}: broken link {target}")
    return problems


def check_okf(
    rel: str, path: Path, meta: dict, body: str, want_type: str, index: dict[str, str]
) -> list[str]:
    p = []
    if meta.get("type") != want_type:
        p.append(f"{rel}: type must be {want_type}")
    for key in ("title", "description"):
        if not meta.get(key):
            p.append(f"{rel}: missing {key}")
    if path.name not in index:
        p.append(f"{rel}: not listed in its index.md; run spec_tool.py reindex")
    elif index[path.name] != meta.get("description"):
        p.append(f"{rel}: index description differs from frontmatter; run spec_tool.py reindex")
    return p + check_links(rel, path, body)


def check_spec(s: Spec, specs: dict[str, Spec], root: Path, index: dict[str, str]) -> list[str]:
    rel, sid, meta = s.rel, s.id, s.meta
    p = check_okf(rel, s.path, meta, s.body, "Capability", index)
    m = SPEC_FILE.match(s.path.name)
    if not m or m.group(1) != sid:
        p.append(f"{rel}: x-fs-id {sid!r} must match the file name FS-NNN-<slug>.md")
    status = meta.get("x-fs-status")
    if status not in STATUSES:
        p.append(f"{rel}: x-fs-status must be one of {sorted(STATUSES)}")
    want = [(i + 1, h) for i, h in enumerate(HEADINGS)]
    if s.headings != want:
        p.append(f"{rel}: headings must be exactly " + ", ".join(f"{n}. {h}" for n, h in want))
    p += [f"{rel}: item {i} appears more than once" for i in s.dup_items]
    for item in s.items.values():
        parts = item.id.split(".")
        if parts[0] != sid or parts[1] != str(item.section):
            p.append(f"{rel}: item {item.id} must start with {sid}.{item.section}.")
    for key in ("x-fs-parent",):
        if meta.get(key) and meta[key] not in specs:
            p.append(f"{rel}: {key} {meta[key]} does not exist")
    for dep in meta.get("x-fs-depends-on") or []:
        if "@" not in dep and dep not in specs:  # repo@version is an external prerequisite
            p.append(f"{rel}: depends on {dep}, which does not exist")
    sections = {f"{x.id}.{n}" for x in specs.values() for n, _ in x.headings}
    known = {i for x in specs.values() for i in x.items} | set(specs) | sections
    for ref in sorted(set(REF.findall(s.body))):
        if ref not in known:
            p.append(f"{rel}: reference {ref} does not exist")
    reqs = {i.id for i in s.active(REQ)}
    covered = set()
    for c in s.active(CRIT):
        # a parent's feature-level criteria may verify requirements its child specs hold
        cites = {
            r
            for r in REF.findall(c.text)
            if re.fullmatch(rf"FS-\d+\.{REQ}\.\d+", r) and r in known
            and (spec_of(r) == sid or is_under(spec_of(r), sid, specs))
        }  # fmt: skip
        if not cites:
            p.append(f"{rel}: criterion {c.id} cites no requirement")
        covered |= cites
    for r in sorted(reqs - covered):
        p.append(f"{rel}: requirement {r} has no acceptance criterion")
    for old in meta.get("x-fs-deprecates") or []:
        owner = specs.get(spec_of(old))
        item = owner.items.get(old) if owner else None
        if not item:
            p.append(f"{rel}: deprecates {old}, which does not exist")
        elif not item.deprecated_by or spec_of(item.deprecated_by) != sid:
            p.append(f"{rel}: deprecates {old}, but {old} has no 'Deprecated by {sid}...' marker")
    for item in s.items.values():
        if item.deprecated_by:
            by = specs.get(spec_of(item.deprecated_by))
            if not by or item.id not in (by.meta.get("x-fs-deprecates") or []):
                p.append(
                    f"{rel}: {item.id} is marked deprecated by {item.deprecated_by}, "
                    "which does not list it in x-fs-deprecates"
                )
    if status in FINAL:
        if "TODO" in s.body or "TODO" in str(meta.get("description")):
            p.append(f"{rel}: a spec that is {status} must have no TODO left")
        if s.section_text(OPEN) != "None.":
            p.append(f"{rel}: a spec that is {status} must have Open questions 'None.'")
    logs = {sid, root_spec(sid, specs)}
    if not any((root / PROMPTS / f"{x}.md").exists() for x in logs):
        p.append(f"{rel}: prompt log {PROMPTS.as_posix()}/{sid}.md is missing")
    return p


def root_spec(sid: str, specs: dict[str, Spec]) -> str:
    seen = set()
    while sid not in seen and (up := (specs[sid].meta.get("x-fs-parent") if sid in specs else "")):
        seen.add(sid)
        sid = up
    return sid


def is_under(child: str, ancestor: str, specs: dict[str, Spec]) -> bool:
    seen = set()
    while child in specs and child not in seen:
        seen.add(child)
        child = specs[child].meta.get("x-fs-parent") or ""
        if child == ancestor:
            return True
    return False


def check_base(root: Path, specs: dict[str, Spec], base: str) -> list[str]:
    res = git(root, "ls-tree", "--name-only", base, FEATURES.as_posix() + "/")
    if res.returncode:
        raise ToolError(f"cannot read {base}: {res.stderr}")
    current = {s.path.name: s for s in specs.values()}
    problems = []
    for rel in res.stdout.splitlines():
        name = Path(rel).name
        if not SPEC_FILE.match(name):
            continue
        if name not in current:
            problems.append(f"{rel}: spec deleted since {base}; deprecate it instead")
            continue
        old = split_frontmatter(git(root, "show", f"{base}:{rel}").stdout)[2]
        for gone in sorted(parse_spec_text(old) - set(current[name].items)):
            problems.append(f"{rel}: item {gone} deleted since {base}; deprecate it instead")
    return problems


def parse_spec_text(body: str) -> set[str]:
    return {m.group(1) for _, line in code_free(body.splitlines()) if (m := ITEM.match(line))}


def check_all(root: Path, base: str | None = None) -> list[str]:
    specs, problems = load_specs(root)
    index = index_entries(root / FEATURES / "index.md")
    for s in specs.values():
        problems += check_spec(s, specs, root, index)
    pindex = index_entries(root / PROMPTS / "index.md")
    for path in sorted((root / PROMPTS).glob("FS-*.md")):
        rel = path.relative_to(root).as_posix()
        meta, _, body = split_frontmatter(path.read_text(encoding="utf-8"))
        problems += check_okf(rel, path, meta, body, "Reference", pindex)
        if path.stem not in specs:
            problems.append(f"{rel}: no spec {path.stem} for this prompt log")
    if base:
        problems += check_base(root, specs, base)
    return problems


def root_of(path: Path) -> Path | None:
    for parent in path.resolve().parents:
        if parent.name == "features" and parent.parent.name == "docs":
            return parent.parent.parent
    return None


def cmd_check(root: Path, paths: list[str], base: str | None) -> list[str]:
    if not paths:
        return check_all(root, base)
    problems = []
    for raw in paths:
        froot = root_of(Path(raw))
        if froot is None:
            continue  # not a spec; the edit hook stays quiet
        rel = Path(raw).resolve().relative_to(froot.resolve()).as_posix()
        problems += [p for p in check_all(froot, base) if p.startswith(rel + ":")]
    return problems


# ---------- deprecate, index, design, plan ----------


def cmd_deprecate(root: Path, new: str, olds: list[str]) -> None:
    specs, _ = load_specs(root)
    owner = specs.get(spec_of(new))
    if not owner or new not in owner.items:
        raise ToolError(f"{new} does not exist")
    today = dt.date.today().isoformat()
    for old in olds:
        target = specs.get(spec_of(old))
        if not target or old not in target.items:
            raise ToolError(f"{old} does not exist")
        if old == new:
            raise ToolError(f"{old} cannot deprecate itself")
        if target.items[old].deprecated_by:
            raise ToolError(f"{old} is already deprecated by {target.items[old].deprecated_by}")
        lines = target.path.read_text(encoding="utf-8").splitlines()
        at = next(i for i, ln in enumerate(lines) if (m := ITEM.match(ln)) and m.group(1) == old)
        at += 1
        while at < len(lines) and lines[at].startswith((" ", "\t")) and lines[at].strip():
            at += 1
        lines.insert(at, f"  > Deprecated by [{new}]({owner.path.name}) on {today}.")
        write(target.path, "\n".join(lines) + "\n")
    text = owner.path.read_text(encoding="utf-8")  # re-read: the owner may be a target
    listed = list(owner.meta.get("x-fs-deprecates") or [])
    listed += [o for o in olds if o not in listed]
    text = re.sub(
        r"^x-fs-deprecates:.*$",
        f"x-fs-deprecates: [{', '.join(listed)}]",
        text,
        count=1,
        flags=re.M,
    )
    write(owner.path, text)


def cmd_index(root: Path) -> str:
    specs, _ = load_specs(root)
    out = []
    for sid in sorted(specs, key=number):
        s = specs[sid]
        out.append(f"{sid} [{s.meta.get('x-fs-status')}] {s.meta.get('title')} ({s.rel})")
        out += [f"  {i.id} {i.text[:160]}" for i in s.items.values() if not i.deprecated_by]
    return "\n".join(out)


def siblings(root: Path, suffix: str) -> list[Path]:
    """Sibling folders ending in suffix: names AGENTS.md gives first, then <prefix><suffix>."""
    agents = root / "AGENTS.md"
    names = (
        re.findall(r"`([\w.-]+)`", agents.read_text(encoding="utf-8")) if agents.exists() else []
    )
    parts = root.name.split("-")
    names += ["-".join(parts[:k]) + suffix for k in range(len(parts) - 1, 0, -1)]
    out: list[Path] = []
    for name in names:
        cand = root.parent / name
        # a repository name has a dash; this also keeps `.` and `..` out
        if "-" in name and name.endswith(suffix) and cand.is_dir() and cand != root:
            out += [cand] if cand not in out else []
    return out


def find_design(root: Path) -> Path | None:
    return next(iter(siblings(root, "-design")), None)


def find_context(root: Path, design: Path | None) -> list[Path]:
    """Repositories AGENTS.md names, and <prefix>-contracts, other than the design one."""
    both = siblings(root, "") + siblings(root, "-contracts")
    return [c for c in dict.fromkeys(both) if c != design]


def cmd_design(root: Path) -> str:
    design = find_design(root)
    if not design:
        return "design: none"
    rows, prose = [], []
    for path in sorted(design.rglob("*.md")):
        if ".git" in path.parts:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if root.name in line:
                hit = f"  {path.relative_to(design).as_posix()}:{n}: {line.strip()[:200]}"
                # table rows and headings state roles; prose often only mentions the name
                (rows if line.lstrip().startswith(("|", "#")) else prose).append(hit)
    role = "\n".join((rows or prose)[:20]) or f"  no mention of {root.name}"
    context = "".join(f"\ncontext: {c}" for c in find_context(root, design))
    return f"design: {design}{context}\nrepo: {root.name}\nrole:\n{role}"


def leaves_of(sid: str, specs: dict[str, Spec]) -> list[str]:
    kids = [k for k, s in specs.items() if s.meta.get("x-fs-parent") == sid]
    return [leaf for k in sorted(kids, key=number) for leaf in leaves_of(k, specs)] or [sid]


def waves(leaves: list[str], specs: dict[str, Spec]) -> list[list[str]]:
    deps = {}
    for leaf in leaves:
        expanded = set()
        for d in specs[leaf].meta.get("x-fs-depends-on") or []:
            expanded |= set(leaves_of(d, specs)) & set(leaves)
        deps[leaf] = expanded
    out, done = [], set()
    while len(done) < len(leaves):
        ready = sorted((x for x in leaves if x not in done and deps[x] <= done), key=number)
        if not ready:
            raise ToolError(
                "x-fs-depends-on has a cycle among " + ", ".join(sorted(set(leaves) - done))
            )
        out.append(ready)
        done |= set(ready)
    return out


def plan_prompt(sid: str, specs: dict[str, Spec]) -> str:
    s = specs[sid]
    lines = [
        f'Plan the implementation of feature specification {sid} "{s.meta.get("title")}" '
        f"in {s.rel}. Read that file first; it is the source of truth."
    ]
    parent = s.meta.get("x-fs-parent")
    if parent:
        lines.append(f"Parent spec: {parent} in {specs[parent].rel}. Read its sections 1 and 2.")
    refs = sorted(set(REPO_REF.findall(s.section_text(1))))
    if refs:
        lines.append("References: " + ", ".join(f"{r}:{p}" for r, p in refs))
        here = s.path.parents[2]
        for repo in sorted({r for r, _ in refs}):
            lines.append(
                f"{repo} is a sibling checkout at ../{repo}."
                if (here.parent / repo).is_dir()
                else f"{repo} was not found next to this repository; ask where it is."
            )
    lines.append("Requirements to implement: " + ", ".join(i.id for i in s.active(REQ)))
    lines.append("Acceptance criteria to satisfy: " + ", ".join(i.id for i in s.active(CRIT)))
    olds = s.meta.get("x-fs-deprecates") or []
    if olds:
        lines.append(
            "Deprecated items whose behaviour changes or goes away: "
            + ", ".join(f"{o} ({specs[spec_of(o)].rel})" for o in olds)
        )
    deps = [d for d in s.meta.get("x-fs-depends-on") or [] if "@" not in d]
    if deps:
        lines.append(
            "Depends on: " + ", ".join(f"{d} ({specs[d].meta.get('x-fs-status')})" for d in deps)
        )
    ext = external(sid, specs)
    if ext:
        lines.append("External prerequisites, which must be released first: " + ", ".join(ext))
    tool = f'python "{Path(__file__).resolve().as_posix()}"'
    lines.append(
        "Make the plan test-first with a red-then-green checkpoint: each step writes its test, "
        "runs it and records that it fails, and only then writes the code. Every step names the "
        "requirement or acceptance criterion IDs it serves, and every acceptance criterion maps "
        "to a test. Plan nothing the spec puts out of scope. Where the spec is ambiguous, ask "
        "instead of guessing."
    )
    lines.append(
        f"Other agents may be building related specs. Before writing code, run `{tool} claims` "
        f"to see their work, then `{tool} claim {sid} --files <every file the plan edits>`. "
        "If another claim names one of those files, stop and agree a merge order with the user. "
        f"Run `{tool} release {sid}` once the pull request merges."
    )
    return "\n".join(lines)


def external(sid: str, specs: dict[str, Spec]) -> list[str]:
    return [d for d in specs[sid].meta.get("x-fs-depends-on") or [] if "@" in d]


def design_files(s: Spec) -> set[str]:
    # a path has a slash; `v0.1.0` and `Event.type` are not files
    return {m.removeprefix("./") for m in CODE_PATH.findall(s.section_text(4)) if "/" in m}


def off_main(root: Path) -> bool:
    f = FEATURES.as_posix()
    if git(root, "diff", "--quiet", "origin/main", "--", f).returncode:
        return True
    return bool(git(root, "ls-files", "--others", "--exclude-standard", "--", f).stdout.strip())


def cmd_plan(root: Path, sid: str) -> str:
    specs, _ = load_specs(root)
    if sid not in specs:
        raise ToolError(f"{sid} does not exist")
    problems = check_all(root)
    if problems:
        raise ToolError("fix these before planning:\n" + "\n".join(problems))
    leaves = leaves_of(sid, specs)
    not_ready = [x for x in {sid, *leaves} if specs[x].meta.get("x-fs-status") != "approved"]
    if not_ready:
        raise ToolError(
            "only approved specs are planned; not approved: " + ", ".join(sorted(not_ready))
        )
    out = [f"# Planning prompts for {sid}", ""]
    if off_main(root):
        out += [
            "WARNING: the spec files differ from origin/main, or there is no origin/main. "
            "Merge the spec pull request before starting sessions from main.",
            "",
        ]
    out += [
        "Specs in the same wave can be planned and built in parallel, each in its own session "
        "or worktree, unless the wave lists shared files. Start a wave only after the waves "
        "before it are planned.",
        "Open plan mode (Claude Code: /plan or Shift+Tab; Cursor: Plan mode), then send:",
    ]
    ext = sorted({d for x in {sid, *leaves} for d in external(x, specs)})
    for n, wave in enumerate(waves(leaves, specs), 1):
        out += ["", f"## Wave {n}"]
        if n == 1 and ext:
            out += ["", "External prerequisites, released before this wave: " + ", ".join(ext)]
        owners: dict[str, list[str]] = {}
        for leaf in wave:
            for f in design_files(specs[leaf]):
                owners.setdefault(f, []).append(leaf)
        for f, who in sorted(owners.items()):
            if len(who) > 1:
                out += [
                    "",
                    f"Shared files in wave {n}: `{f}` ({', '.join(who)}). Build these one "
                    "after another, or agree a merge order.",
                ]
        for leaf in wave:
            out += [
                "",
                f"### {leaf} {specs[leaf].meta.get('title')}",
                "",
                "```text",
                plan_prompt(leaf, specs),
                "```",
            ]
    criteria = [i.id for i in specs[sid].active(CRIT)]
    if leaves != [sid] and criteria:
        out += [
            "",
            "## Integration, after every wave",
            "",
            "```text",
            f"Plan the integration work for feature specification {sid} "
            f'"{specs[sid].meta.get("title")}" in {specs[sid].rel}. Its child specs '
            f"({', '.join(leaves)}) are planned separately. Plan only the tests and glue that "
            f"satisfy these feature-level acceptance criteria: {', '.join(criteria)}. "
            "Every step names the criterion it serves. Where the spec is ambiguous, ask "
            "instead of guessing.",
            "```",
        ]
    return "\n".join(out)


def cmd_ship(root: Path, sid: str) -> list[str]:
    """Mark a spec and its descendants implemented and log it in each changelog."""
    specs, _ = load_specs(root)
    if sid not in specs:
        raise ToolError(f"{sid} does not exist")
    family = sorted({sid, *(k for k in specs if is_under(k, sid, specs))}, key=number)
    not_ready = [x for x in family if specs[x].meta.get("x-fs-status") != "approved"]
    if not_ready:
        raise ToolError("only approved specs ship; not approved: " + ", ".join(not_ready))
    today = dt.date.today().isoformat()
    for x in family:
        text = specs[x].path.read_text(encoding="utf-8")
        text = re.sub(
            r"^x-fs-status: approved$", "x-fs-status: implemented", text, count=1, flags=re.M
        )
        write(specs[x].path, text.rstrip("\n") + f"\n- {today}: implemented.\n")
    return family


def claim_ref(sid: str) -> str:
    return f"{CLAIMS}/{sid}"


def cmd_claims(root: Path) -> list[str]:
    res = git(root, "fetch", "--quiet", "--prune", "origin", f"+{CLAIMS}/*:{CLAIMS}/*")
    if res.returncode:
        raise ToolError("cannot read claims on origin:\n" + res.stderr)
    refs = git(root, "for-each-ref", "--format=%(refname)", CLAIMS).stdout.split()
    out: list[str] = []
    owners: dict[str, list[str]] = {}
    for ref in refs:
        try:
            c = json.loads(git(root, "log", "-1", "--format=%B", ref).stdout)
            line = f"{c['spec']} on {c['branch']} since {c['date']}: {', '.join(c['files'])}"
        except (json.JSONDecodeError, KeyError, TypeError):
            out.append(f"{ref.rsplit('/', 1)[1]}: unreadable claim")
            continue
        out.append(line)
        for f in c["files"]:
            owners.setdefault(f, []).append(c["spec"])
    out += [f"OVERLAP {f}: {', '.join(w)}" for f, w in sorted(owners.items()) if len(w) > 1]
    return out or ["no claims"]


def cmd_claim(root: Path, sid: str, files: list[str]) -> None:
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "unknown"
    # no hostname or user: the ref is visible to everyone who can read origin
    msg = json.dumps(
        {"spec": sid, "branch": branch, "files": files, "date": dt.date.today().isoformat()}
    )
    if not push_new_ref(root, claim_ref(sid), msg):
        current = [c for c in cmd_claims(root) if c.startswith(sid + " ")]
        raise ToolError(f"{sid} is already claimed: " + "; ".join(current))


def cmd_release(root: Path, sids: list[str]) -> None:
    res = git(root, "push", "--quiet", "origin", *(f":{claim_ref(s)}" for s in sids))
    if res.returncode:
        raise ToolError("cannot release on origin:\n" + res.stderr)
    for s in sids:
        git(root, "update-ref", "-d", claim_ref(s))


# ---------- CLI ----------


def default_root() -> Path:
    res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(res.stdout.strip()) if res.returncode == 0 else Path.cwd()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path)
    sub = ap.add_subparsers(dest="cmd", required=True)
    new = sub.add_parser("new")
    new.add_argument("--title", action="append", required=True)
    new.add_argument("--prompt-file", type=Path)
    new.add_argument("--parent", default="")
    for name in ("design", "reindex", "index"):
        sub.add_parser(name)
    chk = sub.add_parser("check")
    chk.add_argument("paths", nargs="*")
    chk.add_argument("--base")
    dep = sub.add_parser("deprecate")
    dep.add_argument("new")
    dep.add_argument("old", nargs="+")
    for name in ("plan", "ship"):
        sub.add_parser(name).add_argument("id")
    cl = sub.add_parser("claim")
    cl.add_argument("id")
    cl.add_argument("--files", nargs="+", required=True)
    sub.add_parser("claims")
    sub.add_parser("release").add_argument("id", nargs="+")
    args = ap.parse_args(argv)
    root = (args.root or default_root()).resolve()
    try:
        if args.cmd == "new":
            for path in cmd_new(root, args.title, args.prompt_file, args.parent):
                print(path.relative_to(root).as_posix())
        elif args.cmd == "design":
            print(cmd_design(root))
        elif args.cmd == "reindex":
            cmd_reindex(root)
        elif args.cmd == "index":
            print(cmd_index(root))
        elif args.cmd == "check":
            problems = cmd_check(root, args.paths, args.base)
            for line in problems:
                print(line)
            return 1 if problems else 0
        elif args.cmd == "deprecate":
            cmd_deprecate(root, args.new, args.old)
        elif args.cmd == "plan":
            print(cmd_plan(root, args.id))
        elif args.cmd == "ship":
            print("implemented: " + ", ".join(cmd_ship(root, args.id)))
        elif args.cmd == "claim":
            cmd_claim(root, args.id, args.files)
        elif args.cmd == "claims":
            print("\n".join(cmd_claims(root)))
        elif args.cmd == "release":
            cmd_release(root, args.id)
    except ToolError as exc:
        print(f"spec_tool: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Check an OKF v0.3 bundle: concept frontmatter, index descriptions, and relative links.

usage: python check_okf.py [bundle-root]    prints one problem per line, exits 1 if any
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TYPES = {"Overview", "Lifecycle Stage", "Capability", "Decision", "Reference", "Flow"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
INDEX_LINE = re.compile(r"^\*\s+\[[^\]]*\]\(([^)]+)\)\s+-\s+(.+)$")
SKIP = {".git", "node_modules", ".venv"}


def frontmatter(text: str) -> dict[str, str]:
    """Top-level scalar keys only; enough for type, title, and description."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    meta = {}
    for line in text[4:end].splitlines() if end > 0 else []:
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "-")):
            meta[key.strip()] = scalar(value.strip())
    return meta


def scalar(value: str) -> str:
    """A double-quoted YAML scalar with JSON escapes (\\u00e9, \\") reads like JSON."""
    if value.startswith('"'):
        try:
            return str(json.loads(value))
        except json.JSONDecodeError:
            pass
    return value.strip('"').strip("'")


def index_entries(index: Path) -> dict[str, str]:
    entries = {}
    for line in index.read_text(encoding="utf-8").splitlines():
        m = INDEX_LINE.match(line.strip())
        if m:
            entries[m.group(1).split("#")[0]] = m.group(2).strip()
    return entries


def check(root: Path) -> list[str]:
    problems = []
    for path in sorted(root.rglob("*.md")):
        if SKIP & set(path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        meta = frontmatter(text)
        if "type" in meta and path.name not in {"index.md", "log.md"}:
            if meta["type"] not in TYPES:
                problems.append(f"{rel}: unknown type {meta['type']!r}")
            for key in ("title", "description"):
                if not meta.get(key):
                    problems.append(f"{rel}: missing {key}")
            index = path.parent / "index.md"
            if path.parent != root and index.exists():
                listed = index_entries(index)
                if path.name not in listed:
                    problems.append(f"{rel}: not listed in its index.md")
                elif meta.get("description") and listed[path.name] != meta["description"]:
                    problems.append(f"{rel}: index description differs from frontmatter")
        fence = ""
        for line in text.splitlines():
            m = re.match(r"^\s*(`{3,}|~{3,})", line)
            if m and (not fence or m.group(1).startswith(fence)):
                fence = "" if fence else m.group(1)
                continue
            if fence:
                continue
            for target in LINK.findall(line):
                if re.match(r"^([a-z][a-z0-9+.-]*:|#)", target):
                    continue
                if not (path.parent / target.split("#")[0]).exists():
                    problems.append(f"{rel}: broken link {target}")
    return problems


def main(argv: list[str]) -> int:
    problems = check(Path(argv[0] if argv else "."))
    for line in problems:
        print(line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

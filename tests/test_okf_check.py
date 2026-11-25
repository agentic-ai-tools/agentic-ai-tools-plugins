from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep src/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src/okf-design/skills/okf-check"))
import check_okf  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def concept(type_: str = "Flow", description: str = "Does a thing.") -> str:
    return f'---\ntype: "{type_}"\ntitle: "T"\ndescription: "{description}"\n---\n\n# T\n'


def test_clean_bundle_passes(tmp_path: Path) -> None:
    write(tmp_path / "index.md", '---\nokf_version: "0.3"\n---\n\n* [A](g/a.md) - Does a thing.\n')
    write(tmp_path / "g/index.md", "# G\n\n* [A](a.md) - Does a thing.\n")
    write(tmp_path / "g/a.md", concept() + "\nSee [the index](../index.md#top).\n")
    assert check_okf.check(tmp_path) == []


def test_reports_each_problem(tmp_path: Path) -> None:
    write(tmp_path / "g/index.md", "# G\n\n* [A](a.md) - Old words.\n")
    write(tmp_path / "g/a.md", concept() + "\n[gone](missing.md) [web](https://x.org)\n")
    write(tmp_path / "g/b.md", concept(type_="Essay"))
    write(tmp_path / "g/c.md", "```\n[not a link](nowhere.md)\n```\n")
    assert sorted(check_okf.check(tmp_path)) == [
        "g/a.md: broken link missing.md",
        "g/a.md: index description differs from frontmatter",
        "g/b.md: not listed in its index.md",
        "g/b.md: unknown type 'Essay'",
    ]

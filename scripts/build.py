"""Build src/<plugin>/ into plugins/<plugin>/ and both marketplace files.

python scripts/build.py          write the generated files
python scripts/build.py --check  exit 1 if the committed files differ from a fresh build
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = "agentic-ai-tools"
OWNER = {"name": "Agentic AI Tools"}
DESCRIPTION = (
    "Coding-agent rules, skills, and hooks for Agentic AI Tools repositories, one plugin per stack."
)
GENERATED = [Path("plugins"), Path(".claude-plugin"), Path(".cursor-plugin")]

# neutral event -> (Claude Code event, Claude matcher, Cursor event)
EVENTS = {
    "after-edit": ("PostToolUse", "Write|Edit", "afterFileEdit"),
    "session-start": ("SessionStart", None, "sessionStart"),
    "before-shell": ("PreToolUse", "Bash", "beforeShellExecution"),
    "stop": ("Stop", None, "stop"),
}
SOURCE_ENTRIES = {"plugin.yaml", "rules", "skills", "agents", "scripts", "hooks.yaml", "mcp.yaml"}
CLAUDE_ROOT = '"${CLAUDE_PLUGIN_ROOT}"'
# Cursor runs plugin hooks from the plugin directory; its docs show only relative paths.
CURSOR_ROOT = "."
ALWAYS_ON = "context/always-on.md"
RULE_SKILLS = "rule-skills"
# src/_shared/scripts/<name> goes into each plugin whose hooks.yaml runs {root}/scripts/<name>.
SHARED = "_shared"


class BuildError(Exception):
    pass


def split_frontmatter(text: str, where: Path) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise BuildError(f"{where}: missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise BuildError(f"{where}: unterminated frontmatter")
    meta = yaml.safe_load(text[4:end]) or {}
    if not isinstance(meta, dict):
        raise BuildError(f"{where}: frontmatter is not a mapping")
    return meta, text[end + 5 :].lstrip("\n")


def render_frontmatter(meta: dict, body: str) -> str:
    head = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000)
    return f"---\n{head}---\n\n{body}"


def dump_json(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def read_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise BuildError(f"{path}: expected a mapping")
    return data


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def build_rules(src: Path, out: dict[str, str]) -> tuple[list[str], list[tuple[str, dict, str]]]:
    """Return (always-on rule bodies, glob rules) and write the Cursor .mdc files."""
    always: list[str] = []
    scoped: list[tuple[str, dict, str]] = []
    for path in sorted((src / "rules").glob("*.md")):
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"), path)
        unknown = set(meta) - {"description", "globs", "alwaysApply"}
        if unknown:
            raise BuildError(f"{path}: unknown frontmatter keys {sorted(unknown)}")
        if not meta.get("description"):
            raise BuildError(f"{path}: description is required")
        globs = as_list(meta.get("globs"))
        if bool(meta.get("alwaysApply")) == bool(globs):
            raise BuildError(f"{path}: set exactly one of alwaysApply: true or globs")
        cursor_meta = {"description": meta["description"]}
        if globs:
            cursor_meta["globs"] = ",".join(globs)
        cursor_meta["alwaysApply"] = not globs
        out[f"rules/{path.stem}.mdc"] = render_frontmatter(cursor_meta, body)
        if globs:
            scoped.append((path.stem, meta, body))
        else:
            always.append(body.rstrip() + "\n")
    return always, scoped


def build_hooks(src: Path, always: list[str], out: dict[str, str]) -> None:
    spec = read_yaml(src / "hooks.yaml") if (src / "hooks.yaml").exists() else {}
    claude: dict[str, list] = {}
    cursor: dict[str, list] = {}
    if always:
        out[ALWAYS_ON] = "\n".join(always)
        claude["SessionStart"] = [
            {"hooks": [{"type": "command", "command": f"cat {CLAUDE_ROOT}/{ALWAYS_ON}"}]}
        ]
    for event, entries in spec.items():
        if event not in EVENTS:
            raise BuildError(f"{src / 'hooks.yaml'}: no mapping for event {event!r}")
        claude_event, matcher, cursor_event = EVENTS[event]
        for entry in entries:
            if set(entry) != {"command"}:
                raise BuildError(f"{src / 'hooks.yaml'}: {event} entries take only 'command'")
            cmd = entry["command"]
            group = {"hooks": [{"type": "command", "command": cmd.replace("{root}", CLAUDE_ROOT)}]}
            if matcher:
                group = {"matcher": matcher, **group}
            claude.setdefault(claude_event, []).append(group)
            cursor.setdefault(cursor_event, []).append(
                {"command": cmd.replace("{root}", CURSOR_ROOT)}
            )
    if claude:
        out["hooks/hooks.json"] = dump_json({"hooks": claude})
    if cursor:
        out["hooks/cursor.json"] = dump_json({"hooks": cursor})


def copy_tree(src: Path, prefix: str, out: dict[str, str]) -> None:
    if src.is_dir():
        # shortcut: text files only; read bytes if a plugin ever ships a binary asset.
        for path in sorted(
            p for p in src.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        ):
            out[f"{prefix}/{path.relative_to(src).as_posix()}"] = path.read_text(encoding="utf-8")


def add_shared_scripts(src: Path, out: dict[str, str]) -> None:
    hooks = src / "hooks.yaml"
    commands = hooks.read_text(encoding="utf-8") if hooks.exists() else ""
    for path in sorted((src.parent / SHARED / "scripts").glob("*")):
        rel = f"scripts/{path.name}"
        if path.is_file() and f"{{root}}/{rel}" in commands:
            if rel in out:
                raise BuildError(f"{src / rel} duplicates src/{SHARED}/{rel}; delete one")
            out[rel] = path.read_text(encoding="utf-8")


def build_plugin(src: Path) -> tuple[dict, dict[str, str]]:
    unknown = {p.name for p in src.iterdir()} - SOURCE_ENTRIES
    if unknown:
        raise BuildError(f"{src}: no mapping for {sorted(unknown)}")
    meta = read_yaml(src / "plugin.yaml")
    for key in ("name", "version", "description"):
        if not meta.get(key):
            raise BuildError(f"{src / 'plugin.yaml'}: {key} is required")
    if meta["name"] != src.name:
        raise BuildError(f"{src / 'plugin.yaml'}: name must match its folder {src.name!r}")
    if set(meta) - {"name", "version", "description"}:
        raise BuildError(f"{src / 'plugin.yaml'}: only name, version, description are allowed")

    out: dict[str, str] = {}
    skill_names: set[str] = set()
    for skill in sorted(p for p in (src / "skills").glob("*") if p.is_dir()):
        skill_md = skill / "SKILL.md"
        smeta, _ = split_frontmatter(skill_md.read_text(encoding="utf-8"), skill_md)
        if smeta.get("name") != skill.name or not smeta.get("description"):
            raise BuildError(f"{skill_md}: needs name equal to its folder and a description")
        skill_names.add(skill.name)
    copy_tree(src / "skills", "skills", out)
    for agent in sorted((src / "agents").glob("*.md")):
        ameta, _ = split_frontmatter(agent.read_text(encoding="utf-8"), agent)
        if not ameta.get("name") or not ameta.get("description"):
            raise BuildError(f"{agent}: needs name and description")
    copy_tree(src / "agents", "agents", out)
    copy_tree(src / "scripts", "scripts", out)
    add_shared_scripts(src, out)

    always, scoped = build_rules(src, out)
    for name, rmeta, body in scoped:
        if name in skill_names:
            raise BuildError(f"{src}: rule {name!r} collides with a skill of the same name")
        globs = ", ".join(as_list(rmeta["globs"]))
        description = f"{rmeta['description'].rstrip('.')}. Use when reading or editing {globs}."
        # Claude Code has no rules, so a scoped rule becomes a skill only its manifest names.
        out[f"{RULE_SKILLS}/{name}/SKILL.md"] = render_frontmatter(
            {"name": name, "description": description}, body
        )
    build_hooks(src, always, out)

    if (src / "mcp.yaml").exists():
        servers = read_yaml(src / "mcp.yaml")
        out[".mcp.json"] = dump_json({"mcpServers": servers})
        out["mcp.json"] = dump_json({"mcpServers": servers})

    base = {**{k: meta[k] for k in ("name", "version", "description")}, "author": OWNER}
    claude = dict(base)
    if scoped:
        claude["skills"] = f"./{RULE_SKILLS}/"
    out[".claude-plugin/plugin.json"] = dump_json(claude)
    cursor = dict(base)
    # A Cursor manifest path replaces folder discovery, so Cursor skips Claude-only files.
    if any(k.startswith("rules/") for k in out):
        cursor["rules"] = "./rules/"
    if "hooks/cursor.json" in out:
        cursor["hooks"] = "./hooks/cursor.json"
    out[".cursor-plugin/plugin.json"] = dump_json(cursor)
    return base, out


def build(root: Path = ROOT) -> dict[str, str]:
    """Return every generated file as {repo-relative posix path: text}."""
    files: dict[str, str] = {}
    entries = []
    for src in sorted(p for p in (root / "src").iterdir() if p.is_dir() and p.name != SHARED):
        meta, out = build_plugin(src)
        for rel, text in out.items():
            files[f"plugins/{src.name}/{rel}"] = text
        entries.append(
            {k: meta[k] for k in ("name", "version", "description")}
            | {"source": f"./plugins/{src.name}"}
        )
    if not entries:
        raise BuildError("src/ holds no plugins")
    marketplace = {
        "name": MARKETPLACE,
        "owner": OWNER,
        "metadata": {"description": DESCRIPTION},
        "plugins": entries,
    }
    files[".claude-plugin/marketplace.json"] = dump_json(marketplace)
    files[".cursor-plugin/marketplace.json"] = dump_json(marketplace)
    return files


def on_disk(root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for top in GENERATED:
        if (root / top).is_dir():
            for path in (root / top).rglob("*"):
                if path.is_file():
                    found[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return found


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args(argv)
    try:
        files = build(root)
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    if args.check:
        current = on_disk(root)
        stale = sorted(k for k in files.keys() | current.keys() if files.get(k) != current.get(k))
        if stale:
            print("generated files are out of date; run python scripts/build.py", file=sys.stderr)
            for path in stale:
                print(f"  {path}", file=sys.stderr)
            return 1
        print("generated files are up to date")
        return 0
    for top in GENERATED:
        shutil.rmtree(root / top, ignore_errors=True)
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    src = tmp_path / "src" / "demo"
    write(src / "plugin.yaml", "name: demo\nversion: 1.0.0\ndescription: Demo plugin.\n")
    write(src / "rules/always.md", "---\ndescription: Always on\nalwaysApply: true\n---\n\n# A\n")
    write(src / "rules/py.md", "---\ndescription: Python rule\nglobs: ['**/*.py']\n---\n\n# P\n")
    write(src / "skills/do-it/SKILL.md", "---\nname: do-it\ndescription: Does it.\n---\n\nBody\n")
    write(src / "hooks.yaml", "after-edit:\n  - command: python {root}/scripts/x.py\n")
    write(src / "scripts/x.py", "print('x')\n")
    return tmp_path


def test_committed_output_is_up_to_date() -> None:
    assert build.main(["--check"], root=ROOT) == 0


def test_rules_map_to_each_agent(repo: Path) -> None:
    files = build.build(repo)
    base = "plugins/demo/"
    always = yaml.safe_load(files[base + "rules/always.mdc"].split("---")[1])
    assert always == {"description": "Always on", "alwaysApply": True}
    scoped = yaml.safe_load(files[base + "rules/py.mdc"].split("---")[1])
    assert scoped == {"description": "Python rule", "globs": "**/*.py", "alwaysApply": False}
    # Claude Code: always-on rules arrive by SessionStart, scoped rules as Claude-only skills.
    assert files[base + "context/always-on.md"] == "# A\n"
    assert "Use when reading or editing **/*.py" in files[base + "rule-skills/py/SKILL.md"]
    claude_hooks = json.loads(files[base + "hooks/hooks.json"])["hooks"]
    assert "context/always-on.md" in claude_hooks["SessionStart"][0]["hooks"][0]["command"]


def test_hooks_map_to_each_agent(repo: Path) -> None:
    files = build.build(repo)
    claude = json.loads(files["plugins/demo/hooks/hooks.json"])["hooks"]["PostToolUse"][0]
    assert claude["matcher"] == "Write|Edit"
    assert claude["hooks"][0]["command"] == 'python "${CLAUDE_PLUGIN_ROOT}"/scripts/x.py'
    cursor = json.loads(files["plugins/demo/hooks/cursor.json"])
    assert cursor == {"hooks": {"afterFileEdit": [{"command": "python ./scripts/x.py"}]}}


def test_manifests_keep_agent_specific_files_apart(repo: Path) -> None:
    files = build.build(repo)
    claude = json.loads(files["plugins/demo/.claude-plugin/plugin.json"])
    cursor = json.loads(files["plugins/demo/.cursor-plugin/plugin.json"])
    assert claude["skills"] == "./rule-skills/"
    assert cursor["rules"] == "./rules/" and cursor["hooks"] == "./hooks/cursor.json"
    assert "skills" not in cursor  # default skills/ holds only the real skills
    for name in (".claude-plugin", ".cursor-plugin"):
        market = json.loads(files[f"{name}/marketplace.json"])
        assert market["name"] == "agentic-ai-tools"
        assert market["plugins"][0]["source"] == "./plugins/demo"


@pytest.mark.parametrize(
    ("rel", "text", "message"),
    [
        ("hooks.yaml", "pre-commit:\n  - command: x\n", "no mapping for event"),
        ("commands/x.md", "x", "no mapping for"),
        ("rules/both.md", "---\ndescription: d\nalwaysApply: true\nglobs: '*'\n---\n", "exactly"),
        ("rules/none.md", "---\ndescription: d\n---\n", "exactly"),
        ("rules/do-it.md", "---\ndescription: d\nglobs: '*'\n---\n", "collides"),
    ],
)
def test_unmapped_source_fails_the_build(repo: Path, rel: str, text: str, message: str) -> None:
    write(repo / "src/demo" / rel, text)
    with pytest.raises(build.BuildError, match=message):
        build.build(repo)


def test_check_reports_stale_output(repo: Path) -> None:
    assert build.main([], root=repo) == 0
    assert build.main(["--check"], root=repo) == 0
    write(repo / "plugins/demo/rules/py.mdc", "edited by hand\n")
    assert build.main(["--check"], root=repo) == 1


def run_on_edit(payload: dict, *args: str) -> subprocess.CompletedProcess[str]:
    script = ROOT / "src/_shared/scripts/on_edit.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def test_on_edit_reads_both_payload_shapes(tmp_path: Path) -> None:
    target = tmp_path / "a.py"
    target.write_text("x = 1\n")
    fail = ("--", sys.executable, "-c", "import sys; print('bad'); sys.exit(1)")
    claude = run_on_edit({"tool_input": {"file_path": str(target)}}, ".py", *fail)
    assert claude.returncode == 2 and "bad" in claude.stderr
    cursor = run_on_edit({"file_path": str(target)}, ".py", *fail)
    assert cursor.returncode == 2
    assert run_on_edit({"file_path": str(target)}, ".tf", *fail).returncode == 0
    assert run_on_edit({"file_path": str(target)}, ".py", "--", "no-such-tool").returncode == 0


def test_shared_scripts_go_only_to_plugins_whose_hooks_run_them(repo: Path) -> None:
    write(repo / "src/_shared/scripts/x.py", "print('shared')\n")
    write(repo / "src/_shared/scripts/unused.py", "")
    (repo / "src/demo/scripts/x.py").unlink()
    write(repo / "src/plain/plugin.yaml", "name: plain\nversion: 1.0.0\ndescription: P.\n")
    files = build.build(repo)
    assert files["plugins/demo/scripts/x.py"] == "print('shared')\n"
    assert "plugins/demo/scripts/unused.py" not in files
    assert not any(k.startswith("plugins/plain/scripts/") for k in files)
    assert not any(k.startswith("plugins/_shared") for k in files)
    write(repo / "src/demo/scripts/x.py", "print('x')\n")
    with pytest.raises(build.BuildError, match="duplicates src/_shared/scripts/x.py"):
        build.build(repo)


@pytest.mark.skipif(shutil.which("claude") is None, reason="Claude Code CLI not installed")
def test_claude_validator_accepts_marketplace() -> None:
    result = subprocess.run(
        ["claude", "plugin", "validate", str(ROOT)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr

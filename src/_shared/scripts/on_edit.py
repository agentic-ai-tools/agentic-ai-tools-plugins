"""After-edit hook: run a tool on the edited file when its suffix matches.

usage: on_edit.py .py [.pyi ...] -- <command> [args...]    (the file path is appended)

Reads the hook payload on stdin. Claude Code sends tool_input.file_path, Cursor sends file_path.
Exit 2 with the tool's output tells the agent what to fix. A missing tool is skipped, not failed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def edited_path(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    return tool_input.get("file_path") or payload.get("file_path")


def main(argv: list[str]) -> int:
    sep = argv.index("--")
    suffixes, command = set(argv[:sep]), argv[sep + 1 :]
    if command and command[0] == "python":
        command[0] = (
            sys.executable
        )  # the interpreter running this hook, even where only python3 exists
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    path = edited_path(payload) if isinstance(payload, dict) else None
    if not path or Path(path).suffix not in suffixes or not Path(path).is_file():
        return 0
    try:
        result = subprocess.run([*command, path], capture_output=True, text=True)
    except FileNotFoundError:
        print(f"{command[0]} is not on PATH; skipped", file=sys.stderr)
        return 0
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

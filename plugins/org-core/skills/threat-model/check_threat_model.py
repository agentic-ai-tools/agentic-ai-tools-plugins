"""Check a threat model written with the threat-model skill.

usage: python check_threat_model.py <threat-model.md>    prints one problem per line, exits 1 if any
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HEADINGS = [
    "Scope",
    "Assets",
    "Data flow and trust boundaries",
    "STRIDE",
    "STRIDE-AI",
    "Attack chains",
    "Residual risk",
    "Review",
]
COLUMNS = {
    "STRIDE": "ID | Component or boundary | Category | Threat | L | I | Risk | Control"
    " | Owner | Test",
    "STRIDE-AI": "ID | Component | Layer | Category or added row | Threat | L | I | Risk | Control"
    " | OWASP LLM | Test",
    "Attack chains": "Chain | Steps (threat IDs) | End state | L | I | Risk"
    " | Breaking controls and their layers | Detection | Scenario test",
    "Residual risk": "ID | Risk | Register entry",
}
NO_AI = "No component touches a model."
STRIDE_PREFIX = {
    "Spoofing": "S",
    "Tampering": "T",
    "Repudiation": "R",
    "Information disclosure": "I",
    "Denial of service": "D",
    "Elevation of privilege": "E",
}
AI_CATEGORIES = {
    "Model Impersonation",
    "Data/Model Poisoning",
    "Provenance Loss",
    "Model Inversion",
    "Resource Exhaustion",
    "Alignment Bypass",
    "Direct prompt injection",
    "Indirect prompt injection",
    "Improper output handling",
    "Excessive agency",
    "Model and prompt supply chain",
}
AI_LAYERS = {"User interface", "Application", "Model", "Infrastructure", "Data sources"}
DEFENCE_LAYERS = {"Edge", "Identity", "Application", "Model", "Data", "Infrastructure"}
INSTRUCTION = re.compile(r"system prompt|instruct|prompt says|tell(s)? the model", re.I)
CONTROL = re.compile(r"([^;()]+)\(([^)]+)\)")


def band(risk: int) -> str:
    if risk >= 20:
        return "Critical"
    if risk >= 12:
        return "High"
    if risk >= 6:
        return "Medium"
    return "Low"


def sections(body: str) -> dict[str, str]:
    parts = re.split(r"^## (.+)$", body, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def table(text: str) -> tuple[str, list[list[str]]]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return "", []
    cells = [[c.strip() for c in ln.strip("|").split("|")] for ln in lines]
    return " | ".join(cells[0]), [row for row in cells[2:]]


def check_frontmatter(text: str) -> list[str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return ["frontmatter: missing"]
    head = text[4 : text.index("\n---\n", 4)]
    problems = []
    if not re.search(r'^type: "?Reference"?$', head, re.M):
        problems.append('frontmatter: type must be "Reference"')
    for key in ("title", "description"):
        if not re.search(rf"^{key}: \S", head, re.M):
            problems.append(f"frontmatter: {key} is required")
    if not re.search(r"^x-[a-z0-9-]+-artifact: \"?threat-model\"?$", head, re.M):
        problems.append("frontmatter: set the bundle's artifact key to threat-model")
    return problems


def score(row_id: str, l_cell: str, i_cell: str, risk_cell: str) -> tuple[list[str], str]:
    """Problems with one row's scores, and its band ('' when unreadable)."""
    try:
        likelihood, impact = int(l_cell), int(i_cell)
    except ValueError:
        return [f"{row_id}: L and I must be whole numbers from 1 to 5"], ""
    if not (1 <= likelihood <= 5 and 1 <= impact <= 5):
        return [f"{row_id}: L and I must be whole numbers from 1 to 5"], ""
    expected = f"{likelihood * impact} {band(likelihood * impact)}"
    if risk_cell != expected:
        return [f"{row_id}: risk is {risk_cell!r}, expected {expected!r}"], band(
            likelihood * impact
        )
    return [], band(likelihood * impact)


def check_text(text: str) -> list[str]:
    problems = check_frontmatter(text)
    found = sections(text)
    for heading in HEADINGS:
        if heading not in found:
            problems.append(f"missing heading '{heading}'")
    ids: dict[str, str] = {}  # id -> band
    severe: list[str] = []

    def register(row_id: str, row_band: str) -> None:
        if row_id in ids:
            problems.append(f"duplicate ID {row_id}")
        ids[row_id] = row_band
        if row_band in {"High", "Critical"}:
            severe.append(row_id)

    for name in ("STRIDE", "STRIDE-AI"):
        if name not in found:
            continue
        if name == "STRIDE-AI" and NO_AI in found[name]:
            continue
        header, rows = table(found[name])
        if header != COLUMNS[name]:
            problems.append(f"{name}: columns must be | {COLUMNS[name]} |")
            continue
        for row in rows:
            if len(row) != len(COLUMNS[name].split(" | ")):
                problems.append(f"{name}: a row has the wrong number of cells")
                continue
            if name == "STRIDE":
                row_id, _, category, _, l_cell, i_cell, risk, control, _, test = row
                prefix = STRIDE_PREFIX.get(category)
                if prefix is None:
                    problems.append(f"{row_id}: category {category!r} is not a STRIDE category")
                elif not re.fullmatch(rf"{prefix}-\d+", row_id):
                    problems.append(f"{row_id}: ID must be {prefix}-<n> for {category}")
            else:
                row_id, _, layer, category, _, l_cell, i_cell, risk, control, _, test = row
                if not re.fullmatch(r"AI-\d+", row_id):
                    problems.append(f"{row_id}: ID must be AI-<n>")
                if category not in AI_CATEGORIES:
                    problems.append(f"{row_id}: category {category!r} is not a STRIDE-AI category")
                if layer not in AI_LAYERS:
                    problems.append(f"{row_id}: layer {layer!r} is not one of {sorted(AI_LAYERS)}")
            found_problems, row_band = score(row_id, l_cell, i_cell, risk)
            problems += found_problems
            if not control:
                problems.append(f"{row_id}: no control (name one, or 'Accepted: <reason>')")
            elif control.startswith("Accepted") and row_band in {"High", "Critical"}:
                problems.append(f"{row_id}: High or Critical cannot be accepted in the model")
            if row_band in {"High", "Critical"} and not test:
                problems.append(f"{row_id}: High or Critical needs a test")
            register(row_id, row_band)

    if "Attack chains" in found:
        header, rows = table(found["Attack chains"])
        if header != COLUMNS["Attack chains"]:
            problems.append(f"Attack chains: columns must be | {COLUMNS['Attack chains']} |")
            rows = []
        steps_ok = set(ids)
        for row in rows:
            if len(row) != 9:
                problems.append("Attack chains: a row has the wrong number of cells")
                continue
            chain, steps, _, l_cell, i_cell, risk, controls, detection, test = row
            if not re.fullmatch(r"C-\d+", chain):
                problems.append(f"{chain}: ID must be C-<n>")
            for step in (s.strip() for s in steps.split(",")):
                if step not in steps_ok:
                    problems.append(f"{chain}: unknown step {step}")
            found_problems, row_band = score(chain, l_cell, i_cell, risk)
            problems += found_problems
            impact_five = i_cell.strip() == "5"
            if impact_five or row_band == "Critical":
                layers = set()
                for text_part, layer in CONTROL.findall(controls):
                    layer = layer.strip()
                    if layer not in DEFENCE_LAYERS:
                        problems.append(
                            f"{chain}: layer {layer!r} is not one of {sorted(DEFENCE_LAYERS)}"
                        )
                    elif INSTRUCTION.search(text_part):
                        problems.append(f"{chain}: a model instruction is not a breaking control")
                    else:
                        layers.add(layer)
                if len(layers) < 2:
                    problems.append(f"{chain}: needs breaking controls on two different layers")
                if not detection:
                    problems.append(f"{chain}: needs a detection")
            if row_band in {"High", "Critical"} and not test:
                problems.append(f"{chain}: High or Critical needs a scenario test")
            register(chain, row_band)

    if "Residual risk" in found:
        header, rows = table(found["Residual risk"])
        listed = {row[0] for row in rows if row}
        if rows and header != COLUMNS["Residual risk"]:
            problems.append(f"Residual risk: columns must be | {COLUMNS['Residual risk']} |")
        for row_id in severe:
            if row_id not in listed:
                problems.append(f"{row_id}: High or Critical but not in Residual risk")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    problems = check_text(Path(args[0]).read_text(encoding="utf-8"))
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

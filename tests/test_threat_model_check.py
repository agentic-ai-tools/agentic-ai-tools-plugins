from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True  # keep src/ free of __pycache__
SKILL = Path(__file__).resolve().parent.parent / "src/org-core/skills/threat-model"
sys.path.insert(0, str(SKILL))
import check_threat_model  # noqa: E402

TEMPLATE = (SKILL / "template.md").read_text(encoding="utf-8")


def check(text: str) -> list[str]:
    return check_threat_model.check_text(text)


def test_template_passes() -> None:
    assert check(TEMPLATE) == []


def test_model_without_ai_components_passes() -> None:
    start = TEMPLATE.index("## STRIDE-AI")
    end = TEMPLATE.index("## Attack chains")
    text = TEMPLATE[:start] + "## STRIDE-AI\n\nNo component touches a model.\n\n" + TEMPLATE[end:]
    text = text.replace("| C-1 | AI-1, AI-2 |", "| C-1 | S-1, I-1 |")
    text = text.replace("| AI-1 | 12 High | R-001 |\n", "")
    assert check(text) == []


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ("x-example-artifact: threat-model", "x-example-artifact: notes", "frontmatter"),
        ("## Assets", "## Things", "missing heading 'Assets'"),
        ("| 1 | 5 | 5 Low |", "| 1 | 5 | 6 Medium |", "S-1: risk"),
        ("| 2 | 5 | 10 Medium | Tenant", "| 2 | 5 | 10 High | Tenant", "I-1: risk"),
        ("| 1 | 5 | 5 Low |", "| 0 | 5 | 0 Low |", "S-1: L and I"),
        ("| S-1 | Client to API | Spoofing |", "| T-1 | Client to API | Spoofing |", "T-1: ID"),
        ("| I-1 | Conversation store |", "| S-1 | Conversation store |", "duplicate ID S-1"),
        ("| Indirect prompt injection |", "| Vibes |", "AI-1: category"),
        ("| Application | Indirect", "| Backend | Indirect", "AI-1: layer"),
        ("| AI-1, AI-2 |", "| AI-1, AI-9 |", "C-1: unknown step AI-9"),
        ("`test_injected_page_is_data`", "", "AI-1: High or Critical needs a test"),
        ("| AI-1 | 12 High | R-001 |\n", "", "AI-1: High or Critical but not in Residual risk"),
        ("| Model output rendered as text | LLM05", "|  | LLM05", "AI-2: no control"),
    ],
)
def test_reports_problem(old: str, new: str, problem: str) -> None:
    assert old in TEMPLATE
    problems = check(TEMPLATE.replace(old, new, 1))
    assert any(problem in p for p in problems), problems


def test_critical_chain_needs_two_layers_and_detection() -> None:
    one_layer = TEMPLATE.replace(
        "Strict content security policy (Edge); output rendered as text (Application); "
        "token kept out of script-readable storage (Identity)",
        "Output rendered as text (Application); escaping (Application)",
    )
    assert any("two different layers" in p for p in check(one_layer))
    no_detection = TEMPLATE.replace("| CSP violation reports |", "|  |")
    assert any("detection" in p for p in check(no_detection))


def test_model_instruction_is_not_a_breaking_control() -> None:
    text = TEMPLATE.replace(
        "Strict content security policy (Edge); output rendered as text (Application)",
        "System prompt says ignore injected text (Model); output rendered as text (Application)",
    ).replace(
        "; token kept out of script-readable storage (Identity)",
        "",
    )
    assert any("model instruction" in p for p in check(text))


def test_cli_exit_codes(tmp_path: Path) -> None:
    good = tmp_path / "good.md"
    good.write_text(TEMPLATE, encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text(TEMPLATE.replace("## Review", "## Notes"), encoding="utf-8")
    assert check_threat_model.main([str(good)]) == 0
    assert check_threat_model.main([str(bad)]) == 1

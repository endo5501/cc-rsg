from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "cc-rsg"
SKILL = SKILL_ROOT / "SKILL.md"
REQUIRED_REFERENCES = {
    "phase-0-setup.md",
    "phase-1-recon.md",
    "phase-2-plan.md",
    "phase-3-investigate.md",
    "phase-4-verify.md",
    "phase-5-refine.md",
    "phase-6-deliver.md",
    "runtime-claude-code.md",
    "runtime-codex.md",
    "chapter-investigator-prompt.md",
}


def frontmatter_keys(text: str) -> set[str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return set()
    return {
        line.split(":", 1)[0].strip()
        for line in match.group(1).splitlines()
        if ":" in line and not line.startswith((" ", "\t"))
    }


class SkillPortabilityTests(unittest.TestCase):
    def read_reference(self, name: str) -> str:
        path = SKILL_ROOT / "references" / name
        self.assertTrue(path.is_file(), f"missing reference: {name}")
        return path.read_text(encoding="utf-8")

    def test_frontmatter_is_portable(self) -> None:
        self.assertEqual(
            frontmatter_keys(SKILL.read_text(encoding="utf-8")),
            {"name", "description"},
        )

    def test_entry_point_is_small(self) -> None:
        self.assertLess(len(SKILL.read_text(encoding="utf-8").splitlines()), 500)

    def test_required_references_exist_and_are_linked(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        available = {
            path.name for path in (SKILL_ROOT / "references").glob("*.md")
        }
        self.assertTrue(REQUIRED_REFERENCES <= available)
        for name in REQUIRED_REFERENCES:
            self.assertIn(f"references/{name}", text)

    def test_shared_entry_point_uses_capability_language(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        forbidden = (
            "AskUserQuestion",
            "Task tool",
            "Read tool",
            "Write tool",
            "Claude recommends",
            ".claude/skills",
        )
        for term in forbidden:
            self.assertNotIn(term, text)

    def test_sequential_is_default_and_parallel_is_explicit(self) -> None:
        phase = self.read_reference("phase-0-setup.md")
        self.assertIn('"execution_mode": "sequential"', phase)
        self.assertRegex(phase, r"(?is)parallel.*explicit")

    def test_phase_five_uses_persisted_dialogue_outcomes(self) -> None:
        phase = self.read_reference("phase-5-refine.md")
        for field in (
            "dialogue_rounds",
            "questions_presented",
            "questions_answered",
        ):
            self.assertIn(field, phase)
        self.assertNotIn("AskUserQuestion", phase)

    def test_chapter_prompt_has_no_runtime_frontmatter(self) -> None:
        prompt = self.read_reference("chapter-investigator-prompt.md")
        self.assertFalse(prompt.startswith("---"))
        self.assertNotRegex(
            prompt,
            r"(?m)^(tools|allowed-tools|subagent_type):",
        )

    def test_runtime_adapters_document_python_detection(self) -> None:
        adapters = "\n".join(
            self.read_reference(name)
            for name in ("runtime-claude-code.md", "runtime-codex.md")
        )
        for launcher in ("python3", "python", "py -3"):
            self.assertIn(launcher, adapters)


if __name__ == "__main__":
    unittest.main()

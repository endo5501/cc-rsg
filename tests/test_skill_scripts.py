from pathlib import Path
import py_compile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / "skills" / "cc-rsg" / "scripts"


class SkillScriptTests(unittest.TestCase):
    def test_bundled_scripts_compile(self) -> None:
        scripts = sorted(SCRIPT_ROOT.glob("*.py"))
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=script.name):
                py_compile.compile(str(script), doraise=True)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import importlib.util
import json
import py_compile
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / "skills" / "cc-rsg" / "scripts"


def _load(module_name: str, filename: str):
    """Load a hyphenated script file as an importable module."""
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # Register before exec so dataclass introspection can resolve the module.
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


source_map = _load("cc_rsg_source_map", "source-map.py")
coverage_check = _load("cc_rsg_coverage_check", "coverage-check.py")


class SkillScriptTests(unittest.TestCase):
    def test_bundled_scripts_compile(self) -> None:
        scripts = sorted(SCRIPT_ROOT.glob("*.py"))
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=script.name):
                py_compile.compile(str(script), doraise=True)


# ---------------------------------------------------------------------------
# Item 1: source-map.py Dart support + file-level fallback for unsupported src
# ---------------------------------------------------------------------------

DART_SAMPLE = """\
import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const Placeholder();
  }
}

enum Status { idle, loading, done }

mixin Logger {
  void log(String m) {}
}

extension StringX on String {
  String shout() => toUpperCase();
}

void main() {
  runApp(const MyApp());
}
"""


class SourceMapDartTests(unittest.TestCase):
    def _build(self, files: dict[str, str]):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "lib"
            target.mkdir()
            for rel, content in files.items():
                p = target / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    p.write_bytes(content)
                else:
                    p.write_text(content, encoding="utf-8")
            return source_map.build_source_map(target, source_map.DEFAULT_EXCLUDES)

    def test_dart_units_extracted(self) -> None:
        out = self._build({"home.dart": DART_SAMPLE})
        kinds = {u["kind"] for u in out["units"]}
        names = {u["name"] for u in out["units"]}
        # class / enum / mixin / extension + top-level function
        self.assertIn("HomeScreen", names)
        self.assertIn("Status", names)
        self.assertIn("Logger", names)
        self.assertIn("StringX", names)
        self.assertIn("main", names)
        self.assertTrue(any(k.startswith("dart_") for k in kinds), kinds)
        self.assertGreater(out["stats"]["files_scanned"], 0)

    def test_unsupported_source_recorded_as_file_unit(self) -> None:
        out = self._build({"thing.swift": "import Foundation\nclass Thing {}\n"})
        self.assertGreater(out["stats"]["files_scanned"], 0)
        self.assertEqual(out["stats"]["units_total"], 1)
        self.assertEqual(out["units"][0]["kind"], "source_file")

    def test_binary_and_generic_markdown_excluded(self) -> None:
        out = self._build({
            "logo.png": b"\x89PNG\r\n\x1a\n\x00\x00",
            "NOTES.md": "# just notes\nsome prose\n",
        })
        # Neither a PNG nor a generic markdown file should become a unit.
        self.assertEqual(out["stats"]["units_total"], 0)
        self.assertEqual(out["stats"]["files_scanned"], 0)

    def test_dart_block_line_range_is_sane(self) -> None:
        out = self._build({"home.dart": DART_SAMPLE})
        home = next(u for u in out["units"] if u["name"] == "HomeScreen")
        start, end = home["line_range"]
        self.assertLessEqual(start, end)
        self.assertGreaterEqual(end - start, 3)  # spans the class body

    def test_mixin_application_class_does_not_engulf_next(self) -> None:
        # `class C = A with B;` is a valid one-line Dart class with no braces.
        # Its unit must not swallow the following class.
        src = (
            "class Controller = BaseController with LoggingMixin;\n"
            "\n"
            "class Widget extends StatelessWidget {\n"
            "  Widget build(c) {\n"
            "    return null;\n"
            "  }\n"
            "}\n"
        )
        out = self._build({"a.dart": src})
        ctrl = next(u for u in out["units"] if u["name"] == "Controller")
        # The alias class occupies only its own line.
        self.assertEqual(ctrl["line_range"], [1, 1])
        # The following widget class is still extracted independently.
        self.assertIn("Widget", {u["name"] for u in out["units"]})

    def test_unit_paths_use_forward_slashes(self) -> None:
        # Paths must be POSIX-style so [REF:] markers and exclude globs match
        # on Windows (build-trace.py matches forward-slash reference paths).
        out = self._build({"features/home.dart": DART_SAMPLE})
        for u in out["units"]:
            self.assertNotIn("\\", u["path"], u)
        self.assertTrue(any("/" in u["path"] for u in out["units"]))


# ---------------------------------------------------------------------------
# Item 2: Sources Read section must survive blank lines
# ---------------------------------------------------------------------------

class SourcesReadTests(unittest.TestCase):
    def test_blank_line_after_heading_does_not_zero_count(self) -> None:
        content = (
            "# Chapter 1\n\nbody text here\n\n"
            "## Sources Read\n\n"
            "- `lib/a.dart`\n"
            "- `lib/b.dart`\n"
            "- `lib/c.dart`\n"
        )
        m = coverage_check.compute_chapter_metrics("01-x.md", content)
        self.assertEqual(m.sources_read_count, 3)

    def test_next_heading_closes_section(self) -> None:
        content = (
            "## Sources Read\n\n"
            "- `lib/a.dart`\n\n"
            "## Another section\n\n"
            "- not a source\n"
        )
        m = coverage_check.compute_chapter_metrics("01-x.md", content)
        self.assertEqual(m.sources_read_count, 1)

    def test_trailing_prose_after_sources_read_still_counts(self) -> None:
        # Non-canonical: prose (with a REF) after the Sources Read list, no
        # intervening heading. It must not be swallowed by the section.
        content = (
            "## Sources Read\n\n"
            "- `lib/a.dart`\n\n"
            "A trailing note. [REF: lib/a.dart:1-2]\n"
        )
        m = coverage_check.compute_chapter_metrics("01-x.md", content)
        self.assertEqual(m.sources_read_count, 1)
        self.assertEqual(m.refs, 1)
        self.assertGreaterEqual(m.body_lines, 1)


# ---------------------------------------------------------------------------
# Item 3: confidence labels counted once
# ---------------------------------------------------------------------------

class ConfidenceCountTests(unittest.TestCase):
    def test_emoji_word_cell_counted_once(self) -> None:
        content = (
            "| a | 🟢 VERIFIED |\n"
            "| b | 🟢 VERIFIED |\n"
            "| c | 🔴 ASSUMED |\n"
            "| d | 🟡 INFERRED |\n"
        )
        v, i, a = coverage_check.count_confidence_labels(content)
        self.assertEqual(v, 2)
        self.assertEqual(a, 1)
        self.assertEqual(i, 1)

    def test_word_only_and_emoji_only_both_one(self) -> None:
        v, i, a = coverage_check.count_confidence_labels("VERIFIED\n🟢\n")
        self.assertEqual(v, 2)


# ---------------------------------------------------------------------------
# Item 4: inventory loader tolerant of both shapes / type aliases
# ---------------------------------------------------------------------------

class InventoryLoaderTests(unittest.TestCase):
    def _write(self, data) -> Path:
        tmp = Path(tempfile.mkdtemp())
        p = tmp / "inventory.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_array_form_with_unit_type(self) -> None:
        p = self._write([
            {"id": "INV-001", "unit_type": "service", "name": "Foo", "file": "a.dart"},
        ])
        items = coverage_check.load_inventory(p)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].type, "service")

    def test_object_form_with_type(self) -> None:
        p = self._write({"units": [
            {"id": "INV-001", "type": "service", "name": "Foo", "file": "a.dart",
             "covered_by": []},
        ]})
        items = coverage_check.load_inventory(p)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].type, "service")


# ---------------------------------------------------------------------------
# Item 5: macro-type detection uses whole-word / suffix matching
# ---------------------------------------------------------------------------

class MacroTypeTests(unittest.TestCase):
    def _item(self, t: str):
        return coverage_check.InventoryItem(id="X", type=t, name="n", file="f", line=1)

    def test_domain_is_not_macro(self) -> None:
        self.assertFalse(coverage_check.is_macro_type(self._item("domain")))
        self.assertFalse(coverage_check.is_macro_type(self._item("service")))
        self.assertFalse(coverage_check.is_macro_type(self._item("module")))

    def test_grouping_suffixes_are_macro(self) -> None:
        self.assertTrue(coverage_check.is_macro_type(self._item("controller_group")))
        self.assertTrue(coverage_check.is_macro_type(self._item("model_bundle")))
        self.assertTrue(coverage_check.is_macro_type(self._item("view_group")))


# ---------------------------------------------------------------------------
# Item 8: min-questions auto scaling
# ---------------------------------------------------------------------------

class AutoMinTests(unittest.TestCase):
    def test_auto_min_questions(self) -> None:
        self.assertEqual(
            coverage_check.compute_auto_min("auto", 80, floor=5, divisor=40), 5
        )
        self.assertEqual(
            coverage_check.compute_auto_min("auto", 400, floor=5, divisor=40), 10
        )

    def test_auto_min_inventory_floor(self) -> None:
        self.assertEqual(
            coverage_check.compute_auto_min("auto", 100, floor=50, divisor=20), 50
        )

    def test_explicit_value_passthrough(self) -> None:
        self.assertEqual(
            coverage_check.compute_auto_min("12", 999, floor=5, divisor=40), 12
        )


if __name__ == "__main__":
    unittest.main()

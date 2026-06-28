from pathlib import Path
import importlib.util
import json
import os
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
# Item 1b: source-map.py C/C++ detailed extraction + file-level fallback
# ---------------------------------------------------------------------------

CPP_SAMPLE = """\
#include <string>

namespace app {

class Foo : public Bar {
 public:
  void doit();
  int value() const { return v_; }
 private:
  int v_;
};

struct Point {
  int x;
  int y;
};

union Value {
  int i;
  float f;
};

enum class Color { red, green, blue };

}  // namespace app

void Foo::doit() {
  v_ = 42;
}

int main(int argc, char** argv) {
  return 0;
}
"""

C_SAMPLE = """\
#include <stdlib.h>

struct Node {
  int data;
  struct Node* next;
};

enum Status { OK, FAIL };

int add(int a, int b) {
  return a + b;
}
"""

C_HEADER_PROTOTYPES_ONLY = """\
#ifndef UTIL_H
#define UTIL_H

int add(int, int);
void log_message(const char* msg);
class Forward;

#endif
"""


class SourceMapCppTests(unittest.TestCase):
    def _build(self, files: dict[str, str]):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "src"
            target.mkdir()
            for rel, content in files.items():
                p = target / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    p.write_bytes(content)
                else:
                    p.write_text(content, encoding="utf-8")
            return source_map.build_source_map(target, source_map.DEFAULT_EXCLUDES)

    def _units(self, out):
        return {u["name"]: u for u in out["units"]}

    def test_cpp_kinds_and_names(self) -> None:
        out = self._build({"app.cpp": CPP_SAMPLE})
        units = self._units(out)
        self.assertEqual(units["Foo"]["kind"], "cpp_class")
        self.assertEqual(units["Point"]["kind"], "cpp_struct")
        self.assertEqual(units["Value"]["kind"], "cpp_union")
        self.assertEqual(units["Color"]["kind"], "cpp_enum")
        self.assertEqual(units["app"]["kind"], "cpp_namespace")
        self.assertEqual(units["main"]["kind"], "cpp_function")

    def test_enum_class_name_is_not_class(self) -> None:
        out = self._build({"app.cpp": CPP_SAMPLE})
        names = {u["name"] for u in out["units"]}
        self.assertIn("Color", names)
        self.assertNotIn("class", names)

    def test_out_of_line_member_definition(self) -> None:
        out = self._build({"app.cpp": CPP_SAMPLE})
        units = self._units(out)
        self.assertIn("doit", units)
        self.assertEqual(units["doit"]["kind"], "cpp_function")

    def test_prototype_does_not_create_function_unit(self) -> None:
        out = self._build({"util.c": C_SAMPLE})
        units = self._units(out)
        # `add` is a real definition; ensure no spurious prototype duplicate.
        self.assertEqual(units["add"]["kind"], "cpp_function")
        add_units = [u for u in out["units"] if u["name"] == "add"]
        self.assertEqual(len(add_units), 1)

    def test_c_struct_and_enum(self) -> None:
        out = self._build({"util.c": C_SAMPLE})
        units = self._units(out)
        self.assertEqual(units["Node"]["kind"], "cpp_struct")
        self.assertEqual(units["Status"]["kind"], "cpp_enum")
        self.assertEqual(units["add"]["kind"], "cpp_function")

    def test_forward_declaration_not_a_unit(self) -> None:
        out = self._build({"fwd.hpp": "class Forward;\nstruct AlsoFwd;\n"})
        # No real definition → falls back to a single file-level unit.
        self.assertEqual(out["stats"]["units_total"], 1)
        self.assertEqual(out["units"][0]["kind"], "source_file")

    def test_line_range_spans_body(self) -> None:
        out = self._build({"app.cpp": CPP_SAMPLE})
        foo = self._units(out)["Foo"]
        start, end = foo["line_range"]
        self.assertLessEqual(start, end)
        self.assertGreaterEqual(end - start, 3)

    def test_prototype_only_header_falls_back_to_file_unit(self) -> None:
        out = self._build({"util.h": C_HEADER_PROTOTYPES_ONLY})
        self.assertEqual(out["stats"]["units_total"], 1)
        self.assertEqual(out["units"][0]["kind"], "source_file")

    def test_cpp_unit_paths_use_forward_slashes(self) -> None:
        out = self._build({"core/app.cpp": CPP_SAMPLE})
        for u in out["units"]:
            self.assertNotIn("\\", u["path"], u)
        self.assertTrue(any("/" in u["path"] for u in out["units"]))

    def test_function_returning_struct_is_a_function(self) -> None:
        src = (
            "struct Node* make_node(int v) {\n"
            "  return 0;\n"
            "}\n"
            "\n"
            "enum State next_state(int x) {\n"
            "  return x;\n"
            "}\n"
        )
        out = self._build({"f.c": src})
        units = self._units(out)
        # The functions must be captured under their real names as functions.
        self.assertEqual(units["make_node"]["kind"], "cpp_function")
        self.assertEqual(units["next_state"]["kind"], "cpp_function")
        # The return types must NOT be misread as type definitions.
        self.assertNotIn("Node", units)
        self.assertNotIn("State", units)

    def test_global_struct_variable_is_not_a_type_unit(self) -> None:
        src = "struct Config g_cfg = {\n  1,\n};\n"
        out = self._build({"g.c": src})
        names = {u["name"] for u in out["units"]}
        # A global of struct type is a variable, not a struct definition.
        self.assertNotIn("Config", names)

    def test_export_macro_does_not_become_the_name(self) -> None:
        src = "class API_EXPORT Widget : public Base {\n  int x;\n};\n"
        out = self._build({"w.hpp": src})
        units = self._units(out)
        self.assertIn("Widget", units)
        self.assertEqual(units["Widget"]["kind"], "cpp_class")
        self.assertNotIn("API_EXPORT", units)

    def test_attribute_does_not_become_the_name(self) -> None:
        src = "struct __attribute__((packed)) Header {\n  int a;\n};\n"
        out = self._build({"h.h": src})
        units = self._units(out)
        self.assertIn("Header", units)
        self.assertEqual(units["Header"]["kind"], "cpp_struct")
        self.assertNotIn("__attribute__", units)

    def test_brace_in_string_does_not_truncate_block(self) -> None:
        src = (
            "void render() {\n"
            '  const char* fmt = "}";\n'
            "  int y = 0;\n"
            "  y++;\n"
            "}\n"
        )
        out = self._build({"r.cpp": src})
        render = self._units(out)["render"]
        # The `}` inside the string literal must not close the function early.
        self.assertEqual(render["line_range"], [1, 5])

    def test_brace_in_comment_does_not_truncate_block(self) -> None:
        src = (
            "struct Foo {\n"
            "  int x;  // closing } here in a comment\n"
            "  int y;\n"
            "};\n"
        )
        out = self._build({"c.h": src})
        foo = self._units(out)["Foo"]
        self.assertEqual(foo["line_range"], [1, 4])

    def test_enum_named_classification_not_truncated(self) -> None:
        # `enum classification` must not be parsed as `enum class` + `ification`.
        src = "enum classification { A, B };\n"
        out = self._build({"e.h": src})
        units = self._units(out)
        self.assertIn("classification", units)
        self.assertEqual(units["classification"]["kind"], "cpp_enum")


# ---------------------------------------------------------------------------
# Item 1c: optional high-fidelity C/C++ tier (libclang + compile_commands.json)
# ---------------------------------------------------------------------------

class CompileCommandsDiscoveryTests(unittest.TestCase):
    """Pure: locating compile_commands.json (no libclang needed)."""

    def test_explicit_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ccj = root / "build" / "compile_commands.json"
            ccj.parent.mkdir(parents=True)
            ccj.write_text("[]", encoding="utf-8")
            found = source_map.find_compile_commands(root / "src", explicit=ccj)
            self.assertEqual(found, ccj.parent)

    def test_explicit_dir_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "compile_commands.json").write_text("[]", encoding="utf-8")
            found = source_map.find_compile_commands(root / "src", explicit=root)
            self.assertEqual(found, root)

    def test_autodiscover_in_build_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "src"
            target.mkdir()
            ccj = root / "build" / "compile_commands.json"
            ccj.parent.mkdir(parents=True)
            ccj.write_text("[]", encoding="utf-8")
            found = source_map.find_compile_commands(target)
            self.assertEqual(found, ccj.parent)

    def test_returns_none_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "src"
            target.mkdir()
            self.assertIsNone(source_map.find_compile_commands(target))

    def test_autodiscover_nested_config_subdir(self) -> None:
        # Multi-config builds place the DB one level below the build dir,
        # e.g. build/msvc_release/compile_commands.json.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "src"
            target.mkdir()
            ccj = root / "build" / "msvc_release" / "compile_commands.json"
            ccj.parent.mkdir(parents=True)
            ccj.write_text("[]", encoding="utf-8")
            found = source_map.find_compile_commands(target)
            self.assertEqual(found, ccj.parent)

    def test_direct_build_db_preferred_over_nested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "src"
            target.mkdir()
            direct = root / "build" / "compile_commands.json"
            direct.parent.mkdir(parents=True)
            direct.write_text("[]", encoding="utf-8")
            nested = root / "build" / "msvc_release" / "compile_commands.json"
            nested.parent.mkdir(parents=True)
            nested.write_text("[]", encoding="utf-8")
            found = source_map.find_compile_commands(target)
            self.assertEqual(found, direct.parent)

    def test_multiple_nested_configs_pick_newest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "src"
            target.mkdir()
            debug = root / "build" / "debug" / "compile_commands.json"
            release = root / "build" / "release" / "compile_commands.json"
            for p in (debug, release):
                p.parent.mkdir(parents=True)
                p.write_text("[]", encoding="utf-8")
            # release built more recently than debug.
            os.utime(debug, (1_000_000, 1_000_000))
            os.utime(release, (2_000_000, 2_000_000))
            found = source_map.find_compile_commands(target)
            self.assertEqual(found, release.parent)


class ClangKindMapTests(unittest.TestCase):
    """Pure: cursor-kind name → cpp_* kind (no libclang needed)."""

    def test_type_kinds(self) -> None:
        self.assertEqual(source_map.clang_kind_to_cpp("CLASS_DECL"), "cpp_class")
        self.assertEqual(source_map.clang_kind_to_cpp("CLASS_TEMPLATE"), "cpp_class")
        self.assertEqual(source_map.clang_kind_to_cpp("STRUCT_DECL"), "cpp_struct")
        self.assertEqual(source_map.clang_kind_to_cpp("UNION_DECL"), "cpp_union")
        self.assertEqual(source_map.clang_kind_to_cpp("ENUM_DECL"), "cpp_enum")
        self.assertEqual(source_map.clang_kind_to_cpp("NAMESPACE"), "cpp_namespace")

    def test_function_kinds(self) -> None:
        for k in ("FUNCTION_DECL", "CXX_METHOD", "CONSTRUCTOR",
                  "DESTRUCTOR", "CONVERSION_FUNCTION"):
            self.assertEqual(source_map.clang_kind_to_cpp(k), "cpp_function", k)

    def test_unknown_kind(self) -> None:
        self.assertIsNone(source_map.clang_kind_to_cpp("PARM_DECL"))
        self.assertIsNone(source_map.clang_kind_to_cpp("FIELD_DECL"))


class CppUnitsFromDeclsTests(unittest.TestCase):
    """Pure: intermediate decl records → SourceUnits (no libclang needed)."""

    def _factory(self):
        n = [0]

        def f():
            n[0] += 1
            return f"SRC-{n[0]:04d}"
        return f

    def test_dedup_across_translation_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "proj" / "a.cpp"
            f.parent.mkdir(parents=True)
            f.write_text("struct S { int x; };\nint g() { return 0; }\n",
                         encoding="utf-8")
            # The same header decl seen from two TUs → one unit.
            decls = [
                {"path": "proj/a.cpp", "start_line": 1, "end_line": 1,
                 "kind": "cpp_struct", "name": "S", "signature": "S"},
                {"path": "proj/a.cpp", "start_line": 1, "end_line": 1,
                 "kind": "cpp_struct", "name": "S", "signature": "S"},
                {"path": "proj/a.cpp", "start_line": 2, "end_line": 2,
                 "kind": "cpp_function", "name": "g", "signature": "g()"},
            ]
            units = source_map.cpp_units_from_decls(decls, root, self._factory())
            self.assertEqual(len(units), 2)
            s = next(u for u in units if u.name == "S")
            self.assertEqual(s.kind, "cpp_struct")
            self.assertEqual(s.line_range, (1, 1))
            self.assertTrue(s.fingerprint.startswith("sha1:"))
            self.assertTrue(s.id.startswith("SRC-"))

    def test_deterministic_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "a.cpp"
            f.write_text("\n".join(f"// line {i}" for i in range(20)),
                         encoding="utf-8")
            decls = [
                {"path": "a.cpp", "start_line": 10, "end_line": 11,
                 "kind": "cpp_function", "name": "b", "signature": "b()"},
                {"path": "a.cpp", "start_line": 2, "end_line": 3,
                 "kind": "cpp_function", "name": "a", "signature": "a()"},
            ]
            units = source_map.cpp_units_from_decls(decls, root, self._factory())
            self.assertEqual([u.name for u in units], ["a", "b"])


@unittest.skipUnless(source_map.HAS_LIBCLANG, "libclang not installed")
class ClangTierEndToEndTests(unittest.TestCase):
    """libclang-backed extraction via a hand-written compile_commands.json."""

    def _build_with_db(self, files: dict[str, str], db_files=None):
        tmp = tempfile.mkdtemp()
        root = Path(tmp)
        target = root / "proj"
        target.mkdir()
        for rel, content in files.items():
            p = target / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        # Hand-written compile DB: one TU per file listed in db_files (default:
        # every .c/.cpp). Files omitted here are absent from the database.
        if db_files is None:
            db_files = [r for r in files if r.endswith((".c", ".cc", ".cpp", ".cxx"))]
        db = []
        for rel in db_files:
            src = (target / rel).resolve()
            db.append({
                "directory": target.as_posix(),
                "file": src.as_posix(),
                "arguments": ["clang", "-std=c++17", "-c", rel],
            })
        (root / "compile_commands.json").write_text(
            json.dumps(db), encoding="utf-8")
        out = source_map.build_source_map(
            target, source_map.DEFAULT_EXCLUDES, compile_commands=root)
        return out

    def test_macro_class_and_struct_return_function(self) -> None:
        src = (
            "#define API_EXPORT __attribute__((visibility(\"default\")))\n"
            "namespace app {\n"
            "class API_EXPORT Widget { public: int value() const { return 1; } };\n"
            "}\n"
            "struct Node* make_node(int v) { return 0; }\n"
        )
        out = self._build_with_db({"a.cpp": src})
        by_name = {u["name"]: u for u in out["units"]}
        # AST resolves the macro'd class name and the struct-returning function.
        self.assertEqual(by_name["Widget"]["kind"], "cpp_class")
        self.assertEqual(by_name["make_node"]["kind"], "cpp_function")
        self.assertNotIn("Node", by_name)  # not a type definition
        self.assertNotIn("API_EXPORT", by_name)
        self.assertEqual(out["stats"]["cpp_extractor"], "clang")

    def test_uncovered_file_falls_back_to_regex(self) -> None:
        # b.cpp is NOT in the compile DB → regex extractor must still cover it.
        out = self._build_with_db({
            "a.cpp": "int main() { return 0; }\n",
            "b.cpp": "class OnlyInB {\n  int z;\n};\n",  # not in DB
        }, db_files=["a.cpp"])
        by_name = {u["name"]: u for u in out["units"]}
        self.assertIn("OnlyInB", by_name)
        self.assertEqual(by_name["OnlyInB"]["kind"], "cpp_class")
        self.assertEqual(out["stats"]["cpp_extractor"], "mixed")


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

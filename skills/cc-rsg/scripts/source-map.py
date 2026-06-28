#!/usr/bin/env python3
"""
cc-rsg source-map.py

Scans the target codebase, extracts "source units", and produces
`.cc-rsg/source-map.json`.

Source-unit definitions are implemented as language-specific regexes.
Tree-sitter adds dependencies and is not used in v1; we stay with
maintainable regex-based extraction.

A source unit is the smallest item for which the spec wants
traceability:
- Ruby/Rails:  class / module level, controller action level, route group, migration, view
- Python:      class / def level
- JavaScript:  export level, function definitions
- Dart:        class / mixin / enum / extension / top-level function level
- Other src:   file level (any recognised text source extension)
- Other:       file level (coarse, but far better than nothing)

Usage:
    python source-map.py \\
        --target ./src \\
        --output .cc-rsg/source-map.json \\
        --exclude-globs '**/test/**,**/vendor/**,**/node_modules/**'

Output schema (source-map.json):
    {
      "schema_version": "0.1.0",
      "target_root": "<input target>",
      "generated_at": "<ISO 8601>",
      "stats": {
        "files_scanned": N,
        "files_excluded": K,
        "units_total": M,
        "by_kind": {"ruby_class": ..., "rails_route": ...}
      },
      "units": [
        {
          "id": "SRC-0001",
          "path": "<relative to repo root>",
          "line_range": [start, end],   // 1-indexed inclusive
          "kind": "ruby_class",
          "name": "Issue",
          "signature": "class Issue < ActiveRecord::Base",
          "fingerprint": "sha1:..."
        },
        ...
      ]
    }
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


# ----------------------------------------------------------------------------
# Source-unit definition
# ----------------------------------------------------------------------------

@dataclass
class SourceUnit:
    id: str
    path: str
    line_range: tuple[int, int]
    kind: str
    name: str
    signature: str
    fingerprint: str


# ----------------------------------------------------------------------------
# Per-language extraction rules
# ----------------------------------------------------------------------------

RUBY_CLASS_RE = re.compile(r"^(\s*)(class|module)\s+([A-Za-z0-9_:]+)([^\n]*)")
RUBY_DEF_RE = re.compile(r"^(\s*)def\s+(self\.)?([A-Za-z_][A-Za-z0-9_!?=]*)([^\n]*)")
PY_CLASS_RE = re.compile(r"^(\s*)class\s+([A-Za-z_][A-Za-z0-9_]*)([^\n]*)")
PY_DEF_RE = re.compile(r"^(\s*)def\s+([A-Za-z_][A-Za-z0-9_]*)([^\n]*)")
JS_EXPORT_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?"
    r"(?:async\s+)?"
    r"(?:function\s+|class\s+|const\s+|let\s+|var\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)
RAILS_ROUTE_BLOCK_RE = re.compile(
    r"^(\s*)(resources?|namespace|scope)\s+:?([A-Za-z0-9_]+)"
)
# Dart type declarations: class / mixin / enum / extension, with optional
# leading modifiers (abstract, final, sealed, base, interface, mixin).
DART_TYPE_RE = re.compile(
    r"^(\s*)(?:(?:abstract|final|sealed|base|interface|mixin)\s+)*"
    r"(class|mixin|enum|extension)\s+([A-Za-z_$][A-Za-z0-9_$]*)([^\n]*)"
)
# Dart top-level functions: a return type/name pair followed by `(` at column 0.
# Conservative: skips control-flow keywords so `if (...)` / `for (...)` aren't matched.
DART_TOP_FN_RE = re.compile(
    r"^([A-Za-z_$][A-Za-z0-9_$<>,. ?]*?)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\([^;]*$"
)
DART_FN_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "return", "assert", "await",
    "class", "enum", "mixin", "extension", "import", "export", "part", "library",
}


def fingerprint(text: str) -> str:
    return "sha1:" + hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def extract_ruby_block(lines: list[str], start_idx: int, indent: str) -> int:
    """
    Return the line number (1-indexed) of the `end` that closes a Ruby
    `class` / `module` / `def` block. Found by matching the `end` whose
    indent equals the starting indent.
    """
    end_pattern = re.compile(rf"^{re.escape(indent)}end\b")
    for j in range(start_idx + 1, len(lines)):
        if end_pattern.match(lines[j]):
            return j + 1  # 1-indexed
    return len(lines)


def extract_py_block(lines: list[str], start_idx: int, indent: str) -> int:
    """
    Python block: while the indent stays equal or deeper than the start,
    the block continues. Stop just before the first line whose indent is
    shallower than the start.
    """
    base = len(indent)
    for j in range(start_idx + 1, len(lines)):
        ln = lines[j]
        if ln.strip() == "":
            continue
        cur_indent = len(ln) - len(ln.lstrip(" "))
        if cur_indent <= base:
            return j  # last line is j-1 (1-indexed: j)
    return len(lines)


def extract_brace_block(lines: list[str], start_idx: int) -> int:
    """
    Brace-language block: starting at `start_idx`, count `{`/`}` and return the
    1-indexed line number where the brace depth returns to zero. Used for Dart.
    Falls back to the start line + 1 when no opening brace is found (e.g. a
    single-line `=>` function or an abstract declaration ending in `;`).
    """
    depth = 0
    seen_open = False
    for j in range(start_idx, len(lines)):
        for ch in lines[j]:
            if ch == "{":
                depth += 1
                seen_open = True
            elif ch == "}":
                depth -= 1
        if seen_open and depth <= 0:
            return j + 1  # 1-indexed
        if not seen_open and (";" in lines[j] or "=>" in lines[j]) and j > start_idx:
            return j + 1
    return len(lines)


def extract_ruby_units(
    rel_path: str, source: str, id_factory
) -> Iterable[SourceUnit]:
    lines = source.splitlines()
    is_routes = rel_path.endswith("config/routes.rb")

    for i, line in enumerate(lines):
        m_cls = RUBY_CLASS_RE.match(line)
        if m_cls:
            indent, kw, name, rest = m_cls.groups()
            end_line = extract_ruby_block(lines, i, indent)
            block_text = "\n".join(lines[i:end_line])
            yield SourceUnit(
                id=id_factory(),
                path=rel_path,
                line_range=(i + 1, end_line),
                kind=f"ruby_{kw}",
                name=name,
                signature=f"{kw} {name}{rest}".strip(),
                fingerprint=fingerprint(block_text),
            )
            continue

        if is_routes:
            m_route = RAILS_ROUTE_BLOCK_RE.match(line)
            if m_route:
                indent, kw, name = m_route.groups()
                # Supports both `do…end` block form and single-line `resources :foo`.
                if "do" in line and " end" not in line:
                    end_line = extract_ruby_block(lines, i, indent)
                else:
                    end_line = i + 1
                block_text = "\n".join(lines[i:end_line])
                yield SourceUnit(
                    id=id_factory(),
                    path=rel_path,
                    line_range=(i + 1, end_line),
                    kind="rails_route",
                    name=f"{kw}:{name}",
                    signature=line.rstrip(),
                    fingerprint=fingerprint(block_text),
                )


def extract_py_units(rel_path: str, source: str, id_factory) -> Iterable[SourceUnit]:
    lines = source.splitlines()
    for i, line in enumerate(lines):
        m_cls = PY_CLASS_RE.match(line)
        if m_cls:
            indent, name, rest = m_cls.groups()
            end_line = extract_py_block(lines, i, indent)
            block_text = "\n".join(lines[i:end_line])
            yield SourceUnit(
                id=id_factory(),
                path=rel_path,
                line_range=(i + 1, end_line),
                kind="py_class",
                name=name,
                signature=f"class {name}{rest}".strip(),
                fingerprint=fingerprint(block_text),
            )
            continue
        m_def = PY_DEF_RE.match(line)
        if m_def:
            indent, name, rest = m_def.groups()
            # Register only top-level `def`s as units (methods are inside the class block).
            if indent == "":
                end_line = extract_py_block(lines, i, indent)
                block_text = "\n".join(lines[i:end_line])
                yield SourceUnit(
                    id=id_factory(),
                    path=rel_path,
                    line_range=(i + 1, end_line),
                    kind="py_function",
                    name=name,
                    signature=f"def {name}{rest}".strip(),
                    fingerprint=fingerprint(block_text),
                )


def extract_js_units(rel_path: str, source: str, id_factory) -> Iterable[SourceUnit]:
    lines = source.splitlines()
    for i, line in enumerate(lines):
        m = JS_EXPORT_RE.match(line)
        if m:
            name = m.group(1)
            yield SourceUnit(
                id=id_factory(),
                path=rel_path,
                line_range=(i + 1, i + 1),
                kind="js_export",
                name=name,
                signature=line.strip(),
                fingerprint=fingerprint(line),
            )


def extract_dart_units(rel_path: str, source: str, id_factory) -> Iterable[SourceUnit]:
    lines = source.splitlines()
    for i, line in enumerate(lines):
        m_type = DART_TYPE_RE.match(line)
        if m_type:
            indent, kw, name, rest = m_type.groups()
            end_line = extract_brace_block(lines, i)
            block_text = "\n".join(lines[i:end_line])
            yield SourceUnit(
                id=id_factory(),
                path=rel_path,
                line_range=(i + 1, end_line),
                kind=f"dart_{kw}",
                name=name,
                signature=f"{kw} {name}{rest}".strip()[:240],
                fingerprint=fingerprint(block_text),
            )
            continue
        # Top-level functions only (indent must be empty; skip control flow).
        if line[:1].strip():
            m_fn = DART_TOP_FN_RE.match(line)
            if m_fn:
                ret, name = m_fn.groups()
                if ret.split()[-1] not in DART_FN_KEYWORDS and name not in DART_FN_KEYWORDS:
                    end_line = extract_brace_block(lines, i)
                    block_text = "\n".join(lines[i:end_line])
                    yield SourceUnit(
                        id=id_factory(),
                        path=rel_path,
                        line_range=(i + 1, end_line),
                        kind="dart_function",
                        name=name,
                        signature=line.strip()[:240],
                        fingerprint=fingerprint(block_text),
                    )


def extract_file_unit(rel_path: str, source: str, kind: str, id_factory) -> SourceUnit:
    """File-granularity coarse unit (used for migrations / views / configs, etc.)."""
    lines = source.splitlines()
    name = Path(rel_path).name
    return SourceUnit(
        id=id_factory(),
        path=rel_path,
        line_range=(1, max(len(lines), 1)),
        kind=kind,
        name=name,
        signature=lines[0].strip() if lines else name,
        fingerprint=fingerprint(source),
    )


# ----------------------------------------------------------------------------
# File classification and dispatch
# ----------------------------------------------------------------------------

# Recognised text source extensions with no dedicated extractor. They are
# still recorded as coarse file-level units so the MECE chain works on any
# stack (matches the docstring contract: unsupported source => kind="file").
# Binaries, images, and generic prose are deliberately excluded.
GENERIC_SOURCE_EXTENSIONS = (
    ".swift", ".kt", ".kts", ".java", ".scala", ".groovy", ".clj", ".cljs",
    ".rs", ".go", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp",
    ".m", ".mm", ".cs", ".fs", ".php", ".pl", ".pm", ".lua", ".r",
    ".ex", ".exs", ".erl", ".hs", ".ml", ".sh", ".bash", ".ps1",
    ".gradle", ".cmake", ".tf", ".proto", ".graphql", ".gql",
)


def classify_file(rel_path: str) -> list[str]:
    """
    Return the list of one or more extraction strategies that apply to the file.
    Strategies look like ["ruby_class_def", "rails_view"].
    Empty list = this file is not a unit-extraction target (binary, image, or
    generic prose). Recognised text source files with no dedicated extractor
    fall back to a coarse file-level unit ("source_file").
    """
    p = rel_path.lower()
    strategies: list[str] = []

    if p.endswith(".rb"):
        strategies.append("ruby_class_def")
        if p.endswith("/config/routes.rb"):
            strategies.append("rails_routes")
        if "/db/migrate/" in p:
            strategies.append("rails_migration")
    elif p.endswith((".py",)):
        strategies.append("py_class_def")
    elif p.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs")):
        strategies.append("js_export")
    elif p.endswith(".dart"):
        strategies.append("dart_decl")
    elif p.endswith((".erb", ".html.erb", ".html", ".vue", ".svelte")):
        strategies.append("view_file")
    elif p.endswith((".yml", ".yaml", ".toml", ".ini", ".conf", ".cfg")):
        strategies.append("config_file")
    elif p.endswith((".css", ".scss", ".sass", ".less")):
        # Stylesheets: coarse, file level.
        strategies.append("style_file")
    elif p.endswith((".md", ".rst", ".txt", ".rdoc")) and not "readme" in p:
        # Skip generic Markdown.
        return []
    elif p.endswith(".sql"):
        strategies.append("sql_file")
    elif p.endswith(GENERIC_SOURCE_EXTENSIONS):
        # Recognised source language with no dedicated extractor: file-level unit.
        strategies.append("source_file")

    return strategies


def matches_any(rel_path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, g) for g in globs)


def iter_target_files(target: Path, exclude_globs: list[str]) -> Iterable[Path]:
    for p in target.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(target.parent)
        rel_str = rel.as_posix()  # normalize separators for glob matching
        if matches_any(rel_str, exclude_globs):
            continue
        yield p


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

DEFAULT_EXCLUDES = [
    "**/.git/**",
    "**/node_modules/**",
    "**/vendor/bundle/**",
    "**/tmp/**",
    "**/log/**",
    "**/coverage/**",
    "**/.bundle/**",
    "**/public/assets/**",
    "**/dist/**",
    "**/build/**",
]


def build_source_map(
    target_path: Path,
    exclude_globs: list[str],
) -> dict:
    units: list[SourceUnit] = []
    files_scanned = 0
    files_excluded = 0
    next_id = [0]

    def id_factory() -> str:
        next_id[0] += 1
        return f"SRC-{next_id[0]:04d}"

    base = target_path.parent

    for file_path in iter_target_files(target_path, exclude_globs):
        # POSIX-style (forward slash) so [REF:] markers, exclude globs, and
        # path-suffix classification match consistently across platforms.
        rel_path = file_path.relative_to(base).as_posix()
        strategies = classify_file(rel_path)
        if not strategies:
            files_excluded += 1
            continue
        files_scanned += 1
        try:
            source = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            try:
                source = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

        for strat in strategies:
            if strat == "ruby_class_def":
                units.extend(extract_ruby_units(rel_path, source, id_factory))
            elif strat == "rails_routes":
                # rails_routes is also handled inside extract_ruby_units; skip duplicate.
                pass
            elif strat == "rails_migration":
                units.append(
                    extract_file_unit(rel_path, source, "rails_migration", id_factory)
                )
            elif strat == "py_class_def":
                units.extend(extract_py_units(rel_path, source, id_factory))
            elif strat == "js_export":
                units.extend(extract_js_units(rel_path, source, id_factory))
            elif strat == "dart_decl":
                units.extend(extract_dart_units(rel_path, source, id_factory))
            elif strat == "source_file":
                units.append(extract_file_unit(rel_path, source, "source_file", id_factory))
            elif strat == "view_file":
                units.append(extract_file_unit(rel_path, source, "view_file", id_factory))
            elif strat == "config_file":
                units.append(extract_file_unit(rel_path, source, "config_file", id_factory))
            elif strat == "style_file":
                units.append(extract_file_unit(rel_path, source, "style_file", id_factory))
            elif strat == "sql_file":
                units.append(extract_file_unit(rel_path, source, "sql_file", id_factory))

    # Statistics
    by_kind: dict[str, int] = {}
    for u in units:
        by_kind[u.kind] = by_kind.get(u.kind, 0) + 1

    return {
        "schema_version": "0.1.0",
        "target_root": target_path.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "files_scanned": files_scanned,
            "files_excluded": files_excluded,
            "units_total": len(units),
            "by_kind": by_kind,
        },
        "units": [
            {
                "id": u.id,
                "path": u.path,
                "line_range": list(u.line_range),
                "kind": u.kind,
                "name": u.name,
                "signature": u.signature[:240],  # truncate overly long lines
                "fingerprint": u.fingerprint,
            }
            for u in units
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cc-rsg source map extractor")
    parser.add_argument("--target", required=True, help="Target codebase root (directory)")
    parser.add_argument(
        "--output",
        default=".cc-rsg/source-map.json",
        help="Output path for source-map.json",
    )
    parser.add_argument(
        "--exclude-globs",
        default=",".join(DEFAULT_EXCLUDES),
        help="Comma-separated glob patterns to exclude",
    )
    args = parser.parse_args(argv)

    target_path = Path(args.target).resolve()
    if not target_path.is_dir():
        print(f"ERROR: target not a directory: {target_path}", file=sys.stderr)
        return 2

    exclude_globs = [g.strip() for g in args.exclude_globs.split(",") if g.strip()]
    out = build_source_map(target_path, exclude_globs)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    stats = out["stats"]
    print(
        f"source-map.py: {stats['units_total']} units extracted from "
        f"{stats['files_scanned']} files (excluded: {stats['files_excluded']}). "
        f"Written to {output_path}"
    )
    print(f"  by kind: {stats['by_kind']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

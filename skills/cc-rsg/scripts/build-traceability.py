#!/usr/bin/env python3
"""
cc-rsg build-traceability.py

`.cc-rsg/trace.json` を読み込み、人間が読める `final/traceability.md`
（または `drafts/traceability.md`）を自動生成する。

これにより:
- 章 → ソース対応表
- ソース → 章対応表
- MECE 検査結果（カバー率・除外内訳）

をユーザーが Markdown 1 枚で確認できる。手書きさせない。

使い方:
    python build-traceability.py --cc-rsg-dir .cc-rsg --output-dir final
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cc-rsg traceability.md generator")
    parser.add_argument("--cc-rsg-dir", default=".cc-rsg")
    parser.add_argument(
        "--output-dir",
        default="final",
        choices=["drafts", "final"],
        help="Where to write traceability.md (drafts/ or final/)",
    )
    args = parser.parse_args(argv)

    cc_rsg = Path(args.cc_rsg_dir)
    trace_path = cc_rsg / "trace.json"
    if not trace_path.exists():
        print(
            f"ERROR: {trace_path} not found. Run scripts/build-trace.py first.",
            file=sys.stderr,
        )
        return 2

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    output_path = cc_rsg / args.output_dir / "traceability.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = trace["source_units_total"]
    covered = trace["source_units_covered"]
    excluded = trace["source_units_excluded"]
    uncovered = trace["source_units_uncovered"]
    mece_ok = trace["mece_passed"]
    coverage_rate = (covered / total * 100) if total else 0.0

    lines: list[str] = []
    lines.append("# Traceability")
    lines.append("")
    lines.append(
        f"<!-- 自動生成: {datetime.now(timezone.utc).isoformat()} | source: trace.json -->"
    )
    lines.append("")
    lines.append("## MECE 検査結果")
    lines.append("")
    lines.append(f"- 抽出されたソースユニット総数: **{total}**")
    lines.append(f"- 仕様書でカバー: **{covered} ({coverage_rate:.1f}%)**")
    lines.append(f"- 明示的除外: **{excluded}**")
    status_mark = "✅ PASSED" if mece_ok else "❌ FAILED"
    lines.append(f"- 未カバー: **{uncovered}** {status_mark}")
    lines.append("")

    if uncovered:
        lines.append("### 未カバー一覧（要対応）")
        lines.append("")
        lines.append("| SRC ID | パス | 行範囲 | kind | name |")
        lines.append("|--------|------|--------|------|------|")
        for sid in trace.get("uncovered_units", []):
            u = trace["by_source"].get(sid, {})
            lr = u.get("line_range", [0, 0])
            lines.append(
                f"| {sid} | `{u.get('path','')}` | {lr[0]}-{lr[1]} | "
                f"{u.get('kind','')} | {u.get('name','')} |"
            )
        lines.append("")

    # 除外内訳
    excluded_units = [
        (sid, u) for sid, u in trace["by_source"].items() if u.get("excluded")
    ]
    if excluded_units:
        lines.append("### 明示的除外内訳")
        lines.append("")
        lines.append("| SRC ID | パス | 除外理由 |")
        lines.append("|--------|------|---------|")
        for sid, u in excluded_units:
            reason = u.get("excluded_reason") or "(no reason given)"
            lines.append(f"| {sid} | `{u.get('path','')}` | {reason} |")
        lines.append("")

    # 章 → ソース対応表
    lines.append("## 章 → ソース対応表")
    lines.append("")
    by_section = trace.get("by_section", {})
    if by_section:
        # ファイル名と セクション名 でグループ化
        sections_by_file: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
        for key, src_ids in by_section.items():
            if "::" in key:
                file_name, section = key.split("::", 1)
            else:
                file_name, section = key, "(no section)"
            sections_by_file[file_name].append((section, src_ids))

        for file_name in sorted(sections_by_file):
            lines.append(f"### {file_name}")
            lines.append("")
            for section, src_ids in sections_by_file[file_name]:
                src_descs = []
                for sid in src_ids[:50]:  # 章あたり50件まで
                    u = trace["by_source"].get(sid, {})
                    lr = u.get("line_range", [0, 0])
                    p = u.get("path", "")
                    src_descs.append(f"{sid} (`{Path(p).name}:{lr[0]}-{lr[1]}`)")
                more = f" ... 他 {len(src_ids)-50} 件" if len(src_ids) > 50 else ""
                lines.append(f"- **{section}** — {', '.join(src_descs)}{more}")
            lines.append("")
    else:
        lines.append("_(参照が記録されていません)_")
        lines.append("")

    # ソース → 章対応表
    lines.append("## ソース → 章対応表（ファイル別）")
    lines.append("")
    by_source = trace.get("by_source", {})
    grouped_by_path: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for sid, u in by_source.items():
        grouped_by_path[u.get("path", "")].append((sid, u))

    for path in sorted(grouped_by_path):
        sids = grouped_by_path[path]
        # 全 SRC が covered_by_sections 空かつ excluded ならスキップ表示
        all_empty = all(
            not u.get("covered_by_sections") and not u.get("excluded")
            for _, u in sids
        )
        if all_empty and len(sids) > 0:
            continue
        lines.append(f"### `{path}`")
        lines.append("")
        for sid, u in sorted(sids, key=lambda x: x[1].get("line_range", [0, 0])[0]):
            lr = u.get("line_range", [0, 0])
            name = u.get("name", "")
            kind = u.get("kind", "")
            covered_by = u.get("covered_by_sections", [])
            if covered_by:
                where = ", ".join(
                    f"{c.get('file','')} §{c.get('section','')}" for c in covered_by[:5]
                )
                more = f" (他 {len(covered_by)-5}件)" if len(covered_by) > 5 else ""
                lines.append(
                    f"- **{sid}** ({kind} `{name}` lines {lr[0]}-{lr[1]}) → {where}{more}"
                )
            elif u.get("excluded"):
                lines.append(
                    f"- ~~{sid}~~ ({kind} `{name}` lines {lr[0]}-{lr[1]}) "
                    f"— **除外**: {u.get('excluded_reason','')}"
                )
            else:
                lines.append(
                    f"- ⚠️ **{sid}** ({kind} `{name}` lines {lr[0]}-{lr[1]}) — **未カバー**"
                )
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"build-traceability.py: written to {output_path} "
        f"(mece_passed={mece_ok}, coverage={coverage_rate:.1f}%)"
    )
    return 0 if mece_ok else 1


if __name__ == "__main__":
    sys.exit(main())

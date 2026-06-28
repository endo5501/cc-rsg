# cc-rsg — Codebase Reverse Specification Generator

> A runtime-neutral Agent Skill that reconstructs auditable specifications from
> existing codebases.

[日本語](#日本語)

`cc-rsg` works with Claude Code, Codex, and compatible Agent Skills runtimes.
It generates maintenance, onboarding, delivery, modernization, and audit
specifications in the "code → spec" direction.

The workflow prioritizes:

- **Honesty:** mark inferences and unresolved intent instead of inventing facts.
- **Traceability:** attach exact source paths and line ranges to claims.
- **Completeness:** inventory source units and verify coverage mechanically.
- **Progressive refinement:** recon → plan → investigate → verify → refine.
- **Resumability:** persist long-running work below `.cc-rsg/`.

## Installation

Install interactively with the Skills CLI:

```bash
npx skills add endo5501/cc-rsg
```

Install globally for both Claude Code and Codex:

```bash
npx skills add endo5501/cc-rsg \
  --skill cc-rsg \
  --global \
  --agent claude-code \
  --agent codex
```

List the skill without installing it:

```bash
npx skills add endo5501/cc-rsg --list
```

### Manual fallback

For a runtime that cannot use the Skills CLI, copy the skill directory into
that runtime's project- or user-level skill location:

```bash
cp -r skills/cc-rsg <runtime-skill-directory>/cc-rsg
```

## Usage

Invoke `cc-rsg` in the target repository and follow the phase reviews:

1. Confirm target, language, goal, and execution mode.
2. Review reconnaissance and select a template and depth.
3. Review inventory and the chapter WBS.
4. Generate evidence-backed chapters.
5. Verify coverage, traceability, and consistency.
6. Resolve Question Bank items with the user.
7. Audit and deliver the final specification.

### Execution mode

Chapter investigation is sequential by default:

```json
{
  "execution_mode": "sequential"
}
```

Select `parallel` explicitly during Phase 0 to authorize independent chapter
delegation when the current runtime supports subagents. If it does not, cc-rsg
records the fallback and continues sequentially with the same quality gates.

### Output language

English is the default. Select Japanese in Phase 0 to render dialogue and
deliverable prose in Japanese. Paths, IDs, JSON keys, enum values, and
traceability markers remain in English.

## Outputs

The target project receives:

```text
.cc-rsg/
├── state.json
├── goal.json
├── recon-report.md
├── inventory.json
├── wbs.json
├── questions.json
├── drafts/
└── final/
```

The final specification always includes metadata, unresolved items, and a
traceability index.

## Depth modes

| Mode | Intended use | Output |
|---|---|---|
| `comprehensive` | audits and detailed maintenance | evidence-rich prose chapters |
| `outline` | large codebases and general understanding | inventory tables and deep-dive candidates |
| `interactive` | iterative team reference | outline plus requested deep dives |

## Bundled coverage

Inventory guidance includes PHP, COBOL/JCL, Python, Java/Kotlin,
JavaScript/TypeScript, C#, Go, Dart/Flutter, Ruby on Rails, Flask, FastAPI,
Next.js, Expo, and React Native patterns. `source-map.py` extracts Ruby,
Python, JavaScript/TypeScript, Dart, and C/C++ units directly, and records every
other recognised source file (Swift, Kotlin, Rust, Go, and more) as a coarse
file-level unit so the coverage and MECE checks work on any stack. C/C++ has an
optional high-fidelity mode: with `pip install libclang` and a
`compile_commands.json` (e.g. CMake's `CMAKE_EXPORT_COMPILE_COMMANDS=ON`), pass
`--compile-commands` to parse via libclang; it falls back to regex when absent.

Bundled templates:

- Web application
- Batch system
- API service
- Library or SDK
- Desktop / mobile GUI application

## Runtime portability

The shared workflow uses capability-oriented instructions. Runtime mappings are
isolated in:

- `skills/cc-rsg/references/runtime-claude-code.md`
- `skills/cc-rsg/references/runtime-codex.md`

The authoritative per-chapter procedure is:

- `skills/cc-rsg/references/chapter-investigator-prompt.md`

No product-specific worker type is required.

## Design heritage

The design draws from KDM (ISO/IEC 19506:2012), Architecture-Driven
Modernization, model-driven reverse engineering, and deterministic
inventory-plus-LLM documentation systems.

Preprint: https://zenodo.org/records/20541685

## License

MIT License. See [LICENSE](LICENSE).

---

## 日本語

`cc-rsg` は、既存コードベースから監査可能な仕様書を再構築する、
Claude Code・Codex対応のランタイム中立Agent Skillです。

### インストール

```bash
npx skills add endo5501/cc-rsg
```

Claude CodeとCodexの両方へグローバルインストールする場合:

```bash
npx skills add endo5501/cc-rsg \
  --skill cc-rsg \
  --global \
  --agent claude-code \
  --agent codex
```

Skills CLIを利用できない環境では、手動コピーをフォールバックとして利用できます。

```bash
cp -r skills/cc-rsg <runtime-skill-directory>/cc-rsg
```

### 実行方式

標準はメインエージェントによる逐次調査です。Phase 0で`parallel`を明示選択
した場合のみ、対応ランタイムで章単位のサブエージェントを利用します。
並列機能が利用できない場合は、理由を状態へ記録して逐次処理へ戻ります。

### 特徴

- 推測・仮定・未解決事項を明示
- 全記述にソースファイルと行番号を付与
- インベントリによる抜け漏れ検証
- Phase単位のレビューとループバック
- `.cc-rsg/state.json`による中断・再開
- 英語・日本語出力

最終成果物は`.cc-rsg/final/`へ出力され、メタデータ、未確定事項、
トレーサビリティ表を必ず含みます。

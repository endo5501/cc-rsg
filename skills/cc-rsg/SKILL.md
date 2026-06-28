---
name: cc-rsg
description: Reverse-engineer auditable specification documents from existing codebases through goal definition, inventory-driven investigation, traceable evidence, verification, and question-bank refinement. Use when an agent must reconstruct maintenance, delivery, architecture, API, batch, library, or system specifications from source code.
---

# cc-rsg — Codebase Reverse Specification Generator

Generate honest, traceable specifications from an existing codebase. Treat
source code as evidence, not as proof of business intent. Persist progress so a
long-running analysis can pause and resume safely.

## Runtime contract

Identify the current host from the capabilities available in the session, then
read exactly one adapter:

- Claude Code: `references/runtime-claude-code.md`
- Codex: `references/runtime-codex.md`

If the runtime is unknown, use the portable sequential workflow.

In shared instructions:

- inspect files with the host's available file-reading capability;
- search with the host's available repository-search capability;
- edit artifacts with the host's available file-editing capability;
- ask through the host's available interaction mechanism;
- prefer structured choices when available and use numbered text otherwise;
- consult official external documentation only when web access is available;
- delegate only when `goal.json.execution_mode == "parallel"`, the user
  explicitly selected it, and the runtime supports delegation.

Never bypass host permissions. If a capability is unavailable, follow the
fallback documented by the current phase.

## Language contract

English is the skill bundle's base language. At Phase 0, confirm
`goal.json.output_language` as `"en"` or `"ja"`. Render all subsequent
natural-language dialogue and deliverable prose in that language.

Keep these elements in English:

- JSON keys and enum values;
- ASCII file slugs and IDs such as `INV-001` and `Q-001`;
- `[REF: path:line]`, `[CONFIDENCE: HIGH|MED|LOW]`, `[ASK SME]`,
  `[ASSUMED: ...]`, and `[BLOCKED: ...]`;
- the literal heading `## Sources Read`.

Emit raw UTF-8. Never put `\uXXXX` escapes into user-visible question text.

## Core principles

1. **Goal-driven:** persist scope, audience, depth, perspectives, language, and
   execution mode before investigation.
2. **Evidence-first:** inspect real files before citing them.
3. **Inventory-backed completeness:** enumerate code units and verify coverage
   mechanically.
4. **Honest uncertainty:** distinguish facts, inferences, assumptions, and
   blocked sections.
5. **Traceability:** attach an exact `[REF: path:line]` or
   `[REF: path:start-end]` to every source-derived statement.
6. **Progressive refinement:** reconnaissance precedes planning, chapter work,
   verification, dialogue, and delivery.
7. **Resumability:** persist phase state and outputs after every bounded unit.
8. **Outcome-based gates:** verify persisted artifacts and user outcomes, not
   whether a particular host tool was called.

## Phase workflow

Read and execute one phase reference at a time:

1. `references/phase-0-setup.md`
2. `references/phase-1-recon.md`
3. `references/phase-2-plan.md`
4. `references/phase-3-investigate.md`
5. `references/phase-4-verify.md`
6. `references/phase-5-refine.md`
7. `references/phase-6-deliver.md`

Do not advance until the current phase's persistence and user-review gates
pass.

| Phase | Name | Required result |
|---|---|---|
| 0 | Setup & Goal | `.cc-rsg/goal.json`, initial `state.json` |
| 1 | Recon & Template | `recon-report.md`, selected template and depth |
| 2 | Plan & WBS | `inventory.json`, `wbs.json`, draft skeleton |
| 3 | Investigate | non-empty chapter drafts with evidence |
| 4 | Verify | coverage and consistency checks pass or loop back |
| 5 | Refine | persisted dialogue outcomes and resolved questions |
| 6 | Deliver | audited final specification and traceability |

## Shared state

Store runtime state below the target project root:

```text
.cc-rsg/
├── state.json
├── goal.json
├── recon-report.md
├── inventory.json
├── wbs.json
├── questions.json
├── drafts/
│   ├── 00-metadata.md
│   ├── 01-overview.md
│   ├── ...
│   ├── 99-unresolved.md
│   └── traceability.md
└── final/
    ├── 00-metadata.md
    ├── 01-overview.md
    ├── ...
    ├── 99-unresolved.md
    ├── traceability.md
    └── README.md
```

Use this minimum `state.json` shape:

```json
{
  "current_phase": 0,
  "phase_progress": {},
  "started_at": "ISO-8601 timestamp",
  "last_updated": "ISO-8601 timestamp",
  "session_history": []
}
```

Append phase transitions, fallbacks, rollbacks, and completion events to
`session_history`. Never infer completion from conversation history alone.

## Question Bank

Store questions in `.cc-rsg/questions.json`:

```json
{
  "id": "Q-001",
  "generated_at_phase": "investigation",
  "category": "business_rule",
  "body": "Question rendered in output_language",
  "evidence": {
    "file": "src/example.py",
    "lines": "10-18",
    "code_excerpt": "short excerpt"
  },
  "related_inventory_ids": ["INV-001"],
  "severity": "important",
  "resolution_type": "ask_sme",
  "status": "open",
  "answer": null,
  "answerer": null,
  "answered_at": null,
  "related_question_ids": []
}
```

Standard categories are `business_rule`, `architecture_decision`,
`data_model_intent`, `external_integration`, `naming_history`,
`operational_requirement`, and `security_compliance`. Read
`references/question-categories.md` when classifying or normalising questions.

Severity controls investigation:

- `critical`: leave the affected section `[BLOCKED: see Q-NNN]`;
- `important`: continue with `[CONFIDENCE: LOW]` and an explicit assumption;
- `nice-to-have`: continue with best evidence and confirm during refinement.

Allowed status flow:

```text
open -> asked -> answered
              -> abandoned
```

Record abandoned questions in `99-unresolved.md`.

## Source and confidence contracts

Every generated chapter must end with:

```markdown
## Sources Read

- `path/to/source.ext`
```

Never cite a file that was not inspected. Keep code excerpts short and use them
only when they support the associated claim.

For outline and interactive depth, label table claims:

- `🟢 VERIFIED`: confirmed in inspected source;
- `🟡 INFERRED`: supported by multiple source signals;
- `🔴 ASSUMED`: plausible but not established.

## Mermaid contract

Mermaid diagrams are structure-only. Do not emit hardcoded colors, `fill`,
`stroke`, `classDef`, color-bearing `style`, or color-bearing `linkStyle`.
Shapes, directions, subgraphs, edge types, and edge labels are allowed.

## Bundled resources

Read only resources needed for the current phase:

- `references/inventory-units.md`: stack-specific inventory units.
- `references/outline-tables.md`: outline-mode table patterns.
- `references/template-catalog.md`: template selection.
- `references/question-categories.md`: Question Bank classification.
- `references/verification-checklists.md`: Phase 4 quality checks.
- `references/subagent-prompt.md`: compatibility note for older integrations.
- `references/chapter-investigator-prompt.md`: authoritative chapter workflow.
- `templates/web-app.md`: web application specification.
- `templates/batch-system.md`: batch specification.
- `templates/api-service.md`: API specification.
- `templates/library-sdk.md`: library or SDK specification.
- `templates/gui-app.md`: desktop / mobile GUI application specification.

Bundled deterministic scripts:

- `scripts/source-map.py`
- `scripts/build-trace.py`
- `scripts/build-traceability.py`
- `scripts/coverage-check.py`

Use the active runtime adapter to select an available Python launcher.

## Hard delivery rules

- Never present an inference as an established fact.
- Never omit `00-metadata.md`, `99-unresolved.md`, or `traceability.md`.
- Never silently drop a user-requested custom deliverable.
- Never mark a phase complete when its required files are missing or empty.
- Never advance past a review gate without recording the user's decision.
- Never require parallel execution for full-quality output.

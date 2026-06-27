# Phase 3 — Chapter Investigation

## Purpose

Investigate every assigned inventory item and produce evidence-backed chapter
drafts.

## Execution strategy

Read `goal.json.execution_mode`; use `sequential` when the field is absent.

### Sequential

Apply `chapter-investigator-prompt.md` directly in the main agent, one chapter
at a time. Persist chapter status, questions, and timestamps after every
chapter.

### Parallel

Use this path only when the user explicitly selected `parallel` and the active
runtime adapter confirms delegation support. Render one independent prompt per
chapter from `chapter-investigator-prompt.md`.

Workers write chapter files directly and return only:

- output path;
- short summary;
- questions raised;
- completion or blocked status.

Use bounded batches that respect the host limit. Wait for the current batch and
persist results before launching another.

If delegation is unavailable, append a fallback event with the reason to
`state.json.session_history` and continue sequentially. Do not lower quality
requirements.

## Comprehensive chapters

For each assigned inventory item:

1. inspect the real source;
2. trace direct callers, callees, data structures, errors, and configuration;
3. write only claims supported by evidence;
4. attach strict source references;
5. register uncertainties in `questions.json`;
6. end with `## Sources Read`.

Each standard comprehensive chapter should contain at least 200 lines, 10
strict `[REF:]` markers, one structure-only Mermaid diagram, and five inspected
sources where the codebase provides enough evidence. Record justified
exceptions rather than inventing padding.

## Outline and interactive chapters

Build stack-appropriate Layer 1 and Layer 2 inventory tables using
`outline-tables.md`. Label every source-derived table cell as VERIFIED,
INFERRED, or ASSUMED.

Add deep-dive candidates based on:

- high ASSUMED density;
- high complexity;
- business-critical areas such as authentication, authorization, payment,
  permissions, data loss, and external delivery.

## Uncertainty

- Critical: write `[BLOCKED: see Q-NNN]` for the affected section.
- Important: write `[CONFIDENCE: LOW]` and `[ASSUMED: ...; basis: ...]`.
- Nice-to-have: use best evidence and register the question.

Never conflate inference with fact.

## Progression gate

Before Phase 3 completes:

- every WBS chapter, including custom and reserved files, has at least 10
  non-blank lines unless its phase is intentionally later;
- every assigned inventory ID is represented;
- each written chapter contains `## Sources Read`;
- questions are merged into `questions.json`;
- WBS statuses and `state.json` are current.

Advance to Phase 4 only after all chapter work is complete or explicitly
blocked.

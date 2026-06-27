# Mode B — Manifest relay

Mode B is an optional context optimisation for explicitly selected parallel
execution. It changes result relay, not chapter quality or evidence rules.

## Preconditions

Use Mode B only when:

- `goal.json.execution_mode == "parallel"`;
- the user explicitly selected parallel execution;
- `goal.json.context_optimization_mode == "B"`;
- the active runtime adapter confirms delegation support.

Otherwise use the sequential workflow in `phase-3-investigate.md`.

## Dispatch

Render one independent assignment from
`references/chapter-investigator-prompt.md` per chapter. The worker writes the
chapter body to its assigned draft path and returns only path, status, summary,
and questions.

Use bounded batches. Persist every completed result before starting another
batch.

## Manifest

Append one row per result to `.cc-rsg/state/manifest.md`:

```markdown
| chapter_id | path | status | summary | question_ids | updated_at |
|---|---|---|---|---|---|
| CH-03 | drafts/03-data.md | complete | Data model mapped | Q-012 | ISO-8601 |
```

Use the manifest as the first entry point for later cross-chapter work. Inspect
a full chapter only when verification, consistency analysis, refinement, or
delivery requires it.

If a worker fails to create its output file, mark the chapter failed and retry
under the Phase 4 loopback rules.

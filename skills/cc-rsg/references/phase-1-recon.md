# Phase 1 — Reconnaissance and Template Selection

## Purpose

Build a shallow, evidence-backed map of the codebase before committing to a
document structure.

## Reconnaissance

Inspect repository metadata and representative entry points:

- top-level directories and file counts;
- languages, frameworks, package manifests, build files, and lock files;
- application, API, batch, CLI, worker, and library entry points;
- configuration and environment samples;
- persistence, migrations, schemas, queues, and external integrations;
- existing documentation and tests;
- deployment and operational assets.

Do not deeply analyse every implementation in this phase. Record inspected
paths and unresolved high-level questions in the Question Bank.

Write `.cc-rsg/recon-report.md` with:

1. scope and exclusions;
2. repository size and stack;
3. system shape and likely entry points;
4. major components and data stores;
5. external systems;
6. operational evidence;
7. risks and unknowns;
8. candidate templates;
9. candidate depth mode;
10. `## Sources Read`.

Every source-derived statement needs a strict `[REF: path:line]` or
`[REF: path:start-end]`.

## Template selection

Read `template-catalog.md` and present:

1. a user-provided template, when supplied;
2. an agent-recommended bundled template;
3. a user-adjusted version of the recommendation.

Bundled templates:

- `templates/web-app.md`
- `templates/batch-system.md`
- `templates/api-service.md`
- `templates/library-sdk.md`

Show the proposed chapter outline and ask the user to add, remove, or rename
chapters. The user's confirmed choice wins.

## Depth selection

Select one:

- `comprehensive`: full chapter prose and exhaustive evidence;
- `outline`: inventory tables, diagrams, and deep-dive candidates;
- `interactive`: outline output followed by on-demand deep dives.

For more than 200 source files, present all three choices and recommend
`outline`. For smaller codebases, recommend `comprehensive` but still honour an
explicit alternative.

Persist the selected template, confirmed outline, and `depth_mode` in
`goal.json`.

## Completion gate

Phase 1 completes only when:

- `recon-report.md` is non-empty and contains `## Sources Read`;
- high-level questions are appended to `questions.json`;
- the user confirmed template, chapter outline, and depth;
- the decision is persisted;
- `state.json.current_phase` advances to `2`.

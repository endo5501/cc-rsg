# Phase 4 — Verification

## Purpose

Mechanically and semantically verify completeness, traceability, consistency,
and deliverable intent.

## Deterministic checks

Run the bundled scripts with the launcher selected by the runtime adapter:

1. `scripts/build-trace.py`
2. `scripts/build-traceability.py`
3. `scripts/coverage-check.py`

Use `verification-checklists.md` for manual checks not encoded by scripts.

Verify:

- all inventory IDs appear in the intended drafts;
- every `[REF:]` uses `path:line` or `path:start-end`;
- referenced paths and line ranges exist;
- chapters contain `## Sources Read`;
- chapters meet their selected depth contract;
- Mermaid source has no hardcoded colors;
- WBS, inventory, trace data, and actual files agree;
- question IDs are unique and references resolve;
- all custom deliverables exist and have substantive content;
- reserved files exist;
- terminology and cross-chapter facts are consistent.

## Loopback

For a failing standard chapter:

1. record the failed checks;
2. return the chapter to Phase 3;
3. re-investigate only the affected scope;
4. rerun checks.

Allow at most three repair iterations. After that, record unresolved quality
issues in `99-unresolved.md`.

For a failing user-custom deliverable, never demote it silently. Ask whether to
retry, reduce scope, or explicitly abandon it. Persist the decision.

## Consistency questions

When two sources or chapters disagree, add a Question Bank item with both
pieces of evidence. Do not choose the more convenient interpretation.

## Completion gate

Phase 4 completes only when:

- deterministic checks pass or every exception is explicitly recorded;
- no inventory item is silently uncovered;
- every user-custom deliverable is present or explicitly abandoned;
- consistency questions are persisted;
- `state.json.current_phase` advances to `5`.

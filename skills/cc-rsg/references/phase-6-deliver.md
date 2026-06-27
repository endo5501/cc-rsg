# Phase 6 — Delivery

## Purpose

Audit the promised outputs, assemble final files, and report unresolved facts
without disguising them.

## Intent-versus-delivery audit

Before copying drafts, compare:

- `goal.json` requirements;
- confirmed template and WBS;
- `user_custom_deliverables`;
- actual draft files;
- Phase 4 results;
- Question Bank status.

Every promised file must exist with substantive content. If source evidence
cannot support a promised custom deliverable, ask for explicit permission to
drop or reduce it. Record opt-outs in state.

## Required final files

Populate:

- `00-metadata.md`: target revision, generation date, goal, scope, depth,
  language, execution mode, and limitations;
- `99-unresolved.md`: blocked, abandoned, conflicting, and insufficient-quality
  items;
- `traceability.md`: chapter and claim mapping to exact sources;
- every standard and custom chapter;
- `README.md`: document index and reading guidance.

Copy verified drafts into `.cc-rsg/final/`. Rebuild traceability after the copy
and rerun `coverage-check.py` against final output.

## Final audit

Confirm:

- no required file is missing or empty;
- all strict references resolve;
- no unresolved marker was silently removed;
- no Mermaid color rule is violated;
- custom deliverables match the confirmed names;
- final metadata identifies the analysed revision;
- final and draft inventories agree.

## Completion report

Report:

- final output path;
- chapter count;
- resolved and unresolved question counts;
- delivered custom filenames;
- recorded limitations and opt-outs.

Mark `state.json` complete only after the final audit passes.

## Interactive deep dives

For `outline` or `interactive` depth, remain available for explicit deep-dive
requests after delivery. Generate a deep-dive only when the user requests a
candidate, entity, or topic.

Use sequential investigation by default. Delegation remains permitted only
when `execution_mode` is `parallel` and the runtime supports it. Write deep
dives below `.cc-rsg/drafts/deep/`, append traceability, update confidence in
the originating overview, and rebuild final output when the user ends the
deep-dive session.

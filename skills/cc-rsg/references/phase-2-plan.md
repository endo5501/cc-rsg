# Phase 2 — Inventory, Skeleton, and WBS

## Purpose

Turn reconnaissance into an exhaustive inventory and a chapter-level work
breakdown.

## Inventory

Read the applicable sections of `inventory-units.md` and
`outline-tables.md`. Enumerate source units appropriate to the detected stack,
including entry points, domain types, handlers, persistence units, routes,
jobs, integrations, configuration, views, and tests.

Write `.cc-rsg/inventory.json`. The canonical shape is an object with a
`units` array; `scripts/coverage-check.py` reads `type` and `covered_by`:

```json
{
  "units": [
    {
      "id": "INV-001",
      "type": "service",
      "name": "Example",
      "file": "src/example.py",
      "line": 1,
      "chapter_id": "CH-02",
      "covered_by": [],
      "status": "planned"
    }
  ]
}
```

`covered_by` lists the chapter files that document the unit (filled during
Phase 4). `related_source_ids` is optional free-form provenance; the MECE check
does not read it — `scripts/build-trace.py` matches the `[REF: path:Lx-Ly]`
markers written in chapters against `source-map.json` instead.

Inventory IDs are stable for the run. Do not silently discard unknown units;
classify them as `other` and assign them to a chapter or unresolved section.

Use `scripts/source-map.py` when it supports the detected stack. For stacks
without a dedicated extractor it records each recognised source file as a
coarse file-level unit, so the MECE chain still works; supplement it with
repository search where finer granularity is required. Only if `source-map.py`
yields **zero** units should you hand-generate a file-level `source-map.json`
(one unit per source file, `line_range: [1, N]`) before running
`build-trace.py`.

## Chapter skeleton

Create `.cc-rsg/drafts/` and empty chapter files in confirmed order. Reserve:

- `00-metadata.md`;
- `99-unresolved.md`;
- `traceability.md`.

Add every `goal.json.user_custom_deliverables` entry as a real chapter. Never
replace a promised file with a note in `99-unresolved.md`.

Standard chapter names follow `NN-ascii-slug.md`. Custom deliverables retain
the user-confirmed safe relative Markdown filename.

## WBS

Write `.cc-rsg/wbs.json`:

```json
{
  "chapters": [
    {
      "id": "CH-01",
      "file_name": "01-overview.md",
      "title": "Overview",
      "kind": "standard",
      "assigned_inventory_ids": ["INV-001"],
      "status": "pending"
    }
  ]
}
```

Each inventory item must belong to at least one chapter. Keep assignments small
enough that one chapter can be investigated independently.

Use `kind` values:

- `reserved`
- `standard`
- `user_custom`

## User review

Present:

- inventory counts by unit type;
- unassigned or ambiguous units;
- chapter order and titles;
- inventory coverage per chapter;
- custom deliverables.

Apply requested corrections before proceeding.

## Completion gate

Phase 2 completes only when:

- every inventory ID is assigned;
- every WBS chapter has a real output filename;
- reserved and custom deliverables exist in the WBS;
- the user approved the WBS;
- `state.json.current_phase` advances to `3`.

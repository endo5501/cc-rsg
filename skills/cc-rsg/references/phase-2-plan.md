# Phase 2 — Inventory, Skeleton, and WBS

## Purpose

Turn reconnaissance into an exhaustive inventory and a chapter-level work
breakdown.

## Inventory

Read the applicable sections of `inventory-units.md` and
`outline-tables.md`. Enumerate source units appropriate to the detected stack,
including entry points, domain types, handlers, persistence units, routes,
jobs, integrations, configuration, views, and tests.

Write `.cc-rsg/inventory.json`:

```json
[
  {
    "id": "INV-001",
    "unit_type": "module",
    "name": "Example",
    "file": "src/example.py",
    "lines": "1-120",
    "chapter_id": "CH-02",
    "status": "planned"
  }
]
```

Inventory IDs are stable for the run. Do not silently discard unknown units;
classify them as `other` and assign them to a chapter or unresolved section.

Use `scripts/source-map.py` when it supports the detected stack. Supplement it
with repository search where required.

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

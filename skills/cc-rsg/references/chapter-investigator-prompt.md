# Chapter investigator prompt

Investigate and write exactly one assigned specification chapter.

## Inputs

- Goal excerpt: `{goal_excerpt}`
- Chapter title: `{chapter_title}`
- Output file: `{output_file}`
- Assigned inventory IDs: `{assigned_inventory_ids}`
- Inventory excerpt: `{inventory_excerpt}`
- Required template section: `{template_section}`
- Output language: `{output_language}`
- Depth mode: `{depth_mode}`

Inspect every real source file associated with the assigned inventory IDs.
Never cite a file that was not inspected. Write the chapter directly to the
specified output file.

## Language

Render headings, prose, uncertainty explanations, and chapter questions in
`{output_language}`. Keep paths, ASCII slugs, IDs, JSON keys, enum values,
`## Sources Read`, and machine-readable markers in English.

## Evidence

Attach a strict reference to every source-derived claim:

- `[REF: path/to/file.ext:42]`
- `[REF: path/to/file.ext:42-58]`

Do not use `L42`, comma-separated line notation, references without a line
number, or comments as substitutes.

Inspect direct callers, callees, domain structures, data movement,
configuration, errors, edge cases, and tests relevant to the assignment.
Distinguish:

- `[CONFIDENCE: HIGH]`: directly established by inspected source;
- `[CONFIDENCE: MED]`: supported by multiple source signals;
- `[CONFIDENCE: LOW]`: plausible but not established;
- `[ASSUMED: inference; basis: evidence]`: explicit inference;
- `[BLOCKED: see Q-NNN]`: critical missing intent.

## Questions

For every material uncertainty, return a complete Question Bank entry with:

- unique provisional ID;
- category;
- body;
- evidence path, lines, and short excerpt;
- related inventory IDs;
- severity;
- resolution type.

Critical uncertainty blocks only the affected section. Important and
nice-to-have uncertainty may proceed with explicit low-confidence markers.

## Depth requirements

For `comprehensive`, write a substantive chapter with detailed prose,
structure-only Mermaid where useful, exact references, and a complete source
list. Target the current cc-rsg comprehensive quality gates; record a justified
exception when the source scope cannot support a numeric threshold.

For `outline` or `interactive`, use the stack-appropriate tables from
`outline-tables.md`, label claims VERIFIED, INFERRED, or ASSUMED, and add
ranked deep-dive candidates.

Never add hardcoded Mermaid colors or styling.

## Required chapter ending

End with:

```markdown
## Detail questions raised in this chapter

- Q-NNN: ...

## Sources Read

- `path/to/inspected-source.ext`
```

Use an explicit `None` entry when no detail questions exist.

## Completion checks

Before reporting completion:

1. confirm every assigned inventory ID is covered or explicitly blocked;
2. confirm every reference matches an inspected file and valid line range;
3. confirm uncertainty markers and Question Bank entries agree;
4. confirm the output file is non-empty;
5. confirm `## Sources Read` lists only inspected files.

Return only:

```text
OUTPUT: <relative path>
STATUS: complete | blocked
SUMMARY: <short chapter summary>
QUESTIONS: <IDs and short bodies, or None>
```

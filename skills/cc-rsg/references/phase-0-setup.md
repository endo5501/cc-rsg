# Phase 0 — Setup and Goal

## Purpose

Fix the target, output contract, and execution strategy before reading the
codebase deeply.

## Procedure

1. Confirm that the current directory is the target codebase root.
2. If `.cc-rsg/state.json` exists, read it and offer resume, rollback, detailed
   status, or full reset. Do not delete state without explicit confirmation.
3. Create `.cc-rsg/` when starting a new run.
4. Ask for output language bilingually. Map English to `"en"` and Japanese to
   `"ja"`. Default to `"en"` unless a host language hint or explicit answer
   selects Japanese.
5. Ask the five goal questions below in sequence.
6. Ask for execution mode.
7. Summarise all answers and obtain confirmation.
8. Write `goal.json`, `questions.json`, and `state.json` only after
   confirmation.

Use the host's interaction mechanism. Prefer structured single-choice controls;
otherwise present numbered choices and accept free-form input.

## Five goal questions

### Primary reader

- `maintenance_developer`
- `new_team_member`
- `end_customer`
- `auditor`
- free-form

### Specification purpose

- `maintenance`
- `modernization`
- `onboarding`
- `delivery`
- `audit`
- free-form

### Granularity

- `overview`
- `standard`
- `detailed`
- free-form

### Perspectives

Allow one or more of:

- `architecture`
- `business_rules`
- `data_model`
- `interfaces`
- `operations`
- `security`
- free-form

### Free-text requirements

Capture exclusions, target modules, required documents, prohibited content, and
named `*.md` deliverables. Store named Markdown deliverables in
`user_custom_deliverables`.

## Execution mode

Ask the user to select:

1. `sequential` (recommended): investigate chapters in the main agent.
2. `parallel`: explicitly authorize delegation of independent chapters when
   the runtime supports subagents.

Persist the result:

```json
{
  "execution_mode": "sequential"
}
```

If an existing `goal.json` has no `execution_mode`, interpret it as
`sequential`; do not require migration. A stored value of `parallel` is valid
only when it came from an explicit user selection.

## Goal schema

```json
{
  "output_language": "en",
  "primary_reader": "maintenance_developer",
  "purpose": "maintenance",
  "granularity": "standard",
  "perspectives": ["architecture", "business_rules"],
  "free_text_notes": "",
  "user_custom_deliverables": [],
  "execution_mode": "sequential"
}
```

Preserve free-form answers verbatim. Store machine-readable enum values in
English.

## Question text quality

- Emit raw UTF-8, never visible `\uXXXX` escapes.
- When writing Japanese, use standard Japanese characters and re-read every
  label before presenting it.
- If uncertain about a kanji, use hiragana rather than inventing a character.
- Keep JSON keys, IDs, enum values, paths, and machine markers in English.

## Completion gate

Phase 0 completes only when:

- the user confirmed the target root and goal summary;
- `goal.json` contains every required field;
- `execution_mode` is `sequential` or `parallel`;
- `questions.json` is an array;
- `state.json.current_phase` is updated to `1`;
- the transition is appended to `session_history`.

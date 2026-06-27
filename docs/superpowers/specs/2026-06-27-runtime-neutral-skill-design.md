# cc-rsg Runtime-Neutral Skill Design

## Goal

Make the existing `cc-rsg` Agent Skill installable and operational through
`npx skills add endo5501/cc-rsg` on both Claude Code and Codex without
maintaining separate copies of the workflow.

Preserve the current Phase 0-6 behavior, generated artifact contracts,
traceability requirements, resumability, and verification standards.

## Decisions

- Use one shared `cc-rsg` skill.
- Make sequential chapter investigation the default execution mode.
- Use parallel subagents only after the user explicitly selects parallel
  execution and the host runtime supports delegation.
- Describe operations as capabilities in shared instructions rather than by
  product-specific tool names.
- Keep runtime-specific mappings in reference files.
- Evaluate workflow completion from persisted outcomes rather than tool-call
  counts.
- Treat a missing `execution_mode` in existing sessions as `sequential`.

## Skill Structure

Keep `SKILL.md` as an orchestration entry point under 500 lines. Move detailed
phase procedures into directly linked reference files:

```text
skills/cc-rsg/
├── SKILL.md
├── references/
│   ├── phase-0-setup.md
│   ├── phase-1-recon.md
│   ├── phase-2-plan.md
│   ├── phase-3-investigate.md
│   ├── phase-4-verify.md
│   ├── phase-5-refine.md
│   ├── phase-6-deliver.md
│   ├── runtime-claude-code.md
│   ├── runtime-codex.md
│   └── chapter-investigator-prompt.md
├── scripts/
├── templates/
└── variants/
```

The entry point must tell the agent exactly when to read every phase and
runtime reference. Detailed requirements must have one authoritative
location.

## Frontmatter and Naming

Limit `SKILL.md` frontmatter to `name` and `description`. Remove the
Claude-specific `allowed-tools` list.

Rename the expanded product name from "Claude Code Reverse Spec Generator" to
"Codebase Reverse Specification Generator". Use "agent" for shared
instructions and product names only in runtime adapters and compatibility
documentation.

## Runtime Capability Abstraction

Shared instructions use capability-oriented language:

- Read and inspect an actual source file.
- Search the repository.
- Write or update a specified artifact.
- Ask the user through the host's available interaction mechanism.
- Consult official external documentation when web access is available.
- Delegate independent work only when explicitly authorized and supported.

`runtime-claude-code.md` maps these capabilities to Claude Code facilities.
`runtime-codex.md` maps them to Codex facilities. An unknown runtime uses the
portable sequential workflow.

Structured choice interfaces are preferred when available. Otherwise the
agent presents numbered choices in ordinary conversation and accepts
free-form input.

## Execution Mode

Persist the selected execution mode in `goal.json`:

```json
{
  "execution_mode": "sequential"
}
```

Supported values:

- `sequential`: the main agent investigates chapters one at a time.
- `parallel`: independent chapters may be delegated when supported.

Phase 0 asks the user to select the mode and recommends `sequential`. Selecting
`parallel` is explicit authorization to use subagents for this workflow.

If `parallel` is selected but delegation is unavailable, record the fallback
reason in state and continue sequentially. Both modes use identical artifact
and quality contracts.

## Chapter Investigator Prompt

Replace the runtime-specific chapter agent definition with
`references/chapter-investigator-prompt.md`. It is a plain prompt template with
no tool frontmatter and no named subagent type.

When parallel execution is active, the host adapter passes the rendered prompt
to a general delegation facility. In sequential mode, the main agent applies
the same investigation instructions directly.

## Outcome-Based Dialogue State

Replace checks such as "at least one AskUserQuestion call" with persisted
outcomes:

```json
{
  "phase_5": {
    "dialogue_rounds": 1,
    "questions_presented": ["Q-001"],
    "questions_answered": ["Q-001"]
  }
}
```

Phase 5 cannot complete unless:

- at least one dialogue round occurred;
- at least one question was presented;
- at least one answer was persisted; and
- the remaining open-question ratio satisfies the existing threshold.

## Compatibility and Error Handling

- Unknown runtime: use sequential execution.
- Missing `execution_mode`: interpret it as `sequential`.
- Missing structured question UI: use numbered text choices.
- Missing web access: do not invent external facts; record the uncertainty.
- Missing subagent capability: record the fallback and continue sequentially.
- Python launcher differences: detect `python3`, `python`, or `py -3` before
  invoking bundled scripts.

Existing `.cc-rsg` sessions must remain resumable without migration.

## Validation

Add automated portability and structure tests that verify:

- `SKILL.md` frontmatter contains only `name` and `description`;
- shared instructions do not require Claude-specific tools;
- `SKILL.md` remains under 500 lines;
- all referenced phase and runtime files exist;
- sequential execution is the documented default;
- parallel execution requires explicit user selection;
- Phase 5 uses persisted dialogue outcomes;
- the chapter investigator prompt is runtime-neutral;
- the Skills CLI discovers `cc-rsg`;
- bundled Python scripts compile successfully.

Update the repository README to lead with:

```bash
npx skills add endo5501/cc-rsg
```

Document explicit global installation for Claude Code and Codex while keeping
manual installation only as a fallback.

## Non-Goals

- Do not publish an npm package.
- Do not create separate Claude Code and Codex skill copies.
- Do not change generated specification formats or traceability semantics.
- Do not require parallel execution for full-quality output.
- Do not redesign the Phase 0-6 business workflow beyond runtime portability.

# cc-rsg Runtime-Neutral Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one `cc-rsg` Agent Skill operate on Claude Code and Codex, with sequential execution by default and explicitly authorized parallel delegation as an option.

**Architecture:** Reduce `SKILL.md` to a portable orchestration entry point and move the existing Phase 0-6 procedures into directly linked reference files. Express shared behavior as runtime capabilities, isolate Claude Code and Codex mappings in two adapters, and validate completion from persisted workflow outcomes instead of product-specific tool calls.

**Tech Stack:** Markdown Agent Skill, Python 3 standard-library `unittest`, existing Python 3 validation scripts, Vercel Skills CLI.

## Global Constraints

- Keep one shared skill at `skills/cc-rsg`; do not create runtime-specific skill copies.
- Keep `SKILL.md` below 500 lines and limit its YAML frontmatter to `name` and `description`.
- Default `goal.json.execution_mode` to `"sequential"`.
- Use subagents only when the user explicitly selects `"parallel"` and the runtime supports delegation.
- Preserve existing `.cc-rsg` sessions by treating a missing `execution_mode` as `"sequential"`.
- Preserve Phase 0-6 artifacts, traceability markers, quality gates, and resumability.
- Keep detailed references one link away from `SKILL.md`.
- Use only Python standard-library modules in the new test suite.

---

### Task 1: Add Failing Portability Contract Tests

**Files:**
- Create: `tests/test_skill_portability.py`
- Create: `tests/test_skill_scripts.py`

**Interfaces:**
- Consumes: the checked-out `skills/cc-rsg` directory.
- Produces: executable portability contracts invoked with `python -m unittest discover -s tests -v`.

- [ ] **Step 1: Write the failing skill structure and portability tests**

Create `tests/test_skill_portability.py`:

```python
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "cc-rsg"
SKILL = SKILL_ROOT / "SKILL.md"
REQUIRED_REFERENCES = {
    "phase-0-setup.md",
    "phase-1-recon.md",
    "phase-2-plan.md",
    "phase-3-investigate.md",
    "phase-4-verify.md",
    "phase-5-refine.md",
    "phase-6-deliver.md",
    "runtime-claude-code.md",
    "runtime-codex.md",
    "chapter-investigator-prompt.md",
}


def frontmatter_keys(text: str) -> set[str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return set()
    return {
        line.split(":", 1)[0].strip()
        for line in match.group(1).splitlines()
        if ":" in line and not line.startswith((" ", "\t"))
    }


class SkillPortabilityTests(unittest.TestCase):
    def test_frontmatter_is_portable(self) -> None:
        self.assertEqual(
            frontmatter_keys(SKILL.read_text(encoding="utf-8")),
            {"name", "description"},
        )

    def test_entry_point_is_small(self) -> None:
        self.assertLess(len(SKILL.read_text(encoding="utf-8").splitlines()), 500)

    def test_required_references_exist_and_are_linked(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        available = {
            path.name for path in (SKILL_ROOT / "references").glob("*.md")
        }
        self.assertTrue(REQUIRED_REFERENCES <= available)
        for name in REQUIRED_REFERENCES:
            self.assertIn(f"references/{name}", text)

    def test_shared_entry_point_uses_capability_language(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        forbidden = (
            "AskUserQuestion",
            "Task tool",
            "Read tool",
            "Write tool",
            "Claude recommends",
            ".claude/skills",
        )
        for term in forbidden:
            self.assertNotIn(term, text)

    def test_sequential_is_default_and_parallel_is_explicit(self) -> None:
        phase = (
            SKILL_ROOT / "references" / "phase-0-setup.md"
        ).read_text(encoding="utf-8")
        self.assertIn('"execution_mode": "sequential"', phase)
        self.assertRegex(phase, r"(?is)parallel.*explicit")

    def test_phase_five_uses_persisted_dialogue_outcomes(self) -> None:
        phase = (
            SKILL_ROOT / "references" / "phase-5-refine.md"
        ).read_text(encoding="utf-8")
        for field in (
            "dialogue_rounds",
            "questions_presented",
            "questions_answered",
        ):
            self.assertIn(field, phase)
        self.assertNotIn("AskUserQuestion", phase)

    def test_chapter_prompt_has_no_runtime_frontmatter(self) -> None:
        prompt = (
            SKILL_ROOT / "references" / "chapter-investigator-prompt.md"
        ).read_text(encoding="utf-8")
        self.assertFalse(prompt.startswith("---"))
        self.assertNotRegex(
            prompt,
            r"(?m)^(tools|allowed-tools|subagent_type):",
        )

    def test_runtime_adapters_document_python_detection(self) -> None:
        adapters = "\n".join(
            (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
            for name in ("runtime-claude-code.md", "runtime-codex.md")
        )
        for launcher in ("python3", "python", "py -3"):
            self.assertIn(launcher, adapters)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Write the bundled script syntax test**

Create `tests/test_skill_scripts.py`:

```python
from pathlib import Path
import py_compile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / "skills" / "cc-rsg" / "scripts"


class SkillScriptTests(unittest.TestCase):
    def test_bundled_scripts_compile(self) -> None:
        scripts = sorted(SCRIPT_ROOT.glob("*.py"))
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=script.name):
                py_compile.compile(str(script), doraise=True)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify the portability contract fails**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: script compilation passes, while portability tests fail because the
frontmatter contains `allowed-tools`, `SKILL.md` exceeds 500 lines, and the new
reference files do not exist.

- [ ] **Step 4: Commit the red tests**

```powershell
git add tests/test_skill_portability.py tests/test_skill_scripts.py
git commit -m "test: define runtime portability contract"
```

---

### Task 2: Create the Portable Entry Point and Phase References

**Files:**
- Modify: `skills/cc-rsg/SKILL.md`
- Create: `skills/cc-rsg/references/phase-0-setup.md`
- Create: `skills/cc-rsg/references/phase-1-recon.md`
- Create: `skills/cc-rsg/references/phase-2-plan.md`
- Create: `skills/cc-rsg/references/phase-3-investigate.md`
- Create: `skills/cc-rsg/references/phase-4-verify.md`
- Create: `skills/cc-rsg/references/phase-5-refine.md`
- Create: `skills/cc-rsg/references/phase-6-deliver.md`

**Interfaces:**
- Consumes: existing Phase 0-6 rules in `skills/cc-rsg/SKILL.md`.
- Produces: a sub-500-line orchestration file and seven authoritative phase references.

- [ ] **Step 1: Replace frontmatter and product branding**

Start `skills/cc-rsg/SKILL.md` with exactly:

```markdown
---
name: cc-rsg
description: Reverse-engineer auditable specification documents from existing codebases through goal definition, inventory-driven investigation, traceable evidence, verification, and question-bank refinement. Use when an agent must reconstruct maintenance, delivery, architecture, API, batch, library, or system specifications from source code.
---

# cc-rsg — Codebase Reverse Specification Generator
```

Do not retain `allowed-tools` or product-specific names in the shared entry
point.

- [ ] **Step 2: Add the runtime capability contract**

Add this section near the beginning of `SKILL.md`:

```markdown
## Runtime contract

Identify the current host runtime from the capabilities available in the
session. Read exactly one adapter:

- Claude Code: `references/runtime-claude-code.md`
- Codex: `references/runtime-codex.md`

If the runtime is unknown, use the portable sequential workflow.

In shared workflow instructions:

- inspect files with the host's available file-reading capability;
- search with the host's available repository-search capability;
- edit artifacts with the host's available file-editing capability;
- ask through the host's available interaction mechanism;
- use structured choices when available and numbered text choices otherwise;
- consult official external documentation only when web access is available;
- delegate only when `goal.json.execution_mode == "parallel"`, the user
  explicitly selected it, and the runtime supports delegation.
```

- [ ] **Step 3: Extract Phase 0 and add execution mode**

Move the existing Phase 0 setup, language selection, goal questions, persistence,
and resume behavior to `references/phase-0-setup.md`. Preserve all current JSON
fields and add:

```markdown
## Execution mode

Ask the user to select an execution mode after the existing goal questions:

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
`sequential`; do not require migration.
```

Express all questions through the host interaction mechanism. Retain the
language quality rules and enum values.

- [ ] **Step 4: Extract Phases 1 and 2 without semantic changes**

Create:

- `references/phase-1-recon.md` for reconnaissance, template selection, depth
  selection, inventory preparation, and the Phase 1 review gate.
- `references/phase-2-plan.md` for skeleton generation, WBS construction,
  reserved chapters, user-custom deliverables, naming, and Phase 2 review.

Replace product-specific verbs with capability language while preserving every
artifact schema and gate.

- [ ] **Step 5: Extract Phase 3 with sequential-first execution**

Create `references/phase-3-investigate.md`. Preserve comprehensive, outline,
interactive, traceability, confidence, and chapter-quality contracts. Replace
the delegation decision with:

```markdown
## Execution strategy

Read `goal.json.execution_mode`; use `sequential` when the field is absent.

### Sequential

Apply `references/chapter-investigator-prompt.md` directly in the main agent,
one chapter at a time. Persist progress after each chapter.

### Parallel

Use this path only when the user explicitly selected `parallel` and the host
adapter confirms delegation support. Render one independent prompt per chapter
from `references/chapter-investigator-prompt.md`. Workers write chapter files
directly and return only paths, summaries, questions, and status.

If delegation is unavailable, append a fallback event with the reason to
`state.json.session_history` and continue sequentially.
```

- [ ] **Step 6: Extract Phases 4, 5, and 6**

Create:

- `references/phase-4-verify.md` with existing coverage, integrity, loopback,
  Mermaid, custom-deliverable, and retry requirements.
- `references/phase-5-refine.md` with the three dialogue stages and this
  persisted state:

```json
{
  "phase_5": {
    "dialogue_rounds": 1,
    "questions_presented": ["Q-001"],
    "questions_answered": ["Q-001"]
  }
}
```

Phase 5 completion requires `dialogue_rounds >= 1`, non-empty
`questions_presented`, non-empty `questions_answered`, at least one persisted
answer, and the existing open-ratio threshold.

- `references/phase-6-deliver.md` with existing intent-vs-delivery audit,
  unresolved-item, traceability, final-copy, metadata, and interactive
  deep-dive requirements.

- [ ] **Step 7: Add phase navigation and shared schemas to `SKILL.md`**

Keep only shared principles, state-machine summary, common schemas, reference
catalog, file layout, and direct phase links:

```markdown
## Phase workflow

Read and execute one phase reference at a time:

1. `references/phase-0-setup.md`
2. `references/phase-1-recon.md`
3. `references/phase-2-plan.md`
4. `references/phase-3-investigate.md`
5. `references/phase-4-verify.md`
6. `references/phase-5-refine.md`
7. `references/phase-6-deliver.md`

Do not advance until the current phase's review and persistence gates pass.
```

- [ ] **Step 8: Run the focused tests**

Run:

```powershell
python -m unittest tests.test_skill_portability -v
```

Expected: failures remain only for the missing runtime adapters and chapter
prompt. Entry-point size, frontmatter, phase links, execution mode, and Phase 5
outcome tests pass.

- [ ] **Step 9: Commit the entry point and phase split**

```powershell
git add skills/cc-rsg/SKILL.md skills/cc-rsg/references/phase-*.md
git commit -m "refactor: split portable cc-rsg phase workflow"
```

---

### Task 3: Add Runtime Adapters and Neutral Chapter Prompt

**Files:**
- Create: `skills/cc-rsg/references/runtime-claude-code.md`
- Create: `skills/cc-rsg/references/runtime-codex.md`
- Create: `skills/cc-rsg/references/chapter-investigator-prompt.md`
- Delete: `skills/cc-rsg/agents/chapter-investigator.md`
- Modify: `skills/cc-rsg/references/subagent-prompt.md`
- Modify: `skills/cc-rsg/variants/B/SKILL.phase3-stepG.md`
- Modify: `skills/cc-rsg/variants/B/chapter-investigator.md`
- Modify: `skills/cc-rsg/variants/B/README.md`

**Interfaces:**
- Consumes: capability contract from `SKILL.md` and chapter assignment data from `wbs.json`.
- Produces: host mappings and one reusable chapter-investigation prompt.

- [ ] **Step 1: Add the Claude Code adapter**

Create `references/runtime-claude-code.md`:

```markdown
# Claude Code runtime adapter

Use Claude Code's native file reading, repository search, editing, shell, web,
and structured-question facilities to satisfy the shared capability contract.

For `execution_mode: parallel`, delegation is authorized by the user's explicit
Phase 0 selection. Launch independent general-purpose workers with rendered
copies of `chapter-investigator-prompt.md`. Respect the host concurrency limit,
wait for every worker in the current batch, and persist chapter completion
before launching the next batch.

If a required capability is unavailable or denied, apply the shared fallback
instead of substituting an unverified result.

Before invoking a bundled Python script, detect an available launcher in this
order: `python3`, `python`, then `py -3`. Report a blocking prerequisite if
none is available.
```

- [ ] **Step 2: Add the Codex adapter**

Create `references/runtime-codex.md`:

```markdown
# Codex runtime adapter

Use Codex's available shell/search, structured patching, web, and user
interaction facilities to satisfy the shared capability contract.

Treat the user's explicit Phase 0 selection of `execution_mode: parallel` as
authorization for this cc-rsg run. Use Codex subagents only under that
condition. Keep workers bounded to independent chapters, wait for their
results, and persist completion after each chapter.

When structured user input or subagents are unavailable, use numbered text
questions or sequential investigation respectively. Do not broaden permissions
or bypass sandbox restrictions.

Before invoking a bundled Python script, detect an available launcher in this
order: `python3`, `python`, then `py -3`. Report a blocking prerequisite if
none is available.
```

- [ ] **Step 3: Convert the chapter agent into a plain prompt**

Create `references/chapter-investigator-prompt.md` from the body of the current
`agents/chapter-investigator.md`. Remove YAML frontmatter, tool names, and
named-agent assumptions. Begin with:

```markdown
# Chapter investigator prompt

Investigate and write exactly one assigned specification chapter.

## Inputs

- Goal excerpt: `{goal_excerpt}`
- Chapter title: `{chapter_title}`
- Output file: `{output_file}`
- Assigned inventory IDs: `{assigned_inventory_ids}`
- Required template section: `{template_section}`

Inspect every real source file associated with the assigned inventory IDs.
Never cite a file that was not inspected. Write the chapter directly to the
specified output file and return only the path, summary, questions raised, and
completion status.
```

Preserve all existing traceability, uncertainty, quality, output-language,
question-bank, and completion requirements.

Delete `skills/cc-rsg/agents/chapter-investigator.md`.

- [ ] **Step 4: Neutralize legacy subagent and Mode B references**

Make `references/subagent-prompt.md` a compatibility explanation that points to
`chapter-investigator-prompt.md` as the authoritative prompt. Remove executable
examples containing `Task(...)` or `subagent_type`.

Keep Mode B as an optional manifest-relay strategy, but make it depend on
`execution_mode: parallel`, host delegation support, and the common prompt.
Replace direct Read/Write/Task tool wording with capability language.

- [ ] **Step 5: Run portability tests**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Scan the distributable bundle for stale requirements**

Run:

```powershell
rg -n "allowed-tools:|AskUserQuestion|Task tool|subagent_type=|Read tool|Write tool|Claude recommends|\\.claude/skills" skills/cc-rsg
```

Expected: product tool names appear only where explicitly explanatory inside
`runtime-claude-code.md`; no shared workflow requires them.

- [ ] **Step 7: Commit runtime adapters and prompt conversion**

```powershell
git add skills/cc-rsg
git commit -m "refactor: add runtime adapters for cc-rsg"
```

---

### Task 4: Update Distribution Documentation and Validate Installation

**Files:**
- Modify: `README.md`
- Modify: `tests/test_skill_portability.py`

**Interfaces:**
- Consumes: the portable skill bundle.
- Produces: documented Skills CLI installation and final repository validation.

- [ ] **Step 1: Add a failing README installation test**

Add to `SkillPortabilityTests`:

```python
    def test_readme_leads_with_skills_cli_installation(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        command = "npx skills add endo5501/cc-rsg"
        self.assertIn(command, readme)
        self.assertLess(readme.index(command), readme.index("cp -r"))
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```powershell
python -m unittest tests.test_skill_portability.SkillPortabilityTests.test_readme_leads_with_skills_cli_installation -v
```

Expected: FAIL because the README currently documents `cp -r` first and lacks
the Skills CLI command.

- [ ] **Step 3: Rewrite README installation and branding**

Describe `cc-rsg` as an Agent Skill for Claude Code, Codex, and compatible
runtimes. Lead with:

```bash
npx skills add endo5501/cc-rsg
```

Add the explicit global command:

```bash
npx skills add endo5501/cc-rsg \
  --skill cc-rsg \
  --global \
  --agent claude-code \
  --agent codex
```

Keep manual copying as a fallback section after Skills CLI installation.
Document sequential as the default and parallel as an explicit Phase 0 choice.

- [ ] **Step 4: Run all Python tests**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Validate Skills CLI discovery**

Run:

```powershell
npx -y skills add . --list
```

Expected: `Found 1 skill` and `cc-rsg`.

- [ ] **Step 6: Validate Python scripts without writing bytecode into the skill**

Run:

```powershell
python -m unittest tests.test_skill_scripts -v
```

Expected: all bundled scripts compile.

- [ ] **Step 7: Check formatting and working tree scope**

Run:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; only planned files are modified.

- [ ] **Step 8: Commit documentation and final validation**

```powershell
git add README.md tests/test_skill_portability.py
git commit -m "docs: publish portable cc-rsg installation"
```

---

### Task 5: Final Compatibility Audit

**Files:**
- Modify only files found defective by this audit.

**Interfaces:**
- Consumes: all deliverables from Tasks 1-4.
- Produces: evidence that the repository satisfies the approved design.

- [ ] **Step 1: Run the complete test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass with no errors or failures.

- [ ] **Step 2: Re-run Skills CLI discovery against GitHub**

Run:

```powershell
npx -y skills add endo5501/cc-rsg --list
```

Expected: the currently published revision still reports one `cc-rsg` skill.
This checks source discoverability; the local `npx ... add . --list` result is
the authoritative check for unpushed changes.

- [ ] **Step 3: Verify design coverage**

Run:

```powershell
rg -n "execution_mode|dialogue_rounds|questions_presented|questions_answered|runtime-claude-code|runtime-codex|chapter-investigator-prompt" skills/cc-rsg
```

Expected: every approved design concept is present in the new authoritative
files.

- [ ] **Step 4: Inspect final diff and history**

Run:

```powershell
git diff HEAD~4 --stat
git log -5 --oneline
git status --short
```

Expected: the runtime-neutralization commits are present and the working tree
is clean.

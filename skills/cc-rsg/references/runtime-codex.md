# Codex runtime adapter

Use Codex's available capabilities to implement the shared workflow:

- inspect and search files with the available shell and search facilities;
- update artifacts through structured patches or the available editor;
- ask through the available user interaction mechanism;
- consult official documentation with web access when available;
- run bundled deterministic scripts through the shell.

Do not expose these product-specific facility names in shared phase
instructions.

## Execution modes

For `execution_mode: sequential`, perform chapter work in the main agent.

Treat the user's explicit Phase 0 selection of `execution_mode: parallel` as
authorization for this cc-rsg run. Use Codex subagents only under that
condition. Keep workers bounded to independent chapters, wait for their
results, and persist completion after each chapter.

When structured user input or subagents are unavailable, use numbered text
questions or sequential investigation respectively. Do not broaden
permissions or bypass sandbox restrictions.

## Python launcher

Before invoking a bundled Python script, detect an available launcher in this
order:

1. `python3`
2. `python`
3. `py -3`

Report a blocking prerequisite if none is available.

libclang (`clang.cindex`) is an **optional** prerequisite for high-fidelity
C/C++ extraction. Its absence is not blocking, but when `source-map.py` reports
`stats.cpp_degraded_reason`, do not silently accept the regex output — follow
the "interactive check" step in `phase-2-plan.md` to prompt the user.

## Failure behavior

If web access is unavailable, register external facts as unverified rather than
guessing. If an edit or command is denied, report the affected phase and
preserve resumable state.

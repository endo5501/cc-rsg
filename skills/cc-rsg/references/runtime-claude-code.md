# Claude Code runtime adapter

Use Claude Code's native capabilities to implement the shared workflow:

- inspect files with its file-reading facility;
- search paths and content with its repository-search facilities;
- update artifacts with its file-editing facilities;
- run deterministic scripts through its shell facility;
- prefer its structured question interface for choices;
- consult official documentation through its web facilities when available.

Do not expose these product-specific facility names in shared phase
instructions.

## Execution modes

For `execution_mode: sequential`, perform chapter work in the main session.

For `execution_mode: parallel`, delegation is authorized only by the user's
explicit Phase 0 selection. Launch independent general-purpose workers with
rendered copies of `chapter-investigator-prompt.md`. Respect the host
concurrency limit, wait for every worker in the current batch, and persist
chapter completion before launching the next batch.

If delegation is unavailable or denied, append a fallback event to
`state.json.session_history` and continue sequentially.

## Python launcher

Before invoking a bundled Python script, detect an available launcher in this
order:

1. `python3`
2. `python`
3. `py -3`

Report a blocking prerequisite if none is available. Do not rewrite the
bundled script in another language merely to avoid the missing prerequisite.

libclang (`clang.cindex`) is an **optional** prerequisite for high-fidelity
C/C++ extraction. Its absence is not blocking, but when `source-map.py` reports
`stats.cpp_degraded_reason`, do not silently accept the regex output — follow
the "interactive check" step in `phase-2-plan.md` to prompt the user.

## Failure behavior

If a required capability is unavailable or denied, apply the shared fallback
instead of substituting an unverified result. Honour repository instructions,
permission prompts, and sandbox restrictions.

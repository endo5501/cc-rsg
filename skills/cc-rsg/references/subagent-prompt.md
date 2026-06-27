# Legacy delegation compatibility

The authoritative chapter workflow is
`references/chapter-investigator-prompt.md`.

Older integrations may refer to this file as the chapter delegation prompt.
Resolve that reference by loading the authoritative prompt, filling its input
placeholders from `goal.json`, `wbs.json`, and `inventory.json`, and applying
the execution strategy in `phase-3-investigate.md`.

Do not depend on a named worker type or product-specific tool. Sequential mode
applies the prompt in the main agent. Parallel mode passes an independent
rendered copy to each host-supported worker only after explicit user selection.

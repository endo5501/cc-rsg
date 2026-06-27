# Mode B chapter result contract

Use `../../references/chapter-investigator-prompt.md` for the complete
investigation procedure.

Mode B changes only the returned result:

```text
OUTPUT: <relative draft path>
STATUS: complete | blocked
SUMMARY: <maximum five concise findings>
QUESTIONS: <IDs and short bodies, or None>
```

Write the full chapter to `OUTPUT`. Do not return the chapter body to the main
agent. Keep all evidence, uncertainty markers, sources, and detail questions in
the file.

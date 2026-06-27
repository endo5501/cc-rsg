# Phase 5 — Refine Through Dialogue

## Purpose

Resolve uncertainty with the user and improve drafts without hiding what
cannot be established from source.

## Dialogue stages

### Stage 1 — Overview

Present counts by category, severity, and status. Explain which chapters are
blocked or low confidence.

### Stage 2 — Critical clusters

Group obviously identical questions. Present critical and high-impact clusters
first. Do not automatically merge questions that differ in evidence or intent.

### Stage 3 — Residual questions

Present remaining questions individually or in small related groups. Prefer
choices supported by evidence, while always allowing free-form answers.

Use the host's interaction mechanism. Persist the outcome of every round:

```json
{
  "phase_5": {
    "dialogue_rounds": 1,
    "questions_presented": ["Q-001"],
    "questions_answered": ["Q-001"]
  }
}
```

Increment `dialogue_rounds` only after a question was actually shown. Append
IDs to `questions_presented` when shown and to `questions_answered` only after
the answer is stored in `questions.json`.

## Applying answers

For each answer:

1. update `status`, `answer`, `answerer`, and `answered_at`;
2. re-inspect relevant code when the answer changes interpretation;
3. update affected chapters and confidence markers;
4. preserve evidence that supports or conflicts with the answer;
5. rerun relevant Phase 4 checks.

Mark permanently unanswerable questions `abandoned` and include them in
`99-unresolved.md`.

## Skip prevention

Phase 5 cannot complete unless:

- `dialogue_rounds >= 1`;
- `questions_presented` is non-empty;
- `questions_answered` is non-empty;
- at least one Question Bank entry has a persisted answer;
- the ratio of `status: open` entries is below 20 percent.

If no questions exist, record an explicit zero-question review outcome with the
user and a justified exception in state rather than manufacturing a question.

## Completion gate

Rerun affected verification checks, persist the final dialogue state, and
advance `state.json.current_phase` to `6`.

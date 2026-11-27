---
name: self-review
description: Review your own diff like a strict reviewer before handing work to a human, covering correctness, tests, security, scope and maintainability, then fix what you find. Use after implementation and verification and before committing or opening a pull request. Do not use to review someone else's pull request on request; use the project's review process for that.
---

# Self Review

Read the diff as if someone else wrote it and you must approve it.

## 1. Collect the change

Run `git status --short` and `git diff` (plus `git diff --staged`). Read every changed hunk in full. Re-read the spec or task to remind yourself what was asked.

## 2. Check each area

**Correctness**
- Does every acceptance criterion have code and a check behind it?
- Edge cases: empty input, null values, large input, concurrency, time zones, encodings, partial failure.
- Errors are handled where they can occur and surfaced, not swallowed; no broad `catch`/`except` that hides failures.

**Tests**
- New behavior has tests that would fail without the change.
- Tests assert outcomes, not implementation details, and are deterministic.

**Security**
- No secrets, tokens or personal data in code, logs, fixtures or commit messages.
- Untrusted input is validated; queries are parameterized; paths and shell arguments are not built from raw input.
- New dependencies are necessary, maintained and pinned through the lockfile.

**Scope**
- Nothing unrelated changed: no drive-by refactors, formatting churn or renamed files outside the task.
- No leftover debug output, commented-out code, or TODOs without an owner.

**Maintainability**
- Names say what things are; the simplest working design was chosen.
- Docs, `AGENTS.md` commands and specs are updated when behavior or commands changed.

## 3. Fix, then re-verify

Fix every issue you can within the task's scope, then run the `verify-change` checks again. Issues outside the scope go into the hand-off as follow-ups rather than into this diff.

## 4. Hand off

Summarize for the reviewer: what changed and why, how it was verified, known limitations, and follow-ups. Point to the riskiest part of the diff so the human reviews it first.

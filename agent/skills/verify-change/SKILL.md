---
name: verify-change
description: Prove a code change works by running the project's real checks (format, lint, type check, tests, build, and UI checks where relevant) and reporting the evidence. Use before declaring any implementation task done, before committing, and whenever the user asks whether something works. Do not use for documentation-only edits that no check covers.
---

# Verify Change

A task is done when an external check says so, not when the agent believes it. Treat your own judgement of "looks right" as a hypothesis.

## 1. Find the project's checks

Look in this order and use the first source that defines them:

1. The `Commands` section of `AGENTS.md`.
2. Task runners: `package.json` scripts, `Makefile`, `justfile`, `Taskfile.yml`, `pyproject.toml`, `noxfile.py`.
3. CI workflows under `.github/workflows/`; run the same commands CI runs.

If no checks exist, say so and propose adding them instead of skipping verification silently.

## 2. Run them, narrow to wide

1. Format and lint the changed files.
2. Type check.
3. Run the tests closest to the change, then the full suite when it is reasonably fast.
4. Build, when the project has a build step.
5. For user interfaces, start the app and check the changed screen with Playwright or another browser tool: take a screenshot, exercise the changed interaction, and read the console for errors.
6. For CLIs and services, run the changed command or hit the changed endpoint once with realistic input.

## 3. Add the missing test

When the change fixes a bug or adds behavior and no test fails without it, write one that does. For a bug, confirm the new test fails before the fix and passes after it.

## 4. Fix forward, never around

- Never delete, skip, weaken or mark as expected-failure a test to get a green run, and never loosen lint, type or coverage settings, unless the user explicitly asks.
- Never bypass hooks (`--no-verify`) or CI gates.
- When a failure is unrelated to your change, show that it also fails without your change, then report it rather than fixing it inside this task.

## 5. Report evidence

End with a short verification report:

- each command you ran and its result (pass, fail, or not run and why);
- for UI work, what you observed and where the screenshot is;
- anything you could not verify and what the user would need to check.

Do not claim success for a step you did not run.

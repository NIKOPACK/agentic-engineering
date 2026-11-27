---
name: spec-first
description: Write and confirm a short specification before implementing a non-trivial change. Use when a task adds a feature, changes behavior across modules, alters a public API, data schema or user flow, or when requirements are ambiguous. Do not use for typo fixes, single-function bug fixes with an obvious cause, dependency bumps, or when the user already supplied an approved spec.
---

# Spec First

Agree on what "done" means before writing code. A spec is a contract the reviewer can check the result against.

## 1. Decide whether a spec is needed

Write one when any of these hold:

- the change touches more than one module or more than about 200 lines;
- it changes a public API, CLI, schema, migration, config format or user-visible flow;
- the request leaves behavior, scope or edge cases open to interpretation.

Otherwise state in one line why no spec is needed and continue with the task.

## 2. Gather facts first

1. Read `AGENTS.md` and any existing spec, ADR or issue for this area.
2. Trace the current implementation and its tests far enough to describe today's behavior accurately.
3. List the open questions you cannot answer from the repository.

## 3. Write the spec

Create `docs/specs/<YYYY-MM-DD>-<slug>.md` from `docs/specs/_template.md` when the template exists; otherwise use the same headings:

- **Goal**: one or two sentences on the user-visible outcome.
- **Non-goals**: what this change deliberately leaves out.
- **Current behavior**: facts from the code, with file references.
- **Proposed behavior**: rules, inputs, outputs, errors and edge cases.
- **Acceptance criteria**: a numbered list where every item can be verified by a test, a command or an observable check.
- **Plan**: ordered steps, each small enough to verify on its own.
- **Risks and rollback**: migrations, compatibility, security impact.
- **Open questions**: anything still unresolved.

Keep it under about one page. Link to code instead of copying it.

## 4. Confirm before implementing

Present the goal, acceptance criteria and open questions to the user and ask for confirmation. Do not start implementation until open questions that change behavior are answered. Record answers in the spec, not only in chat.

## 5. Keep the spec true

- Implement against the acceptance criteria and check them off in the spec as they pass.
- When the plan changes during implementation, update the spec in the same change and tell the user why.
- After merge, the spec stays as the record of intent; do not delete it.

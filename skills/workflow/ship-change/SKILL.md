---
name: ship-change
description: Commit verified work with Conventional Commits on a feature branch and open a pull request that follows the repository template. Use when the user asks to commit, push, or open a PR for finished work. Do not use for work that has not passed verify-change, and never to push directly to a protected branch.
---

# Ship Change

## 1. Preconditions

- `verify-change` has passed in this session, or the user knowingly accepts unverified work; say which.
- `git status --short` shows only files that belong to this change. Ask before staging anything else.

## 2. Branch

Never commit directly on `main`, `master` or another protected branch. Create a branch named `<type>/<short-slug>`, for example `feat/export-csv` or `fix/login-timeout`. If the project or environment specifies a branch name, use that instead.

## 3. Commit

Stage files explicitly by path; avoid `git add -A` unless every change is yours. Write the message in Conventional Commits form:

```text
<type>(<optional scope>): <imperative summary, at most 72 characters>

<why the change was needed and what it does, wrapped at 72 characters>

<footer: Refs/Closes #123, BREAKING CHANGE: ..., trailers the project requires>
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Split unrelated changes into separate commits. If a pre-commit hook fails, fix the cause and commit again; never use `--no-verify`.

## 4. Push

Push with `git push -u origin <branch>`. Use `--force-with-lease` only on your own branch after a rebase, and never on a protected branch.

## 5. Pull request

Only open a pull request when the user asked for one. Fill `.github/pull_request_template.md` when it exists:

- **Summary**: what and why, linked to the issue or spec.
- **Changes**: the main edits, grouped by area.
- **Verification**: commands run and their results, screenshots for UI.
- **Risks**: migrations, compatibility, rollout and rollback.

Keep the PR focused: one concern, ideally under about 400 changed lines. Mark it as a draft when checks are still running or questions remain open.

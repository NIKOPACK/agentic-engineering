# AGENTS.md

<!--
Instructions for coding agents (Codex, Claude Code via CLAUDE.md, pi).
Keep this file short and true: stable, repository-wide rules only.
Replace every <placeholder>, run each command once to confirm it works, and delete sections that do not apply.
-->

## Project

<One or two sentences: what this project is, who uses it, and the main technologies.>

## Layout

- `<src/>`: <what lives here>
- `<tests/>`: <test layout and naming>
- `docs/specs/`: feature specifications; `docs/adr/`: architecture decisions

## Commands

Run these from the repository root.

| Purpose | Command |
| --- | --- |
| Install dependencies | `<npm ci / uv sync / go mod download>` |
| Format | `<npx biome format --write . / uv run ruff format . / gofmt -w .>` |
| Full check (CI parity) | `<npm run check / make check>` |
| Tests | `<npm test / uv run pytest / go test ./...>` |
| Single test | `<npx vitest run path -t name / uv run pytest path::test / go test ./pkg -run Name>` |
| Run locally | `<npm run dev / uv run python -m app / go run ./cmd/app>` |

## Workflow

1. **Understand first.** Read the relevant code, tests and `docs/` before editing. Ask when requirements are ambiguous instead of guessing.
2. **Spec non-trivial work.** For new features, cross-module changes, or API, schema or UX changes, use the `spec-first` skill and get the spec confirmed before implementing.
3. **Small, verifiable steps.** Keep each change focused on one concern. Do not refactor, reformat or rename outside the task.
4. **Verify with evidence.** Before saying a task is done, use the `verify-change` skill: run the full check and the relevant tests, and report the results. For UI work, check the changed screen in a browser.
5. **Review your own diff** with the `self-review` skill before handing off.
6. **Ship through pull requests** with the `ship-change` skill: feature branch, Conventional Commits, PR template.

## Rules

- Never weaken, skip or delete tests, lint rules or type checks to make a run pass, and never bypass hooks with `--no-verify`.
- Never read, print or commit secrets. `.env*` files (except `.env.example`), keys and credential files are off-limits; use `.env.example` for documentation.
- Never push directly to `main`; never force push except `--force-with-lease` on your own branch.
- Add or change dependencies only when the task needs them, and commit the lockfile with them.
- Do not edit agent guardrails (`.agents/hooks/`, `.agents/policy.json`, `.codex/`, `.claude/settings.json`, `.pi/extensions/`); ask the user.
- When docs, commands or behavior change, update this file, the README and the spec in the same change.

## Conventions

<Project-specific conventions an agent cannot infer from the code: error-handling style, logging, naming, module boundaries, generated files that must not be edited by hand.>

---
name: adopt-standards
description: Bring a repository in line with the agentic-engineering standards by auditing its current tooling, installing the shared kit (AGENTS.md, skills, guard hooks for Codex, Claude Code and pi, stack configs, CI) without overwriting existing files, and filling AGENTS.md with the project's real commands. Use when the user asks to set up, adopt or update these development standards in a project. Do not use for ordinary feature work.
---

# Adopt Standards

Install the agentic-engineering kit into the current repository and tailor it, keeping everything the project already has.

## 1. Audit first

1. Read the existing `AGENTS.md`, `CLAUDE.md`, `README` and contributing docs.
2. Run `git status --short`; treat existing changes as the user's and do not touch them.
3. Detect the stack from manifests: `package.json` and lockfiles (TypeScript/Node), `pyproject.toml` or `requirements*.txt` (Python), `go.mod` (Go).
4. Inventory current tooling: formatter, linter, type checker, test runner, CI workflows, pre-commit hooks, `.codex/`, `.claude/`, `.pi/`, `.agents/`.
5. Tell the user what exists and which kit parts would be added, then confirm the stacks and agents to install.

## 2. Install the kit

Locate the kit: a local clone of `https://github.com/NIKOPACK/agentic-engineering`, or clone it into a temporary directory. Preview with `--dry-run`, then run the installer from the target repository root:

```bash
python3 <kit>/scripts/install.py --target . --stack <typescript,python,go> --agents <codex,claude,pi> --dry-run
python3 <kit>/scripts/install.py --target . --stack <typescript,python,go> --agents <codex,claude,pi>
```

The installer never overwrites files; `--upgrade` refreshes only the kit-managed guard, skills and pi extension. On Windows add `--copy-skills`. Read its output: every `skip` line is an existing file you must reconcile by hand.

## 3. Reconcile skipped files

- **Existing tool configs** (ESLint, Prettier, Black, Flake8 and so on): keep the project's tools unless the user agrees to migrate. Do not add a second formatter or linter for the same language.
- **Existing `.claude/settings.json`, `.codex/hooks.json` or `.codex/config.toml`**: merge the kit's `PreToolUse` hook entry into the existing file instead of replacing it.
- If the guard blocks your edit to an agent config (`guard-tamper`), show the user the exact merged content and let them apply it.
- **Existing CI**: add missing steps (format check, lint, type check, tests, secret scan) to the current workflow rather than adding a parallel one.

## 4. Fill AGENTS.md

Replace every `<placeholder>` in `AGENTS.md` with facts from the repository: the project summary, layout, and the exact setup, check, test and run commands. Run each command once to confirm it works before writing it down. Remove sections that do not apply. Keep the file short: stable, repository-wide rules only.

## 5. Verify and report

1. Run the commands you wrote into `AGENTS.md`.
2. Feed one blocked and one allowed sample through the guard, for example `echo '{"tool_name":"Bash","tool_input":{"command":"git push --force"},"cwd":"."}' | python3 .agents/hooks/policy.py` (expect exit code 2).
3. Remind the user of the one-time steps only they can do: trust the project and review hooks with `/hooks` in Codex; approve the project hooks when Claude Code asks; run `pre-commit install`.
4. Report what was installed, what was merged, what was skipped and why.

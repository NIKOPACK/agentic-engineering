# AGENTS.md

This repository is the source of the agentic-engineering kit: development standards (Chinese docs) plus the files `scripts/install.py` copies into other projects. Changes here ship to every project that installs or upgrades the kit.

## Layout

- `docs/standards/`, `docs/stacks/`, `docs/background.md`: the standards, written in Chinese.
- `agent/`: kit-managed agent files. `hooks/policy.py` is the shared guard; `skills/` are the shared skills; `codex/`, `claude/`, `pi/` wire the guard into each tool.
- `templates/common/` and `templates/<stack>/`: files copied verbatim into target projects.
- `scripts/install.py`: the installer. `scripts/validate.py`: config and skill validation.
- `tests/`: stdlib `unittest` tests for the guard and the installer.

This repository does not activate its own guard or skills; `agent/` is the source, not live configuration.

## Commands

| Purpose | Command |
| --- | --- |
| Full check (CI parity) | `make check` |
| Tests only | `python3 -m unittest discover -s tests` |
| Validate configs and skills | `python3 scripts/validate.py` |
| Try the installer | `python3 scripts/install.py --target /tmp/demo --stack ts,py,go --dry-run` |

`make check` needs `uv` and Python 3.11+. The shipped scripts (`policy.py`, `install.py`) must keep working on Python 3.9 with the standard library only.

## Rules

- Keep Codex, Claude Code and pi at parity. A rule, skill or guard change applies to all three, or the docs say clearly why not.
- Every guard rule needs both a "denied" and an "allowed" test in `tests/test_policy.py`. Prefer false negatives over blocking everyday commands.
- The installer never overwrites user files. Only files listed as managed (guard, kit skills, pi extension) may be refreshed, and only with `--upgrade`.
- Skills follow the Agent Skills format: `name` equals the directory name, lowercase with hyphens; `description` at most 1024 characters and states when to use and when not to use the skill; each skill has `agents/openai.yaml`. Run `python3 scripts/validate.py`.
- Verify tool and action versions against upstream before changing pins, and verify stack configs with the real tool (Biome, tsc, Ruff, mypy, golangci-lint, pre-commit) on a scratch project.
- Docs in `docs/` and `README.md` are Chinese; instructions read by agents (`AGENTS.md`, `SKILL.md`, code comments) are English.
- When behavior changes, update the matching standard in `docs/`, the README and the tests in the same change.

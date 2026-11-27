# AGENTS.md

This repository is the source of the agentic-engineering kit: development standards (Chinese docs) plus the files `scripts/install.py` copies into other projects. Changes here ship to every project that installs or upgrades the kit.

## Layout

- `docs/standards/`, `docs/stacks/`, `docs/background.md`: the standards, written in Chinese.
- `agent/`: kit-managed agent files. `hooks/policy.py` is the shared guard; `codex/`, `claude/`, `pi/` wire the guard into each tool.
- `skills/<category>/<name>/`: the skill catalog. `skills/catalog.toml` defines categories, install profiles and the provenance of imported skills; `skills/README.md` holds a generated catalog table and the curation process.
- `templates/common/` and `templates/<stack>/`: files copied verbatim into target projects.
- `scripts/install.py`: the kit installer. `scripts/skills.py`: list, install, remove, scaffold skills and regenerate the catalog table. `scripts/kitlib.py`: shared catalog and file-placement code. `scripts/validate.py`: config and catalog validation.
- `tests/`: stdlib `unittest` tests for the guard and the installer.

This repository does not activate its own guard or skills; `agent/` is the source, not live configuration.

## Commands

| Purpose | Command |
| --- | --- |
| Full check (CI parity) | `make check` |
| Tests only | `python3 -m unittest discover -s tests` |
| Validate configs and skills | `python3 scripts/validate.py` |
| Try the installer | `python3 scripts/install.py --target /tmp/demo --stack ts,py,go --dry-run` |
| Browse skills | `python3 scripts/skills.py list --all` |
| Add a skill | `python3 scripts/skills.py new <category> <name>`, then `python3 scripts/skills.py catalog --write` |

`make check` needs `uv` and Python 3.11+. Scripts under `scripts/` need Python 3.11+ and the standard library only. The guard (`agent/hooks/policy.py`) runs inside every agent session on users' machines, so it must keep working on Python 3.9 with the standard library only.

## Rules

- Keep Codex, Claude Code and pi at parity. A rule, skill or guard change applies to all three, or the docs say clearly why not.
- Every guard rule needs both a "denied" and an "allowed" test in `tests/test_policy.py`. Prefer false negatives over blocking everyday commands.
- The installer never overwrites user files. Only files listed as managed (guard, kit skills, pi extension) may be refreshed, and only with `--upgrade`.
- Skills follow the Agent Skills format: `name` equals the directory name, lowercase with hyphens, unique across all categories; `description` at most 1024 characters and states when to use and when not to use the skill; each skill has `agents/openai.yaml` with Chinese display text.
- Put each skill in the category that matches its purpose; stack-specific skills go in `stacks`. Add a category to `catalog.toml` before using it. Only skills every project needs belong in the default `core` profile.
- Imported skills keep their LICENSE file and get a `[skills.<name>]` entry with `source` and `license` in `catalog.toml`. Read every file of an imported skill, including scripts, before adding it.
- After any skill or catalog change, run `python3 scripts/skills.py catalog --write`; `make check` fails when `skills/README.md` is stale.
- Verify tool and action versions against upstream before changing pins, and verify stack configs with the real tool (Biome, tsc, Ruff, mypy, golangci-lint, pre-commit) on a scratch project.
- Docs in `docs/` and `README.md` are Chinese; instructions read by agents (`AGENTS.md`, `SKILL.md`, code comments) are English.
- When behavior changes, update the matching standard in `docs/`, the README and the tests in the same change.

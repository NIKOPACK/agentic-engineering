#!/usr/bin/env python3
"""Install the agentic-engineering kit into a target repository.

Never overwrites an existing file. Every file it leaves alone is reported as
`skip` with the reason, so the user (or the adopt-standards skill) can merge it
by hand. `--upgrade` refreshes only kit-managed files that users are not meant
to edit: the guard script, the pi extension and the kit skills already
installed in the project.

Skills are installed by profile (see skills/catalog.toml). Without --profile or
--skill, the default profiles are installed; add more later with
`scripts/skills.py install`.

Examples:
  python3 scripts/install.py --target ../my-app --stack typescript --agents codex,claude,pi
  python3 scripts/install.py --target . --stack python,go --profile core --skill some-skill --dry-run
  python3 scripts/install.py --target ../my-app --upgrade

Python 3.11+, standard library only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kitlib import KIT, Catalog, Writer, split_list, tree_files
from skills import install_project, installed_kit_skills

AGENT = KIT / "agent"
TEMPLATES = KIT / "templates"

STACKS = ("typescript", "python", "go")
AGENTS = ("codex", "claude", "pi")
STACK_ALIASES = {"ts": "typescript", "node": "typescript", "py": "python", "golang": "go"}

# Existing files that mean the project already chose a tool for the same job.
CONFLICTS: dict[str, tuple[str, ...]] = {
    "biome.json": (
        "biome.jsonc",
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.cjs",
        ".eslintrc.json",
        ".eslintrc.yml",
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.cjs",
        "eslint.config.ts",
        ".prettierrc",
        ".prettierrc.json",
        ".prettierrc.js",
        "prettier.config.js",
        "prettier.config.mjs",
    ),
    "ruff.toml": (".ruff.toml",),
    ".golangci.yml": (".golangci.yaml", ".golangci.toml", ".golangci.json"),
}
# Config sections inside pyproject.toml that a standalone file would silently override.
PYPROJECT_SECTIONS = {
    "ruff.toml": "[tool.ruff",
    "mypy.ini": "[tool.mypy",
    "pytest.ini": "[tool.pytest",
}


def conflict(target: Path, name: str) -> str | None:
    for other in CONFLICTS.get(name, ()):
        if (target / other).exists():
            return f"project already uses {other}"
    section = PYPROJECT_SECTIONS.get(name)
    pyproject = target / "pyproject.toml"
    if section and pyproject.is_file() and section in pyproject.read_text(encoding="utf-8"):
        return f"pyproject.toml already has {section}]"
    return None


def place_templates(writer: Writer, target: Path, source_root: Path) -> None:
    for relative in tree_files(source_root):
        destination = target / relative
        writer.place(
            source_root / relative, destination, conflict=conflict(target, destination.name)
        )


def parse_list(
    value: str, allowed: tuple[str, ...], aliases: dict[str, str] | None = None
) -> list[str]:
    items = []
    for raw in split_list(value.lower()):
        item = (aliases or {}).get(raw, raw)
        if item not in allowed:
            raise argparse.ArgumentTypeError(
                f"unknown value {raw!r}; choose from {', '.join(allowed)}"
            )
        if item not in items:
            items.append(item)
    return items


def next_steps(agents: list[str]) -> None:
    print("\nNext steps:")
    print("  - Fill the <placeholders> in AGENTS.md with the project's real commands.")
    print("  - Run `pre-commit install` once per clone.")
    print("  - Add skills for this project later: python3 <kit>/scripts/skills.py list")
    if "codex" in agents:
        print("  - Codex: trust the project, then review the hook once with `/hooks`.")
    if "claude" in agents:
        print("  - Claude Code: approve the project hooks when prompted (see `/hooks`).")
    if "pi" in agents:
        print(
            "  - pi: the guard extension loads from .pi/extensions; run `/reload` in a running session."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install the agentic-engineering kit into a repository."
    )
    parser.add_argument(
        "--target", default=".", help="repository root to install into (default: .)"
    )
    parser.add_argument("--stack", default="", help=f"comma list: {', '.join(STACKS)}")
    parser.add_argument(
        "--agents", default=",".join(AGENTS), help=f"comma list: {', '.join(AGENTS)} (default: all)"
    )
    parser.add_argument(
        "--profile", default="", help="skill profiles to install (default: the default profiles)"
    )
    parser.add_argument("--skill", default="", help="extra skills to install")
    parser.add_argument("--no-skills", action="store_true", help="install no skills")
    parser.add_argument(
        "--dry-run", action="store_true", help="print what would happen without writing"
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="refresh kit-managed files (guard, pi extension, installed skills)",
    )
    parser.add_argument(
        "--copy-skills",
        action="store_true",
        help="copy skills into .claude/skills instead of symlinking (Windows)",
    )
    args = parser.parse_args(argv)

    try:
        stacks = parse_list(args.stack, STACKS, STACK_ALIASES)
        agents = parse_list(args.agents, AGENTS)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    target = Path(args.target).resolve()
    if not target.is_dir():
        parser.error(f"target {target} is not a directory")
    if target == KIT:
        parser.error("refusing to install the kit into itself")
    if not (target / ".git").exists():
        print(f"warning: {target} is not a git repository root", file=sys.stderr)

    catalog = Catalog()
    if catalog.errors:
        for error in catalog.errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    try:
        profiles, names = split_list(args.profile), split_list(args.skill)
        if args.no_skills:
            skills = []
        elif profiles or names:
            skills = catalog.resolve(
                profiles, names + (installed_kit_skills(catalog, target) if args.upgrade else [])
            )
        elif args.upgrade:
            skills = catalog.resolve([], installed_kit_skills(catalog, target))
        else:
            skills = catalog.resolve(catalog.default_profiles(), [])
    except ValueError as exc:
        parser.error(str(exc))

    writer = Writer(target, args.dry_run, args.upgrade)
    place_templates(writer, target, TEMPLATES / "common")
    writer.place(AGENT / "hooks" / "policy.py", target / ".agents/hooks/policy.py", managed=True)
    writer.place(AGENT / "policy.json", target / ".agents/policy.json")
    for stack in stacks:
        place_templates(writer, target, TEMPLATES / stack)
    if "codex" in agents:
        writer.place(AGENT / "codex" / "hooks.json", target / ".codex/hooks.json")
        writer.place(AGENT / "codex" / "config.toml", target / ".codex/config.toml")
    if "claude" in agents:
        writer.place(AGENT / "claude" / "settings.json", target / ".claude/settings.json")
    if "pi" in agents:
        writer.place(
            AGENT / "pi" / "extensions" / "agent-policy.ts",
            target / ".pi/extensions/agent-policy.ts",
            managed=True,
        )
    install_project(writer, target, skills, agents, args.copy_skills)

    print(f"\n{writer.summary()}")
    if writer.counts["skip"]:
        print("Reconcile every `skip` line by hand; the adopt-standards skill explains how.")
    print(f"Skills: {', '.join(s.name for s in skills) or 'none'}")
    next_steps(agents)
    return 0


if __name__ == "__main__":
    sys.exit(main())

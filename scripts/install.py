#!/usr/bin/env python3
"""Install the agentic-engineering kit into a target repository.

Never overwrites an existing file. Every file it leaves alone is reported as
`skip` with the reason, so the user (or the adopt-standards skill) can merge it
by hand. `--upgrade` refreshes only kit-managed files that users are not meant
to edit: the guard script, the kit's skills and the pi extension.

Examples:
  python3 scripts/install.py --target ../my-app --stack typescript --agents codex,claude,pi
  python3 scripts/install.py --target . --stack python,go --agents codex --dry-run
  python3 scripts/install.py --target ../my-app --upgrade

Standard library only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
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


class Installer:
    def __init__(self, target: Path, dry_run: bool, upgrade: bool, copy_skills: bool) -> None:
        self.target = target
        self.dry_run = dry_run
        self.upgrade = upgrade
        self.copy_skills = copy_skills
        self.counts = {"add": 0, "update": 0, "skip": 0, "link": 0}

    def log(self, action: str, path: str, note: str = "") -> None:
        self.counts[action] += 1
        suffix = f"  ({note})" if note else ""
        print(f"{action:>6}  {path}{suffix}")

    def conflict(self, name: str) -> str | None:
        for other in CONFLICTS.get(name, ()):
            if (self.target / other).exists():
                return f"project already uses {other}"
        section = PYPROJECT_SECTIONS.get(name)
        pyproject = self.target / "pyproject.toml"
        if section and pyproject.is_file() and section in pyproject.read_text(encoding="utf-8"):
            return f"pyproject.toml already has {section}]"
        return None

    def place(self, source: Path, relative: str, managed: bool = False) -> None:
        destination = self.target / relative
        if destination.exists() or destination.is_symlink():
            if managed and self.upgrade and destination.is_file() and not destination.is_symlink():
                if destination.read_bytes() == source.read_bytes():
                    return
                self.log("update", relative)
                if not self.dry_run:
                    shutil.copy2(source, destination)
                return
            self.log("skip", relative, "exists")
            return
        reason = self.conflict(destination.name)
        if reason:
            self.log("skip", relative, reason)
            return
        self.log("add", relative)
        if not self.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def place_tree(self, source_root: Path, target_prefix: str = "", managed: bool = False) -> None:
        for source in sorted(p for p in source_root.rglob("*") if p.is_file()):
            if "__pycache__" in source.parts:
                continue
            relative = source.relative_to(source_root).as_posix()
            self.place(source, f"{target_prefix}{relative}", managed)

    def link_claude_skill(self, name: str) -> None:
        relative = f".claude/skills/{name}"
        destination = self.target / relative
        if destination.exists() or destination.is_symlink():
            if not destination.is_symlink() and self.upgrade and self.copy_skills:
                self.place_tree(AGENT / "skills" / name, f"{relative}/", managed=True)
            elif not destination.is_symlink():
                self.log("skip", relative, "exists")
            return
        if self.copy_skills:
            self.place_tree(AGENT / "skills" / name, f"{relative}/", managed=True)
            return
        self.log("link", relative, f"-> ../../.agents/skills/{name}")
        if not self.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(
                Path("..") / ".." / ".agents" / "skills" / name,
                destination,
                target_is_directory=True,
            )

    def run(self, stacks: list[str], agents: list[str]) -> None:
        # Shared by every agent: instructions, guard, skills.
        self.place_tree(TEMPLATES / "common")
        self.place(AGENT / "hooks" / "policy.py", ".agents/hooks/policy.py", managed=True)
        self.place(AGENT / "policy.json", ".agents/policy.json")
        skills = sorted(p.name for p in (AGENT / "skills").iterdir() if (p / "SKILL.md").is_file())
        for name in skills:
            self.place_tree(AGENT / "skills" / name, f".agents/skills/{name}/", managed=True)

        for stack in stacks:
            self.place_tree(TEMPLATES / stack)

        if "codex" in agents:
            self.place(AGENT / "codex" / "hooks.json", ".codex/hooks.json")
            self.place(AGENT / "codex" / "config.toml", ".codex/config.toml")
        if "claude" in agents:
            self.place(AGENT / "claude" / "settings.json", ".claude/settings.json")
            for name in skills:
                self.link_claude_skill(name)
        if "pi" in agents:
            self.place(
                AGENT / "pi" / "extensions" / "agent-policy.ts",
                ".pi/extensions/agent-policy.ts",
                managed=True,
            )

    def summary(self, agents: list[str]) -> None:
        c = self.counts
        mode = " (dry run, nothing written)" if self.dry_run else ""
        print(
            f"\n{c['add']} added, {c['link']} linked, {c['update']} updated, {c['skip']} skipped{mode}."
        )
        if c["skip"]:
            print("Reconcile every `skip` line by hand; the adopt-standards skill explains how.")
        print("\nNext steps:")
        print("  1. Fill the <placeholders> in AGENTS.md with the project's real commands.")
        print("  2. Run `pre-commit install` once per clone.")
        if "codex" in agents:
            print("  3. Codex: trust the project, then review the hook once with `/hooks`.")
        if "claude" in agents:
            print("  4. Claude Code: approve the project hooks when prompted (see `/hooks`).")
        if "pi" in agents:
            print(
                "  5. pi: the guard extension loads from .pi/extensions; run `/reload` in a running session."
            )


def parse_list(
    value: str, allowed: tuple[str, ...], aliases: dict[str, str] | None = None
) -> list[str]:
    items = []
    for raw in filter(None, (part.strip().lower() for part in value.split(","))):
        item = (aliases or {}).get(raw, raw)
        if item not in allowed:
            raise argparse.ArgumentTypeError(
                f"unknown value {raw!r}; choose from {', '.join(allowed)}"
            )
        if item not in items:
            items.append(item)
    return items


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
        "--dry-run", action="store_true", help="print what would happen without writing"
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="refresh kit-managed files (guard, skills, pi extension)",
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

    installer = Installer(target, args.dry_run, args.upgrade, args.copy_skills)
    installer.run(stacks, agents)
    installer.summary(agents)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Browse, install and manage the kit's skills per project or per user.

Commands:
  list      show skills by category, and the install profiles
  install   install skills into a project (--target) or for the user (--global)
  remove    uninstall skills that came from the kit
  status    show which kit skills a project or the user has, and whether they are current
  new       scaffold a new skill in this repository
  catalog   regenerate (--write) or check (--check) the catalog table in skills/README.md

Examples:
  python3 scripts/skills.py list
  python3 scripts/skills.py install --target ../app --profile core --skill some-skill
  python3 scripts/skills.py install --global --profile kit
  python3 scripts/skills.py status --target ../app
  python3 scripts/skills.py new frontend ui-check

Python 3.11+, standard library only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kitlib import KIT, NAME_RE, SKILLS_ROOT, Catalog, Skill, Writer, same_tree, split_list

AGENTS = ("codex", "claude", "pi")
README = SKILLS_ROOT / "README.md"
START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"


# --------------------------------------------------------------------------- install helpers


def project_skill_dirs(target: Path) -> tuple[Path, Path]:
    return target / ".agents" / "skills", target / ".claude" / "skills"


def install_project(
    writer: Writer, target: Path, skills: list[Skill], agents: list[str], copy: bool
) -> None:
    """Copy skills into .agents/skills (read by Codex and pi) and expose them to Claude Code."""
    shared, claude = project_skill_dirs(target)
    for skill in skills:
        writer.copy_skill(skill, shared / skill.name)
        if "claude" in agents:
            if copy:
                writer.copy_skill(skill, claude / skill.name)
            else:
                link_target = Path("..") / ".." / ".agents" / "skills" / skill.name
                writer.link(link_target, claude / skill.name, expected=shared / skill.name)


def global_dirs(agents: list[str]) -> list[Path]:
    home = Path.home()
    dirs = []
    if "codex" in agents or "pi" in agents:
        dirs.append(home / ".agents" / "skills")
    if "claude" in agents:
        dirs.append(home / ".claude" / "skills")
    return dirs


def install_global(writer: Writer, skills: list[Skill], agents: list[str]) -> None:
    """Symlink skills into the user's skill directories so `git pull` keeps them current."""
    for directory in global_dirs(agents):
        for skill in skills:
            writer.link(skill.path, directory / skill.name, expected=skill.path)


def installed_kit_skills(catalog: Catalog, target: Path) -> list[str]:
    shared, _ = project_skill_dirs(target)
    if not shared.is_dir():
        return []
    return sorted(p.name for p in shared.iterdir() if p.is_dir() and p.name in catalog.skills)


# --------------------------------------------------------------------------- commands


def cmd_list(catalog: Catalog, args: argparse.Namespace) -> int:
    for cid, skills in catalog.by_category().items():
        if args.category and cid != args.category:
            continue
        category = catalog.categories[cid]
        if not skills and not args.all:
            continue
        print(f"\n{cid}  {category.title}  ({category.description})")
        if not skills:
            print("    (no skills yet)")
        for skill in skills:
            print(f"    {skill.name:<22} {skill.display_name}  {skill.short_description}")
    print("\nprofiles")
    for profile in catalog.profiles.values():
        marker = " (default)" if profile.default else ""
        print(f"    {profile.id + marker:<22} {profile.description}")
        print(f"    {'':<22} {', '.join(profile.skills)}")
    empty = [cid for cid, skills in catalog.by_category().items() if not skills]
    if empty and not args.all and not args.category:
        print(f"\nempty categories: {', '.join(empty)} (show with --all)")
    return 0


def selected_skills(catalog: Catalog, args: argparse.Namespace, fallback: list[str]) -> list[Skill]:
    profiles = split_list(args.profile)
    names = split_list(args.skill)
    if not profiles and not names:
        names = fallback
    return catalog.resolve(profiles, names)


def cmd_install(catalog: Catalog, args: argparse.Namespace) -> int:
    agents = parse_agents(args.agents)
    if args.global_:
        writer = Writer(Path.home(), args.dry_run)
        skills = selected_skills(catalog, args, [])
        if not skills:
            print(
                "error: name the skills to install globally with --profile or --skill",
                file=sys.stderr,
            )
            return 2
        install_global(writer, skills, agents)
    else:
        target = resolve_target(args.target)
        writer = Writer(target, args.dry_run, args.upgrade)
        default = installed_kit_skills(catalog, target) if args.upgrade else []
        if not default and not args.upgrade:
            default = [
                n for pid in catalog.default_profiles() for n in catalog.profiles[pid].skills
            ]
        install_project(writer, target, selected_skills(catalog, args, default), agents, args.copy)
    print(f"\n{writer.summary()}")
    return 0


def cmd_remove(catalog: Catalog, args: argparse.Namespace) -> int:
    names = split_list(args.skill)
    if not names:
        print("error: name the skills to remove with --skill", file=sys.stderr)
        return 2
    refused = 0
    if args.global_:
        writer = Writer(Path.home(), args.dry_run)
        for directory in global_dirs(list(AGENTS)):
            for name in names:
                path = directory / name
                if path.is_symlink() and path.resolve().is_relative_to(KIT):
                    writer.remove(path)
                elif path.exists() or path.is_symlink():
                    print(f"refuse  {path}  (not a link into this kit)")
                    refused += 1
    else:
        target = resolve_target(args.target)
        writer = Writer(target, args.dry_run)
        shared, claude = project_skill_dirs(target)
        for name in names:
            kit_skill = catalog.skills.get(name)
            for path in (claude / name, shared / name):
                if path.is_symlink():
                    writer.remove(path)
                elif path.is_dir():
                    pristine = kit_skill is not None and same_tree(kit_skill.path, path)
                    if pristine or args.force:
                        writer.remove(path)
                    else:
                        print(
                            f"refuse  {writer.show(path)}  (modified or not from the kit; use --force)"
                        )
                        refused += 1
    print(f"\n{writer.summary()}")
    return 1 if refused else 0


def cmd_status(catalog: Catalog, args: argparse.Namespace) -> int:
    if args.global_:
        dirs = global_dirs(list(AGENTS))
        print(
            f"{'skill':<22} "
            + " ".join(f"{str(d).replace(str(Path.home()), '~'):<18}" for d in dirs)
        )
        for skill in sorted(catalog.skills.values(), key=lambda s: s.name):
            cells = []
            for directory in dirs:
                path = directory / skill.name
                if path.is_symlink() and path.resolve() == skill.path.resolve():
                    cells.append("linked")
                elif path.exists():
                    cells.append("other copy")
                else:
                    cells.append("-")
            print(f"{skill.name:<22} " + " ".join(f"{c:<18}" for c in cells))
        return 0

    target = resolve_target(args.target)
    shared, claude = project_skill_dirs(target)
    present = sorted(p for p in shared.iterdir() if p.is_dir()) if shared.is_dir() else []
    if not present:
        print("no skills installed in .agents/skills")
    for path in present:
        kit_skill = catalog.skills.get(path.name)
        if kit_skill is None:
            state = "local (not from the kit)"
        elif same_tree(kit_skill.path, path):
            state = f"current  [{kit_skill.category}]"
        else:
            state = f"differs from the kit (outdated or edited)  [{kit_skill.category}]"
        claude_path = claude / path.name
        if claude_path.is_symlink():
            claude_state = "claude: linked"
        elif claude_path.is_dir():
            claude_state = "claude: copy"
        else:
            claude_state = "claude: -"
        print(f"{path.name:<22} {state:<52} {claude_state}")
    missing = sorted(set(catalog.skills) - {p.name for p in present})
    if missing:
        print(f"\navailable but not installed: {', '.join(missing)}")
    return 0


SKILL_TEMPLATE = """---
name: {name}
description: <What this skill does.> Use when <the situations that should trigger it>. Do not use for <near misses that should not trigger it>.
---

# {title}

<One or two sentences: the outcome this skill produces and the principle behind it.>

## 1. <First step>

1. <Concrete action, with the command or file it touches.>
2. <...>

Finish this step when <observable completion condition>.

## 2. <Next step>

- <...>

## Report

End with <what the agent tells the user: results, evidence, open items>.
"""

METADATA_TEMPLATE = """interface:
  display_name: "{display_name}"
  short_description: "{short_description}"
  default_prompt: "使用 ${name} <描述要完成的任务>。"
"""


def cmd_new(catalog: Catalog, args: argparse.Namespace) -> int:
    name, category = args.name, args.category
    if category not in catalog.categories:
        print(
            f"error: unknown category {category!r}; choose from {', '.join(catalog.categories)}",
            file=sys.stderr,
        )
        return 2
    if not NAME_RE.match(name) or len(name) > 64:
        print(
            "error: name must be lowercase words joined by hyphens, at most 64 characters",
            file=sys.stderr,
        )
        return 2
    if name in catalog.skills:
        print(
            f"error: skill {name!r} already exists at {catalog.where(catalog.skills[name].path)}",
            file=sys.stderr,
        )
        return 2
    skill_dir = catalog.root / category / name
    (skill_dir / "agents").mkdir(parents=True)
    title = name.replace("-", " ").title()
    (skill_dir / "SKILL.md").write_text(
        SKILL_TEMPLATE.format(name=name, title=title), encoding="utf-8"
    )
    (skill_dir / "agents" / "openai.yaml").write_text(
        METADATA_TEMPLATE.format(
            name=name,
            display_name=args.display_name or title,
            short_description=args.short_description or "<一句话说明>",
        ),
        encoding="utf-8",
    )
    print(f"created {catalog.where(skill_dir)}/SKILL.md and agents/openai.yaml")
    print(
        "next: fill in both files, add the skill to a profile in skills/catalog.toml if it belongs in one,"
    )
    print("      then run `python3 scripts/skills.py catalog --write` and `make check`.")
    return 0


def render_catalog(catalog: Catalog) -> str:
    grouped = catalog.by_category()
    lines = [START, "", "| 分类 | 用途 | 数量 |", "| --- | --- | --- |"]
    for cid, skills in grouped.items():
        category = catalog.categories[cid]
        lines.append(f"| `{cid}` {category.title} | {category.description} | {len(skills)} |")
    for cid, skills in grouped.items():
        if not skills:
            continue
        lines += [
            "",
            f"### `{cid}` {catalog.categories[cid].title}",
            "",
            "| Skill | 名称 | 说明 |",
            "| --- | --- | --- |",
        ]
        for skill in skills:
            link = skill.path.relative_to(catalog.root).as_posix()
            lines.append(
                f"| [`{skill.name}`]({link}/SKILL.md) | {skill.display_name} | {skill.short_description} |"
            )
    lines += [
        "",
        "### 预设组合（profile）",
        "",
        "| Profile | 默认安装 | 说明 | 包含 |",
        "| --- | --- | --- | --- |",
    ]
    for profile in catalog.profiles.values():
        default = "是" if profile.default else ""
        members = "、".join(f"`{s}`" for s in profile.skills)
        lines.append(f"| `{profile.id}` | {default} | {profile.description} | {members} |")
    lines += ["", END]
    return "\n".join(lines)


def cmd_catalog(catalog: Catalog, args: argparse.Namespace) -> int:
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print(f"error: {README} needs {START} and {END} markers", file=sys.stderr)
        return 1
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    updated = head + render_catalog(catalog) + tail
    if args.check:
        if updated != text:
            print(
                "error: skills/README.md catalog is stale; run `python3 scripts/skills.py catalog --write`",
                file=sys.stderr,
            )
            return 1
        return 0
    README.write_text(updated, encoding="utf-8")
    print(f"updated {catalog.where(README)}")
    return 0


# --------------------------------------------------------------------------- cli


def parse_agents(value: str) -> list[str]:
    agents = split_list(value)
    unknown = [a for a in agents if a not in AGENTS]
    if unknown:
        raise SystemExit(f"error: unknown agent {unknown[0]!r}; choose from {', '.join(AGENTS)}")
    return agents


def resolve_target(value: str) -> Path:
    target = Path(value).resolve()
    if not target.is_dir():
        raise SystemExit(f"error: target {target} is not a directory")
    if target == KIT:
        raise SystemExit("error: refusing to install the kit into itself")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the kit's skills.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="show skills by category and the profiles")
    p.add_argument("--category", help="only this category")
    p.add_argument("--all", action="store_true", help="include empty categories")

    def scope(p: argparse.ArgumentParser) -> None:
        group = p.add_mutually_exclusive_group()
        group.add_argument("--target", default=".", help="project root (default: .)")
        group.add_argument(
            "--global", dest="global_", action="store_true", help="the user's skill directories"
        )

    p = sub.add_parser("install", help="install skills into a project or for the user")
    scope(p)
    p.add_argument("--profile", default="", help="comma list of profiles")
    p.add_argument("--skill", default="", help="comma list of skills")
    p.add_argument(
        "--agents", default=",".join(AGENTS), help="comma list: codex, claude, pi (default: all)"
    )
    p.add_argument(
        "--copy",
        action="store_true",
        help="copy into .claude/skills instead of symlinking (Windows)",
    )
    p.add_argument(
        "--upgrade",
        action="store_true",
        help="refresh installed kit skills that differ from the kit",
    )
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("remove", help="uninstall kit skills")
    scope(p)
    p.add_argument("--skill", default="", help="comma list of skills")
    p.add_argument(
        "--force", action="store_true", help="also remove copies that were edited locally"
    )
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("status", help="show installed kit skills")
    scope(p)

    p = sub.add_parser("new", help="scaffold a new skill in this repository")
    p.add_argument("category")
    p.add_argument("name")
    p.add_argument("--display-name", default="", help="Chinese display name for agents/openai.yaml")
    p.add_argument("--short-description", default="", help="one-line Chinese summary")

    p = sub.add_parser("catalog", help="regenerate or check the catalog table in skills/README.md")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser


COMMANDS = {
    "list": cmd_list,
    "install": cmd_install,
    "remove": cmd_remove,
    "status": cmd_status,
    "new": cmd_new,
    "catalog": cmd_catalog,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = Catalog()
    if catalog.errors and args.command not in {"new", "catalog"}:
        for error in catalog.errors:
            print(f"error: {error}", file=sys.stderr)
        print("fix the catalog first (`make check` lists every problem)", file=sys.stderr)
        return 1
    try:
        return COMMANDS[args.command](catalog, args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

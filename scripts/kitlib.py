"""Shared helpers for the kit scripts: the skill catalog and safe file placement.

Python 3.11+, standard library only.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import tomllib

KIT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = KIT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LICENSE_FILES = ("LICENSE", "LICENSE.txt", "LICENSE.md")
IGNORED = {"__pycache__", ".DS_Store"}


# --------------------------------------------------------------------------- catalog


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    path: Path
    description: str
    display_name: str
    short_description: str


@dataclass(frozen=True)
class Category:
    id: str
    title: str
    description: str


@dataclass(frozen=True)
class Profile:
    id: str
    description: str
    skills: tuple[str, ...]
    default: bool


def read_frontmatter(text: str) -> dict[str, str] | None:
    """Parse the top-level scalar keys of a SKILL.md frontmatter block."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    fields: dict[str, str] = {}
    lines = match.group(1).splitlines()
    index = 0
    while index < len(lines):
        key, sep, value = lines[index].partition(":")
        index += 1
        if not sep or key.startswith((" ", "\t")):
            continue
        value = value.strip()
        if value in {">", "|", ">-", "|-"}:  # folded or literal block
            block = []
            while index < len(lines) and (lines[index].startswith((" ", "\t")) or not lines[index]):
                block.append(lines[index].strip())
                index += 1
            value = " ".join(part for part in block if part)
        fields[key.strip()] = value.strip("\"'")
    return fields


def read_interface(path: Path) -> dict[str, str]:
    """Read the `interface` scalars from a skill's agents/openai.yaml."""
    if not path.is_file():
        return {}
    interface: dict[str, str] = {}
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith((" ", "\t")):
            inside = line.strip() == "interface:"
            continue
        match = re.match(r"^\s+([a-z_]+):\s*(.*)$", line)
        if inside and match:
            interface[match.group(1)] = match.group(2).strip().strip("\"'")
    return interface


class Catalog:
    """Skills on disk plus the categories and profiles in catalog.toml."""

    def __init__(self, root: Path = SKILLS_ROOT) -> None:
        self.root = root
        self.errors: list[str] = []
        data = tomllib.loads((root / "catalog.toml").read_text(encoding="utf-8"))
        self.categories = {
            cid: Category(cid, str(v.get("title", "")), str(v.get("description", "")))
            for cid, v in data.get("categories", {}).items()
        }
        self.profiles = {
            pid: Profile(
                pid,
                str(v.get("description", "")),
                tuple(v.get("skills", ())),
                bool(v.get("default", False)),
            )
            for pid, v in data.get("profiles", {}).items()
        }
        self.provenance: dict[str, dict[str, str]] = data.get("skills", {})
        self.skills: dict[str, Skill] = {}
        self._scan()
        self._check()

    def where(self, path: Path) -> str:
        try:
            return path.relative_to(self.root.parent).as_posix()
        except ValueError:
            return str(path)

    def _scan(self) -> None:
        for category_dir in sorted(
            p for p in self.root.iterdir() if p.is_dir() and p.name not in IGNORED
        ):
            if category_dir.name not in self.categories:
                self.errors.append(
                    f"{self.where(category_dir)}: category is not defined in catalog.toml"
                )
                continue
            for skill_dir in sorted(
                p for p in category_dir.iterdir() if p.is_dir() and p.name not in IGNORED
            ):
                self._load_skill(category_dir.name, skill_dir)

    def _load_skill(self, category: str, skill_dir: Path) -> None:
        where = self.where(skill_dir)
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            self.errors.append(f"{where}: missing SKILL.md")
            return
        fields = read_frontmatter(skill_md.read_text(encoding="utf-8"))
        if fields is None:
            self.errors.append(f"{where}/SKILL.md: missing YAML frontmatter")
            return
        name, description = fields.get("name", ""), fields.get("description", "")
        if name != skill_dir.name:
            self.errors.append(
                f"{where}/SKILL.md: name {name!r} must match directory {skill_dir.name!r}"
            )
        if not NAME_RE.match(name) or len(name) > 64:
            self.errors.append(
                f"{where}/SKILL.md: name must be lowercase words joined by hyphens, at most 64 characters"
            )
        if not description:
            self.errors.append(f"{where}/SKILL.md: description is required")
        elif len(description) > 1024:
            self.errors.append(
                f"{where}/SKILL.md: description is {len(description)} characters; the limit is 1024"
            )
        interface = read_interface(skill_dir / "agents" / "openai.yaml")
        if not interface:
            self.errors.append(f"{where}: missing agents/openai.yaml with an interface block")
        else:
            for key in ("display_name", "short_description", "default_prompt"):
                if not interface.get(key):
                    self.errors.append(f"{where}/agents/openai.yaml: interface.{key} is required")
            if f"${name}" not in interface.get("default_prompt", ""):
                self.errors.append(
                    f"{where}/agents/openai.yaml: default_prompt should invoke ${name}"
                )
        if any((skill_dir / f).exists() for f in LICENSE_FILES):
            entry = self.provenance.get(name, {})
            if not entry.get("source") or not entry.get("license"):
                self.errors.append(
                    f"{where}: ships its own license, so catalog.toml needs [skills.{name}] with source and license"
                )
        if name in self.skills:
            self.errors.append(
                f"{where}: skill name {name!r} is already used by {self.where(self.skills[name].path)}"
            )
            return
        self.skills[name] = Skill(
            name=name,
            category=category,
            path=skill_dir,
            description=description,
            display_name=interface.get("display_name", name),
            short_description=interface.get("short_description", ""),
        )

    def _check(self) -> None:
        for profile in self.profiles.values():
            if not NAME_RE.match(profile.id):
                self.errors.append(
                    f"catalog.toml: profile id {profile.id!r} must be lowercase words joined by hyphens"
                )
            if not profile.skills:
                self.errors.append(f"catalog.toml: profile {profile.id!r} lists no skills")
            for name in profile.skills:
                if name not in self.skills:
                    self.errors.append(
                        f"catalog.toml: profile {profile.id!r} lists unknown skill {name!r}"
                    )
        for name in self.provenance:
            if name not in self.skills:
                self.errors.append(
                    f"catalog.toml: [skills.{name}] describes a skill that does not exist"
                )
        for category in self.categories:
            if not NAME_RE.match(category):
                self.errors.append(
                    f"catalog.toml: category id {category!r} must be lowercase words joined by hyphens"
                )

    def default_profiles(self) -> list[str]:
        return [p.id for p in self.profiles.values() if p.default]

    def resolve(self, profiles: list[str], names: list[str]) -> list[Skill]:
        """Expand profiles and explicit names into skills, in a stable order."""
        wanted: list[str] = []
        for pid in profiles:
            if pid not in self.profiles:
                raise ValueError(f"unknown profile {pid!r}; choose from {', '.join(self.profiles)}")
            wanted.extend(self.profiles[pid].skills)
        for name in names:
            if name not in self.skills:
                raise ValueError(f"unknown skill {name!r}; run `python3 scripts/skills.py list`")
            wanted.append(name)
        return [self.skills[name] for name in dict.fromkeys(wanted)]

    def by_category(self) -> dict[str, list[Skill]]:
        grouped: dict[str, list[Skill]] = {cid: [] for cid in self.categories}
        for skill in sorted(self.skills.values(), key=lambda s: s.name):
            grouped[skill.category].append(skill)
        return grouped


# --------------------------------------------------------------------------- files


def tree_files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and not IGNORED.intersection(p.relative_to(root).parts)
    }


def same_tree(left: Path, right: Path) -> bool:
    return left.is_dir() and right.is_dir() and tree_files(left) == tree_files(right)


def split_list(value: str) -> list[str]:
    return list(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))


class Writer:
    """Places files without ever overwriting user files, and reports each action."""

    def __init__(self, base: Path, dry_run: bool = False, upgrade: bool = False) -> None:
        self.base = base
        self.dry_run = dry_run
        self.upgrade = upgrade
        self.counts = {"add": 0, "link": 0, "update": 0, "remove": 0, "skip": 0}

    def show(self, path: Path) -> str:
        try:
            return path.relative_to(self.base).as_posix()
        except ValueError:
            return str(path)

    def log(self, action: str, path: Path, note: str = "") -> None:
        self.counts[action] += 1
        suffix = f"  ({note})" if note else ""
        print(f"{action:>6}  {self.show(path)}{suffix}")

    def place(
        self, source: Path, destination: Path, managed: bool = False, conflict: str | None = None
    ) -> None:
        if destination.exists() or destination.is_symlink():
            if managed and self.upgrade and destination.is_file() and not destination.is_symlink():
                if destination.read_bytes() != source.read_bytes():
                    self.log("update", destination)
                    if not self.dry_run:
                        shutil.copy2(source, destination)
                return
            self.log("skip", destination, "exists")
            return
        if conflict:
            self.log("skip", destination, conflict)
            return
        self.log("add", destination)
        if not self.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def place_tree(self, source_root: Path, destination_root: Path) -> None:
        for relative in tree_files(source_root):
            self.place(source_root / relative, destination_root / relative)

    def copy_skill(self, skill: Skill, destination: Path) -> None:
        """Copy a whole skill directory; with upgrade, replace an outdated copy."""
        if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            self.log("skip", destination, "exists and is not a skill copy")
            return
        if destination.is_dir():
            if same_tree(skill.path, destination):
                return
            if not self.upgrade:
                self.log("skip", destination, "differs from the kit; use --upgrade to refresh")
                return
            self.log("update", destination)
            if not self.dry_run:
                shutil.rmtree(destination)
                shutil.copytree(skill.path, destination, ignore=shutil.ignore_patterns(*IGNORED))
            return
        self.log("add", destination)
        if not self.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill.path, destination, ignore=shutil.ignore_patterns(*IGNORED))

    def link(self, target: Path, destination: Path, expected: Path | None = None) -> None:
        """Create a directory symlink at `destination` pointing to `target`."""
        if destination.is_symlink():
            if expected is not None and destination.resolve() == expected.resolve():
                return
            self.log("skip", destination, f"links elsewhere ({os.readlink(destination)})")
            return
        if destination.exists():
            self.log("skip", destination, "exists")
            return
        self.log("link", destination, f"-> {target}")
        if not self.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, destination, target_is_directory=True)

    def remove(self, path: Path) -> None:
        self.log("remove", path)
        if self.dry_run:
            return
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)

    def summary(self) -> str:
        labels = {
            "add": "added",
            "link": "linked",
            "update": "updated",
            "remove": "removed",
            "skip": "skipped",
        }
        mode = " (dry run, nothing written)" if self.dry_run else ""
        return ", ".join(f"{self.counts[k]} {label}" for k, label in labels.items()) + mode + "."

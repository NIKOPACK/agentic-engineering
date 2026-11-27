#!/usr/bin/env python3
"""Validate the kit: config files parse, skills follow the Agent Skills format.

Run from anywhere: `python3 scripts/validate.py`. Exit code 1 on any error.
YAML parsing needs PyYAML; without it YAML files are skipped with a warning
(CI installs it).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

try:
    import yaml
except ImportError:  # pragma: no cover - depends on the environment
    yaml = None  # type: ignore[assignment]


def files(*suffixes: str) -> list[Path]:
    return sorted(
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.suffix in suffixes
        and not SKIP_DIRS.intersection(p.relative_to(ROOT).parts)
    )


def check_configs(errors: list[str]) -> None:
    for path in files(".json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
    for path in files(".toml"):
        try:
            tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid TOML: {exc}")
    yaml_files = files(".yml", ".yaml")
    if yaml is None:
        print(
            f"warning: PyYAML not installed; skipped {len(yaml_files)} YAML files", file=sys.stderr
        )
        return
    for path in yaml_files:
        try:
            list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid YAML: {exc}")


def frontmatter(text: str) -> dict[str, str] | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith(" "):
            fields[key.strip()] = value.strip()
    return fields


def check_skills(errors: list[str]) -> None:
    skills_dir = ROOT / "agent" / "skills"
    for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        where = skill.relative_to(ROOT)
        skill_md = skill / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{where}: missing SKILL.md")
            continue
        fields = frontmatter(skill_md.read_text(encoding="utf-8"))
        if fields is None:
            errors.append(f"{where}/SKILL.md: missing YAML frontmatter")
            continue
        name, description = fields.get("name", ""), fields.get("description", "")
        if name != skill.name:
            errors.append(f"{where}/SKILL.md: name {name!r} must match directory {skill.name!r}")
        if not NAME_RE.match(name) or len(name) > 64:
            errors.append(
                f"{where}/SKILL.md: name must be lowercase words joined by hyphens, at most 64 characters"
            )
        if not description:
            errors.append(f"{where}/SKILL.md: description is required")
        elif len(description) > 1024:
            errors.append(
                f"{where}/SKILL.md: description is {len(description)} characters; the limit is 1024"
            )
        metadata = skill / "agents" / "openai.yaml"
        if not metadata.is_file():
            errors.append(f"{where}: missing agents/openai.yaml")
        elif yaml is not None:
            interface = (yaml.safe_load(metadata.read_text(encoding="utf-8")) or {}).get(
                "interface", {}
            )
            for key in ("display_name", "short_description", "default_prompt"):
                if not interface.get(key):
                    errors.append(f"{where}/agents/openai.yaml: interface.{key} is required")
            if f"${name}" not in interface.get("default_prompt", ""):
                errors.append(f"{where}/agents/openai.yaml: default_prompt should invoke ${name}")


def main() -> int:
    errors: list[str] = []
    check_configs(errors)
    check_skills(errors)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    print("validate: " + ("FAILED" if errors else "ok"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

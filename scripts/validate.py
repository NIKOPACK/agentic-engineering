#!/usr/bin/env python3
"""Validate the kit: config files parse, the skill catalog is consistent.

Run from anywhere: `python3 scripts/validate.py`. Exit code 1 on any error.
YAML parsing needs PyYAML; without it YAML files are skipped with a warning
(CI installs it).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import tomllib

import skills
from kitlib import Catalog

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}

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


def check_skills(errors: list[str]) -> None:
    catalog = Catalog()
    errors.extend(catalog.errors)
    if not catalog.errors and skills.main(["catalog", "--check"]) != 0:
        errors.append("skills/README.md: catalog table is stale")
    if yaml is None:
        return
    for skill in catalog.skills.values():
        metadata = skill.path / "agents" / "openai.yaml"
        try:
            yaml.safe_load(metadata.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{catalog.where(metadata)}: invalid YAML: {exc}")


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

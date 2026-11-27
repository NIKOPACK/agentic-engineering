"""Tests for scripts/skills.py and the catalog in scripts/kitlib.py."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skills.py"
sys.path.insert(0, str(ROOT / "scripts"))

from kitlib import Catalog, read_frontmatter  # noqa: E402


class CatalogTests(unittest.TestCase):
    """Validation rules, exercised on a scratch copy of skills/."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "skills"
        shutil.copytree(ROOT / "skills", self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def errors(self) -> list[str]:
        return Catalog(self.root).errors

    def test_repository_catalog_is_valid(self) -> None:
        self.assertEqual(Catalog().errors, [])

    def test_every_skill_has_a_category_and_core_exists(self) -> None:
        catalog = Catalog()
        for skill in catalog.skills.values():
            self.assertIn(skill.category, catalog.categories)
        self.assertTrue(catalog.profiles["core"].default)

    def test_undefined_category(self) -> None:
        (self.root / "misc").mkdir()
        self.assertTrue(any("category is not defined" in e for e in self.errors()))

    def test_duplicate_name_across_categories(self) -> None:
        shutil.copytree(self.root / "workflow" / "spec-first", self.root / "docs" / "spec-first")
        self.assertTrue(any("already used" in e for e in self.errors()))

    def test_name_must_match_directory(self) -> None:
        shutil.move(self.root / "workflow" / "spec-first", self.root / "workflow" / "spec-first-2")
        self.assertTrue(any("must match directory" in e for e in self.errors()))

    def test_profile_with_unknown_skill(self) -> None:
        catalog = self.root / "catalog.toml"
        catalog.write_text(
            catalog.read_text() + '\n[profiles.broken]\ndescription = "x"\nskills = ["nope"]\n'
        )
        self.assertTrue(any("unknown skill 'nope'" in e for e in self.errors()))

    def test_external_skill_needs_provenance(self) -> None:
        (self.root / "workflow" / "spec-first" / "LICENSE").write_text("Apache-2.0\n")
        self.assertTrue(any("needs [skills.spec-first]" in e for e in self.errors()))
        catalog = self.root / "catalog.toml"
        catalog.write_text(
            catalog.read_text()
            + '\n[skills.spec-first]\nsource = "https://example.com/x"\nlicense = "Apache-2.0"\n'
        )
        self.assertEqual(self.errors(), [])

    def test_missing_metadata(self) -> None:
        (self.root / "workflow" / "spec-first" / "agents" / "openai.yaml").unlink()
        self.assertTrue(any("missing agents/openai.yaml" in e for e in self.errors()))

    def test_folded_description(self) -> None:
        fields = read_frontmatter(
            "---\nname: x\ndescription: >\n  Does a thing.\n  Use when needed.\n---\nbody\n"
        )
        self.assertEqual(fields, {"name": "x", "description": "Does a thing. Use when needed."})

    def test_resolve(self) -> None:
        catalog = Catalog()
        names = [s.name for s in catalog.resolve(["core"], ["verify-change", "adopt-standards"])]
        self.assertEqual(names, [*catalog.profiles["core"].skills, "adopt-standards"])
        with self.assertRaises(ValueError):
            catalog.resolve(["nope"], [])


class CommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.target = Path(self.tmp.name) / "project"
        self.home.mkdir()
        self.target.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *args: str, expect: int = 0) -> str:
        env = {**os.environ, "HOME": str(self.home)}
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_list(self) -> None:
        output = self.run_cli("list")
        self.assertIn("workflow", output)
        self.assertIn("core (default)", output)
        self.assertIn("frontend", self.run_cli("list", "--all"))

    def test_project_install_status_remove(self) -> None:
        self.run_cli("install", "--target", str(self.target), "--skill", "spec-first,verify-change")
        shared = self.target / ".agents/skills"
        self.assertTrue((shared / "spec-first/SKILL.md").is_file())
        self.assertTrue((self.target / ".claude/skills/spec-first").is_symlink())

        (shared / "verify-change/SKILL.md").write_text("edited\n")
        status = self.run_cli("status", "--target", str(self.target))
        self.assertRegex(status, r"spec-first\s+current")
        self.assertRegex(status, r"verify-change\s+differs from the kit")

        self.run_cli("remove", "--target", str(self.target), "--skill", "verify-change", expect=1)
        self.assertTrue(
            (shared / "verify-change").exists(), "edited copy must survive without --force"
        )
        self.run_cli("remove", "--target", str(self.target), "--skill", "spec-first")
        self.assertFalse((shared / "spec-first").exists())
        self.assertFalse((self.target / ".claude/skills/spec-first").exists())

    def test_default_install_is_core(self) -> None:
        self.run_cli("install", "--target", str(self.target), "--agents", "codex")
        installed = sorted(p.name for p in (self.target / ".agents/skills").iterdir())
        self.assertEqual(installed, sorted(Catalog().profiles["core"].skills))
        self.assertFalse((self.target / ".claude").exists())

    def test_global_install_links_into_the_kit(self) -> None:
        self.run_cli("install", "--global", "--profile", "kit")
        for directory in (".agents/skills", ".claude/skills"):
            link = self.home / directory / "adopt-standards"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (ROOT / "skills/kit/adopt-standards").resolve())
        self.assertRegex(self.run_cli("status", "--global"), r"adopt-standards\s+linked\s+linked")
        self.run_cli("install", "--global", expect=2)
        self.run_cli("remove", "--global", "--skill", "adopt-standards")
        self.assertFalse((self.home / ".claude/skills/adopt-standards").exists())

    def test_global_remove_leaves_foreign_skills(self) -> None:
        foreign = self.home / ".claude/skills/adopt-standards"
        foreign.mkdir(parents=True)
        self.run_cli("remove", "--global", "--skill", "adopt-standards", expect=1)
        self.assertTrue(foreign.is_dir())

    def test_unknown_skill(self) -> None:
        output = self.run_cli("install", "--target", str(self.target), "--skill", "nope", expect=2)
        self.assertIn("unknown skill", output)

    def test_catalog_is_up_to_date(self) -> None:
        self.run_cli("catalog", "--check")


class ScaffoldTests(unittest.TestCase):
    """`new` writes into the real skills/ tree, so it runs against a copy of the kit."""

    def test_new_skill_scaffold_validates_after_filling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp) / "kit"
            shutil.copytree(ROOT / "scripts", kit / "scripts")
            shutil.copytree(ROOT / "skills", kit / "skills")
            run = [sys.executable, str(kit / "scripts" / "skills.py")]
            result = subprocess.run(
                [
                    *run,
                    "new",
                    "frontend",
                    "ui-check",
                    "--display-name",
                    "UI 检查",
                    "--short-description",
                    "检查界面",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            skill_dir = kit / "skills/frontend/ui-check"
            self.assertIn("name: ui-check", (skill_dir / "SKILL.md").read_text())
            self.assertIn("$ui-check", (skill_dir / "agents/openai.yaml").read_text())
            self.assertEqual(Catalog(kit / "skills").errors, [])

            stale = subprocess.run(
                [*run, "catalog", "--check"], capture_output=True, text=True, check=False
            )
            self.assertEqual(stale.returncode, 1)
            subprocess.run([*run, "catalog", "--write"], check=True, capture_output=True)
            self.assertIn("ui-check", (kit / "skills/README.md").read_text())

            again = subprocess.run(
                [*run, "new", "frontend", "ui-check"], capture_output=True, text=True, check=False
            )
            self.assertEqual(again.returncode, 2)


if __name__ == "__main__":
    unittest.main()

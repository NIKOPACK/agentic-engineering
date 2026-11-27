"""Tests for scripts/install.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.py"
SKILLS = sorted(p.name for p in (ROOT / "agent" / "skills").iterdir() if (p / "SKILL.md").is_file())


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.target)], check=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def install(self, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, str(INSTALL), "--target", str(self.target), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_full_install(self) -> None:
        self.install("--stack", "typescript,python,go")
        for relative in (
            "AGENTS.md",
            "CLAUDE.md",
            ".editorconfig",
            ".pre-commit-config.yaml",
            ".github/pull_request_template.md",
            ".github/workflows/quality.yml",
            ".github/workflows/ci-typescript.yml",
            ".github/workflows/ci-python.yml",
            ".github/workflows/ci-go.yml",
            "biome.json",
            "tsconfig.json",
            "ruff.toml",
            "mypy.ini",
            "pytest.ini",
            ".golangci.yml",
            "docs/specs/_template.md",
            "docs/adr/0000-template.md",
            ".agents/hooks/policy.py",
            ".agents/policy.json",
            ".codex/hooks.json",
            ".codex/config.toml",
            ".claude/settings.json",
            ".pi/extensions/agent-policy.ts",
        ):
            with self.subTest(path=relative):
                self.assertTrue((self.target / relative).is_file(), relative)
        for name in SKILLS:
            self.assertTrue((self.target / ".agents/skills" / name / "SKILL.md").is_file())
            link = self.target / ".claude/skills" / name
            self.assertTrue(link.is_symlink())
            self.assertTrue((link / "SKILL.md").is_file(), "symlink must resolve")

    def test_installed_guard_works_from_project(self) -> None:
        self.install("--agents", "claude")
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "git push --force"},
            "cwd": str(self.target),
        }
        result = subprocess.run(
            [sys.executable, str(self.target / ".agents/hooks/policy.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)

    def test_never_overwrites(self) -> None:
        (self.target / "AGENTS.md").write_text("mine\n")
        output = self.install()
        self.assertEqual((self.target / "AGENTS.md").read_text(), "mine\n")
        self.assertIn("skip  AGENTS.md  (exists)", output)

    def test_conflicting_tools_are_respected(self) -> None:
        (self.target / "eslint.config.js").write_text("export default [];\n")
        (self.target / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
        output = self.install("--stack", "ts,py")
        self.assertFalse((self.target / "biome.json").exists())
        self.assertFalse((self.target / "mypy.ini").exists())
        self.assertTrue((self.target / "ruff.toml").exists())
        self.assertIn("project already uses eslint.config.js", output)

    def test_agent_selection(self) -> None:
        self.install("--agents", "codex")
        self.assertTrue((self.target / ".codex/hooks.json").exists())
        self.assertFalse((self.target / ".claude").exists())
        self.assertFalse((self.target / ".pi").exists())

    def test_upgrade_refreshes_only_managed_files(self) -> None:
        self.install()
        guard = self.target / ".agents/hooks/policy.py"
        guard.write_text("# stale\n")
        (self.target / ".agents/policy.json").write_text('{"protected_branches": ["trunk"]}\n')
        output = self.install("--upgrade")
        self.assertEqual(guard.read_bytes(), (ROOT / "agent/hooks/policy.py").read_bytes())
        self.assertIn("trunk", (self.target / ".agents/policy.json").read_text())
        self.assertIn("update  .agents/hooks/policy.py", output)

    def test_dry_run_writes_nothing(self) -> None:
        self.install("--dry-run", "--stack", "go")
        self.assertEqual(sorted(p.name for p in self.target.iterdir()), [".git"])

    def test_copy_skills(self) -> None:
        self.install("--agents", "claude", "--copy-skills")
        skill = self.target / ".claude/skills" / SKILLS[0]
        self.assertFalse(skill.is_symlink())
        self.assertTrue((skill / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()

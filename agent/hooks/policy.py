#!/usr/bin/env python3
"""Shared pre-tool-use guard for Codex, Claude Code and pi.

Reads one hook event as JSON on stdin and decides whether the tool call may run.

Exit codes follow the convention shared by Codex and Claude Code hooks:
  0  allow
  2  deny; the reason is written to stderr and shown to the agent
  1  the hook itself failed; the call is allowed (fail open) and a warning is printed

Project overrides live in `.agents/policy.json` at the repository root:
  {
    "protected_branches": ["main", "master", "release"],
    "disabled_rules": ["discard-work"],
    "extra_secret_patterns": ["(^|/)config/credentials\\\\.yml$"]
  }

Standard library only, Python 3.9+.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

DEFAULT_PROTECTED_BRANCHES = ("main", "master")

SHELL_TOOLS = {"bash", "shell", "exec_command", "local_shell", "container.exec"}
READ_TOOLS = {"read", "grep", "glob", "ls", "find", "view"}

SECRET_PATTERNS = (
    r"(^|/)\.env(\.[^/]+)?$",
    r"\.(pem|key|p12|pfx|jks|keystore)$",
    r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$",
    r"(^|/)\.aws/credentials$",
    r"(^|/)\.ssh/[^/]+$",
    r"(^|/)\.netrc$",
    r"(^|/)\.pypirc$",
    r"(^|/)credentials\.json$",
    r"(^|/)service[-_]account[^/]*\.json$",
)
SECRET_EXEMPT = re.compile(
    r"(^|/)\.env\.(example|sample|template|dist|defaults)(\.[^/]+)?$|\.pub$|(^|/)\.ssh/(config|known_hosts)$"
)

GUARD_PATHS = (
    r"(^|/)\.agents/hooks/",
    r"(^|/)\.agents/policy\.json$",
    r"(^|/)\.codex/hooks\.json$",
    r"(^|/)\.codex/config\.toml$",
    r"(^|/)\.claude/settings\.json$",
    r"(^|/)\.pi/extensions/agent-policy\.ts$",
)

PATCH_HEADER = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$", re.M)

SEPARATORS = {";", "&&", "||", "|", "&", "|&", "(", ")", "\n"}
WRAPPERS = {"sudo", "doas", "command", "builtin", "exec", "nohup", "time", "nice", "env", "xargs"}
INTERPRETERS = {
    "sh",
    "bash",
    "zsh",
    "dash",
    "ksh",
    "fish",
    "python",
    "python3",
    "node",
    "perl",
    "ruby",
}
DANGEROUS_RM_TARGETS = {
    "/",
    "/*",
    "~",
    "~/",
    "~/*",
    "$HOME",
    "${HOME}",
    "$HOME/",
    "${HOME}/",
    "$HOME/*",
    "*",
    ".",
    "./",
    "./*",
    "..",
    "../",
    "../*",
}

REMEDY = (
    "If the user explicitly wants this, ask them to run it themselves "
    "or to disable the rule in .agents/policy.json."
)


class DeniedError(Exception):
    def __init__(self, rule: str, reason: str) -> None:
        super().__init__(reason)
        self.rule = rule
        self.reason = reason


# --------------------------------------------------------------------------- config


def find_root(cwd: str) -> Path:
    path = Path(cwd).resolve()
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return path


def load_config(root: Path) -> dict[str, Any]:
    config_path = root / ".agents" / "policy.json"
    if not config_path.is_file():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[agent-policy] ignoring unreadable {config_path}: {exc}", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


class Policy:
    def __init__(self, cwd: str, config: dict[str, Any] | None = None) -> None:
        self.cwd = cwd
        self.root = find_root(cwd)
        config = load_config(self.root) if config is None else config
        self.protected = set(config.get("protected_branches") or DEFAULT_PROTECTED_BRANCHES)
        self.disabled = set(config.get("disabled_rules") or ())
        patterns = list(SECRET_PATTERNS) + list(config.get("extra_secret_patterns") or ())
        self.secret_res = [re.compile(p) for p in patterns]
        self.guard_res = [re.compile(p) for p in GUARD_PATHS]

    def deny(self, rule: str, reason: str) -> None:
        if rule not in self.disabled:
            raise DeniedError(rule, reason)

    # ------------------------------------------------------------------ paths

    def is_secret(self, path: str) -> bool:
        normalized = path.replace("\\", "/").strip("'\"")
        if not normalized or SECRET_EXEMPT.search(normalized):
            return False
        return any(r.search(normalized) for r in self.secret_res)

    def is_guard(self, path: str) -> bool:
        normalized = path.replace("\\", "/")
        return any(r.search(normalized) for r in self.guard_res)

    # ------------------------------------------------------------------ entry

    def check(self, tool_name: str, tool_input: Any) -> None:
        name = (tool_name or "").lower()
        if name in SHELL_TOOLS:
            command = tool_input.get("command") if isinstance(tool_input, dict) else tool_input
            if isinstance(command, list):
                command = shlex.join(str(part) for part in command)
            if isinstance(command, str):
                self.check_command(command)
            return
        paths = list(collect_paths(tool_input))
        for path in paths:
            if self.is_secret(path):
                self.deny(
                    "secret-file",
                    f"`{path}` looks like a secret or credential file; agents must not read or write it.",
                )
        if name in READ_TOOLS:
            return
        for path in paths:
            if self.is_guard(path):
                self.deny(
                    "guard-tamper",
                    f"`{path}` is part of the agent guardrails; only the user changes it.",
                )

    # ------------------------------------------------------------------ shell

    def check_command(self, command: str, depth: int = 0) -> None:
        if depth > 3:
            return
        self.check_raw(command)
        previous: list[str] = []
        for separator, argv, redirects in split_segments(command):
            for target in redirects:
                if self.is_secret(target):
                    self.deny(
                        "secret-file",
                        f"`{target}` looks like a secret or credential file; agents must not write it.",
                    )
            argv = strip_wrappers(argv)
            if not argv:
                continue
            program = os.path.basename(argv[0])
            piped = separator in {"|", "|&"} and previous
            if (
                piped
                and os.path.basename(previous[0]) in {"curl", "wget"}
                and program in INTERPRETERS
            ):
                self.deny(
                    "pipe-to-shell",
                    "Piping a download straight into an interpreter runs unreviewed code. Download, inspect, then run.",
                )
            if program in {"sh", "bash", "zsh", "dash"} and "-c" in argv[1:-1]:
                inner = argv[argv.index("-c") + 1]
                self.check_command(inner, depth + 1)
            self.check_secret_args(program, argv)
            if program == "rm":
                self.check_rm(argv)
            elif program == "git":
                self.check_git(argv)
            elif program.startswith("mkfs"):
                self.deny("disk-destroy", "Formatting a filesystem is never an agent task.")
            elif program == "dd" and any(arg.startswith("of=/dev/") for arg in argv):
                self.deny("disk-destroy", "Writing raw data to a device is never an agent task.")
            elif program == "chmod":
                self.check_chmod(argv)
            previous = argv

    def check_raw(self, command: str) -> None:
        if re.search(r"(ba|z|da)?sh\s+<\(\s*(curl|wget)\b", command):
            self.deny(
                "pipe-to-shell",
                "Running a script straight from the network executes unreviewed code. Download, inspect, then run.",
            )
        if re.search(r">\s*/dev/(sd[a-z]|nvme\d|disk\d|hd[a-z])", command):
            self.deny("disk-destroy", "Writing to a raw disk device is never an agent task.")
        if re.search(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", command):
            self.deny("disk-destroy", "Fork bombs are not allowed.")

    def check_secret_args(self, program: str, argv: list[str]) -> None:
        if program in {"echo", "printf"}:
            return  # e.g. `echo .env >> .gitignore`; redirect targets are checked separately
        if program == "git" and "rm" in argv and "--cached" in argv:
            return  # untracking a committed secret is the fix, not the leak
        for arg in argv[1:]:
            if arg.startswith("-") and "=" not in arg:
                continue
            value = arg.split("=", 1)[1] if arg.startswith("-") else arg
            if self.is_secret(value):
                self.deny(
                    "secret-file",
                    f"`{value}` looks like a secret or credential file; agents must not read, copy or stage it.",
                )

    def check_rm(self, argv: list[str]) -> None:
        flags = [a for a in argv[1:] if a.startswith("-") and a != "--"]
        recursive = any(
            f in {"--recursive", "-r", "-R"} or (not f.startswith("--") and ("r" in f or "R" in f))
            for f in flags
        )
        if not recursive:
            return
        home = str(Path.home())
        protected_dirs = {"/", home, str(self.root), str(Path(self.cwd).resolve())}
        for target in (a for a in argv[1:] if not a.startswith("-")):
            if target in DANGEROUS_RM_TARGETS:
                self.deny(
                    "rm-root", f"`rm -r {target}` would delete the project, home or root directory."
                )
            if "$" in target or "*" in target:
                continue
            resolved = os.path.realpath(os.path.join(self.cwd, os.path.expanduser(target)))
            if resolved in protected_dirs or resolved == os.path.dirname(str(self.root)):
                self.deny(
                    "rm-root", f"`rm -r {target}` would delete the project, home or root directory."
                )

    def check_chmod(self, argv: list[str]) -> None:
        args = argv[1:]
        recursive = any(a in {"-R", "--recursive"} for a in args)
        world_writable = any(a in {"777", "0777", "a+rwx", "ugo+rwx", "o+w", "a+w"} for a in args)
        if recursive and world_writable:
            self.deny(
                "chmod-777",
                "Recursively making files world-writable is unsafe. Grant the narrowest permission needed.",
            )

    def check_git(self, argv: list[str]) -> None:
        sub, args = git_subcommand(argv)
        if sub == "commit":
            if "--no-verify" in args or any(re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", a) for a in args):
                self.deny("no-verify", "Do not skip git hooks. Fix what the hook reports instead.")
        elif sub == "push":
            self.check_push(args)
        elif sub == "reset" and "--hard" in args:
            self.deny(
                "discard-work",
                "`git reset --hard` discards uncommitted work. Use `git stash` or ask the user first.",
            )
        elif sub == "clean" and any(
            a == "--force" or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", a) for a in args
        ):
            self.deny(
                "discard-work",
                "`git clean -f` deletes untracked files that may be the user's. Ask the user first.",
            )
        elif sub in {"checkout", "restore"} and "--staged" not in args:
            paths = args[args.index("--") + 1 :] if "--" in args else args
            if any(p in {".", "./", ":/", "*"} for p in paths):
                self.deny(
                    "discard-work",
                    f"`git {sub} .` discards every uncommitted change. Restore specific files or ask the user first.",
                )

    def check_push(self, args: list[str]) -> None:
        if "--no-verify" in args:
            self.deny("no-verify", "Do not skip git hooks. Fix what the hook reports instead.")
        plain_force = "--force" in args or any(
            re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", a) for a in args
        )
        lease = any(
            a.startswith("--force-with-lease") or a.startswith("--force-if-includes") for a in args
        )
        positional = [a for a in args if not a.startswith("-")]
        refspecs = positional[1:]
        if any(r.startswith("+") for r in refspecs):
            plain_force = True
        if plain_force:
            self.deny(
                "force-push",
                "Plain force push can overwrite other people's commits. Use `--force-with-lease` on your own branch.",
            )
        if "--all" in args or "--mirror" in args:
            targets = set(self.protected)
        elif refspecs:
            targets = {destination(r) for r in refspecs}
        else:
            targets = {"HEAD"}
        if "HEAD" in targets:
            targets = (targets - {"HEAD"}) | {current_branch(self.cwd)}
        hit = sorted(t for t in targets if t in self.protected)
        if hit:
            if lease:
                self.deny("force-push", f"Never force push to protected branch `{hit[0]}`.")
            self.deny(
                "direct-push",
                f"`{hit[0]}` is protected. Push a feature branch and open a pull request instead.",
            )


# --------------------------------------------------------------------------- helpers


def collect_paths(value: Any, key: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for k, v in value.items():
            yield from collect_paths(v, k)
    elif isinstance(value, list):
        for item in value:
            yield from collect_paths(item, key)
    elif isinstance(value, str):
        if key in {"file_path", "path", "notebook_path", "filePath", "target_file", "filename"}:
            yield value
        for match in PATCH_HEADER.finditer(value):
            yield (match.group(1) or match.group(2)).strip()


def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return command.split()


def split_segments(command: str) -> list[tuple[str, list[str], list[str]]]:
    """Split a shell command into (separator_before, argv, redirect_targets)."""
    segments: list[tuple[str, list[str], list[str]]] = []
    separator = ""
    argv: list[str] = []
    redirects: list[str] = []
    pending_redirect = False
    for token in tokenize(command):
        if token in SEPARATORS:
            segments.append((separator, argv, redirects))
            separator, argv, redirects = token, [], []
            pending_redirect = False
        elif set(token) <= set("<>&"):
            pending_redirect = ">" in token or "<" in token
        elif pending_redirect:
            redirects.append(token)
            pending_redirect = False
        else:
            argv.append(token)
    segments.append((separator, argv, redirects))
    return segments


def strip_wrappers(argv: list[str]) -> list[str]:
    argv = list(argv)
    while argv:
        head = os.path.basename(argv[0])
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argv[0]):
            argv.pop(0)
        elif head in WRAPPERS:
            argv.pop(0)
            while argv and argv[0].startswith("-"):
                argv.pop(0)
        else:
            break
    return argv


def git_subcommand(argv: list[str]) -> tuple[str, list[str]]:
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
            index += 2
        elif arg.startswith("-"):
            index += 1
        else:
            return arg, argv[index + 1 :]
    return "", []


def destination(refspec: str) -> str:
    ref = refspec.lstrip("+")
    ref = ref.split(":", 1)[1] if ":" in ref else ref
    return ref.removeprefix("refs/heads/")


def current_branch(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],  # noqa: S607 - git from PATH is intended
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


# --------------------------------------------------------------------------- main


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        print(f"[agent-policy] could not parse hook input: {exc}", file=sys.stderr)
        return 1
    if not isinstance(event, dict):
        return 0
    cwd = event.get("cwd") or os.getcwd()
    try:
        Policy(cwd).check(str(event.get("tool_name", "")), event.get("tool_input", {}))
    except DeniedError as denial:
        print(f"[agent-policy:{denial.rule}] {denial.reason} {REMEDY}", file=sys.stderr)
        return 2
    except Exception as exc:  # a broken guard must not wedge the agent
        print(f"[agent-policy] internal error, allowing call: {exc!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

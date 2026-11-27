/**
 * agentic-engineering guardrails for pi.
 *
 * Forwards pi tool calls to the shared `.agents/hooks/policy.py` guard, which
 * Codex and Claude Code also use, so all three agents follow one rule set.
 * Exit code 2 from the guard blocks the call. Any other failure allows it
 * (fail open) and logs a warning, so a broken guard never wedges the session.
 */

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const TOOL_NAMES: Record<string, string> = {
  bash: "Bash",
  read: "Read",
  write: "Write",
  edit: "Edit",
};

function findPolicy(start: string): string | undefined {
  let dir = start;
  for (;;) {
    const candidate = join(dir, ".agents", "hooks", "policy.py");
    if (existsSync(candidate)) return candidate;
    const parent = dirname(dir);
    if (parent === dir) return undefined;
    dir = parent;
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event) => {
    const toolName = TOOL_NAMES[event.toolName];
    if (!toolName) return;

    const cwd = process.cwd();
    const script = findPolicy(cwd);
    if (!script) return;

    const payload = JSON.stringify({
      hook_event_name: "PreToolUse",
      tool_name: toolName,
      tool_input: event.input,
      cwd,
    });
    const python = process.platform === "win32" ? "python" : "python3";
    const result = spawnSync(python, [script], {
      input: payload,
      encoding: "utf8",
      timeout: 30_000,
    });

    if (result.status === 2) {
      return { block: true, reason: result.stderr.trim() || "Blocked by agent policy" };
    }
    if (result.error || result.status !== 0) {
      console.warn(
        `[agent-policy] guard did not run cleanly; allowing call. ${result.error?.message ?? result.stderr}`,
      );
    }
  });
}

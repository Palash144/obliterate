# Obliterate — Copilot Integration (VS Code Copilot Chat + Copilot CLI)

**Usage**: Token-optimized CLI proxy (60-90% savings on dev operations)

## What's automatic

The `.github/copilot-instructions.md` file is loaded at session start by both Copilot CLI and VS Code Copilot Chat.
It instructs Copilot to prefix commands with `obliterate` automatically.

The `.github/hooks/obliterate-rewrite.json` hook adds a `PreToolUse` safety net via `obliterate hook` —
a cross-platform Rust binary that intercepts raw bash tool calls and rewrites them.
No shell scripts, no `jq` dependency, works on Windows natively.

## Meta commands (always use directly)

```bash
obliterate gain              # Token savings dashboard for this session
obliterate gain --history    # Per-command history with savings %
obliterate discover          # Scan session history for missed obliterate opportunities
obliterate proxy <cmd>       # Run raw (no filtering) but still track it
```

## Installation verification

```bash
obliterate --version   # Should print: obliterate X.Y.Z
obliterate gain        # Should show a dashboard (not "command not found")
which obliterate       # Verify correct binary path
```

> ⚠️ **Name collision**: If `obliterate gain` fails, you may have `reachingforthejack/obliterate`
> (Rust Type Kit) installed instead. Check `which obliterate` and reinstall from obliterate-ai/obliterate.

## How the hook works

`obliterate hook` reads `PreToolUse` JSON from stdin, detects the agent format, and responds appropriately:

**VS Code Copilot Chat** (supports `updatedInput` — transparent rewrite, no denial):
1. Agent runs `git status` → `obliterate hook` intercepts via `PreToolUse`
2. `obliterate hook` detects VS Code format (`tool_name`/`tool_input` keys)
3. Returns `hookSpecificOutput.updatedInput.command = "obliterate git status"`
4. Agent runs the rewritten command silently — no denial, no retry

**GitHub Copilot CLI** (deny-with-suggestion — CLI ignores `updatedInput` today, see [issue #2013](https://github.com/github/copilot-cli/issues/2013)):
1. Agent runs `git status` → `obliterate hook` intercepts via `PreToolUse`
2. `obliterate hook` detects Copilot CLI format (`toolName`/`toolArgs` keys)
3. Returns `permissionDecision: deny` with reason: `"Token savings: use 'obliterate git status' instead"`
4. Copilot reads the reason and re-runs `obliterate git status`

When Copilot CLI adds `updatedInput` support, only `obliterate hook` needs updating — no config changes.

## Integration comparison

| Tool                  | Mechanism                               | Hook output              | File                               |
|-----------------------|-----------------------------------------|--------------------------|------------------------------------|
| Claude Code           | `PreToolUse` hook with `updatedInput`   | Transparent rewrite      | `hooks/obliterate-rewrite.sh`             |
| VS Code Copilot Chat  | `PreToolUse` hook with `updatedInput`   | Transparent rewrite      | `.github/hooks/obliterate-rewrite.json`   |
| GitHub Copilot CLI    | `PreToolUse` deny-with-suggestion       | Denial + retry           | `.github/hooks/obliterate-rewrite.json`   |
| OpenCode              | Plugin `tool.execute.before`            | Transparent rewrite      | `hooks/opencode-obliterate.ts`            |
| (any)                 | Custom instructions                     | Prompt-level guidance    | `.github/copilot-instructions.md`  |

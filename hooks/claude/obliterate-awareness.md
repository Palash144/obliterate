# Obliterate - Rust Token Killer

**Usage**: Token-optimized CLI proxy (60-90% savings on dev operations)

## Meta Commands (always use obliterate directly)

```bash
obliterate gain              # Show token savings analytics
obliterate gain --history    # Show command usage history with savings
obliterate discover          # Analyze Claude Code history for missed opportunities
obliterate proxy <cmd>       # Execute raw command without filtering (for debugging)
```

## Installation Verification

```bash
obliterate --version         # Should show: obliterate X.Y.Z
obliterate gain              # Should work (not "command not found")
which obliterate             # Verify correct binary
```

⚠️ **Name collision**: If `obliterate gain` fails, you may have reachingforthejack/obliterate (Rust Type Kit) installed instead.

## Hook-Based Usage

All other commands are automatically rewritten by the Claude Code hook.
Example: `git status` → `obliterate git status` (transparent, 0 tokens overhead)

Refer to CLAUDE.md for full command reference.

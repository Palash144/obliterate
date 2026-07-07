# Obliterate - Rust Token Killer (Cline)

**Usage**: Token-optimized CLI proxy for shell commands.

## Rule

Always prefix shell commands with `obliterate` to minimize token consumption.

Examples:

```bash
obliterate git status
obliterate cargo test
obliterate ls src/
obliterate grep "pattern" src/
obliterate find "*.rs" .
obliterate docker ps
obliterate gh pr list
```

## Meta Commands

```bash
obliterate gain              # Show token savings
obliterate gain --history    # Command history with savings
obliterate discover          # Find missed Obliterate opportunities
obliterate proxy <cmd>       # Run raw (no filtering, for debugging)
```

## Why

Obliterate filters and compresses command output before it reaches the LLM context, saving 60-90% tokens on common operations. Always use `obliterate <cmd>` instead of raw commands.

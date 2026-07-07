# Obliterate - Rust Token Killer (Codex CLI)

**Usage**: Token-optimized CLI proxy for shell commands.

## Rule

Always prefix shell commands with `obliterate`.

Examples:

```bash
obliterate git status
obliterate cargo test
obliterate npm run build
obliterate pytest -q
```

## Meta Commands

```bash
obliterate gain            # Token savings analytics
obliterate gain --history  # Recent command savings history
obliterate proxy <cmd>     # Run raw command without filtering
```

## Verification

```bash
obliterate --version
obliterate gain
which obliterate
```

# Claude Code Hooks

> Part of [`hooks/`](../README.md) — see also [`src/hooks/`](../../src/hooks/README.md) for installation code

## Specifics

- Shell-based `PreToolUse` hook -- requires `jq` for JSON parsing
- Returns `updatedInput` JSON for transparent command rewrite (agent doesn't know Obliterate is involved)
- Exits silently (exit 0) on any failure: jq missing, obliterate missing, obliterate too old (< 0.23.0), no match
- Version guard checks `obliterate --version` against minimum 0.23.0
- `obliterate-awareness.md` is a slim 10-line instructions file embedded into CLAUDE.md by `obliterate init`

## Testing

```bash
# Run the full test suite (60+ assertions)
bash hooks/test-obliterate-rewrite.sh

# Test against a specific hook path
HOOK=/path/to/obliterate-rewrite.sh bash hooks/test-obliterate-rewrite.sh

# Enable audit logging during testing
OBLITERATE_HOOK_AUDIT=1 OBLITERATE_AUDIT_DIR=/tmp bash hooks/test-obliterate-rewrite.sh
```

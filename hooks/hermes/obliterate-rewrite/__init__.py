"""Hermes plugin adapter for Obliterate command rewriting.

All rewrite logic lives in Obliterate's Rust ``obliterate rewrite`` command; this module
only bridges Hermes ``pre_tool_call`` payloads to that command and fails open.
"""

import shutil
import subprocess
import sys


ACCEPTED_REWRITE_RETURN_CODES = {0, 3}
EXPECTED_PASSTHROUGH_RETURN_CODES = {1, 2}
_obliterate_available = None
_obliterate_missing_warned = False


def register(ctx):
    """Register the Hermes pre-tool callback."""
    if not _check_obliterate():
        return

    ctx.register_hook("pre_tool_call", _pre_tool_call)


def _check_obliterate():
    """Return whether the obliterate binary is in PATH, warning once when missing."""
    global _obliterate_available, _obliterate_missing_warned

    if _obliterate_available is None:
        _obliterate_available = shutil.which("obliterate") is not None

    if not _obliterate_available and not _obliterate_missing_warned:
        _warn("obliterate binary not found in PATH; Hermes hook not registered")
        _obliterate_missing_warned = True

    return _obliterate_available


def _pre_tool_call(tool_name=None, args=None, **_kwargs):
    """Rewrite mutable Hermes terminal command args when Obliterate provides a change."""
    try:
        if tool_name != "terminal" or not isinstance(args, dict):
            return

        command = args.get("command")
        if not isinstance(command, str) or not command.strip():
            return

        try:
            result = subprocess.run(
                ["obliterate", "rewrite", command],
                shell=False,
                timeout=2,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired:
            _warn("obliterate rewrite timed out")
            return

        if result.returncode not in ACCEPTED_REWRITE_RETURN_CODES:
            if result.returncode not in EXPECTED_PASSTHROUGH_RETURN_CODES:
                details = f"obliterate rewrite failed with exit {result.returncode}"
                stderr = result.stderr.strip()
                if stderr:
                    details = f"{details}: {stderr}"
                _warn(details)
            return

        rewritten = result.stdout.strip()
        if rewritten and rewritten != command:
            args["command"] = rewritten
    except Exception as e:
        _warn(str(e))
        return


def _warn(message):
    print(f"obliterate: hermes plugin warning: {message}", file=sys.stderr)

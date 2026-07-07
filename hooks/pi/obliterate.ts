// Obliterate Pi extension — rewrites bash commands to use obliterate for token savings.
// Requires: obliterate >= 0.23.0 in PATH.
//
// This is a thin delegating extension: all rewrite logic lives in `obliterate rewrite`,
// which is the single source of truth (src/discover/registry.rs).
// To add or change rewrite rules, edit the Rust registry — not this file.
//
// Exit code contract for `obliterate rewrite`:
//   0 + stdout  Rewrite found → mutate command
//   1           No Obliterate equivalent → pass through unchanged
//   3 + stdout  Rewrite (advisory) → mutate command

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent"
import { isToolCallEventType } from "@earendil-works/pi-coding-agent"

const REWRITE_TIMEOUT_MS = 2_000
const MIN_SUPPORTED_OBLITERATE_MINOR = 23

// Parse "X.Y.Z" semver, return [major, minor, patch] or null.
function parseSemver(raw: string): [number, number, number] | null {
  const m = raw.trim().match(/(\d+)\.(\d+)\.(\d+)/)
  if (!m) return null
  return [parseInt(m[1], 10), parseInt(m[2], 10), parseInt(m[3], 10)]
}

// Calls `obliterate rewrite`; returns the rewritten command or null (pass through).
async function rewriteCommand(
  pi: ExtensionAPI,
  cmd: string,
  signal?: AbortSignal
): Promise<string | null> {
  const result = await pi.exec("obliterate", ["rewrite", cmd], {
    timeout: REWRITE_TIMEOUT_MS,
    signal,
  })
  if (result.killed) return null
  if (result.code !== 0 && result.code !== 3) return null
  return result.stdout.trim() || null
}

export default async function (pi: ExtensionAPI) {
  // Probe obliterate version at load time; disables extension if missing or too old.
  const ver = await pi.exec("obliterate", ["--version"], { timeout: REWRITE_TIMEOUT_MS })
  if (ver.code !== 0) {
    console.warn("[obliterate] obliterate binary not found in PATH — extension disabled")
    return
  }

  // Warn and bail if obliterate predates 0.23.0 (when `obliterate rewrite` was introduced).
  const parsed = parseSemver(ver.stdout.replace(/^obliterate\s+/, ""))
  if (parsed) {
    const [major, minor] = parsed
    if (major === 0 && minor < MIN_SUPPORTED_OBLITERATE_MINOR) {
      console.warn(`[obliterate] obliterate ${ver.stdout.trim()} is too old (need >= 0.23.0) — extension disabled`)
      return
    }
  }

  pi.on("tool_call", async (event, ctx) => {
    try {
      if (!isToolCallEventType("bash", event)) return

      const cmd = event.input.command
      if (typeof cmd !== "string" || cmd.trim() === "") return

      if (cmd.startsWith("obliterate ")) return
      if (process.env.OBLITERATE_DISABLED === "1") return

      // Delegate to Obliterate.
      const rewritten = await rewriteCommand(pi, cmd, ctx.signal)
      if (rewritten && rewritten !== cmd) {
        event.input.command = rewritten
      }
    } catch (err) {
      // Fail open: never block execution on an unexpected error.
      console.warn("[obliterate] unexpected error in tool_call handler; passing through command", err)
      return
    }
  })
}

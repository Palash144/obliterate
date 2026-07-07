import type { Plugin } from "@opencode-ai/plugin"

// Obliterate OpenCode plugin — rewrites commands to use obliterate for token savings.
// Requires: obliterate >= 0.23.0 in PATH.
//
// This is a thin delegating plugin: all rewrite logic lives in `obliterate rewrite`,
// which is the single source of truth (src/discover/registry.rs).
// To add or change rewrite rules, edit the Rust registry — not this file.

export const ObliterateOpenCodePlugin: Plugin = async ({ $ }) => {
  try {
    await $`which obliterate`.quiet()
  } catch {
    console.warn("[obliterate] obliterate binary not found in PATH — plugin disabled")
    return {}
  }

  return {
    "tool.execute.before": async (input, output) => {
      const tool = String(input?.tool ?? "").toLowerCase()
      if (tool !== "bash" && tool !== "shell") return
      const args = output?.args
      if (!args || typeof args !== "object") return

      const command = (args as Record<string, unknown>).command
      if (typeof command !== "string" || !command) return

      try {
        const result = await $`obliterate rewrite ${command}`.quiet().nothrow()
        const rewritten = String(result.stdout).trim()
        if (rewritten && rewritten !== command) {
          ;(args as Record<string, unknown>).command = rewritten
        }
      } catch {
        // obliterate rewrite failed — pass through unchanged
      }
    },
  }
}

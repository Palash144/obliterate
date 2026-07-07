# Obliterate

> **Snip noisy command output before it hits your AI.**
> 60–90% fewer tokens. Zero quality loss. Runs entirely on-device.

Obliterate is a high-performance CLI proxy written in Rust. It sits between your AI
coding assistant (Claude, Copilot, Cursor, Gemini, …) and the shell, then
filters, groups, deduplicates, and truncates command output so the AI gets a
compact summary instead of thousands of noisy lines.

```
Without Obliterate                                    With Obliterate

AI  --git status-->  shell  -->  git           AI  --git status-->  obliterate  -->  git
  ^                              |               ^                   |        |
  |  ~2,000 tokens (raw)         |               |   ~200 tokens     | filter |
  +------------------------------+               +-------(filtered)--+--------+
```

---

## Token Savings (real-world session)

| Operation              | Frequency | Raw    | Obliterate    | Savings |
| ---------------------- | --------- | ------ | ------ | ------- |
| `ls` / `tree`          | 10×       | 2,000  | 400    | -80%    |
| `cat` / `read`         | 20×       | 40,000 | 12,000 | -70%    |
| `grep` / `rg`          | 8×        | 16,000 | 3,200  | -80%    |
| `git status`           | 10×       | 3,000  | 600    | -80%    |
| `git diff`             | 5×        | 10,000 | 2,500  | -75%    |
| `git log`              | 5×        | 2,500  | 500    | -80%    |
| `git add/commit/push`  | 8×        | 1,600  | 120    | -92%    |
| `cargo test`/`npm test`| 5×        | 25,000 | 2,500  | -90%    |
| `pytest`               | 4×        | 8,000  | 800    | -90%    |
| `go test`              | 3×        | 6,000  | 600    | -90%    |
| `docker ps`            | 3×        | 900    | 180    | -80%    |
| **Total**              |           | **~115,000** | **~23,400** | **-80%** |

---

## Installation

### Prerequisites

> **⚠️ Rust toolchain is required.** Obliterate is a Rust binary you build from source.
> If you don't already have Rust installed, install it first (takes ~2 minutes):

```bash
# Install Rust via rustup (official installer)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Activate it in the current shell (only needed for this terminal session)
source "$HOME/.cargo/env"

# Verify
cargo --version    # should print: cargo 1.xx.x
```

When the rustup installer asks, just press **Enter** to accept the default options. It installs to `~/.cargo` and `~/.rustup` — no `sudo` needed, nothing system-wide.

Already have Rust? Make sure it's reasonably current:
```bash
rustup update stable
```

### Build & install Obliterate

```bash
git clone https://bmw.ghe.com/Palash-Lambhate/obliterate
cd obliterate
cargo install --path .
```

This compiles Obliterate in release mode (~1–2 minutes first time) and puts the `obliterate` binary in `~/.cargo/bin/`. Make sure that's on your `PATH`:

```bash
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc   # or ~/.bashrc
source ~/.zshrc
```

### Verify

```bash
obliterate --version       # → obliterate 0.1.0
obliterate --help
obliterate git status      # inside any git repo
```

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: cargo` | Run `source "$HOME/.cargo/env"` or restart your terminal |
| `command not found: obliterate` after install | `export PATH="$HOME/.cargo/bin:$PATH"` |
| `cargo install` fails with compiler errors | `rustup update stable` to update Rust |
| Build is slow first time | Normal (~2 min). Subsequent builds are seconds. |

---

## Quick Start

```bash
# Files
obliterate ls .
obliterate read src/main.rs
obliterate grep "pattern" .
obliterate find "*.rs" .

# Git
obliterate git status
obliterate git log -n 10
obliterate git diff
obliterate git push           # → "ok main"

# Tests
obliterate cargo test
obliterate pytest
obliterate go test
obliterate jest / obliterate vitest

# Build & lint
obliterate cargo build
obliterate cargo clippy
obliterate mvn verify       # Maven build/test lifecycle (filtered)
obliterate mvn dependency:tree
obliterate lint               # ESLint, grouped by rule
obliterate tsc                # TypeScript errors, grouped by file
obliterate ruff check
obliterate golangci-lint run

# Cloud
obliterate docker ps
obliterate kubectl pods
obliterate aws ec2 describe-instances

# Analytics (see "Check Your Savings" section below for full reference)
obliterate gain               # See token savings stats
obliterate gain --graph       # ASCII graph (last 30 days)
obliterate gain --history     # Recent command history
obliterate parse-health       # Full/degraded/passthrough parser quality
```

---

## How It Works

Obliterate applies **12 filtering strategies** depending on the command:

| # | Strategy            | Example                                              | Reduction |
| - | ------------------- | ---------------------------------------------------- | --------- |
| 1 | Stats Extraction    | 5000 diff lines → `"3 files, +142/-89"`              | 90–99%    |
| 2 | Error Only          | mixed stdout+stderr → stderr only                    | 60–80%    |
| 3 | Grouping            | 100 lint errors → `"no-unused-vars: 23, semi: 45"`   | 80–90%    |
| 4 | Deduplication       | repeated logs → `"[ERROR] ... (×5)"`                 | 70–85%    |
| 5 | Structure Only      | huge JSON → keys + types, values stripped            | 80–95%    |
| 6 | Code Filtering      | source → strip comments/bodies (level-based)         | 20–90%    |
| 7 | Failure Focus       | 100 tests → only failures                            | 94–99%    |
| 8 | Tree Compression    | flat list → tree with counts                         | 50–70%    |
| 9 | Progress Filtering  | ANSI progress bars → final result                    | 85–95%    |
| 10| JSON/Text Dual Mode | uses tool's `--format json` when available           | 80%+      |
| 11| State Machine       | pytest output → counts + failures                    | 90%+      |
| 12| NDJSON Streaming    | `go test` events → aggregated summary                | 90%+      |

---

## Hook Integration (Claude Code)

For zero-friction usage, install the hook so every `git status` is auto-rewritten
to `obliterate git status` before execution:

```bash
obliterate init -g           # Install global hook for Claude Code
```

Then restart Claude Code. After that, the AI's normal shell commands get
filtered transparently — no need to type `obliterate` yourself.

Hooks are also available for Cursor, Gemini CLI, Copilot, Windsurf, Cline, and
more. Run `obliterate init --help` for the full list.

---

## Check Your Savings

Every command Obliterate filters is logged to a local SQLite database. Four ways to inspect it:

### 1. Quick summary

```bash
obliterate gain
```

Sample output:

```
Obliterate Token Savings (Global Scope)
════════════════════════════════════════════════════════════

Total commands:    127
Input tokens:      48,302
Output tokens:     9,142
Tokens saved:      39,160 (81.1%)
Total exec time:   612ms (avg 4ms)
Efficiency meter: ████████████████████░░░░ 81.1%
```

### 2. Recent command history

See which commands got filtered and how much they each saved:

```bash
obliterate gain --history
```

```
05-25 14:22 ▲ obliterate git log -n 10         -82% (412)
05-25 14:21 ▲ obliterate cargo test            -94% (1,830)
05-25 14:20 ▲ obliterate git status            -75% (76)
05-25 14:18 ■ obliterate ls -la .              -89% (57)
```

Symbols: `▲` high savings · `■` medium · `•` low / passthrough.

### 3. 30-day ASCII graph

```bash
obliterate gain --graph
```

Visual bar chart of daily savings — satisfying to watch grow over time.

### 4. Per-project scope

By default `obliterate gain` shows global savings. To see only the project you're in:

```bash
cd /path/to/your-project
obliterate gain --scope project
```

### More flags

```bash
obliterate gain --daily              # Day-by-day breakdown
obliterate gain --weekly             # Week-by-week
obliterate gain --top 10             # Top 10 most-used commands
obliterate gain --since 7            # Last 7 days only
obliterate gain --format json        # Machine-readable (for dashboards)
obliterate gain --all                # All-time stats
```

### Parse quality dashboard

```bash
obliterate parse-health
obliterate parse-health --project
obliterate parse-health --format json
```

Shows parser-tier distribution (`full`, `degraded`, `passthrough`) and the top
commands where parsers are underperforming.

### Telemetry (anonymous aggregate, opt-in)

Obliterate telemetry is consent-gated and sends anonymous aggregate metrics at
most once per day when enabled:

```bash
obliterate telemetry status
obliterate telemetry enable
obliterate telemetry disable
obliterate telemetry forget
```

### Watch savings live

Open a terminal next to your AI assistant and run:

```bash
watch -n 2 'obliterate gain | head -8'
```

The numbers tick up every time your AI runs a shell command.

> **Heads up:** If `obliterate gain` shows `Total commands: 0` even though you've been using Obliterate, the hook may not be loaded. Run `obliterate init --show` to verify the hook is registered, then restart your AI tool. See [Troubleshooting](#troubleshooting) above.

---

## Global Flags

```
-v, --verbose          # Increase verbosity (-v, -vv, -vvv)
-u, --ultra-compact    # ASCII icons + inline format (maximum compression)
```

---

## Configuration

Config lives at `~/.config/obliterate/config.toml` (or `~/Library/Application Support/obliterate/config.toml` on macOS).

```toml
[hooks]
exclude_commands = ["curl", "playwright"]   # skip rewrite for these

[tee]
enabled = true        # save raw output on failure (default: true)
mode = "failures"     # "failures", "always", or "never"
```

When a command fails, Obliterate saves the full unfiltered output to a `tee` file
so the AI can read it without re-executing the command.

---

## Performance

- Binary: ~4 MB stripped
- Startup: <10ms cold
- Memory: <5 MB typical
- Filter overhead: 2–15ms depending on strategy

---

## Architecture

- `src/main.rs` — Clap router, command dispatch
- `src/cmds/` — 42 command filter modules (git, cargo, npm, pytest, docker, …)
- `src/core/` — Shared infra (utils, tracking, tee, config, TOML filter engine)
- `src/filters/` — 60+ declarative TOML filter recipes
- `src/hooks/` — Hook installer (`obliterate init`) for 10+ AI tools
- `src/analytics/` — Token savings reporting (`obliterate gain`)

---

## Contributing

PRs welcome. New filters are easy to add — see `src/cmds/README.md` for the
step-by-step checklist.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

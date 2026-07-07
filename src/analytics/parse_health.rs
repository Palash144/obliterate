//! Parser quality dashboard for Full/Degraded/Passthrough tier distribution.

use anyhow::{Context, Result};
use serde::Serialize;

use crate::core::tracking::{ParseTierCommandStat, ParseTierSummary, Tracker};

#[derive(Debug, Serialize)]
struct ExportData {
    summary: ParseTierSummary,
}

pub fn run(project: bool, limit: usize, format: &str) -> Result<()> {
    let tracker = Tracker::new().context("Failed to initialize tracking database")?;
    let project_scope = resolve_project_scope(project)?;
    let summary = tracker
        .get_parse_tier_summary(project_scope.as_deref(), limit)
        .context("Failed to load parse-tier summary from database")?;

    match format {
        "json" => {
            println!(
                "{}",
                serde_json::to_string_pretty(&ExportData { summary })?
            );
            return Ok(());
        }
        "text" => {}
        _ => anyhow::bail!("Unsupported format '{}'. Use text or json.", format),
    }

    if summary.total_tracked == 0 {
        println!("No tracking data yet.");
        println!("Run parser-backed commands (vitest/playwright/pnpm) to build parse health stats.");
        return Ok(());
    }

    println!("Obliterate Parse Health");
    println!("{}", "═".repeat(60));
    if let Some(scope) = project_scope {
        println!("Scope: {}", scope);
    }
    println!();
    println!("{:<18} {}", "Total tracked:", summary.total_tracked);
    println!("{:<18} {}", "Full:", summary.full);
    println!(
        "{:<18} {} ({:.1}%)",
        "Degraded:", summary.degraded, summary.degraded_pct
    );
    println!(
        "{:<18} {} ({:.1}%)",
        "Passthrough:", summary.passthrough, summary.passthrough_pct
    );
    println!("{:<18} {}", "Untracked:", summary.untracked);
    println!();

    if !summary.by_command.is_empty() {
        print_hotspots(&summary.by_command);
    }

    Ok(())
}

fn print_hotspots(by_command: &[ParseTierCommandStat]) {
    println!("Top Parse Hotspots");
    println!("{}", "─".repeat(84));
    println!(
        "{:<32} {:>8} {:>12} {:>12} {:>12}",
        "Command", "Total", "Degraded%", "PassThrough%", "IssueCount"
    );
    println!("{}", "─".repeat(84));
    for stat in by_command {
        let cmd = if stat.command.chars().count() > 32 {
            format!("{}...", stat.command.chars().take(29).collect::<String>())
        } else {
            stat.command.clone()
        };
        let issues = stat.degraded + stat.passthrough;
        println!(
            "{:<32} {:>8} {:>11.1}% {:>11.1}% {:>12}",
            cmd, stat.total, stat.degraded_pct, stat.passthrough_pct, issues
        );
    }
    println!("{}", "─".repeat(84));
}

fn resolve_project_scope(project: bool) -> Result<Option<String>> {
    if !project {
        return Ok(None);
    }
    let cwd = std::env::current_dir().context("Failed to resolve current working directory")?;
    let canonical = cwd.canonicalize().unwrap_or(cwd);
    Ok(Some(canonical.to_string_lossy().to_string()))
}

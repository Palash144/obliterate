use anyhow::{Context, Result};
use clap::Subcommand;

#[derive(Debug, Subcommand)]
pub enum TelemetrySubcommand {
    Status,
    Enable,
    Disable,
    Forget,
}

pub fn run(command: &TelemetrySubcommand) -> Result<()> {
    match command {
        TelemetrySubcommand::Status => run_status(),
        TelemetrySubcommand::Enable => run_enable(),
        TelemetrySubcommand::Disable => run_disable(),
        TelemetrySubcommand::Forget => run_forget(),
    }
}

fn run_status() -> Result<()> {
    let config = crate::core::config::Config::load().unwrap_or_default();

    let consent_str = match config.telemetry.consent_given {
        Some(true) => "yes",
        Some(false) => "no",
        None => "never asked",
    };

    let enabled_str = if config.telemetry.enabled {
        "yes"
    } else {
        "no"
    };
    let endpoint_available = if super::telemetry::telemetry_available() {
        "yes"
    } else {
        "no (build has no telemetry endpoint configured)"
    };

    let env_override = std::env::var("OBLITERATE_TELEMETRY_DISABLED").unwrap_or_default() == "1";

    println!("Telemetry status:");
    println!("  consent:       {}", consent_str);
    if let Some(date) = &config.telemetry.consent_date {
        println!("  consent date:  {}", date);
    }
    println!("  enabled:       {}", enabled_str);
    println!("  endpoint:      {}", endpoint_available);
    println!("  cadence:       at most once per day");
    if env_override {
        println!("  env override:  blocked");
    }

    Ok(())
}

fn run_enable() -> Result<()> {
    crate::hooks::init::save_telemetry_consent(true)?;
    if super::telemetry::telemetry_available() {
        println!("Telemetry enabled.");
        println!("Anonymous aggregate metrics may be sent at most once per day.");
    } else {
        println!("Telemetry preference saved as enabled.");
        println!("This build has no telemetry endpoint configured, so nothing will be sent.");
    }
    Ok(())
}

fn run_disable() -> Result<()> {
    crate::hooks::init::save_telemetry_consent(false)?;
    println!("Telemetry disabled.");
    Ok(())
}

fn run_forget() -> Result<()> {
    crate::hooks::init::save_telemetry_consent(false).ok();

    let salt_path = super::telemetry::salt_file_path();
    let marker_path = super::telemetry::telemetry_marker_path();

    if salt_path.exists() {
        std::fs::remove_file(&salt_path)
            .with_context(|| format!("Failed to delete {}", salt_path.display()))?;
    }

    if marker_path.exists() {
        let _ = std::fs::remove_file(&marker_path);
    }

    // Purge local tracking database (right to erasure applies to local data too).
    let db_path = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join(super::constants::OBLITERATE_DATA_DIR)
        .join(super::constants::HISTORY_DB);
    if db_path.exists() {
        match std::fs::remove_file(&db_path) {
            Ok(()) => println!("Local tracking database deleted: {}", db_path.display()),
            Err(e) => eprintln!("obliterate: could not delete {}: {}", db_path.display(), e),
        }
    }

    println!("All local telemetry and tracking data deleted.");
    if !super::telemetry::telemetry_available() {
        println!("(This build has no telemetry endpoint configured — nothing was sent.)");
    }
    Ok(())
}

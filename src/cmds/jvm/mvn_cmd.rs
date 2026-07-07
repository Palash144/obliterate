use crate::core::runner::{self, RunOptions};
use crate::core::stream::StreamFilter;
use crate::core::truncate::CAP_LIST;
use crate::core::utils::resolved_command;
use anyhow::Result;
use lazy_static::lazy_static;
use regex::Regex;
use std::ffi::OsString;
use std::process::Command;

lazy_static! {
    static ref BUILD_STATUS: Regex = Regex::new(r"^\[INFO\]\s+BUILD (SUCCESS|FAILURE)").unwrap();
    static ref ERROR_LINE: Regex = Regex::new(
        r"(?i)(^\[ERROR\]|^\[FATAL\]|compilation failure|failed to execute goal|there are test failures|could not resolve)"
    )
    .unwrap();
    static ref WARN_LINE: Regex = Regex::new(r"(?i)^\[WARNING\]").unwrap();
    static ref TEST_SUMMARY: Regex =
        Regex::new(r"^Tests run:\s+\d+,\s+Failures:\s+\d+,\s+Errors:\s+\d+").unwrap();
    static ref LINT_SUMMARY: Regex =
        Regex::new(r"(?i)(checkstyle|spotbugs).*(violation|bug|error|warning|failed)").unwrap();
    static ref DEPS_LINE: Regex = Regex::new(r"^\[INFO\]\s+[\+\|\\]-").unwrap();
}

#[derive(Debug, PartialEq)]
enum MvnTask {
    Build,
    Test,
    Lint,
    Dependencies,
    Other,
}

fn detect_task(args: &[String]) -> MvnTask {
    let joined = args.join(" ").to_lowercase();
    if joined.contains("dependency:tree") {
        MvnTask::Dependencies
    } else if joined.contains("checkstyle") || joined.contains("spotbugs") {
        MvnTask::Lint
    } else if joined.contains(" test")
        || joined.starts_with("test")
        || joined.contains("surefire:test")
    {
        MvnTask::Test
    } else if joined.contains(" clean")
        || joined.starts_with("clean")
        || joined.contains(" compile")
        || joined.contains(" package")
        || joined.contains(" install")
        || joined.contains(" verify")
    {
        MvnTask::Build
    } else {
        MvnTask::Other
    }
}

fn mvn_binary() -> &'static str {
    if cfg!(windows) {
        if std::path::Path::new(".\\mvnw.cmd").exists() {
            ".\\mvnw.cmd"
        } else {
            "mvn"
        }
    } else if std::path::Path::new("./mvnw").exists() {
        "./mvnw"
    } else {
        "mvn"
    }
}

fn new_mvn_command(args: &[String]) -> Command {
    let mut cmd = if cfg!(windows) {
        if std::path::Path::new(".\\mvnw.cmd").exists() {
            Command::new(".\\mvnw.cmd")
        } else {
            resolved_command("mvn")
        }
    } else if std::path::Path::new("./mvnw").exists() {
        Command::new("./mvnw")
    } else {
        resolved_command("mvn")
    };
    cmd.args(args);
    cmd
}

struct BuildLineFilter;
impl StreamFilter for BuildLineFilter {
    fn feed_line(&mut self, line: &str) -> Option<String> {
        if BUILD_STATUS.is_match(line) || ERROR_LINE.is_match(line) || WARN_LINE.is_match(line) {
            Some(format!("{}\n", line))
        } else {
            None
        }
    }
    fn flush(&mut self) -> String {
        String::new()
    }
}

pub fn run(args: &[String], verbose: u8) -> Result<i32> {
    if args
        .iter()
        .any(|a| a == "-X" || a == "--debug" || a == "-e" || a == "--errors")
    {
        let osargs: Vec<OsString> = args.iter().map(OsString::from).collect();
        return runner::run_passthrough(mvn_binary(), &osargs, verbose);
    }

    let cmd = new_mvn_command(args);
    let args_display = args.join(" ");
    let tool = mvn_binary();

    match detect_task(args) {
        MvnTask::Build => runner::run_streamed(
            cmd,
            tool,
            &args_display,
            Box::new(BuildLineFilter),
            RunOptions::with_tee("mvn_build"),
        ),
        MvnTask::Test => runner::run_filtered(
            cmd,
            tool,
            &args_display,
            filter_test,
            RunOptions::with_tee("mvn_test"),
        ),
        MvnTask::Lint => runner::run_filtered(
            cmd,
            tool,
            &args_display,
            filter_lint,
            RunOptions::with_tee("mvn_lint"),
        ),
        MvnTask::Dependencies => runner::run_filtered(
            cmd,
            tool,
            &args_display,
            filter_dependencies,
            RunOptions::with_tee("mvn_deps"),
        ),
        MvnTask::Other => {
            let osargs: Vec<OsString> = args.iter().map(OsString::from).collect();
            runner::run_passthrough(mvn_binary(), &osargs, verbose)
        }
    }
}

fn filter_test(output: &str) -> String {
    let mut out = Vec::new();
    for line in output.lines() {
        if TEST_SUMMARY.is_match(line)
            || ERROR_LINE.is_match(line)
            || BUILD_STATUS.is_match(line)
            || line.starts_with("[ERROR] Failed tests:")
        {
            out.push(line.to_string());
        }
    }
    if out.is_empty() {
        "No test failures detected".to_string()
    } else {
        out.join("\n")
    }
}

fn filter_lint(output: &str) -> String {
    let mut out = Vec::new();
    for line in output.lines() {
        if LINT_SUMMARY.is_match(line) || ERROR_LINE.is_match(line) || BUILD_STATUS.is_match(line) {
            out.push(line.to_string());
        }
    }
    if out.is_empty() {
        "No lint violations detected".to_string()
    } else {
        out.join("\n")
    }
}

fn filter_dependencies(output: &str) -> String {
    let mut out = Vec::new();
    for line in output.lines() {
        if DEPS_LINE.is_match(line) {
            out.push(line.replacen("[INFO] ", "", 1));
        }
    }

    if out.is_empty() {
        return "No dependency tree output detected".to_string();
    }

    if out.len() > CAP_LIST {
        let shown = out.iter().take(CAP_LIST).cloned().collect::<Vec<_>>();
        format!(
            "{}\n... +{} more\n{}",
            shown.join("\n"),
            out.len() - CAP_LIST,
            crate::core::tee::force_tee_hint(output, "mvn-deps").unwrap_or_default()
        )
    } else {
        out.join("\n")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_task_core_goals() {
        assert_eq!(detect_task(&["test".into()]), MvnTask::Test);
        assert_eq!(detect_task(&["checkstyle:check".into()]), MvnTask::Lint);
        assert_eq!(detect_task(&["dependency:tree".into()]), MvnTask::Dependencies);
        assert_eq!(detect_task(&["clean".into(), "install".into()]), MvnTask::Build);
    }

    #[test]
    fn test_filter_test_keeps_summary() {
        let raw = "Tests run: 3, Failures: 1, Errors: 0, Skipped: 0\n[INFO] BUILD FAILURE";
        let out = filter_test(raw);
        assert!(out.contains("Tests run: 3"));
        assert!(out.contains("BUILD FAILURE"));
    }
}

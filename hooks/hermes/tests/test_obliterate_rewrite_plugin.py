import io
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_PATH = Path(__file__).resolve().parents[1] / "obliterate-rewrite" / "__init__.py"


class FakeContext:
    def __init__(self):
        self.hooks = {}

    def register_hook(self, hook_name, callback):
        self.hooks[hook_name] = callback


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def load_plugin_module(path=PLUGIN_PATH, module_name="obliterate_rewrite_plugin"):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Hermes plugin from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fake_obliterate(bin_dir):
    fake_obliterate = bin_dir / "obliterate"
    fake_obliterate.write_text(
        "\n".join(
            [
                f"#!{sys.executable}",
                "import sys",
                "if sys.argv[1:] == ['rewrite', 'git status']:",
                "    print('obliterate git status')",
                "    raise SystemExit(0)",
                "print('unexpected obliterate args:', sys.argv[1:], file=sys.stderr)",
                "raise SystemExit(1)",
                "",
            ]
        )
    )
    fake_obliterate.chmod(fake_obliterate.stat().st_mode | stat.S_IXUSR)
    return fake_obliterate


class ObliterateRewritePluginTest(unittest.TestCase):
    def load_callback(self):
        module = load_plugin_module()
        module._obliterate_available = None
        module._obliterate_missing_warned = False
        ctx = FakeContext()

        with mock.patch.object(module.shutil, "which", return_value="/usr/bin/obliterate"):
            module.register(ctx)

        self.assertIn("pre_tool_call", ctx.hooks)
        return module, ctx.hooks["pre_tool_call"]

    def test_missing_obliterate_skips_registering_pre_tool_call(self):
        module = load_plugin_module()
        module._obliterate_available = None
        module._obliterate_missing_warned = False
        ctx = FakeContext()

        with mock.patch.object(module.shutil, "which", return_value=None):
            with mock.patch.object(module.sys, "stderr", new_callable=io.StringIO) as stderr:
                module.register(ctx)

        self.assertNotIn("pre_tool_call", ctx.hooks)
        self.assertEqual(
            "obliterate: hermes plugin warning: obliterate binary not found in PATH; Hermes hook not registered\n",
            stderr.getvalue(),
        )

    def test_missing_obliterate_warns_only_once(self):
        module = load_plugin_module()
        module._obliterate_available = None
        module._obliterate_missing_warned = False

        with mock.patch.object(module.shutil, "which", return_value=None):
            with mock.patch.object(module.sys, "stderr", new_callable=io.StringIO) as stderr:
                self.assertFalse(module._check_obliterate())
                self.assertFalse(module._check_obliterate())

        self.assertEqual(
            "obliterate: hermes plugin warning: obliterate binary not found in PATH; Hermes hook not registered\n",
            stderr.getvalue(),
        )

    def test_check_obliterate_found_is_quiet(self):
        module = load_plugin_module()
        module._obliterate_available = None
        module._obliterate_missing_warned = False

        with mock.patch.object(module.shutil, "which", return_value="/usr/bin/obliterate"):
            with mock.patch.object(module.sys, "stderr", new_callable=io.StringIO) as stderr:
                self.assertTrue(module._check_obliterate())

        self.assertEqual("", stderr.getvalue())

    def test_check_obliterate_caches_result_across_calls(self):
        module = load_plugin_module()
        module._obliterate_available = None
        module._obliterate_missing_warned = False

        with mock.patch.object(module.shutil, "which", return_value="/usr/bin/obliterate") as which:
            self.assertTrue(module._check_obliterate())
            self.assertTrue(module._check_obliterate())

        which.assert_called_once_with("obliterate")

    def test_rewrite_success_mutates_same_terminal_args_dict(self):
        module, callback = self.load_callback()
        args = {"command": "git status"}

        with mock.patch.object(
            module.subprocess,
            "run",
            return_value=FakeCompletedProcess(stdout="obliterate git status\n"),
        ):
            callback(tool_name="terminal", args=args)

        self.assertEqual({"command": "obliterate git status"}, args)

    def test_rewrite_returncode_three_mutates_same_terminal_args_dict(self):
        module, callback = self.load_callback()
        args = {"command": "git status"}

        with mock.patch.object(
            module.subprocess,
            "run",
            return_value=FakeCompletedProcess(returncode=3, stdout="obliterate git status\n"),
        ):
            callback(tool_name="terminal", args=args)

        self.assertEqual({"command": "obliterate git status"}, args)

    def test_rewrite_returncode_zero_mutates_when_rewrite_changes_command(self):
        module, callback = self.load_callback()
        args = {"command": "git status"}

        with mock.patch.object(
            module.subprocess,
            "run",
            return_value=FakeCompletedProcess(stdout="obliterate git status\n"),
        ):
            callback(tool_name="terminal", args=args)

        self.assertEqual({"command": "obliterate git status"}, args)

    def test_expected_passthrough_returncodes_do_not_warn_or_mutate(self):
        for returncode in (1, 2):
            with self.subTest(returncode=returncode):
                module, callback = self.load_callback()
                args = {"command": "git status"}

                with mock.patch.object(
                    module.subprocess,
                    "run",
                    return_value=FakeCompletedProcess(
                        returncode=returncode,
                        stdout="obliterate git status\n",
                        stderr="unexpected stderr",
                    ),
                ):
                    with mock.patch.object(module.sys, "stderr", new_callable=io.StringIO) as stderr:
                        callback(tool_name="terminal", args=args)

                self.assertEqual({"command": "git status"}, args)
                self.assertEqual("", stderr.getvalue())

    def test_unexpected_returncode_warns_with_stderr_details(self):
        module, callback = self.load_callback()
        args = {"command": "git status"}

        with mock.patch.object(
            module.subprocess,
            "run",
            return_value=FakeCompletedProcess(returncode=4, stdout="obliterate git status\n", stderr="bad news"),
        ):
            with mock.patch.object(module.sys, "stderr", new_callable=io.StringIO) as stderr:
                callback(tool_name="terminal", args=args)

        self.assertEqual({"command": "git status"}, args)
        self.assertEqual("obliterate: hermes plugin warning: obliterate rewrite failed with exit 4: bad news\n", stderr.getvalue())

    def test_rewrite_timeout_warns_and_preserves_original_command(self):
        module, callback = self.load_callback()
        args = {"command": "git status"}

        timeout = subprocess.TimeoutExpired(cmd=["obliterate", "rewrite", "git status"], timeout=2)
        with mock.patch.object(module.subprocess, "run", side_effect=timeout):
            with mock.patch.object(module.sys, "stderr", new_callable=io.StringIO) as stderr:
                callback(tool_name="terminal", args=args)

        self.assertEqual({"command": "git status"}, args)
        self.assertEqual("obliterate: hermes plugin warning: obliterate rewrite timed out\n", stderr.getvalue())

    def test_file_not_found_preserves_original_command(self):
        module, callback = self.load_callback()
        args = {"command": "git status"}

        with mock.patch.object(module.subprocess, "run", side_effect=FileNotFoundError):
            with mock.patch.object(module.sys, "stderr", new_callable=io.StringIO) as stderr:
                callback(tool_name="terminal", args=args)

        self.assertEqual({"command": "git status"}, args)
        self.assertIn("obliterate: hermes plugin warning:", stderr.getvalue())

    def test_unexpected_exception_prints_warning_and_keeps_command(self):
        module, callback = self.load_callback()
        args = {"command": "git status"}

        with mock.patch.object(module.subprocess, "run", side_effect=RuntimeError("boom")):
            with mock.patch.object(module.sys, "stderr", new_callable=io.StringIO) as stderr:
                callback(tool_name="terminal", args=args)

        self.assertEqual({"command": "git status"}, args)
        self.assertEqual("obliterate: hermes plugin warning: boom\n", stderr.getvalue())

    def test_non_terminal_tool_is_noop(self):
        module, callback = self.load_callback()
        args = {"command": "git status"}

        with mock.patch.object(module.subprocess, "run") as run:
            callback(tool_name="read_file", args=args)

        run.assert_not_called()
        self.assertEqual({"command": "git status"}, args)

    def test_missing_command_is_noop(self):
        module, callback = self.load_callback()
        args = {}

        with mock.patch.object(module.subprocess, "run") as run:
            callback(tool_name="terminal", args=args)

        run.assert_not_called()
        self.assertEqual({}, args)

    def test_non_string_command_is_noop(self):
        module, callback = self.load_callback()
        args = {"command": ["git", "status"]}

        with mock.patch.object(module.subprocess, "run") as run:
            callback(tool_name="terminal", args=args)

        run.assert_not_called()
        self.assertEqual({"command": ["git", "status"]}, args)

    def test_empty_command_strings_are_noop(self):
        for command in ("", "   ", "\t\n"):
            with self.subTest(command=command):
                module, callback = self.load_callback()
                args = {"command": command}

                with mock.patch.object(module.subprocess, "run") as run:
                    callback(tool_name="terminal", args=args)

                run.assert_not_called()
                self.assertEqual({"command": command}, args)

    def test_empty_or_unchanged_rewrite_output_preserves_original_command(self):
        for stdout in ("", "\n", "git status\n"):
            with self.subTest(stdout=stdout):
                module, callback = self.load_callback()
                args = {"command": "git status"}

                with mock.patch.object(
                    module.subprocess,
                    "run",
                    return_value=FakeCompletedProcess(stdout=stdout),
                ):
                    callback(tool_name="terminal", args=args)

                self.assertEqual({"command": "git status"}, args)


class InstalledObliterateRewritePluginTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cargo"), "cargo is required for installed flow")
    def test_cargo_init_installs_importable_plugin_that_rewrites_with_fake_obliterate(self):
        repo_root = Path(__file__).resolve().parents[3]
        self.assertTrue((repo_root / "Cargo.toml").exists(), "repo_root must point at the repository root")
        real_home = Path(os.path.expanduser("~"))

        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as bin_dir:
            home_path = Path(home)
            fake_bin = Path(bin_dir)
            write_fake_obliterate(fake_bin)

            env = os.environ.copy()
            env["HOME"] = str(home_path)
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            env["OBLITERATE_TELEMETRY_DISABLED"] = "1"
            env["CARGO_TERM_COLOR"] = "never"
            env.setdefault("RUSTUP_TOOLCHAIN", "stable")
            if "RUSTUP_HOME" not in env and (real_home / ".rustup").exists():
                env["RUSTUP_HOME"] = str(real_home / ".rustup")
            if "CARGO_HOME" not in env and (real_home / ".cargo").exists():
                env["CARGO_HOME"] = str(real_home / ".cargo")
            env.pop("OBLITERATE_CLAUDE_DIR", None)

            result = subprocess.run(
                ["cargo", "run", "--quiet", "--", "init", "--agent", "hermes"],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

            self.assertEqual(
                0,
                result.returncode,
                msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )

            plugin_dir = home_path / ".hermes" / "plugins" / "obliterate-rewrite"
            init_path = plugin_dir / "__init__.py"
            manifest_path = plugin_dir / "plugin.yaml"
            self.assertTrue(init_path.exists(), "installed plugin __init__.py must exist")
            self.assertTrue(manifest_path.exists(), "installed plugin.yaml must exist")

            module = load_plugin_module(init_path, "installed_obliterate_rewrite_plugin")
            ctx = FakeContext()
            with mock.patch.dict(os.environ, {"PATH": env["PATH"]}):
                module.register(ctx)
                callback = ctx.hooks["pre_tool_call"]

                args = {"command": "git status"}
                callback(tool_name="terminal", args=args)

            self.assertEqual({"command": "obliterate git status"}, args)


if __name__ == "__main__":
    unittest.main()

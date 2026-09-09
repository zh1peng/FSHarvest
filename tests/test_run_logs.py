from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from test_fs_extract_all import MODULE


class RunLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.subjects = self.root / "subjects"
        self.subjects.mkdir()
        self.output = self.root / "output with spaces"
        self.argv = [str(self.subjects), str(self.output)]

    def test_output_errors_exit_codes_and_repeated_runs(self):
        worker = self.root / "worker.py"
        logs = []
        for code in (0, 2, 1, 130):
            worker.write_text(
                "import os, sys\n"
                "assert os.environ['FSHARVEST_RUN_LOG_ACTIVE'] == '1'\n"
                "print('progress: 被试', flush=True)\n"
                "print('stderr detail', file=sys.stderr, flush=True)\n"
                f"raise SystemExit({code})\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with patch.object(MODULE, "__file__", str(worker)), redirect_stdout(output):
                self.assertEqual(MODULE.run_logged(self.argv), code)
            path = Path(output.getvalue().splitlines()[0].removeprefix("Run log: "))
            self.assertNotIn(path, logs)
            logs.append(path)
            self.assertEqual(path.read_text(encoding="utf-8"), output.getvalue())
            self.assertIn("progress: 被试\nstderr detail\n", output.getvalue())
            self.assertIn(f"Run exit code: {code}", output.getvalue())
        self.assertEqual(len(list((self.output / "logs").glob("*.log"))), 4)

    def test_real_python_entry_logs_preflight_error_and_banner(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = MODULE.run_logged([*self.argv, "--freesurfer-home", str(self.root / "missing-fs")])
        self.assertEqual(code, 1)
        log = next((self.output / "logs").glob("*.log")).read_text(encoding="utf-8")
        self.assertEqual(log, output.getvalue())
        self.assertEqual(log.count(MODULE.ASCII_LOGO), 1)
        self.assertIn("[STOPPED]", log)
        self.assertIn("ERROR: FreeSurfer home does not exist:", log)
        self.assertIn("Run exit code: 1", log)

    def test_shell_entry_logs_setup_failure_once(self):
        bash = shutil.which("bash")
        if bash is None and Path("D:/Git/bin/bash.exe").is_file():
            bash = "D:/Git/bin/bash.exe"
        if bash is None:
            self.skipTest("Bash is unavailable")
        environment = dict(os.environ)
        environment.pop("FSHARVEST_RUN_LOG_ACTIVE", None)
        environment.pop("FSHARVEST_LAUNCHER_BANNER_SHOWN", None)
        environment["PATH"] = os.pathsep.join([str(Path(bash).parent), str(Path(sys.executable).parent), environment["PATH"]])
        launcher = Path(MODULE.__file__).resolve().parent / "fsharvest"
        completed = subprocess.run(
            [bash, launcher.as_posix(), *self.argv, "--freesurfer-home", str(self.root / "missing-fs")],
            env=environment, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(completed.returncode, 69, completed.stdout + completed.stderr)
        self.assertEqual(len(list((self.output / "logs").glob("*.log"))), 1)
        log = next((self.output / "logs").glob("*.log")).read_text(encoding="utf-8")
        self.assertEqual(log.count(MODULE.ASCII_LOGO), 1)
        self.assertIn("[SETUP]", log)
        self.assertIn("ERROR: Missing", log)
        self.assertIn("Run exit code: 69", log)

    def test_help_version_and_invalid_arguments_do_not_create_logs(self):
        for extra, expected in ((["--help"], 0), (["--version"], 0), (["--not-an-option"], 2)):
            with redirect_stdout(io.StringIO()), patch.object(MODULE.sys, "stderr", io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    MODULE.run_logged([*self.argv, *extra])
            self.assertEqual(stopped.exception.code, expected)
            self.assertFalse(self.output.exists())

    def test_overlapping_output_does_not_write_to_input(self):
        with self.assertRaisesRegex(ValueError, "must not contain"):
            MODULE.run_logged([str(self.subjects), str(self.subjects / "output")])
        self.assertEqual(list(self.subjects.iterdir()), [])

    def test_log_creation_failure_does_not_launch_work(self):
        self.output.mkdir()
        (self.output / "logs").write_text("existing file", encoding="utf-8")
        with patch.object(MODULE.subprocess, "Popen") as process:
            with self.assertRaises(FileExistsError):
                MODULE.run_logged(self.argv)
            process.assert_not_called()


if __name__ == "__main__":
    unittest.main()

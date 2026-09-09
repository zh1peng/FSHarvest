from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from test_fs_extract_all import DK68_REGIONS, MODULE, write_cortical, write_valid_aseg


class CLIProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.subject = self.root / "subjects/sub-01"
        self.output = self.root / "output"
        self.fs_home = self.root / "freesurfer"
        self.fs_home.mkdir()
        for hemi in MODULE.HEMISPHERES:
            write_cortical(self.subject / "stats" / f"{hemi}.aparc.stats", 34, regions=DK68_REGIONS)
        write_valid_aseg(self.subject / "stats/aseg.stats")
        (self.subject / "scripts").mkdir()
        (self.subject / "scripts/recon-all.done").touch()
        self.argv = [str(self.subject.parent), str(self.output), "--freesurfer-home", str(self.fs_home), "--jobs", "1"]

    def run_cli(self, extra=()):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(
            MODULE.shutil, "which", return_value="/fake/tool"
        ), patch.object(MODULE, "command_version", return_value="FS-test"):
            code = MODULE.main([*self.argv, *extra])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_banner_phases_and_summary_are_available_without_wrapper_echoes(self):
        code, output, errors = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(errors, "")
        self.assertEqual(output.count(MODULE.ASCII_LOGO), 1)
        self.assertIn(f"FSHarvest v{MODULE.TOOL_VERSION}", output)
        self.assertIn(f"Developer: {MODULE.TOOL_DEVELOPER}", output)
        self.assertIn(MODULE.TOOL_URL, output)
        phases = ["[CHECK]", "[DISCOVER]", "[PREPARE]", "[EXTRACT]", "[1/1]", "[AGGREGATE]", "[DONE]"]
        self.assertEqual(sorted(output.index(phase) for phase in phases), [output.index(phase) for phase in phases])
        self.assertIn("Table status: OK=1, PARTIAL=0, FAILED=0, NOT_RUN=0", output)
        self.assertIn(str(self.output), output)
        self.assertIn("extract.log", output)
        self.assertRegex(output, r"elapsed \d+:\d{2}:\d{2}")
        self.assertNotIn("[QC]", output)
        self.assertNotIn("[EXPORT]", output)
        self.assertNotIn("QC report:", output)
        code, cached, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("[1/1] sub-01: OK (cached)", cached)

    def test_progress_is_announced_before_work_starts(self):
        output = io.StringIO()
        extract = MODULE.extract_subject
        aggregate = MODULE.aggregate

        def checked_extract(*args, **kwargs):
            self.assertIn("[EXTRACT] Starting", output.getvalue())
            return extract(*args, **kwargs)

        def checked_aggregate(*args, **kwargs):
            self.assertIn("[AGGREGATE] Writing", output.getvalue())
            return aggregate(*args, **kwargs)

        with redirect_stdout(output), patch.object(MODULE.shutil, "which", return_value="/fake/tool"), patch.object(
            MODULE, "command_version", return_value="FS-test"
        ), patch.object(MODULE, "extract_subject", side_effect=checked_extract), patch.object(
            MODULE, "aggregate", side_effect=checked_aggregate
        ):
            self.assertEqual(MODULE.main(self.argv), 0)

    def test_launcher_banner_is_not_repeated_by_python_entry(self):
        with patch.dict(os.environ, {"FSHARVEST_LAUNCHER_BANNER_SHOWN": "1"}):
            code, output, _ = self.run_cli()
            self.assertNotIn("FSHARVEST_LAUNCHER_BANNER_SHOWN", os.environ)
        self.assertEqual(code, 0)
        self.assertNotIn(MODULE.ASCII_LOGO, output)
        self.assertIn("[CHECK]", output)

    def test_optional_phases_and_partial_results_are_reported(self):
        (self.subject / "stats/lh.aparc.stats").unlink()
        with patch("fs_render_qc.render_subject", return_value=[]):
            code, output, _ = self.run_cli(["--qc-plots", "--export-to-freesurfer"])
        self.assertEqual(code, 2)
        self.assertIn("[EXPORT]", output)
        self.assertIn("[QC]", output)
        self.assertIn("[QC 1/1]", output)
        self.assertIn("PARTIAL=1", output)
        self.assertIn("0 OK, 1 non-OK across all requested phases", output)
        self.assertIn("Available data are retained", output)
        self.assertIn("QC report:", output)

    def test_fatal_subject_is_counted_in_final_summary(self):
        with patch.object(MODULE, "extract_subject", side_effect=RuntimeError("test failure")):
            code, output, errors = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("FAILED=1", output)
        self.assertIn("[1/1] sub-01: FATAL: test failure", errors)
        self.assertIn("[DONE]", output)

    def test_help_and_version_remain_clean(self):
        for option in ("--version", "--help"):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as stopped:
                MODULE.main([option])
            self.assertEqual(stopped.exception.code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertNotIn(MODULE.ASCII_LOGO, stdout.getvalue())
            self.assertNotIn("elapsed", stdout.getvalue())
            if option == "--version":
                self.assertEqual(stdout.getvalue(), f"fsharvest {MODULE.TOOL_VERSION}\n")

    def test_environment_error_and_interrupt_are_not_reported_as_done(self):
        for exception in (RuntimeError("environment unavailable"), KeyboardInterrupt()):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(
                MODULE, "resolve_atlases", side_effect=exception
            ), patch.object(MODULE.shutil, "which", return_value="/fake/tool"), self.assertRaises(type(exception)):
                MODULE.main(self.argv)
            self.assertIn(MODULE.ASCII_LOGO, stdout.getvalue())
            self.assertIn("[STOPPED]", stderr.getvalue())
            self.assertNotIn("[DONE]", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

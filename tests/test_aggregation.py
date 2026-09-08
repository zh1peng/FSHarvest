from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_fs_extract_all import MODULE, selected_atlases, write_cortical, write_valid_aseg


class PartialAggregationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / "output"
        self.atlases = selected_atlases(("dk68",))
        self.subjects = []

    def extract(self, name, regions=None, run_id="current"):
        subject = self.root / name
        regions = regions or [f"region_{i}" for i in range(34)]
        spec = next(iter(self.atlases.values()))
        for hemi in MODULE.HEMISPHERES:
            write_cortical(subject / "stats" / f"{hemi}.{spec.stats_stem}.stats", len(regions), regions=regions)
        write_valid_aseg(subject / "stats/aseg.stats")
        (subject / "scripts").mkdir()
        (subject / "scripts/recon-all.done").touch()
        with patch.object(MODULE, "ensure_link", lambda *_args: None):
            MODULE.extract_subject(
                subject, self.output, self.root, self.atlases, "atlas", {}, self.root,
                "FS-6", "template", False, run_id=run_id,
            )
        self.subjects.append(subject)
        return self.output / "per_subject" / name

    def save_rows(self, base, filename, rows):
        MODULE.write_tsv(base / filename, rows, list(rows[0]))
        self.update_status(base, output_artifacts=MODULE.output_artifact_integrity(base))

    def update_status(self, base, **changes):
        path = base / "status.json"
        status = json.loads(path.read_text())
        status.update(changes)
        path.write_text(json.dumps(status))

    def aggregate(self):
        return MODULE.aggregate(self.output, self.subjects, self.atlases, {"run_id": "current"})

    def test_partial_subjects_keep_actual_names_and_missing_cells(self):
        first = self.extract("sub-01", ["G&S"] + [f"region_{i}" for i in range(1, 34)])
        second = self.extract("sub-02", ["G_and_S"] + [f"region_{i}" for i in range(1, 33)])
        for base in (first, second):
            self.update_status(base, status="PARTIAL", errors="region names do not match pinned schema")
        original = (first / "cortical.tsv").read_bytes()
        self.assertEqual(self.aggregate(), {"sub-01", "sub-02"})
        wide = MODULE.read_tsv(self.output / "wide/dk68.tsv")
        self.assertEqual(len(wide), 2)
        self.assertEqual(wide[0]["L_G&S_thickavg"], "2.5")
        self.assertEqual(wide[0]["L_G_and_S_thickavg"], "")
        self.assertEqual(wide[1]["L_region_33_thickavg"], "")
        self.assertEqual(wide[0]["status"], "PARTIAL")
        self.assertIn("pinned schema", wide[0]["errors"])
        cortical = MODULE.read_tsv(self.output / "cortical_long.tsv")
        self.assertEqual(len(cortical), 134)
        self.assertEqual(cortical[0]["status"], "PARTIAL")
        self.assertEqual(len(MODULE.read_tsv(self.output / "aseg_long.tsv")), 40)
        self.assertEqual((first / "cortical.tsv").read_bytes(), original)
        differences = MODULE.read_tsv(self.output / "region_differences.tsv")
        self.assertTrue(any("G&S" in row["absent_from_subject"] for row in differences))

    def test_duplicate_cortical_key_excludes_both_copies_only(self):
        base = self.extract("sub-01")
        rows = MODULE.read_tsv(base / "cortical.tsv")
        self.save_rows(base, "cortical.tsv", rows + [{**rows[0], "thickavg": "99"}])
        self.assertEqual(self.aggregate(), {"sub-01"})
        kept = MODULE.read_tsv(self.output / "cortical_long.tsv")
        self.assertEqual(len(kept), 67)
        self.assertFalse(any(row["hemisphere"] == "lh" and row["region"] == "region_0" for row in kept))
        self.assertEqual(len(MODULE.read_tsv(self.output / "aseg_long.tsv")), 20)
        self.assertIn("duplicate", MODULE.read_tsv(self.output / "subjects.tsv")[0]["errors"].lower())

    def test_checksum_failure_or_missing_file_keeps_other_tables_and_subjects(self):
        first = self.extract("sub-01")
        second = self.extract("sub-02")
        (first / "cortical.tsv").write_text("damaged")
        (second / "aseg.tsv").unlink()
        self.assertEqual(self.aggregate(), {"sub-01", "sub-02"})
        self.assertEqual(len(MODULE.read_tsv(self.output / "cortical_long.tsv")), 68)
        self.assertEqual(len(MODULE.read_tsv(self.output / "aseg_long.tsv")), 20)
        self.assertEqual(len(MODULE.read_tsv(self.output / "all_features_wide.tsv")), 2)

    def test_destrieux_aliases_are_reported_without_renaming_or_exclusion(self):
        repo = Path(MODULE.__file__).parent
        self.atlases = MODULE.resolve_atlases(["destrieux"], repo / "atlases", self.root)
        names = [name.replace("_and_", "&") for name in self.atlases["destrieux"].region_names("lh")]
        self.extract("sub-01", names)
        self.assertEqual(self.aggregate(), {"sub-01"})
        wide = MODULE.read_tsv(self.output / "wide/destrieux.tsv")[0]
        self.assertEqual(wide["L_G&S_frontomargin_thickavg"], "2.5")
        self.assertNotIn("L_G_and_S_frontomargin_thickavg", wide)
        self.assertEqual(len(MODULE.read_tsv(self.output / "cortical_long.tsv")), 148)
        differences = MODULE.read_tsv(self.output / "region_differences.tsv")
        self.assertIn("G_and_S_frontomargin", differences[0]["missing_expected"])
        self.assertIn("G&S_frontomargin", differences[0]["unexpected_names"])
        self.assertEqual(differences[0]["absent_from_subject"], "[]")

    def test_bad_header_is_local_to_file_even_with_matching_checksum(self):
        base = self.extract("sub-01")
        (base / "cortical.tsv").write_text("broken\n1\n")
        self.update_status(base, output_artifacts=MODULE.output_artifact_integrity(base))
        self.aggregate()
        self.assertEqual(MODULE.read_tsv(self.output / "cortical_long.tsv"), [])
        self.assertEqual(len(MODULE.read_tsv(self.output / "aseg_long.tsv")), 20)
        self.assertIn("invalid table header", MODULE.read_tsv(self.output / "subjects.tsv")[0]["errors"])

    def test_malformed_and_misattributed_rows_are_excluded_locally(self):
        base = self.extract("sub-01")
        rows = MODULE.read_tsv(base / "cortical.tsv")
        rows[0]["folder_id"] = "wrong-subject"
        rows[1]["hemisphere"] = "invalid"
        self.save_rows(base, "cortical.tsv", rows)
        with (base / "cortical.tsv").open("a") as handle:
            handle.write("truncated\trow\n")
        self.update_status(base, output_artifacts=MODULE.output_artifact_integrity(base))
        self.aggregate()
        self.assertEqual(len(MODULE.read_tsv(self.output / "cortical_long.tsv")), 66)
        self.assertEqual(len(MODULE.read_tsv(self.output / "aseg_long.tsv")), 20)
        self.assertFalse(list(self.output.glob(".fsharvest-aggregate-*")))

    def test_failed_subject_keeps_available_current_run_data(self):
        base = self.extract("sub-01")
        self.update_status(base, status="FAILED", errors="other phase failed")
        self.aggregate()
        self.assertEqual(len(MODULE.read_tsv(self.output / "cortical_long.tsv")), 68)
        self.assertEqual(MODULE.read_tsv(self.output / "wide/dk68.tsv")[0]["status"], "FAILED")
        self.assertEqual(len(MODULE.read_tsv(self.output / "aseg_long.tsv")), 20)
        self.assertEqual(len(MODULE.read_tsv(self.output / "all_features_wide.tsv")), 1)

    def test_invalid_numeric_row_does_not_hide_other_regions(self):
        base = self.extract("sub-01")
        rows = MODULE.read_tsv(base / "cortical.tsv")
        rows[0]["thickavg"] = "nan"
        self.save_rows(base, "cortical.tsv", rows)
        self.aggregate()
        self.assertEqual(len(MODULE.read_tsv(self.output / "cortical_long.tsv")), 67)

    def test_aseg_structure_and_global_metric_collisions_do_not_overwrite(self):
        base = self.extract("sub-01")
        rows = MODULE.read_tsv(base / "aseg.tsv")
        self.save_rows(base, "aseg.tsv", rows + [{**rows[0], "segid": "999"}])
        globals_ = MODULE.read_tsv(base / "global.tsv")
        self.save_rows(base, "global.tsv", globals_ + [{**globals_[0], "measure": "other", "value": "999"}])
        self.aggregate()
        self.assertEqual(len(MODULE.read_tsv(self.output / "aseg_long.tsv")), 19)
        self.assertEqual(len(MODULE.read_tsv(self.output / "global_measures_long.tsv")), 2)
        self.assertEqual(len(MODULE.read_tsv(self.output / "cortical_long.tsv")), 68)
        wide = MODULE.read_tsv(self.output / "all_features_wide.tsv")[0]
        self.assertEqual(wide["eTIV_mm3"], "")
        self.assertNotIn("global__eTIV", wide)

    def test_previous_run_tables_are_not_included(self):
        self.extract("sub-01", run_id="previous")
        self.aggregate()
        self.assertEqual(MODULE.read_tsv(self.output / "cortical_long.tsv"), [])
        self.assertEqual(MODULE.read_tsv(self.output / "subjects.tsv")[0]["status"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()

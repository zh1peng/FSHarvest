import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_fs_extract_all import MODULE, MODULE_PATH, DK68_REGIONS, write_cortical, write_valid_aseg


COUNTS = {
    "cammoun33": (34, 34),
    "cammoun60": (57, 57),
    "cammoun125": (111, 108),
    "cammoun250": (225, 223),
    "cammoun500": (499, 501),
}


class CammounAtlasTests(unittest.TestCase):
    def test_bundled_scales_have_expected_assigned_regions_and_geometry(self):
        for key, counts in COUNTS.items():
            spec = MODULE.ATLAS_SPECS[key]
            self.assertEqual(spec.expected_total, sum(counts))
            self.assertEqual(spec.source_subject, "fsaverage")
            for hemi, count in zip(MODULE.HEMISPHERES, counts):
                with self.subTest(atlas=key, hemi=hemi):
                    vertices, names = MODULE.annotation_contents(
                        spec.annotation_path(MODULE_PATH.parent / "atlases", hemi),
                        used_only=True,
                    )
                    regions = set(names) - set(spec.excluded_regions)
                    self.assertEqual(vertices, 163842)
                    self.assertEqual(len(regions), count)
                    self.assertEqual(spec.expected_rows(hemi), count)
                    if key == "cammoun33":
                        self.assertEqual(regions, set(DK68_REGIONS))

    def test_all_scales_extract_aggregate_export_and_reuse_cache(self):
        # Real bundled labels, with FreeSurfer projection/statistics simulated.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subjects = root / "subjects"
            subject = subjects / "sub-01"
            output = root / "output"
            fs_home = root / "freesurfer"
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            (subject / "label").mkdir()
            (subject / "surf").mkdir()
            template = fs_home / "subjects" / "fsaverage" / "surf"
            template.mkdir(parents=True)
            for hemi in MODULE.HEMISPHERES:
                (subject / "label" / f"{hemi}.cortex.label").write_bytes(b"cortex")
                for name in ("sphere.reg", "white", "pial", "thickness"):
                    (subject / "surf" / f"{hemi}.{name}").write_bytes(b"surface")
                (template / f"{hemi}.sphere.reg").write_bytes(b"template")
            calls = []

            def fake_run(command, _env, _log):
                calls.append(command)
                if command[0] == "mri_surf2surf":
                    self.assertEqual(command[command.index("--srcsubject") + 1], "fsaverage")
                    source = Path(command[command.index("--sval-annot") + 1])
                    target = Path(command[command.index("--tval") + 1])
                    MODULE.atomic_copy_file(source, target)
                else:
                    self.assertEqual(command[0], "mris_anatomical_stats")
                    annotation = Path(command[command.index("-a") + 1])
                    names = MODULE.annotation_region_names(annotation)
                    write_cortical(
                        Path(command[command.index("-f") + 1]), len(names),
                        annotation_name=annotation.name, regions=names,
                    )

            argv = [
                str(subjects), str(output), "--freesurfer-home", str(fs_home),
                "--atlases", *COUNTS, "--jobs", "1", "--export-to-freesurfer",
            ]
            with (
                patch.object(MODULE.shutil, "which", return_value="/fake/tool"),
                patch.object(MODULE, "command_version", return_value="FS-7"),
                patch.object(MODULE, "read_surface_vertex_count", return_value=163842),
                patch.object(MODULE, "ensure_link", lambda *_args: None),
                patch.object(MODULE, "run_command", fake_run),
            ):
                self.assertEqual(MODULE.main(argv), 0)
                self.assertEqual(len(calls), 20)
                self.assertEqual(MODULE.main(argv), 0)
                self.assertEqual(len(calls), 20)
            status = json.loads((output / "per_subject/sub-01/status.json").read_text())
            self.assertEqual(status["cache_hit"], 1)
            rows = MODULE.read_tsv(output / "cortical_long.tsv")
            self.assertEqual(len(rows), 1849)
            self.assertNotIn("unknown", {row["region"] for row in rows})
            self.assertNotIn("corpuscallosum", {row["region"] for row in rows})
            for key, counts in COUNTS.items():
                for hemi, count in zip(MODULE.HEMISPHERES, counts):
                    self.assertEqual(sum(row["atlas"] == key and row["hemisphere"] == hemi
                                         for row in rows), count)
                    self.assertTrue((subject / "label" / f"{hemi}.{key}.annot").is_file())
                    self.assertTrue((subject / "stats" / f"{hemi}.{key}.stats").is_file())
                self.assertEqual(len(MODULE.read_tsv(output / "wide" / f"{key}.tsv")), 1)

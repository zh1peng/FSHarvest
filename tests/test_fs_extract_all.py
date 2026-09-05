from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "fs_extract_all.py"
SPEC = importlib.util.spec_from_file_location("fs_extract_all", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

DK68_REGIONS = """
bankssts caudalanteriorcingulate caudalmiddlefrontal cuneus entorhinal fusiform
inferiorparietal inferiortemporal isthmuscingulate lateraloccipital
lateralorbitofrontal lingual medialorbitofrontal middletemporal parahippocampal
paracentral parsopercularis parsorbitalis parstriangularis pericalcarine
postcentral posteriorcingulate precentral precuneus rostralanteriorcingulate
rostralmiddlefrontal superiorfrontal superiorparietal superiortemporal
supramarginal frontalpole temporalpole transversetemporal insula
""".split()


def write_cortical(
    path: Path,
    count: int,
    thickavg: float = 2.5,
    annotation_name: str | None = None,
    regions: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    region_names = regions or [f"region_{index}" for index in range(count)]
    if len(region_names) != count:
        raise ValueError("regions must contain exactly count names")
    path.write_text(
        (f"# AnnotationFile {annotation_name}\n" if annotation_name else "")
        + "\n".join(
            f"{region} 10 20 30 {thickavg} 0.1 0.2 0.3 4.0 5.0"
            for region in region_names
        )
        + "\n",
        encoding="utf-8",
    )


def write_valid_aseg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    structures = [
        "Left-Test", "Brain-Stem", "Left-Thalamus-Proper", "Right-Thalamus-Proper",
        "Left-Caudate", "Right-Caudate", "Left-Putamen", "Right-Putamen",
        "Left-Hippocampus", "Right-Hippocampus", "Left-Amygdala", "Right-Amygdala",
        "Left-Pallidum", "Right-Pallidum", "Left-Accumbens-area", "Right-Accumbens-area",
        "Left-Lateral-Ventricle", "Right-Lateral-Ventricle",
        "Left-Cerebellum-Cortex", "Right-Cerebellum-Cortex",
    ]
    path.write_text(
        """# subjectname sub-01
# NRows 20
# NTableCols 10
# ColHeaders Index SegId NVoxels Volume_mm3 StructName normMean normStdDev normMin normMax normRange
# Measure EstimatedTotalIntraCranialVol, eTIV, Estimated total intracranial volume, 1234.5, mm^3
# Measure lhSurfaceHoles, lhSurfaceHoles, Number of defect holes, 12, unitless
# Measure rhSurfaceHoles, rhSurfaceHoles, Number of defect holes, 13, unitless
"""
        + "\n".join(
            f"{index} {index + 100} {index + 10} {index + 0.5} {structure} 6 7 8 9 10"
            for index, structure in enumerate(structures, start=1)
        )
        + "\n",
        encoding="utf-8",
    )


def write_artifact_metadata(subject_out: Path, atlas: str) -> None:
    spec = MODULE.ATLAS_SPECS[atlas]
    for hemi in MODULE.HEMISPHERES:
        path = subject_out / "stats" / f"{hemi}.{spec.stats_stem}.artifact.json"
        path.write_text(
            json.dumps(
                {
                    "fingerprint": "test",
                    "atlas": atlas,
                    "hemisphere": hemi,
                    "source": "test",
                    "output_artifacts": MODULE.external_artifact_integrity(
                        subject_out, spec, hemi
                    ),
                }
            ),
            encoding="utf-8",
        )


class ExtractionUnitTests(unittest.TestCase):
    def test_release_version_metadata_is_synchronized(self):
        root = MODULE_PATH.parent
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, MODULE.TOOL_VERSION)
        self.assertIn(
            f"version: {version}",
            (root / "CITATION.cff").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f"## {version}",
            (root / "CHANGELOG.md").read_text(encoding="utf-8"),
        )

    def test_default_is_dk68_and_optional_atlases_are_available(self):
        self.assertEqual(MODULE.DEFAULT_ATLASES, ("dk68",))
        self.assertIn("dk308", MODULE.ATLAS_SPECS)
        self.assertNotIn("dk300", MODULE.DEFAULT_ATLASES)
        self.assertEqual(MODULE.ATLAS_SPECS["dk308"].expected_total, 308)
        self.assertEqual(
            MODULE.ATLAS_SPECS["dk308"].excluded_regions,
            ("unknown_part1", "corpuscallosum_part1"),
        )
        self.assertIn(
            "Background+FreeSurfer_Defined_Medial_Wall",
            MODULE.ATLAS_SPECS["schaefer100"].excluded_regions,
        )
        for parcels in range(100, 1001, 100):
            spec = MODULE.ATLAS_SPECS[f"schaefer{parcels}"]
            self.assertEqual(spec.expected_total, parcels)
            self.assertEqual(spec.source_subject, "fsaverage5")
            self.assertEqual(spec.annot_pattern, f"{{hemi}}.schaefer-{parcels}_mics.annot")
        self.assertEqual(MODULE.ATLAS_SPECS["glasser360"].source_subject, "fsaverage5")
        self.assertEqual(MODULE.ATLAS_SPECS["economo"].expected_total, 86)
        self.assertEqual(MODULE.ATLAS_SPECS["vosdewael300"].expected_total, 300)

    def test_bundled_external_atlases_match_manifest(self):
        atlas_dir = MODULE_PATH.parent / "atlases"
        checksums = MODULE.validate_atlas_files(atlas_dir, tuple(MODULE.ATLAS_SPECS))
        self.assertEqual(len(checksums), 28)

    def test_external_atlas_region_schema_matches_annotations(self):
        try:
            import nibabel.freesurfer.io as fsio
        except ImportError:
            self.skipTest("nibabel is required to inspect annotation label tables")
        atlas_dir = MODULE_PATH.parent / "atlases"
        schema = MODULE.load_region_schema(atlas_dir, tuple(MODULE.ATLAS_SPECS))
        for atlas, spec in MODULE.ATLAS_SPECS.items():
            if spec.kind != "external":
                continue
            for hemi in MODULE.HEMISPHERES:
                path = atlas_dir / spec.annot_pattern.format(hemi=hemi)
                _labels, _ctab, names = fsio.read_annot(str(path), orig_ids=False)
                regions = [
                    name.decode("utf-8")
                    for name in names
                    if name.decode("utf-8") not in spec.excluded_regions
                ]
                self.assertEqual(
                    MODULE.region_set_sha256(regions),
                    schema[f"{atlas}:{hemi}"],
                    f"Region schema mismatch for {atlas}/{hemi}",
                )

    def test_dependency_free_annotation_validation_matches_schema(self):
        atlas_dir = MODULE_PATH.parent / "atlases"
        schema = MODULE.load_region_schema(atlas_dir, tuple(MODULE.ATLAS_SPECS))
        for atlas, spec in MODULE.ATLAS_SPECS.items():
            if spec.kind != "external":
                continue
            for hemi in MODULE.HEMISPHERES:
                path = atlas_dir / spec.annot_pattern.format(hemi=hemi)
                self.assertEqual(
                    MODULE.validate_annotation_file(
                        path, spec, atlas, hemi, schema[f"{atlas}:{hemi}"]
                    ),
                    [],
                )

    def test_annotation_vertex_count_must_match_surface(self):
        atlas_dir = MODULE_PATH.parent / "atlases"
        path = atlas_dir / "lh.schaefer-100_mics.annot"
        vertex_count, _names = MODULE.annotation_contents(path)
        schema = MODULE.load_region_schema(atlas_dir, ("schaefer100",))
        errors = MODULE.validate_annotation_file(
            path,
            MODULE.ATLAS_SPECS["schaefer100"],
            "schaefer100",
            "lh",
            schema["schaefer100:lh"],
            vertex_count + 1,
        )
        self.assertIn("surface has", " ".join(errors))

    def test_parse_cortical_stats(self):
        content = """# subjectname sub-01
region_a 10 20 30 2.5 0.1 0.2 0.3 4.0 5.0
region_b 11 21 31 2.6 0.2 0.3 0.4 5.0 6.0
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lh.test.stats"
            path.write_text(content, encoding="utf-8")
            rows = MODULE.parse_cortical_stats(path, "test", "lh")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["region"], "region_a")
        self.assertEqual(rows[0]["numvert"], 10)
        self.assertEqual(rows[1]["thickavg"], 2.6)

    def test_parse_aseg_and_global_measures(self):
        content = """# Measure EstimatedTotalIntraCranialVol, eTIV, Estimated total intracranial volume, 1234.5, mm^3
# Measure lhSurfaceHoles, lhSurfaceHoles, Number of defect holes, 12, unitless
1 2 3 4.5 Left-Test 6 7 8 9 10
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aseg.stats"
            path.write_text(content, encoding="utf-8")
            aseg = MODULE.parse_aseg_stats(path)
            measures = MODULE.parse_measure_lines(path)
        self.assertEqual(aseg[0]["structure"], "Left-Test")
        self.assertEqual(aseg[0]["volume_mm3"], 4.5)
        self.assertEqual(measures[0]["measure"], "EstimatedTotalIntraCranialVol")
        self.assertEqual(measures[0]["metric"], "eTIV")
        self.assertEqual(measures[1]["value"], 12)

    def test_subject_discovery_ignores_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub-01" / "stats").mkdir(parents=True)
            (root / "sub-01" / "stats" / "aseg.stats").touch()
            (root / "fsaverage" / "stats").mkdir(parents=True)
            (root / "fsaverage" / "stats" / "aseg.stats").touch()
            found = MODULE.discover_subjects(root, recursive=False)
        self.assertEqual([path.name for path in found], ["sub-01"])

    def test_empty_aseg_is_invalid(self):
        self.assertIn("no structure rows", " ".join(MODULE.validate_aseg_rows([], [])))

    def test_changed_subject_input_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34, 1.0)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34, 1.0)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            args = (subject, output, root, ("dk68",), "atlas", {}, root, "FS-7", "template", False)
            with patch.object(MODULE, "ensure_link", lambda *_args: None):
                first = MODULE.extract_subject(*args)
                write_cortical(subject / "stats" / "lh.aparc.stats", 34, 99.0)
                second = MODULE.extract_subject(*args)
            rows = MODULE.read_tsv(output / "per_subject" / "sub-01" / "cortical.tsv")
            self.assertEqual(first["status"], "OK")
            self.assertNotEqual(first["fingerprint"], second["fingerprint"])
            self.assertEqual(rows[0]["thickavg"], "99.0")

    def test_corrupt_cached_table_is_recomputed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            args = (subject, output, root, ("dk68",), "atlas", {}, root, "FS-7", "template", False)
            with patch.object(MODULE, "ensure_link", lambda *_args: None):
                first = MODULE.extract_subject(*args)
                cortical = output / "per_subject" / "sub-01" / "cortical.tsv"
                cortical.write_text(cortical.read_text(encoding="utf-8").splitlines()[0] + "\n")
                second = MODULE.extract_subject(*args)
            self.assertEqual(first["status"], "OK")
            self.assertEqual(second["status"], "OK")
            self.assertEqual(second["cache_hit"], 0)
            self.assertEqual(len(MODULE.read_tsv(cortical)), 68)

    def test_cache_hit_clears_previous_optional_phase_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            args = (subject, output, root, ("dk68",), "atlas", {}, root, "FS-7", "template", False)
            with patch.object(MODULE, "ensure_link", lambda *_args: None):
                MODULE.extract_subject(*args)
            status_path = output / "per_subject" / "sub-01" / "status.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update({"qc_status": "FAILED", "qc_errors": "old", "export_status": "OK"})
            status_path.write_text(json.dumps(status), encoding="utf-8")
            with patch.object(MODULE, "ensure_link", lambda *_args: None):
                result = MODULE.extract_subject(*args, run_id="new-run")
            self.assertEqual(result["cache_hit"], 1)
            self.assertEqual(result["run_id"], "new-run")
            self.assertNotIn("qc_status", result)
            self.assertNotIn("export_status", result)

    def test_same_schema_older_tool_cache_is_reused_after_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            args = (subject, output, root, ("dk68",), "atlas", {}, root, "FS-7", "template", False)
            with patch.object(MODULE, "TOOL_VERSION", "1.0.0rc0"):
                first = MODULE.extract_subject(*args)
            second = MODULE.extract_subject(*args)
            self.assertEqual(first["cache_produced_by_tool_version"], "1.0.0rc0")
            self.assertEqual(second["cache_hit"], 1)
            self.assertEqual(second["cache_produced_by_tool_version"], "1.0.0rc0")
            self.assertEqual(
                second["cache_last_validated_by_tool_version"], MODULE.TOOL_VERSION
            )

    def test_different_cache_schema_is_recomputed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            args = (subject, output, root, ("dk68",), "atlas", {}, root, "FS-7", "template", False)
            with patch.object(MODULE, "CACHE_SCHEMA_VERSION", 0):
                first = MODULE.extract_subject(*args)
            second = MODULE.extract_subject(*args)
            self.assertEqual(first["cache_schema_version"], 0)
            self.assertEqual(second["cache_schema_version"], MODULE.CACHE_SCHEMA_VERSION)
            self.assertEqual(second["cache_hit"], 0)

    def test_region_schema_rejects_wrong_names_with_correct_count(self):
        schema = MODULE.load_region_schema(MODULE_PATH.parent / "atlases", ("dk68",))
        rows = [
            {
                "region": region,
                **{column: 10 if column == "numvert" else 1.0 for column in MODULE.CORTICAL_COLUMNS},
            }
            for region in DK68_REGIONS
        ]
        self.assertEqual(
            MODULE.validate_cortical_rows(rows, "dk68", "lh", schema["dk68:lh"]),
            [],
        )
        rows[0]["region"] = "wrong-region"
        self.assertIn(
            "region names do not match",
            " ".join(MODULE.validate_cortical_rows(rows, "dk68", "lh", schema["dk68:lh"])),
        )

    def test_aseg_with_only_one_structure_is_incomplete(self):
        row = dict(zip(MODULE.ASEG_COLUMNS, [1, 2, 3, 4.5, "Left-Test", 6, 7, 8, 9, 10]))
        errors = MODULE.validate_aseg_rows([row], [])
        self.assertIn("expected at least", " ".join(errors))

    def test_aseg_declared_row_count_must_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aseg.stats"
            write_valid_aseg(path)
            text = path.read_text(encoding="utf-8").replace("# NRows 20", "# NRows 79")
            path.write_text(text, encoding="utf-8")
            errors = MODULE.validate_aseg_rows(
                MODULE.parse_aseg_stats(path),
                MODULE.parse_measure_lines(path),
                MODULE.parse_aseg_header(path),
            )
        self.assertIn("NRows does not match", " ".join(errors))

    def test_aseg_column_order_must_match_supported_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aseg.stats"
            write_valid_aseg(path)
            text = path.read_text(encoding="utf-8").replace(
                "# ColHeaders Index SegId NVoxels Volume_mm3",
                "# ColHeaders SegId Index NVoxels Volume_mm3",
            )
            path.write_text(text, encoding="utf-8")
            errors = MODULE.validate_aseg_rows(
                MODULE.parse_aseg_stats(path),
                MODULE.parse_measure_lines(path),
                MODULE.parse_aseg_header(path),
            )
        self.assertIn("ColHeaders are missing or unsupported", " ".join(errors))

    def test_builtin_atlas_uses_existing_stats_without_projection_or_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()

            def unexpected_command(*_args):
                self.fail("Built-in atlas extraction must not invoke FreeSurfer commands")

            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", unexpected_command
            ):
                result = MODULE.extract_subject(
                    subject, output, root, ("dk68",), "atlas", {}, root, "FS-7", "template", False
                )

            self.assertEqual(result["status"], "OK")
            self.assertFalse((output / "per_subject" / "sub-01" / "label").exists())
            self.assertFalse((output / "per_subject" / "sub-01" / "stats").exists())

    def test_partial_result_is_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            args = (subject, output, root, ("dk68",), "atlas", {}, root, "FS-7", "template", False)
            with patch.object(MODULE, "ensure_link", lambda *_args: None):
                first = MODULE.extract_subject(*args)
                write_cortical(subject / "stats" / "rh.aparc.stats", 34)
                second = MODULE.extract_subject(*args)
            self.assertEqual(first["status"], "PARTIAL")
            self.assertEqual(second["status"], "OK")
            self.assertEqual(second["cortical_rows"], 68)

    def test_changed_atlas_recomputes_external_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            atlas_dir = root / "atlases"
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            atlas_dir.mkdir()
            names = [
                "lh.schaefer-100_mics.annot",
                "rh.schaefer-100_mics.annot",
            ]
            for name in names:
                (atlas_dir / name).write_bytes(b"annot")
            calls = []

            def fake_run(command, _env, _log):
                calls.append(command)
                if "-f" in command:
                    write_cortical(
                        Path(command[command.index("-f") + 1]),
                        50,
                        annotation_name=Path(command[command.index("-a") + 1]).name,
                    )
                else:
                    target = Path(command[command.index("--tval") + 1])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"projected")

            common = (subject, output, atlas_dir, ("schaefer100",))
            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(MODULE, "run_command", fake_run):
                first = MODULE.extract_subject(
                    *common, "atlas-a", {name: "a" for name in names}, root, "FS-7", "template", False,
                    work_subjects=root / "work",
                )
                first_call_count = len(calls)
                second = MODULE.extract_subject(
                    *common, "atlas-b", {name: "b" for name in names}, root, "FS-7", "template", False,
                    work_subjects=root / "work",
                )
            self.assertEqual(first["status"], "OK")
            self.assertEqual(second["status"], "OK")
            self.assertEqual(first_call_count, 4)
            self.assertEqual(len(calls), 8)
            self.assertFalse(any("--mapmethod" in command for command in calls))

    def test_corrupt_cached_annotation_recomputes_external_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            atlas_dir = root / "atlases"
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            atlas_dir.mkdir()
            names = [f"{hemi}.schaefer-100_mics.annot" for hemi in ("lh", "rh")]
            for name in names:
                (atlas_dir / name).write_bytes(b"template")
            calls = []

            def fake_run(command, _env, _log):
                calls.append(command)
                if "-f" in command:
                    write_cortical(
                        Path(command[command.index("-f") + 1]),
                        50,
                        annotation_name=Path(command[command.index("-a") + 1]).name,
                    )
                else:
                    target = Path(command[command.index("--tval") + 1])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"projected")

            args = (
                subject, output, atlas_dir, ("schaefer100",), "atlas",
                {name: "checksum" for name in names}, root, "FS-7", "template", False,
            )
            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", fake_run
            ):
                first = MODULE.extract_subject(*args, work_subjects=root / "work")
                annotation = output / "per_subject" / "sub-01" / "label" / "lh.schaefer100.annot"
                annotation.write_bytes(b"corrupt")
                second = MODULE.extract_subject(*args, work_subjects=root / "work")

            self.assertEqual(first["status"], "OK")
            self.assertEqual(second["status"], "OK")
            self.assertEqual(second["cache_hit"], 0)
            self.assertEqual(annotation.read_bytes(), b"projected")
            self.assertEqual(len(calls), 6)

    def test_existing_subject_stats_are_not_reused_without_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            atlas_dir = root / "atlases"
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            atlas_dir.mkdir()
            checksums = {}
            for hemi in ("lh", "rh"):
                name = f"{hemi}.schaefer-100_mics.annot"
                (atlas_dir / name).write_bytes(b"template")
                checksums[name] = "checksum"
                (subject / "label").mkdir(exist_ok=True)
                (subject / "label" / name).write_bytes(b"subject-annotation")
                write_cortical(
                    subject / "stats" / name.replace(".annot", ".stats"),
                    50,
                    annotation_name=name,
                )
                stats_path = subject / "stats" / name.replace(".annot", ".stats")
                stats_path.write_text(
                    "# subjectname sub-other\n" + stats_path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )

            calls = []

            def fake_run(command, _env, _log):
                calls.append(command)
                if "-f" in command:
                    write_cortical(
                        Path(command[command.index("-f") + 1]),
                        50,
                        annotation_name=Path(command[command.index("-a") + 1]).name,
                    )
                else:
                    target = Path(command[command.index("--tval") + 1])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"projected")

            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", fake_run
            ):
                result = MODULE.extract_subject(
                    subject,
                    output,
                    atlas_dir,
                    ("schaefer100",),
                    "atlas",
                    checksums,
                    root,
                    "FS-7",
                    "template",
                    False,
                    work_subjects=root / "work",
            )

            subject_out = output / "per_subject" / "sub-01"
            artifact = json.loads(
                (subject_out / "stats" / "lh.schaefer100.artifact.json").read_text(encoding="utf-8")
            )
            self.assertEqual(result["status"], "OK")
            self.assertEqual(artifact["source"], "projected")
            self.assertEqual(len(calls), 4)
            self.assertEqual(
                (subject_out / "label" / "lh.schaefer100.annot").read_bytes(),
                b"projected",
            )

    def test_overwrite_does_not_reuse_subject_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            atlas_dir = root / "atlases"
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            atlas_dir.mkdir()
            checksums = {}
            for hemi in ("lh", "rh"):
                name = f"{hemi}.schaefer-100_mics.annot"
                (atlas_dir / name).write_bytes(b"template")
                checksums[name] = "checksum"
                (subject / "label").mkdir(exist_ok=True)
                (subject / "label" / name).write_bytes(b"subject-annotation")
                write_cortical(
                    subject / "stats" / name.replace(".annot", ".stats"),
                    50,
                    annotation_name=name,
                )
            calls = []

            def fake_run(command, _env, _log):
                calls.append(command)
                if "-f" in command:
                    write_cortical(
                        Path(command[command.index("-f") + 1]),
                        50,
                        annotation_name=Path(command[command.index("-a") + 1]).name,
                    )
                else:
                    target = Path(command[command.index("--tval") + 1])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"new-projection")

            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", fake_run
            ):
                result = MODULE.extract_subject(
                    subject, output, atlas_dir, ("schaefer100",), "atlas", checksums,
                    root, "FS-7", "template", True,
                    work_subjects=root / "work",
                )
            self.assertEqual(result["status"], "OK")
            self.assertEqual(len(calls), 4)
            self.assertEqual(
                (output / "per_subject" / "sub-01" / "label" / "lh.schaefer100.annot").read_bytes(),
                b"new-projection",
            )

    def test_legacy_annotations_cache_is_imported_into_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject_out = Path(tmp) / "per_subject" / "sub-01"
            legacy = subject_out / "annotations" / "lh.schaefer100.annot"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"legacy")
            path = MODULE.output_annotation_path(
                subject_out, MODULE.ATLAS_SPECS["schaefer100"], "lh"
            )
            self.assertEqual(path, subject_out / "label" / "lh.schaefer100.annot")
            self.assertEqual(path.read_bytes(), b"legacy")

    def test_newer_tool_cache_is_not_reused_by_older_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            atlas_dir = root / "atlases"
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            atlas_dir.mkdir()
            checksums = {}
            for hemi in ("lh", "rh"):
                name = f"{hemi}.schaefer-100_mics.annot"
                (atlas_dir / name).write_bytes(b"template")
                checksums[name] = "checksum"

            def fake_run(command, _env, _log):
                if "-f" in command:
                    write_cortical(
                        Path(command[command.index("-f") + 1]),
                        50,
                        annotation_name=Path(command[command.index("-a") + 1]).name,
                    )
                else:
                    target = Path(command[command.index("--tval") + 1])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"projected")

            args = (
                subject, output, atlas_dir, ("schaefer100",), "atlas", checksums,
                root, "FS-7", "template", False,
            )
            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", fake_run
            ), patch.object(MODULE, "TOOL_VERSION", "1.2.0"):
                first = MODULE.extract_subject(*args, work_subjects=root / "work")
            subject_out = output / "per_subject" / "sub-01"
            (subject_out / "label").rename(subject_out / "annotations")

            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", fake_run
            ):
                second = MODULE.extract_subject(*args, work_subjects=root / "work")

            self.assertEqual(first["tool_version"], "1.2.0")
            self.assertEqual(second["tool_version"], MODULE.TOOL_VERSION)
            self.assertEqual(second["cache_hit"], 0)
            self.assertTrue((subject_out / "label" / "lh.schaefer100.annot").is_file())

    def test_legacy_external_cache_without_artifact_checksums_is_recomputed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            atlas_dir = root / "atlases"
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            atlas_dir.mkdir()
            names = [f"{hemi}.schaefer-100_mics.annot" for hemi in ("lh", "rh")]
            for name in names:
                (atlas_dir / name).write_bytes(b"template")
            calls = []

            def fake_run(command, _env, _log):
                calls.append(command)
                if "-f" in command:
                    write_cortical(
                        Path(command[command.index("-f") + 1]),
                        50,
                        annotation_name=Path(command[command.index("-a") + 1]).name,
                    )
                else:
                    target = Path(command[command.index("--tval") + 1])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"projected")

            args = (
                subject, output, atlas_dir, ("schaefer100",), "atlas",
                {name: "checksum" for name in names}, root, "FS-7", "template", False,
            )
            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", fake_run
            ), patch.object(MODULE, "TOOL_VERSION", "1.0.0rc0"):
                MODULE.extract_subject(*args, work_subjects=root / "work")

            subject_out = output / "per_subject" / "sub-01"
            for hemi in MODULE.HEMISPHERES:
                status_path = subject_out / "stats" / f"{hemi}.schaefer100.artifact.json"
                status = json.loads(status_path.read_text(encoding="utf-8"))
                status.pop("output_artifacts")
                status_path.write_text(json.dumps(status), encoding="utf-8")

            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", fake_run
            ):
                result = MODULE.extract_subject(*args, work_subjects=root / "work")

            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["cache_hit"], 0)
            self.assertEqual(len(calls), 8)

    def test_export_to_freesurfer_is_opt_in_and_never_overwrites(self):
        self.assertFalse(MODULE.parse_args(["subjects", "output"]).export_to_freesurfer)
        self.assertTrue(
            MODULE.parse_args(
                ["subjects", "output", "--export-to-freesurfer"]
            ).export_to_freesurfer
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "subjects" / "sub-01"
            subject_out = root / "output" / "per_subject" / "sub-01"
            (subject / "label").mkdir(parents=True)
            (subject / "stats").mkdir()
            (subject_out / "label").mkdir(parents=True)
            (subject_out / "stats").mkdir()
            for hemi in ("lh", "rh"):
                name = f"{hemi}.schaefer100"
                (subject_out / "label" / f"{name}.annot").write_bytes(b"projected")
                write_cortical(
                    subject_out / "stats" / f"{name}.stats",
                    50,
                    annotation_name=f"{name}.annot",
                )
            write_artifact_metadata(subject_out, "schaefer100")

            first = MODULE.export_subject_artifacts(
                subject, subject_out, ("dk68", "schaefer100")
            )
            migrated = MODULE.managed_exports_from_status(
                subject, subject_out, {"exported_paths": first["exported_paths"]}
            )
            second = MODULE.export_subject_artifacts(
                subject,
                subject_out,
                ("dk68", "schaefer100"),
                managed_exports=migrated,
            )
            self.assertEqual(first["exported_files"], 4)
            self.assertEqual(len(migrated), 4)
            self.assertEqual(second["exported_files"], 0)
            self.assertEqual(second["existing_export_files"], 4)

            (subject / "label" / "lh.schaefer100.annot").write_bytes(b"conflict")
            with self.assertRaisesRegex(FileExistsError, "Refusing to replace"):
                MODULE.export_subject_artifacts(subject, subject_out, ("schaefer100",))
            self.assertEqual(
                (subject / "label" / "lh.schaefer100.annot").read_bytes(), b"conflict"
            )

    def test_repeated_full_export_reuses_cache_and_detects_later_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subjects = root / "subjects"
            subject = subjects / "sub-01"
            output = root / "output"
            fs_home = root / "freesurfer"
            atlas_dir = MODULE_PATH.parent / "atlases"
            write_cortical(
                subject / "stats" / "lh.aparc.stats", 34, regions=DK68_REGIONS
            )
            write_cortical(
                subject / "stats" / "rh.aparc.stats", 34, regions=DK68_REGIONS
            )
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            (subject / "label").mkdir()
            (subject / "surf").mkdir()
            for hemi in MODULE.HEMISPHERES:
                (subject / "label" / f"{hemi}.cortex.label").write_bytes(b"cortex")
                for name in ("sphere.reg", "white", "pial", "thickness"):
                    (subject / "surf" / f"{hemi}.{name}").write_bytes(b"surface")
                template_surf = fs_home / "subjects" / "fsaverage5" / "surf"
                template_surf.mkdir(parents=True, exist_ok=True)
                (template_surf / f"{hemi}.sphere.reg").write_bytes(b"template")

            calls: list[list[str]] = []

            def fake_run(command, _env, _log):
                calls.append(command)
                if command[0] == "mri_surf2surf":
                    source = Path(command[command.index("--sval-annot") + 1])
                    target = Path(command[command.index("--tval") + 1])
                    MODULE.atomic_copy_file(source, target)
                    return
                annotation = Path(command[command.index("-a") + 1])
                spec = MODULE.ATLAS_SPECS["schaefer100"]
                regions = [
                    name
                    for name in MODULE.annotation_region_names(annotation)
                    if name not in spec.excluded_regions
                ]
                write_cortical(
                    Path(command[command.index("-f") + 1]),
                    50,
                    annotation_name=annotation.name,
                    regions=regions,
                )

            argv = [
                str(subjects),
                str(output),
                "--freesurfer-home",
                str(fs_home),
                "--atlas-dir",
                str(atlas_dir),
                "--atlases",
                "dk68",
                "schaefer100",
                "--export-to-freesurfer",
                "--jobs",
                "1",
            ]
            patches = (
                patch.object(MODULE.shutil, "which", return_value="/fake/tool"),
                patch.object(MODULE, "command_version", return_value="FS-7"),
                patch.object(MODULE, "read_surface_vertex_count", return_value=10242),
                patch.object(MODULE, "ensure_link", lambda *_args: None),
                patch.object(MODULE, "run_command", fake_run),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                self.assertEqual(MODULE.main(argv), 0)
                first_call_count = len(calls)
                self.assertEqual(MODULE.main(argv), 0)
                second_call_count = len(calls)
                second_status = json.loads(
                    (output / "per_subject" / "sub-01" / "status.json").read_text(
                        encoding="utf-8"
                    )
                )

                exported_annotation = subject / "label" / "lh.schaefer100.annot"
                exported_annotation.write_bytes(exported_annotation.read_bytes() + b"conflict")
                conflicting_bytes = exported_annotation.read_bytes()
                self.assertEqual(MODULE.main(argv), 2)
                third_call_count = len(calls)

            status = json.loads(
                (output / "per_subject" / "sub-01" / "status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(first_call_count, 4)
            self.assertEqual(second_call_count, 4)
            self.assertEqual(third_call_count, 4)
            self.assertEqual(second_status["cache_hit"], 1)
            self.assertEqual(len(second_status["managed_exports"]), 4)
            self.assertEqual(status["export_status"], "FAILED")
            self.assertIn("Refusing to replace", status["export_errors"])
            self.assertEqual(exported_annotation.read_bytes(), conflicting_bytes)
            self.assertFalse(any(output.glob(".fsharvest-work-*")))

    def test_export_rejects_empty_annotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "subjects" / "sub-01"
            subject_out = root / "output" / "per_subject" / "sub-01"
            (subject / "label").mkdir(parents=True)
            (subject / "stats").mkdir()
            (subject_out / "label").mkdir(parents=True)
            (subject_out / "stats").mkdir()
            for hemi in ("lh", "rh"):
                name = f"{hemi}.schaefer100"
                (subject_out / "label" / f"{name}.annot").write_bytes(b"")
                write_cortical(
                    subject_out / "stats" / f"{name}.stats",
                    50,
                    annotation_name=f"{name}.annot",
                )
            write_artifact_metadata(subject_out, "schaefer100")

            with self.assertRaisesRegex(RuntimeError, "annotation.*empty"):
                MODULE.export_subject_artifacts(subject, subject_out, ("schaefer100",))

    def test_export_conflict_is_preflighted_before_any_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "subjects" / "sub-01"
            subject_out = root / "output" / "per_subject" / "sub-01"
            (subject / "label").mkdir(parents=True)
            (subject / "stats").mkdir()
            (subject_out / "label").mkdir(parents=True)
            (subject_out / "stats").mkdir()
            for hemi in ("lh", "rh"):
                name = f"{hemi}.schaefer100"
                (subject_out / "label" / f"{name}.annot").write_bytes(b"projected")
                write_cortical(
                    subject_out / "stats" / f"{name}.stats",
                    50,
                    annotation_name=f"{name}.annot",
                )
            write_artifact_metadata(subject_out, "schaefer100")
            (subject / "label" / "lh.schaefer100.annot").write_bytes(b"conflict")

            with self.assertRaisesRegex(FileExistsError, "Refusing to replace"):
                MODULE.export_subject_artifacts(subject, subject_out, ("schaefer100",))

            self.assertFalse((subject / "label" / "rh.schaefer100.annot").exists())
            self.assertEqual(list((subject / "stats").iterdir()), [])

    def test_invalid_subject_annotation_falls_back_to_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            atlas_dir = root / "atlases"
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            atlas_dir.mkdir()
            calls = []
            checksums = {}
            for hemi in ("lh", "rh"):
                name = f"{hemi}.schaefer-100_mics.annot"
                (atlas_dir / name).write_bytes(b"template")
                checksums[name] = "checksum"
                (subject / "label").mkdir(exist_ok=True)
                (subject / "label" / name).write_bytes(b"subject-annotation")

            def fake_run(command, _env, _log):
                calls.append(command)
                if "-f" in command:
                    write_cortical(
                        Path(command[command.index("-f") + 1]),
                        50,
                        annotation_name=Path(command[command.index("-a") + 1]).name,
                    )
                else:
                    target = Path(command[command.index("--tval") + 1])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"projected")

            with patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "run_command", fake_run
            ):
                result = MODULE.extract_subject(
                    subject,
                    output,
                    atlas_dir,
                    ("schaefer100",),
                    "atlas",
                    checksums,
                    root,
                    "FS-7",
                    "template",
                    False,
                    work_subjects=root / "work",
            )

            self.assertEqual(result["status"], "OK")
            self.assertEqual(len(calls), 4)
            self.assertEqual(
                (output / "per_subject" / "sub-01" / "label" / "lh.schaefer100.annot").read_bytes(),
                b"projected",
            )

    def test_streaming_aggregate_outputs_expected_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            with patch.object(MODULE, "ensure_link", lambda *_args: None):
                MODULE.extract_subject(
                    subject, output, root, ("dk68",), "atlas", {}, root, "FS-7", "template", False
                )
            metadata = {"tool": "test", "tool_version": MODULE.TOOL_VERSION}
            MODULE.aggregate(output, [subject], ("dk68",), metadata)
            self.assertEqual(len(MODULE.read_tsv(output / "cortical_long.tsv")), 68)
            self.assertEqual(len(MODULE.read_tsv(output / "aseg_long.tsv")), MODULE.MIN_ASEG_ROWS)
            self.assertEqual(len(MODULE.read_tsv(output / "wide" / "dk68.tsv")), 1)
            run_metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertIn("finished_at_utc", run_metadata)
            self.assertTrue((output / "all_qc.html").is_file())

    def test_changed_run_scope_rewrites_current_tables_and_archives_stale_wide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subjects = root / "subjects"
            fs_home = root / "freesurfer"
            output = root / "output"
            fs_home.mkdir()
            for index in range(3):
                subject = subjects / f"sub-{index + 1:02d}"
                write_cortical(
                    subject / "stats" / "lh.aparc.stats", 34, regions=DK68_REGIONS
                )
                write_cortical(
                    subject / "stats" / "rh.aparc.stats", 34, regions=DK68_REGIONS
                )
                write_cortical(subject / "stats" / "lh.aparc.a2009s.stats", 74)
                write_cortical(subject / "stats" / "rh.aparc.a2009s.stats", 74)
                write_valid_aseg(subject / "stats" / "aseg.stats")
                (subject / "scripts").mkdir()
                (subject / "scripts" / "recon-all.done").touch()

            common = [
                str(subjects),
                str(output),
                "--freesurfer-home",
                str(fs_home),
                "--jobs",
                "1",
            ]
            with patch.object(MODULE.shutil, "which", return_value="/fake/tool"), patch.object(
                MODULE, "command_version", return_value="FS-7"
            ), patch.object(
                MODULE, "load_region_schema", return_value={}
            ):
                self.assertEqual(
                    MODULE.main([*common, "--atlases", "dk68", "destrieux"]), 0
                )
                self.assertEqual(len(MODULE.read_tsv(output / "subjects.tsv")), 3)
                self.assertTrue((output / "wide" / "destrieux.tsv").is_file())
                first_cortical = MODULE.read_tsv(output / "cortical_long.tsv")
                subject_keys = {
                    (row["folder_id"], row["atlas"], row["hemisphere"], row["region"])
                    for row in first_cortical
                }
                region_keys = {
                    (row["atlas"], row["hemisphere"], row["region"])
                    for row in first_cortical
                }
                self.assertEqual(len(subject_keys), len(first_cortical))
                self.assertLess(len(region_keys), len(first_cortical))

                two_subject_rows = [
                    row
                    for row in first_cortical
                    if row["folder_id"] in {"sub-01", "sub-02"}
                    and row["atlas"] == "dk68"
                    and row["hemisphere"] == "lh"
                    and row["region"] == "bankssts"
                ]
                self.assertEqual(len(two_subject_rows), 2)
                compound_join = [
                    (left, right)
                    for left in two_subject_rows
                    for right in two_subject_rows
                    if all(
                        left[key] == right[key]
                        for key in ("folder_id", "atlas", "hemisphere", "region")
                    )
                ]
                region_only_join = [
                    (left, right)
                    for left in two_subject_rows
                    for right in two_subject_rows
                    if all(
                        left[key] == right[key]
                        for key in ("atlas", "hemisphere", "region")
                    )
                ]
                self.assertEqual(len(compound_join), 2)
                self.assertEqual(len(region_only_join), 4)

                stale_wide = output / "wide" / "destrieux.tsv"
                original_stale_wide = stale_wide.read_bytes()
                stale_wide.write_bytes(original_stale_wide + b"user change\n")
                with self.assertRaisesRegex(RuntimeError, "matching provenance"):
                    MODULE.main([*common, "--limit", "1", "--atlases", "dk68"])
                self.assertTrue(stale_wide.is_file())
                stale_wide.write_bytes(original_stale_wide)

                self.assertEqual(
                    MODULE.main([*common, "--limit", "1", "--atlases", "dk68"]), 0
                )

            summaries = MODULE.read_tsv(output / "subjects.tsv")
            cortical = MODULE.read_tsv(output / "cortical_long.tsv")
            self.assertEqual([row["folder_id"] for row in summaries], ["sub-01"])
            self.assertEqual({row["folder_id"] for row in cortical}, {"sub-01"})
            compound_keys = {
                (row["folder_id"], row["atlas"], row["hemisphere"], row["region"])
                for row in cortical
            }
            self.assertEqual(len(compound_keys), len(cortical))
            self.assertFalse((output / "wide" / "destrieux.tsv").exists())
            metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["n_subjects"], 1)
            self.assertEqual(len(metadata["archived_wide_tables"]), 1)
            self.assertTrue((output / metadata["archived_wide_tables"][0]).is_file())

    def test_aggregate_rejects_output_changed_after_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-01"
            output = root / "output"
            write_cortical(subject / "stats" / "lh.aparc.stats", 34)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            with patch.object(MODULE, "ensure_link", lambda *_args: None):
                MODULE.extract_subject(
                    subject, output, root, ("dk68",), "atlas", {}, root,
                    "FS-7", "template", False, run_id="run-1",
                )
            cortical = output / "per_subject" / "sub-01" / "cortical.tsv"
            cortical.write_text(
                cortical.read_text(encoding="utf-8").replace("\t2.5\t", "\t2.6\t", 1),
                encoding="utf-8",
            )
            non_ok = MODULE.aggregate(
                output,
                [subject],
                ("dk68",),
                {"tool": "test", "tool_version": MODULE.TOOL_VERSION, "run_id": "run-1"},
            )
            status = json.loads(
                (output / "per_subject" / "sub-01" / "status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(non_ok, {"sub-01"})
            self.assertEqual(status["status"], "PARTIAL")
            self.assertIn("checksums", status["errors"])
            self.assertEqual(MODULE.read_tsv(output / "cortical_long.tsv"), [])
            self.assertEqual(MODULE.read_tsv(output / "wide" / "dk68.tsv"), [])

    def test_main_happy_path_and_fatal_status_are_aggregated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subjects = root / "subjects"
            subject = subjects / "sub-01"
            fs_home = root / "freesurfer"
            output = root / "output"
            fs_home.mkdir()
            (output / "work").mkdir(parents=True)
            (output / "work" / "user_notes.txt").write_text("keep", encoding="utf-8")
            write_cortical(subject / "stats" / "lh.aparc.stats", 34, regions=DK68_REGIONS)
            write_cortical(subject / "stats" / "rh.aparc.stats", 34, regions=DK68_REGIONS)
            write_valid_aseg(subject / "stats" / "aseg.stats")
            (subject / "scripts").mkdir()
            (subject / "scripts" / "recon-all.done").touch()
            argv = [str(subjects), str(output), "--freesurfer-home", str(fs_home), "--jobs", "1"]
            with patch.object(MODULE.shutil, "which", return_value="/fake/tool"), patch.object(
                MODULE, "command_version", return_value="FS-7"
            ), patch.object(MODULE, "ensure_link", lambda *_args: None):
                self.assertEqual(MODULE.main(argv), 0)
            run_metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
            status = json.loads(
                (output / "per_subject" / "sub-01" / "status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(status["run_id"], run_metadata["run_id"])
            self.assertEqual(status["status"], "OK")
            self.assertEqual(
                (output / "work" / "user_notes.txt").read_text(encoding="utf-8"), "keep"
            )
            self.assertFalse(any(output.glob(".fsharvest-work-*")))
            self.assertFalse((output / ".fsharvest.lock").exists())

            failed_output = root / "failed-output"
            (failed_output / "work").mkdir(parents=True)
            (failed_output / "work" / "user_notes.txt").write_text("keep", encoding="utf-8")
            failed_argv = [
                str(subjects), str(failed_output), "--freesurfer-home", str(fs_home), "--jobs", "1"
            ]
            with patch.object(MODULE.shutil, "which", return_value="/fake/tool"), patch.object(
                MODULE, "command_version", return_value="FS-7"
            ), patch.object(MODULE, "ensure_link", lambda *_args: None), patch.object(
                MODULE, "extract_subject", side_effect=RuntimeError("boom")
            ):
                self.assertEqual(MODULE.main(failed_argv), 2)
            failed_status = json.loads(
                (failed_output / "per_subject" / "sub-01" / "status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(failed_status["status"], "FAILED")
            self.assertIn("boom", failed_status["errors"])
            self.assertEqual(
                (failed_output / "work" / "user_notes.txt").read_text(encoding="utf-8"), "keep"
            )
            self.assertFalse((failed_output / ".fsharvest.lock").exists())

    def test_cleanup_removes_only_the_owned_work_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            existing = output / "work" / "user_notes.txt"
            existing.parent.mkdir(parents=True)
            existing.write_text("keep", encoding="utf-8")
            resources = MODULE.RunResources()
            resources.acquire(output, False)
            owned = resources.create_work_dir()
            (owned / "temporary.txt").write_text("remove", encoding="utf-8")
            resources.cleanup()
            self.assertEqual(existing.read_text(encoding="utf-8"), "keep")
            self.assertFalse(owned.exists())
            self.assertFalse((output / ".fsharvest.lock").exists())

    def test_keyboard_interrupt_preserves_preexisting_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subjects = root / "subjects"
            subject = subjects / "sub-01"
            output = root / "output"
            fs_home = root / "freesurfer"
            fs_home.mkdir()
            write_valid_aseg(subject / "stats" / "aseg.stats")
            existing = output / "work" / "user_notes.txt"
            existing.parent.mkdir(parents=True)
            existing.write_text("keep", encoding="utf-8")
            argv = [str(subjects), str(output), "--freesurfer-home", str(fs_home)]
            with patch.object(MODULE.shutil, "which", return_value="/fake/tool"), patch.object(
                MODULE, "command_version", return_value="FS-7"
            ), patch.object(MODULE, "extract_subject", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    MODULE.main(argv)
            self.assertEqual(existing.read_text(encoding="utf-8"), "keep")
            self.assertFalse((output / ".fsharvest.lock").exists())

    def test_output_cannot_contain_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "project"
            subjects = output / "work" / "freesurfer"
            subject = subjects / "sub-01"
            fs_home = Path(tmp) / "freesurfer-home"
            fs_home.mkdir()
            write_valid_aseg(subject / "stats" / "aseg.stats")
            with patch.object(MODULE.shutil, "which", return_value="/fake/tool"):
                with self.assertRaisesRegex(ValueError, "must not contain one another"):
                    MODULE.main(
                        [str(subjects), str(output), "--freesurfer-home", str(fs_home)]
                    )
            self.assertTrue((subject / "stats" / "aseg.stats").is_file())
            self.assertFalse((output / ".fsharvest.lock").exists())

    def test_output_lock_rejects_concurrent_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            first = MODULE.RunResources()
            second = MODULE.RunResources()
            first.acquire(output, False)
            try:
                with self.assertRaisesRegex(RuntimeError, "Output directory is locked"):
                    second.acquire(output, False)
            finally:
                first.cleanup()
                second.cleanup()
            self.assertFalse((output / ".fsharvest.lock").exists())

    def test_force_unlock_replaces_only_stale_same_host_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            output.mkdir()
            lock = output / ".fsharvest.lock"
            lock.write_text(
                json.dumps({"hostname": MODULE.socket.gethostname(), "pid": 999999999}),
                encoding="utf-8",
            )
            resources = MODULE.RunResources()
            with patch.object(MODULE, "process_is_running", return_value=False):
                resources.acquire(output, True)
            try:
                current = json.loads(lock.read_text(encoding="utf-8"))
                self.assertEqual(current["lock_id"], resources.lock_id)
            finally:
                resources.cleanup()

    def test_qc_dependencies_are_checked_before_output_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subjects = root / "subjects"
            fs_home = root / "freesurfer"
            output = root / "output"
            subjects.mkdir()
            fs_home.mkdir()
            argv = [
                str(subjects), str(output), "--freesurfer-home", str(fs_home), "--qc-plots"
            ]
            with patch.object(MODULE.shutil, "which", return_value="/fake/tool"), patch.dict(
                sys.modules, {"fs_render_qc": None}
            ):
                with self.assertRaisesRegex(RuntimeError, "QC plots require"):
                    MODULE.main(argv)
            self.assertFalse(output.exists())

    def test_qc_report_uses_only_current_validated_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            subject = Path(tmp) / "inputs" / "sub-01"
            subject_out = output / "per_subject" / subject.name
            for hemi in MODULE.HEMISPHERES:
                (subject / "surf").mkdir(parents=True, exist_ok=True)
                (subject / "label").mkdir(exist_ok=True)
                (subject / "surf" / f"{hemi}.inflated").write_bytes(b"surface")
                (subject / "label" / f"{hemi}.aparc.annot").write_bytes(b"annotation")
            image = subject_out / "qc" / "dk68_inflated_4view.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"png")
            existing_image = subject_out / "qc" / "schaefer100_pial_4view.png"
            existing_image.write_bytes(b"png")
            current = MODULE.write_qc_artifact_metadata(
                subject, subject_out, image, "dk68", "inflated", 150, "run-1"
            )
            records = [(
                subject,
                subject_out,
                {
                    "subject_id": "participant-01",
                    "status": "OK",
                    "qc_status": "OK",
                    "run_id": "run-1",
                    "qc_artifacts": [current],
                },
            )]
            MODULE.write_qc_report(output, records, ("dk68",))
            report = (output / "all_qc.html").read_text(encoding="utf-8")
            self.assertIn("per_subject/sub-01/qc/dk68_inflated_4view.png", report)
            self.assertNotIn("schaefer100_pial_4view.png", report)
            self.assertNotIn(str(output), report)
            self.assertIn('data-subject="participant-01 sub-01"', report)
            self.assertEqual(report.count('class="atlas-tab"'), 1)
            self.assertEqual(report.count('class="atlas-panel"'), 1)
            self.assertNotIn("<select", report)

            image.write_bytes(b"changed")
            MODULE.write_qc_report(output, records, ("dk68",))
            refreshed = (output / "all_qc.html").read_text(encoding="utf-8")
            self.assertNotIn("dk68_inflated_4view.png", refreshed)


if __name__ == "__main__":
    unittest.main()

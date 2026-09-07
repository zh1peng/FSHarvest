import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_fs_extract_all import MODULE, MODULE_PATH, DK68_REGIONS, write_cortical, write_valid_aseg


def write_annotation(path, names, vertices=6, shift=0):
    def integer(value):
        return struct.pack(">i", value)

    def string(value):
        raw = value.encode("utf-8") + b"\0"
        return integer(len(raw)) + raw

    data = integer(vertices)
    for vertex in range(vertices):
        data += integer(vertex) + integer((vertex + shift) % len(names) + 1)
    data += integer(1) + integer(len(names)) + string("test")
    for index, name in enumerate(names, 1):
        data += string(name) + struct.pack(">4i", index, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_surface(path, vertices=6):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xff\xfecreated by test\n\n" + struct.pack(">2i", vertices, 0)
                     + bytes(vertices * 3 * 4))


class CustomAtlasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fs_home = self.root / "freesurfer"
        self.atlas_dir = MODULE_PATH.parent / "atlases"
        self.definition = self.root / "my atlas" / "atlas.json"
        self.document = {
            "key": "lab",
            "display_name": "Laboratory atlas",
            "source_subject": "fsaverage5",
            "annotations": {"lh": "left.annot", "rh": "right.annot"},
            "excluded_regions": ["unknown"],
        }
        self.names = {"lh": ["unknown", "A", "B"], "rh": ["unknown", "C", "D", "E"]}
        for hemi in MODULE.HEMISPHERES:
            write_annotation(self.definition.parent / self.document["annotations"][hemi], self.names[hemi])
            for surface in ("white", "sphere.reg"):
                write_surface(self.fs_home / "subjects" / "fsaverage5" / "surf" / f"{hemi}.{surface}")
        self.save_definition()

    def save_definition(self):
        self.definition.write_text(json.dumps(self.document), encoding="utf-8")

    def resolve(self, *inputs):
        return MODULE.resolve_atlases(inputs or [str(self.definition)], self.atlas_dir, self.fs_home)

    def test_mixed_input_and_asymmetric_region_counts(self):
        atlases = self.resolve("dk68", str(self.definition))
        spec = atlases["lab"]
        self.assertEqual(list(atlases), ["dk68", "lab"])
        self.assertEqual(spec.expected_total, 5)
        self.assertEqual(spec.expected_rows("lh"), 2)
        self.assertEqual(spec.expected_rows("rh"), 3)
        self.assertEqual(spec.region_names("rh"), ("C", "D", "E"))
        self.assertEqual(spec.annotation_path(self.atlas_dir, "lh"), self.definition.parent / "left.annot")
        self.assertNotIn("lab", MODULE.ATLAS_SPECS)
        # A custom-only run needs neither a curated manifest nor a region hash file.
        custom = {"lab": spec}
        self.assertEqual(MODULE.load_region_schema(self.root, custom), {})
        self.assertEqual(set(MODULE.validate_atlas_files(self.root, custom)), {"lab:lh", "lab:rh"})

    def test_curated_annotations_resolve_to_the_same_definition(self):
        for hemi in MODULE.HEMISPHERES:
            write_surface(self.fs_home / "subjects" / "fsaverage5" / "surf" / f"{hemi}.white", 10242)
        spec = self.resolve("schaefer100")["schaefer100"]
        self.assertEqual(spec.expected_total, 100)
        self.assertEqual(len(spec.region_names("lh")), 50)
        self.assertEqual(Path(spec.annotations[0]), self.atlas_dir / "lh.schaefer-100_mics.annot")

    def test_source_template_mismatch_is_rejected(self):
        write_surface(self.fs_home / "subjects" / "fsaverage5" / "surf" / "rh.white", 7)
        with self.assertRaisesRegex(ValueError, "lab/rh.*6 vertices.*7"):
            self.resolve()

    def test_invalid_definitions_fail_before_extraction(self):
        for field, value, message in (
            ("source_subject", "native", "source_subject"),
            ("key", "dk68", "reserved"),
            ("key", "../lab", "Atlas key"),
            ("excluded_regions", "unknown", "list of region names"),
        ):
            with self.subTest(field=field, value=value):
                original = self.document[field]
                self.document[field] = value
                self.save_definition()
                with self.assertRaisesRegex(ValueError, message):
                    self.resolve()
                self.document[field] = original
        self.save_definition()
        with self.assertRaisesRegex(ValueError, "Duplicate atlas key"):
            self.resolve(str(self.definition), str(self.definition))

    def test_invalid_region_names_and_missing_hemisphere(self):
        left = self.definition.parent / "left.annot"
        for names in (["unknown"], ["A", "A"]):
            with self.subTest(names=names):
                write_annotation(left, names)
                with self.assertRaisesRegex(ValueError, "nonempty, unique"):
                    self.resolve()
        write_annotation(left, self.names["lh"])
        (self.definition.parent / "right.annot").unlink()
        with self.assertRaises(FileNotFoundError):
            self.resolve()

    def test_region_validation_rejects_same_count_with_wrong_names(self):
        spec = self.resolve()["lab"]
        stats = self.root / "lh.stats"
        write_cortical(stats, 2, regions=["A", "Wrong"])
        rows = MODULE.parse_cortical_stats(stats, "lab", "lh")
        self.assertIn("region names", " ".join(MODULE.validate_cortical_rows(rows, spec, "lh")))

    def test_freesurfer_skipped_labels_are_excluded_by_default(self):
        del self.document["excluded_regions"]
        self.save_definition()
        names = ["unknown", "Unknown", "corpuscallosum", "Medial_wall", "A", "B"]
        for hemi in MODULE.HEMISPHERES:
            write_annotation(self.definition.parent / self.document["annotations"][hemi], names)
        spec = self.resolve()["lab"]
        self.assertEqual(spec.region_names("lh"), ("A", "B"))
        self.assertEqual(spec.expected_total, 4)

    def test_unused_color_entries_do_not_require_stats_rows(self):
        left = self.definition.parent / "left.annot"
        write_annotation(left, ["unknown", "A", "B", "C", "D", "E", "Unused"])
        spec = self.resolve()["lab"]
        self.assertEqual(spec.region_names("lh"), ("A", "B", "C", "D", "E"))
        stats = self.root / "lh.stats"
        write_cortical(stats, 5, regions=["A", "B", "C", "D", "E"])
        self.assertEqual(MODULE.validate_cortical_rows(
            MODULE.parse_cortical_stats(stats, "lab", "lh"), spec, "lh"), [])
        self.assertEqual(MODULE.validate_annotation_file(left, spec, "lab", "lh", None, 6), [])
        # A region present in the source but lost on the target must still fail validation.
        write_annotation(left, ["unknown", "A", "B", "C", "D", "E"], vertices=5)
        self.assertIn("region", " ".join(MODULE.validate_annotation_file(left, spec, "lab", "lh", None)))

    def test_stats_preserve_spaced_names_and_all_nine_metrics(self):
        stats = self.root / "lh.stats"
        stats.write_text("  Region  A 10 20 30 2.5 0.1 0.2 0.3 4.0 5.0\n", encoding="utf-8")
        row = MODULE.parse_cortical_stats(stats, "lab", "lh")[0]
        self.assertEqual(row["region"], "Region  A")
        self.assertEqual([row[column] for column in MODULE.CORTICAL_COLUMNS],
                         [10, 20, 30, 2.5, 0.1, 0.2, 0.3, 4.0, 5.0])

    def test_custom_atlas_extraction_aggregation_and_cache(self):
        self.document.pop("excluded_regions")
        self.save_definition()
        self.names["lh"] = ["unknown", "Region A", "B"]
        write_annotation(self.definition.parent / "left.annot", self.names["lh"])
        subject = self.root / "subjects" / "sub-01"
        output = self.root / "output"
        write_valid_aseg(subject / "stats" / "aseg.stats")
        (subject / "scripts").mkdir()
        (subject / "scripts" / "recon-all.done").touch()
        for hemi in MODULE.HEMISPHERES:
            write_surface(subject / "surf" / f"{hemi}.white")
            write_cortical(subject / "stats" / f"{hemi}.aparc.stats", 34, regions=DK68_REGIONS)
            # Same-name subject annotations must not override the explicit custom source.
            write_annotation(subject / "label" / f"{hemi}.lab.annot", self.names[hemi], shift=1)
        calls = []

        def run(command, _env, _log):
            calls.append(command)
            if command[0] == "mri_surf2surf":
                self.assertEqual(command[command.index("--srcsubject") + 1], "fsaverage5")
                source = Path(command[command.index("--sval-annot") + 1])
                target = Path(command[command.index("--tval") + 1])
                shutil.copyfile(source, target)
            else:
                self.assertEqual(command[0], "mris_anatomical_stats")
                annotation = Path(command[command.index("-a") + 1])
                # Emulate the stats program's vertex-based selection, independently
                # of the production annotation reader and region resolver.
                raw = annotation.read_bytes()
                vertex_count = struct.unpack_from(">i", raw)[0]
                used = {struct.unpack_from(">i", raw, 8 + vertex * 8)[0] for vertex in range(vertex_count)}
                hemi = command[-2]
                names = [name for color, name in enumerate(self.names[hemi], 1)
                         if color in used and name not in {"unknown", "Unknown", "corpuscallosum", "Medial_wall"}]
                write_cortical(Path(command[command.index("-f") + 1]), len(names),
                               annotation_name=annotation.name, regions=names)

        args = [str(subject.parent), str(output), "--freesurfer-home", str(self.fs_home),
                "--atlases", "dk68", str(self.definition), "--jobs", "1"]
        with patch.object(MODULE.shutil, "which", return_value="available"), \
             patch.object(MODULE, "command_version", return_value="FS-test"), \
             patch.object(MODULE, "ensure_link"), patch.object(MODULE, "run_command", run):
            self.assertEqual(MODULE.main(args), 0)
            self.assertEqual(len(calls), 4)
            self.assertEqual(MODULE.main(args), 0)
            self.assertEqual(len(calls), 4)
            write_annotation(self.definition.parent / "left.annot", self.names["lh"], shift=1)
            self.assertEqual(MODULE.main(args), 0)
            self.assertEqual(len(calls), 6)  # Only the changed hemisphere is recomputed.

        rows = MODULE.read_tsv(output / "cortical_long.tsv")
        custom_rows = [row for row in rows if row["atlas"] == "lab"]
        self.assertEqual(len(custom_rows), 5)
        self.assertEqual({row["region"] for row in custom_rows}, {"Region A", "B", "C", "D", "E"})
        wide = MODULE.read_tsv(output / "wide" / "lab.tsv")
        self.assertEqual(len(wide), 1)
        self.assertEqual(wide[0]["L_Region A_thickavg"], "2.5")
        metadata = json.loads((output / "run_metadata.json").read_text())
        self.assertEqual(metadata["atlas_definitions"]["lab"]["expected_total"], 5)
        manifest = MODULE.read_tsv(output / "atlas_manifest.tsv")
        self.assertEqual(manifest[1]["observed_subjects_complete"], "1")


if __name__ == "__main__":
    unittest.main()

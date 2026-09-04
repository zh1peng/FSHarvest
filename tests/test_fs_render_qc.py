import tempfile
import unittest
from pathlib import Path


try:
    import nibabel.freesurfer.io as fsio
    import numpy as np
    from PIL import Image

    import fs_render_qc

    HAS_QC_DEPS = True
except ImportError:
    HAS_QC_DEPS = False


@unittest.skipUnless(HAS_QC_DEPS, "optional QC dependencies are not installed")
class RenderQCTests(unittest.TestCase):
    def test_render_synthetic_four_view_png(self):
        vertices = np.array(
            [
                [-1.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, -1.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, -1.0],
                [0.0, 0.0, 1.0],
            ]
        )
        faces = np.array(
            [
                [0, 2, 5], [2, 1, 5], [1, 3, 5], [3, 0, 5],
                [2, 0, 4], [1, 2, 4], [3, 1, 4], [0, 3, 4],
            ],
            dtype=np.int32,
        )
        labels = np.array([0, 0, 1, 1, 0, 1], dtype=np.int32)
        ctab = np.array([[220, 30, 30, 0], [30, 180, 60, 0]], dtype=np.int32)
        names = [b"region_a", b"region_b"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "sub-test"
            subject_out = root / "output" / "per_subject" / subject.name
            (subject / "surf").mkdir(parents=True)
            (subject / "label").mkdir()
            for hemi in ("lh", "rh"):
                fsio.write_geometry(str(subject / "surf" / f"{hemi}.inflated"), vertices, faces)
                fsio.write_annot(
                    str(subject / "label" / f"{hemi}.aparc.annot"), labels, ctab, names
                )
            outputs = fs_render_qc.render_subject(subject, subject_out, ("dk68",), dpi=72)
            self.assertEqual(len(outputs), 1)
            self.assertGreater(outputs[0].stat().st_size, 1_000)
            with Image.open(outputs[0]) as image:
                self.assertGreater(image.width, image.height * 4)


if __name__ == "__main__":
    unittest.main()

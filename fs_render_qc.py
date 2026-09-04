#!/usr/bin/env python3
"""Render headless four-view PNGs for FSHarvest cortical annotations."""

from __future__ import annotations

import argparse
import gc
import io
import os
import tempfile
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel.freesurfer.io as fsio
import numpy as np
from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]
from PIL import Image, ImageChops


ANNOTATION_STEMS = {
    "dk68": "aparc",
    "destrieux": "aparc.a2009s",
    "dk308": "dk308",
    "schaefer100": "schaefer100",
    "schaefer200": "schaefer200",
    "schaefer300": "schaefer300",
    "schaefer400": "schaefer400",
    "schaefer500": "schaefer500",
    "schaefer600": "schaefer600",
    "schaefer700": "schaefer700",
    "schaefer800": "schaefer800",
    "schaefer900": "schaefer900",
    "schaefer1000": "schaefer1000",
    "glasser360": "glasser360",
    "economo": "economo",
    "vosdewael300": "vosdewael300",
}
BUILTIN_ATLASES = {"dk68", "destrieux"}
VIEWS = (
    ("lh", 180),
    ("lh", 0),
    ("rh", 0),
    ("rh", 180),
)


def annotation_path(subject_dir: Path, subject_out: Path, atlas: str, hemi: str) -> Path:
    stem = ANNOTATION_STEMS[atlas]
    if atlas in BUILTIN_ATLASES:
        return subject_dir / "label" / f"{hemi}.{stem}.annot"
    canonical = subject_out / "label" / f"{hemi}.{stem}.annot"
    if canonical.is_file():
        return canonical
    return subject_out / "annotations" / f"{hemi}.{stem}.annot"


def face_colors(vertices: np.ndarray, faces: np.ndarray, labels: np.ndarray, ctab: np.ndarray) -> np.ndarray:
    triangle_labels = labels[faces]
    selected = triangle_labels[:, 0].copy()
    for column in (1, 2):
        missing = selected < 0
        selected[missing] = triangle_labels[missing, column]

    colors = np.full((len(faces), 4), (0.72, 0.72, 0.72, 1.0), dtype=float)
    valid = (selected >= 0) & (selected < len(ctab))
    colors[valid, :3] = ctab[selected[valid], :3] / 255.0

    edge_a = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    edge_b = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    normals = np.cross(edge_a, edge_b)
    lengths = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(lengths[:, None], 1e-12)
    light = np.array((-0.35, -0.45, 0.82), dtype=float)
    light /= np.linalg.norm(light)
    intensity = 0.58 + 0.42 * np.abs(normals @ light)
    colors[:, :3] *= intensity[:, None]
    return np.clip(colors, 0.0, 1.0)


def draw_surface(
    axis: Axes3D,
    vertices: np.ndarray,
    faces: np.ndarray,
    colors: np.ndarray,
    azimuth: float,
) -> None:
    collection = axis.plot_trisurf(
        vertices[:, 0],
        vertices[:, 1],
        vertices[:, 2],
        triangles=faces,
        linewidth=0,
        antialiased=False,
        shade=False,
    )
    collection.set_facecolors(colors)
    lower = vertices.min(axis=0)
    upper = vertices.max(axis=0)
    ranges = np.maximum(upper - lower, 1e-6)
    padding = ranges * 0.02
    axis.set_xlim(lower[0] - padding[0], upper[0] + padding[0])
    axis.set_ylim(lower[1] - padding[1], upper[1] + padding[1])
    axis.set_zlim(lower[2] - padding[2], upper[2] + padding[2])
    axis.set_box_aspect(tuple(ranges))
    axis.set_proj_type("ortho")
    axis.view_init(elev=0, azim=azimuth)
    axis.set_axis_off()


def render_view(
    vertices: np.ndarray,
    faces: np.ndarray,
    colors: np.ndarray,
    azimuth: float,
    dpi: int,
) -> Image.Image:
    figure = plt.figure(figsize=(6, 3), facecolor="white")
    try:
        axis = figure.add_axes((0.0, 0.0, 1.0, 1.0), projection="3d")
        draw_surface(axis, vertices, faces, colors, azimuth)
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", dpi=dpi, facecolor="white")
        buffer.seek(0)
        image = Image.open(buffer).convert("RGB")
        image.load()
        buffer.close()
        return image
    finally:
        plt.close(figure)
        gc.collect()


def crop_white_margin(image: Image.Image, padding: int) -> Image.Image:
    background = Image.new("RGB", image.size, "white")
    difference = ImageChops.difference(image, background).convert("L")
    mask = difference.point(lambda value: 255 if value > 4 else 0)
    box = mask.getbbox()
    if box is None:
        return image.copy()
    left = max(0, box[0] - padding)
    top = max(0, box[1] - padding)
    right = min(image.width, box[2] + padding)
    bottom = min(image.height, box[3] + padding)
    return image.crop((left, top, right, bottom))


def render_atlas(
    subject_dir: Path,
    subject_out: Path,
    atlas: str,
    surface: str,
    dpi: int,
) -> Path:
    if atlas not in ANNOTATION_STEMS:
        raise ValueError(f"Unknown atlas: {atlas}")
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for hemi in ("lh", "rh"):
        surface_path = subject_dir / "surf" / f"{hemi}.{surface}"
        annot_path = annotation_path(subject_dir, subject_out, atlas, hemi)
        if not surface_path.is_file():
            raise FileNotFoundError(f"Missing surface: {surface_path}")
        if not annot_path.is_file():
            raise FileNotFoundError(f"Missing annotation: {annot_path}")
        vertices, faces = fsio.read_geometry(str(surface_path))
        labels, ctab, _names = fsio.read_annot(str(annot_path), orig_ids=False)
        if len(labels) != len(vertices):
            raise RuntimeError(f"Annotation/surface vertex mismatch for {atlas}/{hemi}")
        loaded[hemi] = (vertices, faces, face_colors(vertices, faces, labels, ctab))

    panels = []
    try:
        for hemi, azimuth in VIEWS:
            raw_panel = render_view(*loaded[hemi], azimuth, dpi)
            try:
                panels.append(crop_white_margin(raw_panel, max(2, dpi // 50)))
            finally:
                raw_panel.close()
        gap = max(3, dpi // 30)
        canvas = Image.new(
            "RGB",
            (sum(panel.width for panel in panels) + gap * (len(panels) - 1), max(panel.height for panel in panels)),
            "white",
        )
        x = 0
        for panel in panels:
            canvas.paste(panel, (x, (canvas.height - panel.height) // 2))
            x += panel.width + gap
        output = subject_out / "qc" / f"{atlas}_{surface}_4view.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".png", dir=output.parent)
        os.close(fd)
        try:
            canvas.save(tmp_name, format="PNG", dpi=(dpi, dpi), optimize=True)
            os.replace(tmp_name, output)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        canvas.close()
        return output
    finally:
        for panel in panels:
            panel.close()


def render_subject(
    subject_dir: Path,
    subject_out: Path,
    atlases: Iterable[str],
    surface: str = "inflated",
    dpi: int = 150,
) -> list[Path]:
    return [render_atlas(subject_dir, subject_out, atlas, surface, dpi) for atlas in atlases]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render four-view PNGs from FSHarvest annotations.")
    parser.add_argument("subject_dir", type=Path)
    parser.add_argument("subject_output_dir", type=Path)
    parser.add_argument("--atlases", nargs="+", choices=tuple(ANNOTATION_STEMS), default=list(ANNOTATION_STEMS))
    parser.add_argument("--surface", choices=("inflated", "pial", "white"), default="inflated")
    parser.add_argument("--dpi", type=int, default=150)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs = render_subject(
        args.subject_dir.resolve(),
        args.subject_output_dir.resolve(),
        args.atlases,
        args.surface,
        args.dpi,
    )
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

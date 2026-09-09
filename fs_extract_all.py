#!/usr/bin/env python3
"""Generic, dependency-free extraction of FreeSurfer regional statistics.

Input FreeSurfer outputs are read-only by default. External annotations are
projected through a unique, run-owned SUBJECTS_DIR that is removed on exit. The
explicit ``--export-to-freesurfer`` option can copy validated external atlas
artifacts back to each subject's standard ``label/`` and ``stats/`` folders.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_lib
import json
import math
import os
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional
from urllib.parse import quote


TOOL_VERSION = "1.0.4"
CACHE_SCHEMA_VERSION = 1
OUTPUT_SCHEMA_VERSION = 1
TOOL_NAME = "FSHarvest"
TOOL_DEVELOPER = "zh1peng"
TOOL_URL = "https://github.com/zh1peng/FSHarvest"
ASCII_LOGO = r"""
  _____ ____  _   _                           _
 |  ___/ ___|| | | | __ _ _ ____   _____  ___| |_
 | |_  \___ \| |_| |/ _` | '__\ \ / / _ \/ __| __|
 |  _|  ___) |  _  | (_| | |   \ V /  __/\__ \ |_
 |_|   |____/|_| |_|\__,_|_|    \_/ \___||___/\__|
"""
HEMISPHERES = ("lh", "rh")
# mris_anatomical_stats omits these labels even when they have assigned vertices.
STATS_EXCLUDED_REGIONS = ("unknown", "Unknown", "corpuscallosum", "Medial_wall")
CORTICAL_COLUMNS = (
    "numvert",
    "surfarea",
    "grayvol",
    "thickavg",
    "thickstd",
    "meancurv",
    "gauscurv",
    "foldind",
    "curvind",
)
ASEG_COLUMNS = (
    "index",
    "segid",
    "nvoxels",
    "volume_mm3",
    "structure",
    "norm_mean",
    "norm_stddev",
    "norm_min",
    "norm_max",
    "norm_range",
)
BLACKLIST = {
    "fsaverage",
    "fsaverage3",
    "fsaverage4",
    "fsaverage5",
    "fsaverage6",
    "fsaverage_sym",
    "logs",
    "scripts",
    "tmp",
}
MIN_ASEG_ROWS = 20
ASEG_COL_HEADERS = (
    "Index",
    "SegId",
    "NVoxels",
    "Volume_mm3",
    "StructName",
    "normMean",
    "normStdDev",
    "normMin",
    "normMax",
    "normRange",
)
REQUIRED_ASEG_STRUCTURE_GROUPS = (
    ("Brain-Stem", ("Brain-Stem",)),
    ("Left-Thalamus", ("Left-Thalamus", "Left-Thalamus-Proper")),
    ("Right-Thalamus", ("Right-Thalamus", "Right-Thalamus-Proper")),
    ("Left-Caudate", ("Left-Caudate",)),
    ("Right-Caudate", ("Right-Caudate",)),
    ("Left-Putamen", ("Left-Putamen",)),
    ("Right-Putamen", ("Right-Putamen",)),
    ("Left-Hippocampus", ("Left-Hippocampus",)),
    ("Right-Hippocampus", ("Right-Hippocampus",)),
)


@dataclass(frozen=True)
class AtlasSpec:
    key: str
    display_name: str
    expected_total: int
    kind: str
    stats_stem: str
    source_subject: Optional[str] = None
    annot_pattern: Optional[str] = None
    excluded_regions: tuple[str, ...] = ()
    annotations: tuple[str, ...] = ()
    regions: tuple[tuple[str, ...], ...] = ()

    def annotation_path(self, atlas_dir: Path, hemi: str) -> Path:
        if self.annotations:
            return Path(self.annotations[HEMISPHERES.index(hemi)])
        return atlas_dir / str(self.annot_pattern).format(hemi=hemi)

    def region_names(self, hemi: str) -> tuple[str, ...]:
        return self.regions[HEMISPHERES.index(hemi)] if self.regions else ()

    def expected_rows(self, hemi: str) -> int:
        if self.regions:
            return len(self.region_names(hemi))
        return EXPECTED_HEMISPHERE_ROWS[self.key][hemi]


ATLAS_SPECS = {
    "dk68": AtlasSpec("dk68", "Desikan-Killiany (aparc)", 68, "builtin", "aparc"),
    "destrieux": AtlasSpec(
        "destrieux", "Destrieux (aparc.a2009s)", 148, "builtin", "aparc.a2009s"
    ),
    "dk308": AtlasSpec(
        "dk308",
        "DK308 / NSPN500 (500.aparc)",
        308,
        "external",
        "dk308",
        "fsaverage",
        "{hemi}.500.aparc.annot",
        ("unknown_part1", "corpuscallosum_part1"),
    ),
    "schaefer100": AtlasSpec(
        "schaefer100",
        "Schaefer2018 100 parcels, Yeo 7-network order",
        100,
        "external",
        "schaefer100",
        "fsaverage5",
        "{hemi}.schaefer-100_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer200": AtlasSpec(
        "schaefer200",
        "Schaefer2018 200 parcels, Yeo 7-network order",
        200,
        "external",
        "schaefer200",
        "fsaverage5",
        "{hemi}.schaefer-200_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer300": AtlasSpec(
        "schaefer300",
        "Schaefer2018 300 parcels, Yeo 7-network order",
        300,
        "external",
        "schaefer300",
        "fsaverage5",
        "{hemi}.schaefer-300_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer400": AtlasSpec(
        "schaefer400",
        "Schaefer2018 400 parcels, Yeo 7-network order",
        400,
        "external",
        "schaefer400",
        "fsaverage5",
        "{hemi}.schaefer-400_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer500": AtlasSpec(
        "schaefer500", "Schaefer2018 500 parcels, Yeo 7-network order", 500,
        "external", "schaefer500", "fsaverage5", "{hemi}.schaefer-500_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer600": AtlasSpec(
        "schaefer600", "Schaefer2018 600 parcels, Yeo 7-network order", 600,
        "external", "schaefer600", "fsaverage5", "{hemi}.schaefer-600_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer700": AtlasSpec(
        "schaefer700", "Schaefer2018 700 parcels, Yeo 7-network order", 700,
        "external", "schaefer700", "fsaverage5", "{hemi}.schaefer-700_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer800": AtlasSpec(
        "schaefer800", "Schaefer2018 800 parcels, Yeo 7-network order", 800,
        "external", "schaefer800", "fsaverage5", "{hemi}.schaefer-800_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer900": AtlasSpec(
        "schaefer900", "Schaefer2018 900 parcels, Yeo 7-network order", 900,
        "external", "schaefer900", "fsaverage5", "{hemi}.schaefer-900_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "schaefer1000": AtlasSpec(
        "schaefer1000", "Schaefer2018 1000 parcels, Yeo 7-network order", 1000,
        "external", "schaefer1000", "fsaverage5", "{hemi}.schaefer-1000_mics.annot",
        ("Background+FreeSurfer_Defined_Medial_Wall",),
    ),
    "glasser360": AtlasSpec(
        "glasser360",
        "Glasser HCP-MMP1.0 multimodal 360-area parcellation",
        360,
        "external",
        "glasser360",
        "fsaverage5",
        "{hemi}.glasser-360_mics.annot",
        ("medialwall",),
    ),
    "economo": AtlasSpec(
        "economo",
        "MRI implementation of the von Economo-Koskinas atlas",
        86,
        "external",
        "economo",
        "fsaverage5",
        "{hemi}.economo_mics.annot",
        ("unknown", "corpuscallosum"),
    ),
    "vosdewael300": AtlasSpec(
        "vosdewael300",
        "Vos de Wael anatomical 300-parcel subparcellation of aparc",
        300,
        "external",
        "vosdewael300",
        "fsaverage5",
        "{hemi}.vosdewael-300_mics.annot",
        ("1",),
    ),
}
DEFAULT_ATLASES = ("dk68",)
EXPECTED_HEMISPHERE_ROWS = {
    "dk68": {"lh": 34, "rh": 34},
    "destrieux": {"lh": 74, "rh": 74},
    "dk308": {"lh": 152, "rh": 156},
    "schaefer100": {"lh": 50, "rh": 50},
    "schaefer200": {"lh": 100, "rh": 100},
    "schaefer300": {"lh": 150, "rh": 150},
    "schaefer400": {"lh": 200, "rh": 200},
    "schaefer500": {"lh": 250, "rh": 250},
    "schaefer600": {"lh": 300, "rh": 300},
    "schaefer700": {"lh": 350, "rh": 350},
    "schaefer800": {"lh": 400, "rh": 400},
    "schaefer900": {"lh": 450, "rh": 450},
    "schaefer1000": {"lh": 500, "rh": 500},
    "glasser360": {"lh": 180, "rh": 180},
    "economo": {"lh": 43, "rh": 43},
    "vosdewael300": {"lh": 150, "rh": 150},
}


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def atomic_copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, tmp_name)
        os.replace(tmp_name, destination)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def atomic_copy_file_no_replace(source: Path, destination: Path) -> None:
    """Atomically copy source without ever replacing an existing destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, tmp_name)
        os.link(tmp_name, destination)
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def write_tsv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n"
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in fields})
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def version_order(version: str) -> tuple[int, int, int, int, int]:
    """Return an ordering key for the supported SemVer final/RC spellings."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?", version)
    if match is None:
        raise ValueError(f"Unsupported tool version in cache metadata: {version}")
    major, minor, patch, rc = match.groups()
    return int(major), int(minor), int(patch), 0 if rc is None else -1, int(rc or 0)


def cache_tool_version_is_compatible(producer_version: str) -> bool:
    """Allow validated older/equal producers, but never trust a downgrade."""
    try:
        return version_order(producer_version) <= version_order(TOOL_VERSION)
    except ValueError:
        return False


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def lock_is_stale(lock_path: Path, metadata: dict[str, Any]) -> bool:
    if metadata.get("hostname") == socket.gethostname():
        try:
            return not process_is_running(int(metadata.get("pid", 0)))
        except (TypeError, ValueError):
            return True
    try:
        age_seconds = time.time() - lock_path.stat().st_mtime
    except OSError:
        return True
    return not metadata and age_seconds > 24 * 60 * 60


class RunResources:
    """Own the output lock and disposable FreeSurfer working links."""

    def __init__(self) -> None:
        self.output_dir: Optional[Path] = None
        self.lock_path: Optional[Path] = None
        self.work_dir: Optional[Path] = None
        self.lock_id = uuid.uuid4().hex

    def acquire(self, output_dir: Path, force_unlock: bool) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        lock_path = output_dir / ".fsharvest.lock"
        while True:
            try:
                fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                try:
                    metadata = json.loads(lock_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    metadata = {}
                if force_unlock and lock_is_stale(lock_path, metadata):
                    lock_path.unlink(missing_ok=True)
                    continue
                owner = json.dumps(metadata, ensure_ascii=False) if metadata else "unreadable lock"
                raise RuntimeError(
                    f"Output directory is locked: {lock_path} ({owner}). "
                    "Use --force-unlock only after verifying that the recorded process is no longer running."
                )
            else:
                self.output_dir = output_dir
                self.lock_path = lock_path
                metadata = {
                    "lock_id": self.lock_id,
                    "tool_version": TOOL_VERSION,
                    "hostname": socket.gethostname(),
                    "pid": os.getpid(),
                    "started_at_utc": datetime.now(timezone.utc).isoformat(),
                    "command": sys.argv,
                }
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(metadata, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                return

    def create_work_dir(self) -> Path:
        if self.output_dir is None or self.lock_path is None:
            raise RuntimeError("Output lock must be acquired before creating a work directory.")
        if self.work_dir is None:
            self.work_dir = Path(
                tempfile.mkdtemp(prefix=".fsharvest-work-", dir=self.output_dir)
            )
            atomic_write_text(
                self.work_dir / ".owner.json",
                json.dumps({"lock_id": self.lock_id}, indent=2) + "\n",
            )
        return self.work_dir

    def cleanup(self) -> None:
        try:
            if self.work_dir is not None and not self.work_dir.is_symlink():
                marker = self.work_dir / ".owner.json"
                try:
                    metadata = json.loads(marker.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    metadata = {}
                if metadata.get("lock_id") == self.lock_id and self.work_dir.is_dir():
                    shutil.rmtree(self.work_dir)
        finally:
            if self.lock_path is not None and self.lock_path.is_file():
                try:
                    metadata = json.loads(self.lock_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    metadata = {}
                if metadata.get("lock_id") == self.lock_id:
                    self.lock_path.unlink(missing_ok=True)


def region_set_sha256(regions: Iterable[str]) -> str:
    payload = "".join(f"{region}\n" for region in sorted(regions))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_region_schema(atlas_dir: Path, atlases: dict[str, AtlasSpec]) -> dict[str, str]:
    curated = {key: spec for key, spec in atlases.items() if spec.kind == "builtin" or spec.annot_pattern}
    if not curated:
        return {}
    path = atlas_dir / "region_schema.json"
    if not path.is_file():
        raise FileNotFoundError(f"Atlas region schema is required: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("atlases"), dict):
        raise RuntimeError(f"Unsupported atlas region schema: {path}")
    result: dict[str, str] = {}
    for atlas in curated:
        atlas_schema = document["atlases"].get(atlas)
        for hemi in HEMISPHERES:
            digest = atlas_schema.get(hemi) if isinstance(atlas_schema, dict) else None
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise RuntimeError(f"Missing region-set SHA-256 for {atlas}/{hemi} in {path}")
            result[f"{atlas}:{hemi}"] = digest
    return result


IntegrityCache = dict[Path, tuple[tuple[int, int, int], dict[str, Any]]]


def file_integrity(
    path: Path, cache: Optional[IntegrityCache] = None
) -> dict[str, Any]:
    stat = path.stat()
    signature = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    cache_key = path.resolve()
    if cache is not None:
        cached = cache.get(cache_key)
        if cached is not None and cached[0] == signature:
            return cached[1]
    integrity = {"size": stat.st_size, "sha256": sha256(path)}
    if cache is not None:
        cache[cache_key] = (signature, integrity)
    return integrity


def output_artifact_integrity(subject_out: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for name in ("cortical.tsv", "aseg.tsv", "global.tsv"):
        path = subject_out / name
        if path.is_file():
            result[name] = file_integrity(path)
    return result


def file_state(path: Path) -> dict[str, Any]:
    """Return a cache signature, hashing small scientific inputs by content."""
    if not path.is_file():
        return {"path": str(path), "missing": True}
    stat = path.stat()
    result = {
        "path": str(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "ctime_ns": stat.st_ctime_ns,
        "device": stat.st_dev,
        "inode": stat.st_ino,
    }
    if path.suffix in {".stats", ".annot", ".label", ".txt", ".done"}:
        result["sha256"] = sha256(path)
    return result


def managed_export_key(subject_dir: Path, path: Path) -> Optional[str]:
    try:
        return path.resolve().relative_to(subject_dir.resolve()).as_posix()
    except ValueError:
        return None


def validated_managed_exports(
    subject_dir: Path, value: Any
) -> dict[str, dict[str, Any]]:
    """Return FSHarvest export records whose destination still matches exactly."""
    if not isinstance(value, dict):
        return {}
    validated: dict[str, dict[str, Any]] = {}
    for relative, expected in value.items():
        if not isinstance(relative, str) or not isinstance(expected, dict):
            continue
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            continue
        destination = subject_dir / relative_path
        key = managed_export_key(subject_dir, destination)
        if key != relative or not destination.is_file():
            continue
        actual = file_integrity(destination)
        if actual == expected:
            validated[key] = actual
    return validated


def subject_external_artifact_candidates(
    subject_dir: Path,
    spec: AtlasSpec,
    hemi: str,
) -> list[tuple[Path, Path]]:
    original_name = str(spec.annot_pattern).format(hemi=hemi)
    normalized_name = f"{hemi}.{spec.stats_stem}.annot"
    names = list(dict.fromkeys((original_name, normalized_name)))
    pairs = [
        (subject_dir / "label" / name, subject_dir / "stats" / f"{name[:-len('.annot')]}.stats")
        for name in names
    ]
    if len(pairs) == 2:
        pairs.extend(((pairs[0][0], pairs[1][1]), (pairs[1][0], pairs[0][1])))
    return pairs


def reusable_subject_artifacts(
    subject_dir: Path,
    spec: AtlasSpec,
    atlas: str,
    hemi: str,
    expected_region_sha256: Optional[str] = None,
    managed_exports: Optional[dict[str, dict[str, Any]]] = None,
) -> tuple[Optional[Path], Optional[Path]]:
    try:
        surface_vertex_count = read_surface_vertex_count(subject_dir / "surf" / f"{hemi}.white")
    except (OSError, RuntimeError):
        return None, None
    seen: set[Path] = set()
    for annotation, _stats in subject_external_artifact_candidates(subject_dir, spec, hemi):
        if annotation in seen:
            continue
        seen.add(annotation)
        if not annotation.is_file():
            continue
        if managed_export_key(subject_dir, annotation) in (managed_exports or {}):
            continue
        if not validate_annotation_file(
            annotation,
            spec,
            atlas,
            hemi,
            expected_region_sha256,
            surface_vertex_count,
        ):
            # Subject-level stats are deliberately never reused: without an
            # FSHarvest sidecar they cannot prove subject/command provenance.
            return annotation, None
    return None, None


def output_annotation_path(subject_out: Path, spec: AtlasSpec, hemi: str) -> Path:
    return subject_out / "label" / f"{hemi}.{spec.stats_stem}.annot"


def external_artifact_integrity(
    subject_out: Path, spec: AtlasSpec, hemi: str
) -> dict[str, dict[str, Any]]:
    paths = {
        "annotation": output_annotation_path(subject_out, spec, hemi),
        "stats": subject_out / "stats" / f"{hemi}.{spec.stats_stem}.stats",
    }
    return {name: file_integrity(path) for name, path in paths.items() if path.is_file()}


def annotation_contents(path: Path, *, used_only: bool = False) -> tuple[int, list[str]]:
    """Read and structurally validate a FreeSurfer annotation without optional dependencies."""
    data = path.read_bytes()
    offset = 0

    def read_int() -> int:
        nonlocal offset
        if offset + 4 > len(data):
            raise RuntimeError("annotation is truncated")
        value = struct.unpack_from(">i", data, offset)[0]
        offset += 4
        return value

    def read_bytes(length: int) -> bytes:
        nonlocal offset
        if length < 0 or offset + length > len(data):
            raise RuntimeError("annotation contains an invalid string length")
        value = data[offset : offset + length]
        offset += length
        return value

    def read_string() -> str:
        raw = read_bytes(read_int())
        if raw.endswith(b"\0"):
            raw = raw[:-1]
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("annotation contains a non-UTF-8 region name") from exc

    if not data:
        raise RuntimeError("annotation is empty")
    vertex_count = read_int()
    if vertex_count <= 0 or vertex_count > (len(data) - offset) // 8:
        raise RuntimeError(f"annotation has an invalid vertex count: {vertex_count}")
    vertex_ids: set[int] = set()
    annotation_values: set[int] = set()
    for _ in range(vertex_count):
        vertex_ids.add(read_int())
        annotation_values.add(read_int())
    if vertex_ids != set(range(vertex_count)):
        raise RuntimeError("annotation vertex indices are incomplete or duplicated")
    if read_int() == 0:
        raise RuntimeError("annotation does not contain a color table")

    entry_marker = read_int()
    names: list[str] = []
    color_values: list[int] = []
    if entry_marker > 0:
        read_string()  # original color-table path
        entries = entry_marker
        for _ in range(entries):
            names.append(read_string())
            red, green, blue, _alpha = (read_int() for _ in range(4))
            if any(channel < 0 or channel > 255 for channel in (red, green, blue)):
                raise RuntimeError("annotation contains an invalid color-table value")
            color_values.append(red + (green << 8) + (blue << 16))
    elif entry_marker == -2:
        max_index = read_int()
        if max_index <= 0:
            raise RuntimeError("annotation contains an invalid color-table size")
        read_string()  # original color-table path
        entries = read_int()
        if entries < 0 or entries > max_index:
            raise RuntimeError("annotation contains an invalid color-table entry count")
        indices: set[int] = set()
        for _ in range(entries):
            index = read_int()
            if index < 0 or index >= max_index or index in indices:
                raise RuntimeError("annotation contains an invalid color-table index")
            indices.add(index)
            names.append(read_string())
            red, green, blue, _alpha = (read_int() for _ in range(4))
            if any(channel < 0 or channel > 255 for channel in (red, green, blue)):
                raise RuntimeError("annotation contains an invalid color-table value")
            color_values.append(red + (green << 8) + (blue << 16))
    else:
        raise RuntimeError(f"unsupported annotation color-table version: {-entry_marker}")

    if any(data[offset:]):
        raise RuntimeError("annotation contains unexpected trailing data")
    unknown_values = annotation_values - set(color_values) - {0}
    if unknown_values:
        raise RuntimeError("annotation contains labels missing from its color table")
    if not names or any(not name for name in names):
        raise RuntimeError("annotation contains an empty color table")
    if used_only:
        names = [name for name, color in zip(names, color_values) if color in annotation_values]
    return vertex_count, names


def annotation_region_names(path: Path) -> list[str]:
    return annotation_contents(path)[1]


def read_surface_vertex_count(path: Path) -> int:
    """Read the vertex count from a triangular FreeSurfer surface file."""
    with path.open("rb") as handle:
        magic = int.from_bytes(handle.read(3), "big")
        if magic != 16777214:
            raise RuntimeError(f"unsupported FreeSurfer surface format: {path}")
        handle.readline()
        handle.readline()
        raw = handle.read(4)
    if len(raw) != 4:
        raise RuntimeError(f"truncated FreeSurfer surface: {path}")
    count = struct.unpack(">i", raw)[0]
    if count <= 0:
        raise RuntimeError(f"invalid surface vertex count: {path}")
    return count


def validate_annotation_file(
    path: Path,
    spec: AtlasSpec,
    atlas: str,
    hemi: str,
    expected_region_sha256: Optional[str],
    expected_vertex_count: Optional[int] = None,
) -> list[str]:
    if not path.is_file():
        return [f"{atlas}/{hemi}: missing annotation: {path}"]
    if path.stat().st_size == 0:
        return [f"{atlas}/{hemi}: annotation is empty: {path}"]
    if expected_region_sha256 is None and expected_vertex_count is None and not spec.regions:
        return []
    try:
        vertex_count, names = annotation_contents(path, used_only=not bool(spec.annot_pattern))
    except (OSError, RuntimeError) as exc:
        return [f"{atlas}/{hemi}: invalid annotation {path}: {exc}"]
    if expected_vertex_count is not None and vertex_count != expected_vertex_count:
        return [
            f"{atlas}/{hemi}: annotation has {vertex_count} vertices; "
            f"surface has {expected_vertex_count}"
        ]
    regions = [name for name in names if name not in spec.excluded_regions]
    if spec.regions and set(regions) != set(spec.region_names(hemi)):
        return [f"{atlas}/{hemi}: annotation regions do not match the atlas definition"]
    if expected_region_sha256 and region_set_sha256(regions) != expected_region_sha256:
        return [f"{atlas}/{hemi}: annotation regions do not match the pinned atlas schema"]
    return []


def validate_external_artifacts(
    subject_out: Path,
    atlases: dict[str, AtlasSpec],
    atlas_region_hashes: Optional[dict[str, str]] = None,
) -> list[str]:
    atlas_region_hashes = atlas_region_hashes or {}
    errors: list[str] = []
    for atlas in atlases:
        spec = atlases[atlas]
        if spec.kind != "external":
            continue
        for hemi in HEMISPHERES:
            annotation = output_annotation_path(subject_out, spec, hemi)
            stats = subject_out / "stats" / f"{hemi}.{spec.stats_stem}.stats"
            errors.extend(
                validate_annotation_file(
                    annotation,
                    spec,
                    atlas,
                    hemi,
                    atlas_region_hashes.get(f"{atlas}:{hemi}"),
                )
            )
            if not stats.is_file():
                errors.append(f"{atlas}/{hemi}: missing external stats: {stats}")
                continue
            artifact_status = subject_out / "stats" / f"{hemi}.{spec.stats_stem}.artifact.json"
            try:
                artifact = json.loads(artifact_status.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{atlas}/{hemi}: invalid or missing artifact metadata: {exc}")
                continue
            actual_integrity = external_artifact_integrity(subject_out, spec, hemi)
            if artifact.get("output_artifacts") != actual_integrity:
                errors.append(f"{atlas}/{hemi}: external artifact checksums do not match metadata")
            annotation_header = header_value(stats, "AnnotationFile")
            if not annotation_header or Path(annotation_header).name != annotation.name:
                errors.append(f"{atlas}/{hemi}: stats annotation does not match cached annotation")
            rows = [
                row
                for row in parse_cortical_stats(stats, atlas, hemi)
                if row["region"] not in spec.excluded_regions
            ]
            errors.extend(
                validate_cortical_rows(
                    rows,
                    spec,
                    hemi,
                    atlas_region_hashes.get(f"{atlas}:{hemi}"),
                )
            )
    return errors


def files_identical(left: Path, right: Path) -> bool:
    if not left.is_file() or not right.is_file():
        return False
    if left.stat().st_size != right.stat().st_size:
        return False
    return sha256(left) == sha256(right)


def managed_exports_from_status(
    subject_dir: Path, subject_out: Path, status: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    managed: dict[str, dict[str, Any]] = {}
    recorded = status.get("managed_exports")
    if isinstance(recorded, dict):
        for relative, expected in recorded.items():
            if not isinstance(relative, str) or not isinstance(expected, dict):
                continue
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                continue
            destination = subject_dir / relative_path
            key = managed_export_key(subject_dir, destination)
            cached_source = subject_out / relative_path
            if (
                key == relative
                and cached_source.is_file()
                and file_integrity(cached_source) == expected
            ):
                # Preserve ownership even if the destination was deleted or edited.
                # It remains excluded from scientific inputs; export validation will
                # recreate a missing copy or reject a conflicting one.
                managed[key] = expected
    return managed


def export_subject_artifacts(
    subject_dir: Path,
    subject_out: Path,
    atlases: dict[str, AtlasSpec],
    atlas_region_hashes: Optional[dict[str, str]] = None,
    managed_exports: Optional[dict[str, dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Export validated external atlas annotations/stats into a FreeSurfer subject.

    All destinations are checked before any file is created. Existing identical
    files are accepted; conflicting files are never replaced.
    """
    validation_errors = validate_external_artifacts(
        subject_out, atlases, atlas_region_hashes
    )
    if validation_errors:
        raise RuntimeError("; ".join(validation_errors))

    plans: list[tuple[Path, Path]] = []
    for atlas in atlases:
        spec = atlases[atlas]
        if spec.kind != "external":
            continue
        for hemi in HEMISPHERES:
            annotation = output_annotation_path(subject_out, spec, hemi)
            stats = subject_out / "stats" / f"{hemi}.{spec.stats_stem}.stats"
            if not annotation.is_file() or not stats.is_file():
                raise FileNotFoundError(
                    f"Missing validated output artifacts for {atlas}/{hemi}: "
                    f"{annotation}, {stats}"
                )
            plans.extend(
                (
                    (annotation, subject_dir / "label" / annotation.name),
                    (stats, subject_dir / "stats" / stats.name),
                )
            )

    conflicts = [
        str(destination)
        for source, destination in plans
        if destination.exists() and not files_identical(source, destination)
    ]
    if conflicts:
        raise FileExistsError(
            "Refusing to replace existing FreeSurfer artifacts: " + ", ".join(conflicts)
        )

    current_managed = validated_managed_exports(subject_dir, managed_exports)
    exported_paths: list[str] = []
    existing_paths: list[str] = []
    for source, destination in plans:
        if destination.exists():
            existing_paths.append(str(destination))
            continue
        try:
            atomic_copy_file_no_replace(source, destination)
            exported_paths.append(str(destination))
            key = managed_export_key(subject_dir, destination)
            if key is not None:
                current_managed[key] = file_integrity(destination)
        except FileExistsError:
            if files_identical(source, destination):
                existing_paths.append(str(destination))
                continue
            raise FileExistsError(f"Export destination appeared concurrently: {destination}")

    return {
        "export_status": "OK",
        "exported_files": len(exported_paths),
        "existing_export_files": len(existing_paths),
        "exported_paths": exported_paths,
        "existing_export_paths": existing_paths,
        "export_errors": "",
        "managed_exports": current_managed,
    }


def subject_input_fingerprint(
    subject_dir: Path,
    atlases: dict[str, AtlasSpec],
    managed_exports: Optional[dict[str, dict[str, Any]]] = None,
) -> str:
    paths = {
        subject_dir / "stats" / "aseg.stats",
        subject_dir / "scripts" / "build-stamp.txt",
        subject_dir / "scripts" / "recon-all.done",
    }
    for key in atlases:
        spec = atlases[key]
        if spec.kind == "builtin":
            paths.update(subject_dir / "stats" / f"{hemi}.{spec.stats_stem}.stats" for hemi in HEMISPHERES)
        else:
            for hemi in HEMISPHERES:
                paths.update(
                    {
                        subject_dir / "label" / f"{hemi}.cortex.label",
                        subject_dir / "surf" / f"{hemi}.sphere.reg",
                        subject_dir / "surf" / f"{hemi}.white",
                        subject_dir / "surf" / f"{hemi}.pial",
                        subject_dir / "surf" / f"{hemi}.thickness",
                    }
                )
                if spec.annot_pattern:
                    for annotation, _stats in subject_external_artifact_candidates(subject_dir, spec, hemi):
                        paths.add(annotation)
    states = []
    for path in sorted(paths):
        if managed_export_key(subject_dir, path) in (managed_exports or {}):
            states.append({"path": str(path), "missing": True})
        else:
            states.append(file_state(path))
    return json_fingerprint(states)


def external_surface_fingerprint(subject_dir: Path, hemi: str) -> str:
    paths = (
        subject_dir / "label" / f"{hemi}.cortex.label",
        subject_dir / "surf" / f"{hemi}.sphere.reg",
        subject_dir / "surf" / f"{hemi}.white",
        subject_dir / "surf" / f"{hemi}.pial",
        subject_dir / "surf" / f"{hemi}.thickness",
    )
    return json_fingerprint([file_state(path) for path in paths])


def template_input_fingerprint(fs_home: Path, atlases: dict[str, AtlasSpec]) -> str:
    source_subjects = {atlases[key].source_subject for key in atlases} - {None}
    paths = []
    for source_subject in sorted(str(source) for source in source_subjects):
        for hemi in HEMISPHERES:
            paths.append(fs_home / "subjects" / source_subject / "surf" / f"{hemi}.sphere.reg")
    return json_fingerprint([file_state(path) for path in paths])


def parse_number(value: str) -> int | float | str:
    value = value.strip()
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


def parse_measure_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.startswith("# Measure "):
                continue
            values = next(csv.reader([line[len("# Measure ") :].strip()]))
            values = [value.strip() for value in values]
            if len(values) < 5:
                continue
            rows.append(
                {
                    "measure": values[0],
                    "metric": values[1],
                    "description": ",".join(values[2:-2]).strip(),
                    "value": parse_number(values[-2]),
                    "unit": values[-1],
                }
            )
    return rows


def header_value(path: Path, key: str) -> Optional[str]:
    prefix = f"# {key} "
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
    return None


def parse_cortical_stats(path: Path, atlas: str, hemi: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            values = line.strip().rsplit(None, len(CORTICAL_COLUMNS))
            if len(values) < 10:
                continue
            rows.append(
                {
                    "atlas": atlas,
                    "hemisphere": hemi,
                    "region": values[0],
                    "numvert": parse_number(values[1]),
                    "surfarea": parse_number(values[2]),
                    "grayvol": parse_number(values[3]),
                    "thickavg": parse_number(values[4]),
                    "thickstd": parse_number(values[5]),
                    "meancurv": parse_number(values[6]),
                    "gauscurv": parse_number(values[7]),
                    "foldind": parse_number(values[8]),
                    "curvind": parse_number(values[9]),
                }
            )
    return rows


def parse_aseg_stats(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            values = line.split()
            if len(values) < 10 or not values[0].isdigit():
                continue
            rows.append(dict(zip(ASEG_COLUMNS, [parse_number(value) for value in values[:10]])))
    return rows


def parse_aseg_header(path: Path) -> dict[str, Any]:
    header: dict[str, Any] = {}
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("# NRows "):
                header["nrows"] = parse_number(line[len("# NRows ") :])
            elif line.startswith("# NTableCols "):
                header["ntablecols"] = parse_number(line[len("# NTableCols ") :])
            elif line.startswith("# ColHeaders "):
                header["colheaders"] = tuple(line[len("# ColHeaders ") :].split())
    return header


def is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_nonnegative_integer(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and value >= 0 and float(value).is_integer()


def validate_cortical_rows(
    rows: list[dict[str, Any]],
    spec: AtlasSpec,
    hemi: str,
    expected_region_sha256: Optional[str] = None,
) -> list[str]:
    errors = []
    atlas = spec.key
    expected = spec.expected_rows(hemi)
    if len(rows) != expected:
        errors.append(f"{atlas}/{hemi}: expected {expected} cortical rows, observed {len(rows)}")
    regions = [str(row["region"]) for row in rows]
    duplicates = sorted(name for name, count in Counter(regions).items() if count > 1)
    if duplicates:
        errors.append(f"{atlas}/{hemi}: duplicate regions: {', '.join(duplicates)}")
    if expected_region_sha256 and region_set_sha256(regions) != expected_region_sha256:
        errors.append(f"{atlas}/{hemi}: region names do not match the pinned atlas schema")
    if spec.regions and set(regions) != set(spec.region_names(hemi)):
        expected_names = set(spec.region_names(hemi))
        errors.append(
            f"{atlas}/{hemi}: region names do not match the atlas definition; "
            f"{len(expected_names - set(regions))} missing, "
            f"{len(set(regions) - expected_names)} unexpected (see region_differences.tsv)"
        )
    invalid = [
        str(row["region"])
        for row in rows
        if any(not is_finite_number(row[column]) for column in CORTICAL_COLUMNS)
    ]
    if invalid:
        errors.append(f"{atlas}/{hemi}: non-numeric or non-finite values in: {', '.join(invalid)}")
    invalid_numvert = [str(row["region"]) for row in rows if not is_nonnegative_integer(row["numvert"])]
    if invalid_numvert:
        errors.append(f"{atlas}/{hemi}: NumVert must be a non-negative integer in: {', '.join(invalid_numvert)}")
    return errors


def validate_aseg_rows(
    aseg_rows: list[dict[str, Any]],
    global_rows: list[dict[str, Any]],
    header: Optional[dict[str, Any]] = None,
) -> list[str]:
    errors = []
    if header is not None:
        if header.get("nrows") != len(aseg_rows):
            errors.append(
                "aseg.stats NRows does not match structure rows: "
                f"declared {header.get('nrows', 'missing')}, observed {len(aseg_rows)}"
            )
        if header.get("ntablecols") != len(ASEG_COL_HEADERS):
            errors.append(
                "aseg.stats NTableCols is missing or unsupported: "
                f"expected {len(ASEG_COL_HEADERS)}, observed {header.get('ntablecols', 'missing')}"
            )
        if header.get("colheaders") != ASEG_COL_HEADERS:
            observed = " ".join(str(value) for value in header.get("colheaders", ())) or "missing"
            errors.append(
                "aseg.stats ColHeaders are missing or unsupported: "
                f"expected {' '.join(ASEG_COL_HEADERS)}, observed {observed}"
            )
    if not aseg_rows:
        errors.append("aseg.stats contains no structure rows")
    else:
        if len(aseg_rows) < MIN_ASEG_ROWS:
            errors.append(
                f"aseg.stats appears incomplete: expected at least {MIN_ASEG_ROWS} structure rows, "
                f"observed {len(aseg_rows)}"
            )
        invalid = [
            str(row.get("structure", "<unknown>"))
            for row in aseg_rows
            if any(
                not is_finite_number(row[column])
                for column in ASEG_COLUMNS
                if column != "structure"
            )
            or not str(row.get("structure", "")).strip()
        ]
        if invalid:
            errors.append("aseg.stats has invalid structure rows: " + ", ".join(invalid))
        keys = [(row["segid"], row["structure"]) for row in aseg_rows]
        duplicates = sorted(str(key) for key, count in Counter(keys).items() if count > 1)
        if duplicates:
            errors.append("aseg.stats has duplicate structure keys: " + ", ".join(duplicates))
        invalid_integers = [
            str(row.get("structure", "<unknown>"))
            for row in aseg_rows
            if any(not is_nonnegative_integer(row[column]) for column in ("index", "segid", "nvoxels"))
        ]
        if invalid_integers:
            errors.append(
                "aseg.stats has non-integer or negative Index/SegId/NVoxels values in: "
                + ", ".join(invalid_integers)
            )
        structures = {str(row["structure"]) for row in aseg_rows}
        missing_structures = [
            label
            for label, alternatives in REQUIRED_ASEG_STRUCTURE_GROUPS
            if not any(name in structures for name in alternatives)
        ]
        if missing_structures:
            errors.append("aseg.stats is missing required structures: " + ", ".join(missing_structures))

    if not global_rows:
        errors.append("aseg.stats contains no global # Measure rows")
        return errors
    invalid_measures = [
        str(row.get("metric", "<unknown>"))
        for row in global_rows
        if not is_finite_number(row.get("value"))
    ]
    if invalid_measures:
        errors.append("aseg.stats has non-numeric global measures: " + ", ".join(invalid_measures))
    measure_keys = [str(row.get("measure", "")) for row in global_rows]
    metric_keys = [str(row.get("metric", "")) for row in global_rows]
    duplicate_measures = sorted(key for key, count in Counter(measure_keys).items() if key and count > 1)
    duplicate_metrics = sorted(key for key, count in Counter(metric_keys).items() if key and count > 1)
    if duplicate_measures:
        errors.append("aseg.stats has duplicate measure names: " + ", ".join(duplicate_measures))
    if duplicate_metrics:
        errors.append("aseg.stats has duplicate metric names: " + ", ".join(duplicate_metrics))
    values = {str(row["measure"]): row["value"] for row in global_rows}
    values.update({str(row["metric"]): row["value"] for row in global_rows})
    required_groups = (
        ("eTIV", ("EstimatedTotalIntraCranialVol", "eTIV")),
        ("lhSurfaceHoles", ("lhSurfaceHoles",)),
        ("rhSurfaceHoles", ("rhSurfaceHoles",)),
    )
    missing = [label for label, alternatives in required_groups if not any(key in values for key in alternatives)]
    if missing:
        errors.append("aseg.stats is missing required global measures: " + ", ".join(missing))
    for key in ("lhSurfaceHoles", "rhSurfaceHoles"):
        if key in values and not is_nonnegative_integer(values[key]):
            errors.append(f"aseg.stats measure {key} must be a non-negative integer")
    return errors


def read_required_tsv(path: Path, required_fields: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = [field for field in required_fields if field not in (reader.fieldnames or [])]
        if missing:
            raise RuntimeError(f"{path} is missing columns: {', '.join(missing)}")
        return list(reader)


def validate_subject_output_tables(
    subject_out: Path,
    atlases: dict[str, AtlasSpec],
    atlas_region_hashes: Optional[dict[str, str]] = None,
) -> list[str]:
    """Validate cached/serialized subject tables before they are trusted."""
    atlas_region_hashes = atlas_region_hashes or {}
    metadata_fields = ["subject_id", "folder_id", "subject_path", "fs_version"]
    cortical_fields = metadata_fields + ["atlas", "hemisphere", "region"] + list(CORTICAL_COLUMNS)
    aseg_fields = metadata_fields + list(ASEG_COLUMNS)
    global_fields = metadata_fields + ["measure", "metric", "description", "value", "unit"]
    paths = {
        "cortical": subject_out / "cortical.tsv",
        "aseg": subject_out / "aseg.tsv",
        "global": subject_out / "global.tsv",
    }
    missing_files = [str(path) for path in paths.values() if not path.is_file()]
    if missing_files:
        return ["Missing subject output tables: " + ", ".join(missing_files)]

    try:
        cortical_raw = read_required_tsv(paths["cortical"], cortical_fields)
        aseg_raw = read_required_tsv(paths["aseg"], aseg_fields)
        global_raw = read_required_tsv(paths["global"], global_fields)
    except (OSError, csv.Error, RuntimeError) as exc:
        return [str(exc)]

    errors: list[str] = []
    for label, rows in (("cortical", cortical_raw), ("aseg", aseg_raw), ("global", global_raw)):
        unexpected_folders = sorted({row.get("folder_id", "") for row in rows} - {subject_out.name})
        if unexpected_folders:
            errors.append(
                f"{label}.tsv contains unexpected folder_id values: {', '.join(unexpected_folders)}"
            )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in cortical_raw:
        atlas = row["atlas"]
        hemi = row["hemisphere"]
        if atlas not in atlases or hemi not in HEMISPHERES:
            errors.append(f"cortical.tsv contains unexpected atlas/hemisphere: {atlas}/{hemi}")
            continue
        typed = {**row, **{column: parse_number(row[column]) for column in CORTICAL_COLUMNS}}
        grouped.setdefault((atlas, hemi), []).append(typed)
    for atlas in atlases:
        for hemi in HEMISPHERES:
            errors.extend(
                validate_cortical_rows(
                    grouped.get((atlas, hemi), []),
                    atlases[atlas],
                    hemi,
                    atlas_region_hashes.get(f"{atlas}:{hemi}"),
                )
            )

    typed_aseg = [
        {**row, **{column: parse_number(row[column]) for column in ASEG_COLUMNS if column != "structure"}}
        for row in aseg_raw
    ]
    typed_globals = [{**row, "value": parse_number(row["value"])} for row in global_raw]
    errors.extend(validate_aseg_rows(typed_aseg, typed_globals))
    return errors


def validate_cached_subject_outputs(
    subject_out: Path,
    previous: dict[str, Any],
    atlases: dict[str, AtlasSpec],
    atlas_region_hashes: Optional[dict[str, str]] = None,
) -> list[str]:
    errors = validate_subject_output_tables(subject_out, atlases, atlas_region_hashes)
    errors.extend(validate_external_artifacts(subject_out, atlases, atlas_region_hashes))
    expected_integrity = previous.get("output_artifacts")
    if expected_integrity is not None and expected_integrity != output_artifact_integrity(subject_out):
        errors.append("Cached subject output checksums do not match status.json")
    return errors


def discover_subjects(root: Path, recursive: bool) -> list[Path]:
    root = root.resolve()
    candidates = root.rglob("*") if recursive else root.iterdir()
    found = []
    for path in candidates:
        if not path.is_dir() or path.name in BLACKLIST or path.name.startswith("."):
            continue
        signatures = (
            path / "stats" / "aseg.stats",
            path / "surf" / "lh.white",
            path / "scripts" / "recon-all.log",
        )
        if any(item.is_file() for item in signatures):
            found.append(path.resolve())
    unique = {str(path): path for path in found}
    return sorted(unique.values(), key=lambda item: (item.name, str(item)))


def infer_fs_version(subject_dir: Path) -> tuple[str, str]:
    build_stamp = subject_dir / "scripts" / "build-stamp.txt"
    raw = build_stamp.read_text(encoding="utf-8", errors="replace").strip() if build_stamp.is_file() else ""
    if not raw:
        log_path = subject_dir / "scripts" / "recon-all.log"
        if log_path.is_file():
            text = log_path.read_text(encoding="utf-8", errors="replace")[:20000]
            match = re.search(r"freesurfer[^\n]*?([0-9]+\.[0-9]+(?:\.[0-9]+)?)", text, re.I)
            raw = match.group(0).strip() if match else ""
    match = re.search(r"(?<!\d)([0-9]+\.[0-9]+(?:\.[0-9]+)?)(?!\d)", raw)
    return (match.group(1) if match else "unknown", raw or "unknown")


def validate_atlas_files(atlas_dir: Path, atlases: dict[str, AtlasSpec]) -> dict[str, str]:
    checksums = {}
    curated_checksums = {}
    missing = []
    for key in atlases:
        spec = atlases[key]
        if spec.kind != "external":
            continue
        for hemi in HEMISPHERES:
            path = spec.annotation_path(atlas_dir, hemi)
            if not path.is_file():
                missing.append(str(path))
            else:
                checksums[f"{key}:{hemi}"] = sha256(path)
                if spec.annot_pattern:
                    curated_checksums[path.name] = checksums[f"{key}:{hemi}"]
    if missing:
        raise FileNotFoundError("Missing atlas files:\n" + "\n".join(missing))

    manifest_path = atlas_dir / "manifest.json"
    if curated_checksums and not manifest_path.is_file():
        raise FileNotFoundError(f"Atlas manifest is required: {manifest_path}")
    if curated_checksums:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {item["file"]: item["sha256"] for item in manifest.get("files", [])}
        mismatches = [name for name, digest in curated_checksums.items() if expected.get(name) != digest]
        if mismatches:
            raise RuntimeError("Atlas checksum mismatch: " + ", ".join(mismatches))
    return checksums


def resolve_atlases(inputs: Iterable[str], atlas_dir: Path, fs_home: Path) -> dict[str, AtlasSpec]:
    """Resolve curated names and JSON definitions before processing any subjects."""
    atlases = {}
    for value in inputs:
        if value in ATLAS_SPECS:
            spec = ATLAS_SPECS[value]
        else:
            definition_path = Path(value).resolve()
            document = json.loads(definition_path.read_text(encoding="utf-8"))
            key = document["key"]
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", key):
                raise ValueError("Atlas key must start with a letter or digit and contain only letters, digits, _ or -")
            if key in ATLAS_SPECS:
                raise ValueError(f"Custom atlas key is reserved for a curated atlas: {key}")
            source = document["source_subject"]
            if source not in {"fsaverage", "fsaverage5"}:
                raise ValueError(f"{key}: source_subject must be fsaverage or fsaverage5")
            annotations = tuple(
                str((definition_path.parent / document["annotations"][hemi]).resolve())
                for hemi in HEMISPHERES
            )
            excluded = document.get("excluded_regions", [])
            if not isinstance(excluded, list) or not all(isinstance(name, str) for name in excluded):
                raise ValueError(f"{key}: excluded_regions must be a list of region names")
            spec = AtlasSpec(
                key, document.get("display_name", key), 0, "external", key,
                source, excluded_regions=tuple(dict.fromkeys((*STATS_EXCLUDED_REGIONS, *excluded))),
                annotations=annotations,
            )
        if spec.key in atlases:
            raise ValueError(f"Duplicate atlas key: {spec.key}")
        if spec.kind == "builtin":
            schema = json.loads((atlas_dir / "region_schema.json").read_text(encoding="utf-8"))
            entry = schema["atlases"][spec.key]
            names = entry.get("region_names")
            if names is not None:
                if (
                    not isinstance(names, list) or not all(isinstance(name, str) for name in names)
                    or len(set(names)) != spec.expected_total // 2
                    or any(region_set_sha256(names) != entry[hemi] for hemi in HEMISPHERES)
                ):
                    raise ValueError(f"{spec.key}: region names do not match the pinned schema")
                spec = replace(spec, regions=(tuple(names), tuple(names)))
        if spec.kind == "external":
            annotations = tuple(str(spec.annotation_path(atlas_dir, hemi).resolve()) for hemi in HEMISPHERES)
            regions = []
            for hemi, annotation in zip(HEMISPHERES, annotations):
                vertex_count, names = annotation_contents(
                    Path(annotation), used_only=not bool(spec.annot_pattern)
                )
                surface = fs_home / "subjects" / str(spec.source_subject) / "surf" / f"{hemi}.white"
                template_vertices = read_surface_vertex_count(surface)
                if vertex_count != template_vertices:
                    raise ValueError(
                        f"{spec.key}/{hemi}: annotation has {vertex_count} vertices; "
                        f"{spec.source_subject} surface has {template_vertices}"
                    )
                selected = tuple(name for name in names if name not in spec.excluded_regions)
                if not selected or len(set(selected)) != len(selected):
                    raise ValueError(f"{spec.key}/{hemi}: expected nonempty, unique region names after exclusions")
                if spec.annot_pattern and len(selected) != spec.expected_rows(hemi):
                    raise ValueError(f"{spec.key}/{hemi}: region count does not match the curated atlas")
                regions.append(selected)
            spec = replace(
                spec, annotations=annotations, regions=tuple(regions),
                expected_total=sum(map(len, regions)),
            )
        atlases[spec.key] = spec
    return atlases


def ensure_link(path: Path, target: Path) -> None:
    if path.is_symlink():
        if path.resolve() == target.resolve():
            return
        path.unlink()
    elif path.exists():
        raise RuntimeError(f"Working path exists and is not the expected symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target, target_is_directory=True)


def command_version() -> str:
    result = subprocess.run(
        ["recon-all", "-version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else "unknown"


def tool_source_checksums() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    result = {}
    for name in ("fs_extract_all.py", "fs_render_qc.py", "VERSION"):
        path = root / name
        if path.is_file():
            result[name] = sha256(path)
    return result


def run_command(command: list[str], env: dict[str, str], log_handle: Any) -> None:
    log_handle.write("$ " + " ".join(command) + "\n")
    log_handle.flush()
    result = subprocess.run(command, env=env, text=True, stdout=log_handle, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")


def subject_metadata(subject_dir: Path) -> dict[str, Any]:
    aseg = subject_dir / "stats" / "aseg.stats"
    subject_id = header_value(aseg, "subjectname") if aseg.is_file() else None
    fs_version, build_stamp = infer_fs_version(subject_dir)
    return {
        "subject_id": subject_id or subject_dir.name,
        "folder_id": subject_dir.name,
        "subject_path": str(subject_dir),
        "fs_version": fs_version,
        "fs_build_stamp": build_stamp,
        "recon_all_done": int((subject_dir / "scripts" / "recon-all.done").is_file()),
    }


def append_metadata(rows: list[dict[str, Any]], metadata: dict[str, Any]) -> list[dict[str, Any]]:
    return [{**metadata, **row} for row in rows]


def extract_subject(
    subject_dir: Path,
    output_dir: Path,
    atlas_dir: Path,
    atlases: dict[str, AtlasSpec],
    atlas_fingerprint: str,
    atlas_checksums: dict[str, str],
    fs_home: Path,
    runtime_version: str,
    template_fingerprint: str,
    overwrite: bool,
    atlas_region_hashes: Optional[dict[str, str]] = None,
    run_id: str = "",
    work_subjects: Optional[Path] = None,
) -> dict[str, Any]:
    start = time.time()
    atlas_region_hashes = atlas_region_hashes or {}
    metadata = subject_metadata(subject_dir)
    folder_id = metadata["folder_id"]
    subject_out = output_dir / "per_subject" / folder_id
    status_path = subject_out / "status.json"
    try:
        previous_status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous_status = {}
    managed_exports = managed_exports_from_status(
        subject_dir, subject_out, previous_status
    )
    input_fingerprint = subject_input_fingerprint(
        subject_dir, atlases, managed_exports
    )
    fingerprint_payload = {
        "atlas_fingerprint": atlas_fingerprint,
        "atlases": {key: asdict(spec) for key, spec in atlases.items()},
        "subject_dir": str(subject_dir),
        "subject_input_fingerprint": input_fingerprint,
        "runtime_version": runtime_version,
        "freesurfer_home": str(fs_home),
        "template_fingerprint": template_fingerprint,
    }
    fingerprint = json_fingerprint(
        {"cache_schema_version": CACHE_SCHEMA_VERSION, **fingerprint_payload}
    )

    cache_validation_errors: list[str] = []
    if status_path.is_file() and not overwrite:
        previous = previous_status
        if (
            previous.get("status") == "OK"
            and previous.get("fingerprint") == fingerprint
            and previous.get("cache_schema_version") == CACHE_SCHEMA_VERSION
            and cache_tool_version_is_compatible(
                str(previous.get("cache_produced_by_tool_version", ""))
            )
        ):
            cache_validation_errors = validate_cached_subject_outputs(
                subject_out, previous, atlases, atlas_region_hashes
            )
            if not cache_validation_errors:
                for key in (
                    "qc_status", "qc_errors", "qc_artifacts", "export_status", "exported_files",
                    "existing_export_files", "exported_paths", "existing_export_paths",
                    "export_errors",
                ):
                    previous.pop(key, None)
                previous["run_id"] = run_id
                previous["cache_hit"] = 1
                previous["cache_last_validated_by_tool_version"] = TOOL_VERSION
                previous["runtime_seconds"] = round(time.time() - start, 3)
                atomic_write_text(
                    status_path, json.dumps(previous, indent=2, ensure_ascii=False) + "\n"
                )
                return previous

    subject_out.mkdir(parents=True, exist_ok=True)
    has_external_atlas = any(atlases[key].kind == "external" for key in atlases)
    if has_external_atlas:
        if work_subjects is None:
            raise RuntimeError("A managed work directory is required for external atlases.")
        ensure_link(work_subjects / folder_id, subject_dir)
    env = os.environ.copy()
    env["SUBJECTS_DIR"] = str(work_subjects or subject_dir.parent)
    env["OMP_NUM_THREADS"] = "1"
    env["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"] = "1"
    errors: list[str] = []
    if not metadata["recon_all_done"]:
        errors.append(f"Missing recon-all completion marker: {subject_dir / 'scripts' / 'recon-all.done'}")
    cortical_rows: list[dict[str, Any]] = []
    with (subject_out / "extract.log").open("a", encoding="utf-8") as log:
        log.write(f"\nSTART tool={TOOL_VERSION} cache_schema={CACHE_SCHEMA_VERSION} subject={folder_id}\n")
        for message in cache_validation_errors:
            log.write(f"CACHE_INVALID {message}\n")
        for key in atlases:
            spec = atlases[key]
            atlas_rows: list[dict[str, Any]] = []
            for hemi in HEMISPHERES:
                try:
                    if spec.kind == "builtin":
                        stats_path = subject_dir / "stats" / f"{hemi}.{spec.stats_stem}.stats"
                        if not stats_path.is_file():
                            raise FileNotFoundError(f"Missing standard FreeSurfer stats: {stats_path}")
                    else:
                        annotation_dir = subject_out / "label"
                        stats_dir = subject_out / "stats"
                        annotation_dir.mkdir(exist_ok=True)
                        stats_dir.mkdir(exist_ok=True)
                        source_annot = spec.annotation_path(atlas_dir, hemi)
                        target_annot = output_annotation_path(subject_out, spec, hemi)
                        stats_path = stats_dir / f"{hemi}.{spec.stats_stem}.stats"
                        artifact_status = stats_dir / f"{hemi}.{spec.stats_stem}.artifact.json"
                        subject_annot, subject_stats = (
                            (None, None)
                            if overwrite or not spec.annot_pattern
                            else reusable_subject_artifacts(
                                subject_dir,
                                spec,
                                key,
                                hemi,
                                atlas_region_hashes.get(f"{key}:{hemi}"),
                                managed_exports,
                            )
                        )
                        source_kind = (
                            "subject_stats"
                            if subject_stats is not None
                            else "subject_annotation"
                            if subject_annot is not None
                            else "projected"
                        )
                        artifact_fingerprint = json_fingerprint(
                            {
                                "cache_schema_version": CACHE_SCHEMA_VERSION,
                                "atlas": key,
                                "hemisphere": hemi,
                                "atlas_sha256": atlas_checksums.get(f"{key}:{hemi}"),
                                "atlas_definition": asdict(spec),
                                "subject_surface_fingerprint": external_surface_fingerprint(subject_dir, hemi),
                                "runtime_version": runtime_version,
                                "freesurfer_home": str(fs_home),
                                "template_fingerprint": template_fingerprint,
                                "mapmethod": "FreeSurfer default",
                                "source_kind": source_kind,
                                "subject_annotation": file_state(subject_annot) if subject_annot else None,
                                "subject_stats": file_state(subject_stats) if subject_stats else None,
                            }
                        )
                        artifact_previous: dict[str, Any] = {}
                        if artifact_status.is_file() and not overwrite:
                            try:
                                artifact_previous = json.loads(artifact_status.read_text(encoding="utf-8"))
                            except (OSError, json.JSONDecodeError):
                                artifact_previous = {}
                        artifact_current = (
                            artifact_previous.get("fingerprint") == artifact_fingerprint
                            and artifact_previous.get("cache_schema_version")
                            == CACHE_SCHEMA_VERSION
                            and cache_tool_version_is_compatible(
                                str(artifact_previous.get("tool_version", ""))
                            )
                            and target_annot.is_file()
                            and stats_path.is_file()
                            and artifact_previous.get("output_artifacts")
                            == external_artifact_integrity(subject_out, spec, hemi)
                        )
                        if not artifact_current:
                            if subject_annot is not None:
                                atomic_copy_file(subject_annot, target_annot)
                                log.write(f"REUSE {key}/{hemi} annotation={subject_annot}\n")
                            else:
                                run_command(
                                    [
                                        "mri_surf2surf",
                                        "--hemi",
                                        hemi,
                                        "--srcsubject",
                                        str(spec.source_subject),
                                        "--trgsubject",
                                        folder_id,
                                        "--sval-annot",
                                        str(source_annot),
                                        "--tval",
                                        str(target_annot),
                                    ],
                                    env,
                                    log,
                                )
                            if subject_stats is not None:
                                atomic_copy_file(subject_stats, stats_path)
                                log.write(f"REUSE {key}/{hemi} stats={subject_stats}\n")
                            else:
                                run_command(
                                    [
                                        "mris_anatomical_stats",
                                        "-th3",
                                        "-mgz",
                                        "-cortex",
                                        str(subject_dir / "label" / f"{hemi}.cortex.label"),
                                        "-f",
                                        str(stats_path),
                                        "-b",
                                        "-a",
                                        str(target_annot),
                                        folder_id,
                                        hemi,
                                        "white",
                                    ],
                                    env,
                                    log,
                                )
                        else:
                            source_kind = str(artifact_previous.get("source", source_kind))
                            log.write(f"REUSE {key}/{hemi} output-cache\n")
                    hemi_rows = [
                        row
                        for row in parse_cortical_stats(stats_path, key, hemi)
                        if row["region"] not in spec.excluded_regions
                    ]
                    hemi_errors = []
                    if spec.kind == "external":
                        surface_path = subject_dir / "surf" / f"{hemi}.white"
                        surface_vertex_count = (
                            read_surface_vertex_count(surface_path) if surface_path.is_file() else None
                        )
                        hemi_errors.extend(
                            validate_annotation_file(
                                target_annot,
                                spec,
                                key,
                                hemi,
                                atlas_region_hashes.get(f"{key}:{hemi}"),
                                surface_vertex_count,
                            )
                        )
                    hemi_errors.extend(
                        validate_cortical_rows(
                            hemi_rows,
                            spec,
                            hemi,
                            atlas_region_hashes.get(f"{key}:{hemi}"),
                        )
                    )
                    errors.extend(hemi_errors)
                    for message in hemi_errors:
                        log.write(f"ERROR {message}\n")
                    if spec.kind == "external":
                        stored_fingerprint = "invalid" if hemi_errors else artifact_fingerprint
                        atomic_write_text(
                            artifact_status,
                            json.dumps(
                                {
                                    "fingerprint": stored_fingerprint,
                                    "tool_version": TOOL_VERSION,
                                    "cache_schema_version": CACHE_SCHEMA_VERSION,
                                    "atlas": key,
                                    "hemisphere": hemi,
                                    "source": source_kind,
                                    "output_artifacts": external_artifact_integrity(
                                        subject_out, spec, hemi
                                    ),
                                },
                                indent=2,
                            )
                            + "\n",
                        )
                    atlas_rows.extend(hemi_rows)
                except Exception as exc:  # continue so one failed atlas does not hide valid outputs
                    errors.append(f"{key}/{hemi}: {exc}")
                    log.write(f"ERROR {key}/{hemi}: {exc}\n")

            cortical_rows.extend(atlas_rows)

    aseg_path = subject_dir / "stats" / "aseg.stats"
    aseg_rows: list[dict[str, Any]] = []
    global_rows: list[dict[str, Any]] = []
    if aseg_path.is_file():
        aseg_rows = parse_aseg_stats(aseg_path)
        global_rows = parse_measure_lines(aseg_path)
        errors.extend(validate_aseg_rows(aseg_rows, global_rows, parse_aseg_header(aseg_path)))
    else:
        errors.append(f"Missing standard FreeSurfer stats: {aseg_path}")

    global_values: dict[str, Any] = {}
    for row in global_rows:
        global_values[str(row["measure"])] = row["value"]
        global_values[str(row["metric"])] = row["value"]
    lh_holes = global_values.get("lhSurfaceHoles")
    rh_holes = global_values.get("rhSurfaceHoles")
    lh_euler = 2 - 2 * int(lh_holes) if isinstance(lh_holes, (int, float)) else None
    rh_euler = 2 - 2 * int(rh_holes) if isinstance(rh_holes, (int, float)) else None
    etiv = global_values.get("EstimatedTotalIntraCranialVol", global_values.get("eTIV"))

    status = "OK" if not errors else ("PARTIAL" if cortical_rows or aseg_rows else "FAILED")
    summary = {
        **metadata,
        "status": status,
        "eTIV_mm3": etiv,
        "lh_surface_holes": lh_holes,
        "rh_surface_holes": rh_holes,
        "lh_euler": lh_euler,
        "rh_euler": rh_euler,
        "euler_sum": (lh_euler + rh_euler) if lh_euler is not None and rh_euler is not None else None,
        "cortical_rows": len(cortical_rows),
        "aseg_rows": len(aseg_rows),
        "runtime_seconds": round(time.time() - start, 3),
        "errors": " | ".join(errors),
        "tool_version": TOOL_VERSION,
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "cache_produced_by_tool_version": TOOL_VERSION,
        "cache_last_validated_by_tool_version": TOOL_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "fingerprint": fingerprint,
        "input_fingerprint": input_fingerprint,
        "runtime_freesurfer_version": runtime_version,
        "run_id": run_id,
        "cache_hit": 0,
        "managed_exports": managed_exports,
    }
    row_metadata = {key: metadata[key] for key in ("subject_id", "folder_id", "subject_path", "fs_version")}
    write_tsv(
        subject_out / "cortical.tsv",
        append_metadata(cortical_rows, row_metadata),
        list(row_metadata) + ["atlas", "hemisphere", "region"] + list(CORTICAL_COLUMNS),
    )
    write_tsv(
        subject_out / "aseg.tsv",
        append_metadata(aseg_rows, row_metadata),
        list(row_metadata) + list(ASEG_COLUMNS),
    )
    write_tsv(
        subject_out / "global.tsv",
        append_metadata(global_rows, row_metadata),
        list(row_metadata) + ["measure", "metric", "description", "value", "unit"],
    )
    serialized_errors = validate_subject_output_tables(
        subject_out, atlases, atlas_region_hashes
    )
    if serialized_errors:
        errors.extend(
            f"Serialized output validation: {message}"
            for message in serialized_errors
            if message not in errors
        )
        summary["status"] = "PARTIAL" if cortical_rows or aseg_rows else "FAILED"
        summary["errors"] = " | ".join(errors)
    summary["output_artifacts"] = output_artifact_integrity(subject_out)
    atomic_write_text(status_path, json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def read_aggregate_table(
    path: Path,
    summary: dict[str, Any],
    fields: list[str],
    key_groups: tuple[tuple[str, ...], ...],
    numeric_fields: tuple[str, ...],
    integer_fields: tuple[str, ...],
    atlases: dict[str, AtlasSpec],
) -> tuple[list[dict[str, str]], list[str]]:
    """Keep unambiguous rows; a damaged file must not hide other subject tables."""
    try:
        if not path.is_file():
            raise RuntimeError("missing output file")
        artifacts = summary.get("output_artifacts")
        recorded = artifacts.get(path.name) if isinstance(artifacts, dict) else None
        if recorded != file_integrity(path):
            raise RuntimeError("missing or mismatched output checksum")
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t", strict=True)
            headers = reader.fieldnames or []
            missing = sorted(set(fields) - set(headers))
            if missing or len(set(headers)) != len(headers):
                raise RuntimeError("invalid table header; missing columns: " + ", ".join(missing))
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error, RuntimeError) as exc:
        return [], [f"{path.name}: excluded file: {exc}"]

    errors = []
    rejected = set()
    keys: dict[tuple[str, ...], dict[tuple[str, ...], list[int]]] = {group: {} for group in key_groups}
    for index, row in enumerate(rows):
        # Include invalid numeric rows in duplicate detection so a conflicting
        # valid-looking copy cannot silently win.
        for group in key_groups:
            if all(isinstance(row.get(field), str) and row[field].strip() for field in group):
                key = tuple(row[field] for field in group)
                keys[group].setdefault(key, []).append(index)
        reason = ""
        if None in row or any(row.get(field) is None for field in fields):
            reason = "malformed TSV row"
        elif any(row[field] != str(summary.get(field, "")) for field in ("subject_id", "folder_id", "subject_path", "fs_version")):
            reason = "subject metadata mismatch"
        elif any(not row[field].strip() for group in key_groups for field in group):
            reason = "empty key"
        elif path.name == "cortical.tsv" and (row["atlas"] not in atlases or row["hemisphere"] not in HEMISPHERES):
            reason = "unexpected atlas/hemisphere"
        elif any(not is_finite_number(parse_number(row[field])) for field in numeric_fields):
            reason = "non-numeric or non-finite value"
        elif any(not is_nonnegative_integer(parse_number(row[field])) for field in integer_fields):
            reason = "invalid integer value"
        if reason:
            rejected.add(index)
            errors.append(f"{path.name}: excluded record {index + 1}: {reason}")
    for group, grouped in keys.items():
        for key, indices in grouped.items():
            if len(indices) > 1:
                rejected.update(indices)
                errors.append(f"{path.name}: excluded duplicate {','.join(group)} key {key}")
    return [row for index, row in enumerate(rows) if index not in rejected], errors


def iter_aggregate_tsv(
    records: list[tuple[Path, Path, dict[str, Any]]],
    filename: str,
) -> Iterator[dict[str, str]]:
    for _subject, base, summary in records:
        for row in read_tsv(base / filename):
            yield {**row, "status": summary.get("status", ""), "errors": summary.get("errors", "")}


def qc_annotation_path(subject_dir: Path, subject_out: Path, spec: AtlasSpec, hemi: str) -> Path:
    if spec.kind == "builtin":
        return subject_dir / "label" / f"{hemi}.{spec.stats_stem}.annot"
    return output_annotation_path(subject_out, spec, hemi)


def qc_input_integrity(
    subject_dir: Path,
    subject_out: Path,
    spec: AtlasSpec,
    surface: str,
    integrity_cache: Optional[IntegrityCache] = None,
) -> dict[str, dict[str, Any]]:
    paths: dict[str, Path] = {}
    for hemi in HEMISPHERES:
        paths[f"{hemi}_surface"] = subject_dir / "surf" / f"{hemi}.{surface}"
        paths[f"{hemi}_annotation"] = qc_annotation_path(subject_dir, subject_out, spec, hemi)
    return {
        name: file_integrity(path, integrity_cache)
        for name, path in paths.items()
        if path.is_file()
    }


def write_qc_artifact_metadata(
    subject_dir: Path,
    subject_out: Path,
    image_path: Path,
    spec: AtlasSpec,
    surface: str,
    dpi: int,
    run_id: str,
    integrity_cache: Optional[IntegrityCache] = None,
) -> dict[str, Any]:
    artifact = {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "atlas": spec.key,
        "surface": surface,
        "dpi": dpi,
        "image": image_path.name,
        "image_integrity": file_integrity(image_path),
        "input_integrity": qc_input_integrity(
            subject_dir, subject_out, spec, surface, integrity_cache
        ),
    }
    sidecar = Path(str(image_path) + ".json")
    atomic_write_text(sidecar, json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")
    return artifact


def valid_qc_artifacts(
    subject: Path,
    base: Path,
    summary: dict[str, Any],
    atlases: dict[str, AtlasSpec],
    integrity_cache: Optional[IntegrityCache] = None,
) -> list[tuple[Path, str, str]]:
    valid: list[tuple[Path, str, str]] = []
    for artifact in summary.get("qc_artifacts", []):
        if not isinstance(artifact, dict) or artifact.get("run_id") != summary.get("run_id"):
            continue
        atlas = str(artifact.get("atlas", ""))
        surface = str(artifact.get("surface", ""))
        if atlas not in atlases or surface not in {"inflated", "pial", "white"}:
            continue
        image_name = str(artifact.get("image", ""))
        if Path(image_name).name != image_name:
            continue
        image_path = base / "qc" / image_name
        sidecar = Path(str(image_path) + ".json")
        try:
            sidecar_artifact = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if sidecar_artifact != artifact:
            continue
        if not image_path.is_file() or artifact.get("image_integrity") != file_integrity(image_path):
            continue
        current_inputs = qc_input_integrity(
            subject, base, atlases[atlas], surface, integrity_cache
        )
        if len(current_inputs) != 4 or artifact.get("input_integrity") != current_inputs:
            continue
        valid.append((image_path, atlas, surface))
    return valid


def write_qc_report(
    output_dir: Path,
    records: list[tuple[Path, Path, dict[str, Any]]],
    atlases: dict[str, AtlasSpec],
    integrity_cache: Optional[IntegrityCache] = None,
) -> None:
    atlas_images: dict[str, dict[str, list[tuple[Path, str]]]] = {}
    for subject, base, summary in records:
        for image_path, atlas, surface in valid_qc_artifacts(
            subject, base, summary, atlases, integrity_cache
        ):
            atlas_images.setdefault(atlas, {}).setdefault(subject.name, []).append((image_path, surface))

    atlas_order = [atlas for atlas in atlases if atlas in atlas_images]
    tabs = []
    panels = []
    for index, atlas in enumerate(atlas_order):
        panel_id = f"atlas-panel-{index}"
        atlas_count = sum(len(images) for images in atlas_images[atlas].values())
        tabs.append(
            '<button class="atlas-tab" type="button" role="tab" data-atlas="{atlas}" '
            'aria-controls="{panel_id}" aria-selected="{selected}">{atlas}<span>{count}</span></button>'.format(
                atlas=html_lib.escape(atlas, quote=True),
                panel_id=panel_id,
                selected="true" if index == 0 else "false",
                count=atlas_count,
            )
        )
        subject_cards = []
        for subject, _base, summary in records:
            subject_id = str(summary.get("subject_id") or subject.name)
            status = str(summary.get("status", "UNKNOWN"))
            qc_status = str(summary.get("qc_status", "NOT GENERATED"))
            status_class = "ok" if status == "OK" and qc_status in {"OK", "NOT GENERATED"} else "bad"
            folder = (
                f'<span class="folder-id">{html_lib.escape(subject.name)}</span>'
                if subject_id != subject.name
                else ""
            )
            images = []
            for image_path, surface in atlas_images[atlas].get(subject.name, []):
                relative = image_path.relative_to(output_dir).as_posix()
                source = quote(relative, safe="/") + f"?v={image_path.stat().st_mtime_ns}"
                images.append(
                    '<figure><span class="surface-label">{surface}</span>'
                    '<a href="{src}" target="_blank" title="Open full-size image">'
                    '<img src="{src}" loading="lazy" decoding="async" alt="{subject} {atlas} QC"></a>'
                    "</figure>".format(
                        surface=html_lib.escape(surface),
                        src=html_lib.escape(source, quote=True),
                        subject=html_lib.escape(subject_id, quote=True),
                        atlas=html_lib.escape(atlas, quote=True),
                    )
                )
            content = "".join(images) or '<p class="missing">QC image missing</p>'
            subject_cards.append(
                '<article class="subject-card" data-subject="{data_subject}" data-images="{image_total}">'
                '<header><strong>{subject}</strong>{folder}'
                '<span class="status {status_class}">{status}</span>'
                '<span class="qc-state">QC: {qc_status}</span></header>{content}</article>'.format(
                    data_subject=html_lib.escape(f"{subject_id} {subject.name}".casefold(), quote=True),
                    image_total=len(images),
                    subject=html_lib.escape(subject_id),
                    folder=folder,
                    status_class=status_class,
                    status=html_lib.escape(status),
                    qc_status=html_lib.escape(qc_status),
                    content=content,
                )
            )
        display_name = atlases[atlas].display_name
        panels.append(
            '<section id="{panel_id}" class="atlas-panel" role="tabpanel" data-atlas="{atlas}" {hidden}>'
            '<div class="panel-head"><h2>{atlas}</h2><span>{display}</span>'
            '<b>{images} images / {subjects} subjects</b></div>'
            '<div class="subject-grid">{cards}</div></section>'.format(
                panel_id=panel_id,
                atlas=html_lib.escape(atlas, quote=True),
                hidden="" if index == 0 else "hidden",
                display=html_lib.escape(display_name),
                images=atlas_count,
                subjects=len(records),
                cards="".join(subject_cards),
            )
        )

    empty_report = '<p class="report-empty">No QC images found.</p>' if not panels else ""
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    page_start = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FSHarvest QC</title>
<style>
:root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }
* { box-sizing: border-box; }
body { margin: 0; color: #18202b; background: #eef1f5; }
.toolbar { position: sticky; top: 0; z-index: 20; display: flex; flex-wrap: wrap; align-items: center;
  gap: 10px; padding: 10px 14px; color: white; background: #111827; box-shadow: 0 2px 8px #0004; }
.toolbar h1 { margin: 0 14px 0 0; font-size: 18px; letter-spacing: .02em; }
.toolbar input { min-height: 34px; border: 1px solid #475569; border-radius: 6px;
  padding: 5px 9px; color: #111827; background: white; }
.toolbar input { width: min(300px, 42vw); }
.summary { margin-left: auto; color: #cbd5e1; font-size: 13px; }
main { padding: 8px; }
.tabs { display: flex; gap: 5px; overflow-x: auto; margin: -8px -8px 8px; padding: 7px 8px;
  border-bottom: 1px solid #cbd5e1; background: #dfe5ec; }
.atlas-tab { flex: 0 0 auto; border: 1px solid #94a3b8; border-radius: 6px; padding: 6px 10px;
  color: #334155; background: #f8fafc; font-weight: 800; cursor: pointer; }
.atlas-tab span { margin-left: 6px; border-radius: 999px; padding: 1px 6px; color: #475569; background: #e2e8f0; font-size: 10px; }
.atlas-tab[aria-selected="true"] { border-color: #1d4ed8; color: white; background: #1d4ed8; }
.atlas-tab[aria-selected="true"] span { color: #1e3a8a; background: #dbeafe; }
.panel-head { display: flex; align-items: baseline; gap: 8px; padding: 2px 2px 7px; }
.panel-head h2 { margin: 0; color: #0f172a; font-size: 18px; }
.panel-head span { color: #64748b; font-size: 12px; }
.panel-head b { margin-left: auto; color: #475569; font-size: 11px; }
.subject-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 7px; }
.subject-card { min-width: 0; overflow: hidden; border: 1px solid #d5dae2; border-radius: 7px; background: white; }
.subject-card:hover { border-color: #2563eb; box-shadow: 0 0 0 1px #2563eb; }
.subject-card header { display: flex; align-items: center; gap: 7px; min-height: 31px; padding: 4px 8px;
  border-bottom: 1px solid #e3e7ed; background: #f8fafc; }
.subject-card header strong { color: #0f172a; font-size: 14px; }
.folder-id { color: #64748b; font-size: 11px; }
.status, .qc-state { border-radius: 999px; padding: 2px 7px; font-size: 11px; font-weight: 700; }
.status.ok { color: #065f46; background: #d1fae5; }
.status.bad { color: #991b1b; background: #fee2e2; }
.qc-state { color: #334155; background: #e2e8f0; }
.subject-card figure { position: relative; margin: 0; }
.subject-card a { display: block; line-height: 0; }
.subject-card img { display: block; width: 100%; height: auto; background: white; }
.surface-label { position: absolute; z-index: 2; top: 4px; left: 4px; border-radius: 5px; padding: 3px 7px;
  color: #bfdbfe; background: #111827e8; font-size: 10px; font-weight: 700; pointer-events: none; }
.missing, .report-empty { margin: 0; padding: 20px; color: #991b1b; background: #fff7f7; text-align: center; font-size: 12px; font-weight: 700; }
[hidden] { display: none !important; }
@media (min-width: 1500px) { .subject-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
</head>
<body>
<header class="toolbar">
  <h1>FSHarvest QC</h1>
  <input id="subject-filter" type="search" placeholder="Filter subject ID…" autocomplete="off">
  <span class="summary"><span id="visible-count"></span> · generated """
    page_end = """</span>
</header>
<main><nav class="tabs" role="tablist">""" + "".join(tabs) + """</nav>""" + "".join(panels) + empty_report + """</main>
<script>
const subjectFilter = document.getElementById('subject-filter');
const tabs = [...document.querySelectorAll('.atlas-tab')];
const panels = [...document.querySelectorAll('.atlas-panel')];
let activeAtlas = tabs[0]?.dataset.atlas || '';
function applyFilters() {
  const query = subjectFilter.value.trim().toLocaleLowerCase();
  let visibleSubjects = 0;
  let visibleImages = 0;
  for (const panel of panels) {
    panel.hidden = panel.dataset.atlas !== activeAtlas;
    if (panel.hidden) continue;
    for (const card of panel.querySelectorAll('.subject-card')) {
      const show = card.dataset.subject.includes(query);
      card.hidden = !show;
      if (show) {
        visibleSubjects++;
        visibleImages += Number(card.dataset.images);
      }
    }
  }
  document.getElementById('visible-count').textContent = `${visibleSubjects} subjects · ${visibleImages} images`;
}
function selectAtlas(atlas) {
  activeAtlas = atlas;
  for (const tab of tabs) tab.setAttribute('aria-selected', String(tab.dataset.atlas === atlas));
  applyFilters();
}
for (const tab of tabs) tab.addEventListener('click', () => selectAtlas(tab.dataset.atlas));
subjectFilter.addEventListener('input', applyFilters);
applyFilters();
</script>
</body>
</html>
"""
    page = (
        page_start
        + html_lib.escape(generated)
        + page_end
    )
    atomic_write_text(output_dir / "all_qc.html", page)


def stale_wide_archive_plans(
    output_dir: Path, atlases: dict[str, AtlasSpec]
) -> list[tuple[Path, Path]]:
    metadata_path = output_dir / "run_metadata.json"
    if not metadata_path.is_file():
        return []
    try:
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw_atlases = previous.get("atlases")
    previous_atlases = {
        key for key in raw_atlases if isinstance(key, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", key)
    } if isinstance(raw_atlases, list) else set()
    stale_atlases = sorted(previous_atlases - set(atlases))
    if not stale_atlases:
        return []
    recorded = previous.get("aggregate_artifacts")
    if not isinstance(recorded, dict):
        recorded = {}
    previous_run_id = str(previous.get("run_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9._-]+", previous_run_id):
        previous_run_id = json_fingerprint(previous)[:16]
    plans = []
    for atlas in stale_atlases:
        relative = f"wide/{atlas}.tsv"
        source = output_dir / relative
        if not source.exists():
            continue
        expected = recorded.get(relative)
        if not isinstance(expected, dict) or file_integrity(source) != expected:
            raise RuntimeError(
                f"Cannot safely archive stale wide table without matching provenance: {source}. "
                "Move it outside the output directory and retry."
            )
        destination = output_dir / "archive" / previous_run_id / relative
        if destination.exists():
            raise FileExistsError(f"Wide-table archive destination already exists: {destination}")
        plans.append((source, destination))
    return plans


def aggregate(
    output_dir: Path,
    subjects: list[Path],
    atlases: dict[str, AtlasSpec],
    run_metadata: dict[str, Any],
    atlas_region_hashes: Optional[dict[str, str]] = None,
    qc_integrity_cache: Optional[IntegrityCache] = None,
) -> set[str]:
    # Stage only accepted rows once, so long and wide outputs use identical data
    # without holding the entire cohort in memory or changing per-subject TSVs.
    with tempfile.TemporaryDirectory(prefix=".fsharvest-aggregate-", dir=output_dir) as temporary:
        return aggregate_staged(
            output_dir, subjects, atlases, run_metadata, Path(temporary),
            atlas_region_hashes, qc_integrity_cache,
        )


def aggregate_staged(
    output_dir: Path,
    subjects: list[Path],
    atlases: dict[str, AtlasSpec],
    run_metadata: dict[str, Any],
    staging_dir: Path,
    atlas_region_hashes: Optional[dict[str, str]] = None,
    qc_integrity_cache: Optional[IntegrityCache] = None,
) -> set[str]:
    atlas_region_hashes = atlas_region_hashes or {}
    stale_wide_plans = stale_wide_archive_plans(output_dir, atlases)
    summaries: list[dict[str, Any]] = []
    records: list[tuple[Path, Path, dict[str, Any]]] = []
    data_records: list[tuple[Path, Path, dict[str, Any]]] = []
    non_ok_subjects: set[str] = set()
    metadata_fields = ["subject_id", "folder_id", "subject_path", "fs_version"]
    cortical_fields = metadata_fields + ["atlas", "hemisphere", "region"] + list(CORTICAL_COLUMNS)
    aseg_fields = metadata_fields + list(ASEG_COLUMNS)
    global_fields = metadata_fields + ["measure", "metric", "description", "value", "unit"]
    table_specs = (
        ("cortical.tsv", cortical_fields, (("atlas", "hemisphere", "region"),), CORTICAL_COLUMNS, ("numvert",)),
        ("aseg.tsv", aseg_fields, (("segid",), ("structure",)), tuple(field for field in ASEG_COLUMNS if field != "structure"), ("index", "segid", "nvoxels")),
        ("global.tsv", global_fields, (("metric",), ("measure",)), ("value",), ()),
    )
    expected_run_id = str(run_metadata.get("run_id", ""))
    for subject in subjects:
        base = output_dir / "per_subject" / subject.name
        status_path = base / "status.json"
        try:
            summary = json.loads(status_path.read_text(encoding="utf-8"))
            if not isinstance(summary, dict):
                raise ValueError("status.json must contain an object")
        except (OSError, ValueError) as exc:
            metadata = subject_metadata(subject)
            summary = {**metadata, "status": "NOT_RUN", "errors": f"Invalid or missing status.json: {exc}"}
        current_run = not expected_run_id or summary.get("run_id") == expected_run_id
        if not current_run:
            metadata = subject_metadata(subject)
            summary = {
                **metadata,
                "status": "NOT_RUN",
                "run_id": expected_run_id,
                "errors": "No status was produced for this run.",
            }
        if current_run and summary.get("status") != "NOT_RUN":
            staged = staging_dir / subject.name
            aggregation_errors = []
            for filename, fields, key_groups, numeric_fields, integer_fields in table_specs:
                rows, errors = read_aggregate_table(
                    base / filename, summary, fields, key_groups, numeric_fields, integer_fields, atlases
                )
                aggregation_errors.extend(errors)
                write_tsv(staged / filename, rows, fields)
            if aggregation_errors:
                if summary.get("status") != "FAILED":
                    summary["status"] = "PARTIAL"
                summary["errors"] = " | ".join(dict.fromkeys(filter(None, (
                    *str(summary.get("errors", "")).split(" | "), *aggregation_errors,
                ))))
            # Do not reintroduce rejected global values through wide-table metadata.
            global_values = {}
            for row in read_tsv(staged / "global.tsv"):
                for field in ("measure", "metric"):
                    global_values[row[field]] = parse_number(row["value"])
            summary["eTIV_mm3"] = global_values.get("EstimatedTotalIntraCranialVol", global_values.get("eTIV"))
            for hemi in HEMISPHERES:
                holes = global_values.get(f"{hemi}SurfaceHoles")
                summary[f"{hemi}_surface_holes"] = holes
                summary[f"{hemi}_euler"] = (
                    2 - 2 * int(holes)
                    if isinstance(holes, (int, float)) and is_nonnegative_integer(holes) else None
                )
            eulers = [summary[f"{hemi}_euler"] for hemi in HEMISPHERES]
            summary["euler_sum"] = sum(eulers) if all(value is not None for value in eulers) else None
            data_records.append((subject, staged, summary))
        if summary.get("status") != "OK":
            non_ok_subjects.add(subject.name)
        if status_path.parent.is_dir():
            atomic_write_text(status_path, json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        summaries.append(summary)
        records.append((subject, base, summary))

    write_tsv(
        output_dir / "cortical_long.tsv",
        iter_aggregate_tsv(data_records, "cortical.tsv"),
        cortical_fields + ["status", "errors"],
    )
    write_tsv(
        output_dir / "aseg_long.tsv",
        iter_aggregate_tsv(data_records, "aseg.tsv"),
        aseg_fields + ["status", "errors"],
    )
    write_tsv(
        output_dir / "global_measures_long.tsv",
        iter_aggregate_tsv(data_records, "global.tsv"),
        global_fields + ["status", "errors"],
    )

    summary_fields = [
        "subject_id", "folder_id", "subject_path", "fs_version", "fs_build_stamp",
        "recon_all_done", "status", "eTIV_mm3", "lh_surface_holes", "rh_surface_holes",
        "lh_euler", "rh_euler", "euler_sum", "cortical_rows", "aseg_rows",
        "runtime_seconds", "errors", "qc_status", "qc_errors", "export_status",
        "exported_files", "existing_export_files", "export_errors", "tool_version",
        "cache_schema_version", "output_schema_version", "runtime_freesurfer_version",
        "input_fingerprint", "run_id", "cache_hit",
    ]
    write_tsv(output_dir / "subjects.tsv", summaries, summary_fields)

    meta_fields = ["subject_id", "folder_id", "subject_path", "fs_version", "status", "errors", "eTIV_mm3", "lh_euler", "rh_euler", "euler_sum"]
    atlas_feature_fields: dict[str, set[str]] = {key: set() for key in atlases}
    atlas_complete: Counter[str] = Counter()
    aseg_feature_fields: set[str] = set()
    global_feature_fields: set[str] = set()
    observed_regions: dict[tuple[str, str], set[str]] = {
        (atlas, hemi): set() for atlas in atlases for hemi in HEMISPHERES
    }
    for subject, base, _summary in data_records:
        per_atlas: Counter[tuple[str, str]] = Counter()
        if (base / "cortical.tsv").is_file():
            for row in read_tsv(base / "cortical.tsv"):
                atlas = row["atlas"]
                if atlas not in atlas_feature_fields:
                    continue
                per_atlas[atlas, row["hemisphere"]] += 1
                observed_regions[atlas, row["hemisphere"]].add(row["region"])
                hemi = "L" if row["hemisphere"] == "lh" else "R"
                atlas_feature_fields[atlas].update(
                    f"{hemi}_{row['region']}_{metric}" for metric in CORTICAL_COLUMNS
                )
        for atlas in atlases:
            if all(per_atlas[atlas, hemi] == atlases[atlas].expected_rows(hemi) for hemi in HEMISPHERES):
                atlas_complete[atlas] += 1
        if (base / "aseg.tsv").is_file():
            aseg_feature_fields.update(
                f"aseg__{row['structure']}__volume_mm3" for row in read_tsv(base / "aseg.tsv")
            )
        if (base / "global.tsv").is_file():
            global_feature_fields.update(
                f"global__{row['metric']}" for row in read_tsv(base / "global.tsv")
            )

    def region_differences() -> Iterator[dict[str, Any]]:
        for subject, base, _summary in data_records:
            grouped: dict[tuple[str, str], set[str]] = {key: set() for key in observed_regions}
            for row in read_tsv(base / "cortical.tsv"):
                grouped[row["atlas"], row["hemisphere"]].add(row["region"])
            for (atlas, hemi), names in grouped.items():
                expected = set(atlases[atlas].region_names(hemi))
                missing = sorted(expected - names)
                unexpected = sorted(names - expected) if expected else []
                absent = sorted(observed_regions[atlas, hemi] - names)
                if missing or unexpected or absent:
                    yield {
                        "folder_id": subject.name, "atlas": atlas, "hemisphere": hemi,
                        "reference": "atlas_definition" if expected else "cohort_union",
                        "missing_expected": json.dumps(missing, ensure_ascii=False),
                        "unexpected_names": json.dumps(unexpected, ensure_ascii=False),
                        "absent_from_subject": json.dumps(absent, ensure_ascii=False),
                    }

    write_tsv(output_dir / "region_differences.tsv", region_differences(), [
        "folder_id", "atlas", "hemisphere", "reference",
        "missing_expected", "unexpected_names", "absent_from_subject",
    ])

    def metadata_row(summary: dict[str, Any]) -> dict[str, Any]:
        return {field: summary.get(field) for field in meta_fields}

    def atlas_rows(atlas: str) -> Iterator[dict[str, Any]]:
        for _subject, base, summary in data_records:
            output = metadata_row(summary)
            if (base / "cortical.tsv").is_file():
                for row in read_tsv(base / "cortical.tsv"):
                    if row["atlas"] != atlas:
                        continue
                    hemi = "L" if row["hemisphere"] == "lh" else "R"
                    for metric in CORTICAL_COLUMNS:
                        output[f"{hemi}_{row['region']}_{metric}"] = row[metric]
            yield output

    output_dir.joinpath("wide").mkdir(exist_ok=True)
    for atlas in atlases:
        fields = sorted(atlas_feature_fields[atlas])
        write_tsv(output_dir / "wide" / f"{atlas}.tsv", atlas_rows(atlas), meta_fields + fields)

    all_feature_fields = sorted(
        {f"{atlas}__{field}" for atlas in atlases for field in atlas_feature_fields[atlas]}
        | aseg_feature_fields
        | global_feature_fields
    )

    def all_feature_rows() -> Iterator[dict[str, Any]]:
        for _subject, base, summary in data_records:
            output = metadata_row(summary)
            if (base / "cortical.tsv").is_file():
                for row in read_tsv(base / "cortical.tsv"):
                    if row["atlas"] not in atlas_feature_fields:
                        continue
                    hemi = "L" if row["hemisphere"] == "lh" else "R"
                    for metric in CORTICAL_COLUMNS:
                        output[f"{row['atlas']}__{hemi}_{row['region']}_{metric}"] = row[metric]
            if (base / "aseg.tsv").is_file():
                for row in read_tsv(base / "aseg.tsv"):
                    output[f"aseg__{row['structure']}__volume_mm3"] = row["volume_mm3"]
            if (base / "global.tsv").is_file():
                for row in read_tsv(base / "global.tsv"):
                    output[f"global__{row['metric']}"] = row["value"]
            yield output

    write_tsv(output_dir / "all_features_wide.tsv", all_feature_rows(), meta_fields + all_feature_fields)

    atlas_manifest = [
        {
            **asdict(atlases[key]),
            "excluded_regions": ",".join(atlases[key].excluded_regions),
            "lh_annotation": atlases[key].annotations[0] if atlases[key].annotations else "",
            "rh_annotation": atlases[key].annotations[1] if atlases[key].annotations else "",
            "lh_expected_rows": atlases[key].expected_rows("lh"),
            "rh_expected_rows": atlases[key].expected_rows("rh"),
            "lh_region_sha256": atlas_region_hashes.get(f"{key}:lh"),
            "rh_region_sha256": atlas_region_hashes.get(f"{key}:rh"),
            "observed_subjects_complete": atlas_complete[key],
        }
        for key in atlases
    ]
    write_tsv(
        output_dir / "atlas_manifest.tsv",
        atlas_manifest,
        [
            "key", "display_name", "expected_total", "kind", "stats_stem",
            "source_subject", "annot_pattern", "lh_annotation", "rh_annotation", "excluded_regions",
            "lh_expected_rows", "rh_expected_rows",
            "lh_region_sha256", "rh_region_sha256", "observed_subjects_complete",
        ],
    )
    write_qc_report(output_dir, records, atlases, qc_integrity_cache)
    archived_wide_tables = []
    for source, destination in stale_wide_plans:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        archived_wide_tables.append(str(destination.relative_to(output_dir)))
    run_metadata["archived_wide_tables"] = archived_wide_tables
    run_metadata["aggregate_artifacts"] = {
        f"wide/{atlas}.tsv": file_integrity(output_dir / "wide" / f"{atlas}.tsv")
        for atlas in atlases
    }
    run_metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_write_text(output_dir / "run_metadata.json", json.dumps(run_metadata, indent=2) + "\n")
    return non_ok_subjects


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fsharvest",
        description="One-command extraction of cortical, aseg, global, Euler, and provenance data from FreeSurfer outputs."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {TOOL_VERSION}")
    parser.add_argument("subjects_dir", type=Path, help="Directory whose child directories are FreeSurfer subjects.")
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Output directory; input subjects are read-only unless --export-to-freesurfer is used.",
    )
    parser.add_argument("--jobs", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--limit", type=int, help="Process only the first N sorted subjects (testing).")
    parser.add_argument("--recursive", action="store_true", help="Discover FreeSurfer subjects recursively.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Force fresh external atlas projection/stats; ignore output and subject-level artifacts.",
    )
    parser.add_argument(
        "--export-to-freesurfer",
        action="store_true",
        help=(
            "Copy validated external atlas annotations/stats to each input subject's label/ and stats/ "
            "directories; never replaces existing files."
        ),
    )
    parser.add_argument("--freesurfer-home", type=Path, default=os.environ.get("FREESURFER_HOME"))
    parser.add_argument("--atlas-dir", type=Path, default=Path(__file__).resolve().parent / "atlases")
    parser.add_argument(
        "--atlases", nargs="+", metavar="NAME_OR_JSON", default=list(DEFAULT_ATLASES),
        help="Curated atlas names or custom atlas JSON files; may be mixed. Default: dk68.",
    )
    parser.add_argument("--qc-plots", action="store_true", help="Render four-view cortical atlas PNGs (optional dependencies).")
    parser.add_argument("--qc-atlases", nargs="+", help="Keys of selected atlases to render, including custom atlas keys.")
    parser.add_argument("--qc-surface", choices=("inflated", "pial", "white"), default="inflated")
    parser.add_argument("--qc-dpi", type=int, default=150)
    parser.add_argument(
        "--force-unlock",
        action="store_true",
        help="Remove a stale same-host output lock after confirming its process has exited.",
    )
    return parser.parse_args(argv)


def print_banner() -> None:
    print(
        f"{ASCII_LOGO}\n"
        f"  {TOOL_NAME} v{TOOL_VERSION} | FreeSurfer regional feature extraction\n"
        f"  Developer: {TOOL_DEVELOPER}\n"
        f"  License: MIT | Source: {TOOL_URL}\n",
        flush=True,
    )


def print_progress(message: str, started: float, *, error: bool = False) -> None:
    elapsed = max(0, int(time.monotonic() - started))
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    print(
        f"[{timestamp} | elapsed {hours:02d}:{minutes:02d}:{seconds:02d}] {message}",
        file=sys.stderr if error else sys.stdout,
        flush=True,
    )


def validate_output_directory(subjects_dir: Path, output_dir: Path) -> Path:
    subjects_root = subjects_dir.resolve()
    output_root = output_dir.resolve()
    if (
        output_root == subjects_root
        or output_root.is_relative_to(subjects_root)
        or subjects_root.is_relative_to(output_root)
    ):
        raise ValueError("Input and output directories must not contain one another.")
    return output_root


def _main(argv: Optional[list[str]], resources: RunResources, started: float) -> int:
    args = parse_args(argv)
    # The shell launcher displays the same banner before FreeSurfer setup.
    if os.environ.pop("FSHARVEST_LAUNCHER_BANNER_SHOWN", "") != "1":
        print_banner()
    print_progress("[CHECK] Checking options, input directory and FreeSurfer environment...", started)
    print(f"Input: {args.subjects_dir.resolve()}\nOutput: {args.output_dir.resolve()}", flush=True)
    print(f"Atlases: {', '.join(args.atlases)} | Parallel jobs: {args.jobs}", flush=True)
    if args.jobs < 1:
        raise ValueError("--jobs must be at least 1")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1")
    if args.qc_dpi < 72:
        raise ValueError("--qc-dpi must be at least 72")
    if not args.subjects_dir.is_dir():
        raise FileNotFoundError(f"Subjects directory does not exist: {args.subjects_dir}")
    if args.freesurfer_home is None:
        raise RuntimeError("Set FREESURFER_HOME or pass --freesurfer-home.")
    fs_home = Path(args.freesurfer_home).resolve()
    if not fs_home.is_dir():
        raise FileNotFoundError(f"FreeSurfer home does not exist: {fs_home}")
    for command in ("mri_surf2surf", "mris_anatomical_stats", "recon-all"):
        if shutil.which(command) is None:
            raise RuntimeError(
                f"FreeSurfer command '{command}' is not on PATH. Use run_extract.sh or source SetUpFreeSurfer.sh."
            )

    subjects_root = args.subjects_dir.resolve()
    output_root = validate_output_directory(args.subjects_dir, args.output_dir)

    atlas_root = args.atlas_dir.resolve()
    print_progress("[CHECK] Resolving atlas definitions and validating atlas assets...", started)
    atlases = resolve_atlases(args.atlases, atlas_root, fs_home)
    qc_keys = args.qc_atlases or list(atlases)
    unselected_qc = sorted(set(qc_keys) - set(atlases))
    if args.qc_plots and unselected_qc:
        raise ValueError("--qc-atlases must be included in --atlases: " + ", ".join(unselected_qc))
    qc_atlases = {key: atlases[key] for key in qc_keys if key in atlases}
    render_subject_function: Any = None
    qc_integrity_cache: IntegrityCache = {}
    if args.qc_plots:
        try:
            from fs_render_qc import render_subject as render_subject_function
        except ImportError as exc:
            raise RuntimeError(
                "QC plots require numpy, nibabel, matplotlib, and Pillow; install requirements-qc.txt."
            ) from exc

    atlas_checksums = validate_atlas_files(atlas_root, atlases)
    atlas_region_hashes = load_region_schema(atlas_root, atlases)
    atlas_fingerprint = json_fingerprint(
        {"files": atlas_checksums, "definitions": {key: asdict(spec) for key, spec in atlases.items()}}
    )
    print_progress("[DISCOVER] Finding FreeSurfer subjects...", started)
    subjects = discover_subjects(subjects_root, args.recursive)
    if args.limit is not None:
        subjects = subjects[: args.limit]
    if not subjects:
        raise RuntimeError(f"No FreeSurfer subject directories found under {args.subjects_dir}")
    duplicate_names = sorted(name for name, count in Counter(path.name for path in subjects).items() if count > 1)
    if duplicate_names:
        raise RuntimeError("Duplicate subject folder IDs are not supported: " + ", ".join(duplicate_names))
    subjects_inside_output = [
        str(subject) for subject in subjects if subject.resolve().is_relative_to(output_root)
    ]
    if subjects_inside_output:
        raise ValueError(
            "Resolved subject directories must not be inside the output directory: "
            + ", ".join(subjects_inside_output)
        )

    output_root.mkdir(parents=True, exist_ok=True)
    resources.acquire(output_root, args.force_unlock)
    has_external_atlas = any(atlases[key].kind == "external" for key in atlases)
    work_subjects = resources.create_work_dir() / "subjects" if has_external_atlas else None
    for source_subject in {atlases[key].source_subject for key in atlases} - {None}:
        if work_subjects is None:
            raise AssertionError("External atlas source requires a managed work directory.")
        source_path = fs_home / "subjects" / str(source_subject)
        if not source_path.is_dir():
            raise FileNotFoundError(f"FreeSurfer template subject is missing: {source_path}")
        ensure_link(work_subjects / str(source_subject), source_path)

    runtime_version = command_version()
    print_progress("[PREPARE] Checking template inputs before extraction...", started)
    template_fingerprint = template_input_fingerprint(fs_home, atlases)
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = uuid.uuid4().hex
    print_progress(f"Discovered {len(subjects)} subjects; jobs={args.jobs}; FreeSurfer={runtime_version}", started)
    print_progress(
        f"[EXTRACT] Starting {len(subjects)} subjects; progress is reported after each subject finishes.",
        started,
    )
    failed_subjects: set[str] = set()
    extraction_results: dict[Path, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {
            executor.submit(
                extract_subject,
                subject,
                output_root,
                args.atlas_dir.resolve(),
                atlases,
                atlas_fingerprint,
                atlas_checksums,
                fs_home,
                runtime_version,
                template_fingerprint,
                args.overwrite,
                atlas_region_hashes,
                run_id,
                work_subjects,
            ): subject
            for subject in subjects
        }
        for count, future in enumerate(as_completed(futures), start=1):
            subject = futures[future]
            try:
                result = future.result()
                extraction_results[subject] = result
                cached = " (cached)" if result.get("cache_hit") else ""
                print_progress(f"[{count}/{len(subjects)}] {subject.name}: {result['status']}{cached}", started)
                if result["status"] != "OK":
                    failed_subjects.add(subject.name)
            except Exception as exc:
                failed_subjects.add(subject.name)
                fatal_status = {
                    **subject_metadata(subject),
                    "status": "FAILED",
                    "errors": f"Fatal extraction error: {exc}",
                    "tool_version": TOOL_VERSION,
                    "cache_schema_version": CACHE_SCHEMA_VERSION,
                    "output_schema_version": OUTPUT_SCHEMA_VERSION,
                    "runtime_freesurfer_version": runtime_version,
                    "run_id": run_id,
                    "cache_hit": 0,
                }
                status_path = output_root / "per_subject" / subject.name / "status.json"
                atomic_write_text(
                    status_path, json.dumps(fatal_status, indent=2, ensure_ascii=False) + "\n"
                )
                print_progress(f"[{count}/{len(subjects)}] {subject.name}: FATAL: {exc}", started, error=True)

    if args.export_to_freesurfer:
        print_progress("[EXPORT] Exporting validated external-atlas artifacts to FreeSurfer subjects...", started)
        for count, subject in enumerate(subjects, start=1):
            subject_out = output_root / "per_subject" / subject.name
            status_path = subject_out / "status.json"
            status = extraction_results.get(subject)
            if status is None:
                try:
                    status = json.loads(status_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    status = {"status": "FAILED"}
            if subject.name in failed_subjects or status.get("status") != "OK":
                export_result = {
                    "export_status": "SKIPPED",
                    "exported_files": 0,
                    "existing_export_files": 0,
                    "exported_paths": [],
                    "existing_export_paths": [],
                    "export_errors": "Extraction is not OK; no files were exported.",
                }
                failed_subjects.add(subject.name)
                print_progress(f"[EXPORT {count}/{len(subjects)}] {subject.name}: SKIPPED (extraction is not OK)", started)
            else:
                try:
                    export_result = export_subject_artifacts(
                        subject,
                        subject_out,
                        atlases,
                        atlas_region_hashes,
                        status.get("managed_exports"),
                    )
                    print_progress(
                        f"[EXPORT {count}/{len(subjects)}] {subject.name}: "
                        f"{export_result['exported_files']} new, "
                        f"{export_result['existing_export_files']} existing",
                        started,
                    )
                except Exception as exc:
                    export_result = {
                        "export_status": "FAILED",
                        "exported_files": 0,
                        "existing_export_files": 0,
                        "exported_paths": [],
                        "existing_export_paths": [],
                        "export_errors": str(exc),
                    }
                    failed_subjects.add(subject.name)
                    print_progress(
                        f"[EXPORT {count}/{len(subjects)}] {subject.name}: FAILED: {exc}",
                        started, error=True,
                    )
            status.update(export_result)
            extraction_results[subject] = status
            atomic_write_text(status_path, json.dumps(status, indent=2, ensure_ascii=False) + "\n")

    if args.qc_plots:
        assert render_subject_function is not None
        print_progress(f"[QC] Rendering {len(qc_atlases)} atlases for {len(subjects)} subjects...", started)
        for count, subject in enumerate(subjects, start=1):
            subject_out = output_root / "per_subject" / subject.name
            status_path = subject_out / "status.json"
            try:
                outputs = render_subject_function(
                    subject, subject_out, qc_atlases, args.qc_surface, args.qc_dpi
                )
                qc_artifacts = []
                for image_path in outputs:
                    suffix = f"_{args.qc_surface}_4view.png"
                    if not image_path.name.endswith(suffix):
                        raise RuntimeError(f"Unexpected QC output name: {image_path}")
                    atlas = image_path.name[: -len(suffix)]
                    qc_artifacts.append(
                        write_qc_artifact_metadata(
                            subject,
                            subject_out,
                            image_path,
                            atlases[atlas],
                            args.qc_surface,
                            args.qc_dpi,
                            run_id,
                            qc_integrity_cache,
                        )
                    )
                qc_status, qc_errors = "OK", ""
                print_progress(f"[QC {count}/{len(subjects)}] {subject.name}: {len(outputs)} PNGs", started)
            except Exception as exc:
                qc_status, qc_errors, qc_artifacts = "FAILED", str(exc), []
                failed_subjects.add(subject.name)
                print_progress(f"[QC {count}/{len(subjects)}] {subject.name}: FAILED: {exc}", started, error=True)
            try:
                status = json.loads(status_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            status.update(
                {
                    "qc_status": qc_status,
                    "qc_errors": qc_errors,
                    "qc_artifacts": qc_artifacts,
                }
            )
            atomic_write_text(status_path, json.dumps(status, indent=2, ensure_ascii=False) + "\n")

    run_metadata = {
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "run_id": run_id,
        "started_at_utc": started_at,
        "runtime_freesurfer_version": runtime_version,
        "freesurfer_home": str(fs_home),
        "subjects_dir": str(subjects_root),
        "output_dir": str(output_root),
        "atlases": list(atlases),
        "atlas_definitions": {key: asdict(spec) for key, spec in atlases.items()},
        "atlas_checksums": atlas_checksums,
        "atlas_fingerprint": atlas_fingerprint,
        "atlas_region_sha256": atlas_region_hashes,
        "tool_source_checksums": tool_source_checksums(),
        "template_fingerprint": template_fingerprint,
        "n_subjects": len(subjects),
        "jobs": args.jobs,
        "recursive": args.recursive,
        "limit": args.limit,
        "overwrite": args.overwrite,
        "export_to_freesurfer": args.export_to_freesurfer,
        "qc_plots": args.qc_plots,
        "qc_atlases": list(qc_atlases) if args.qc_plots else None,
        "qc_surface": args.qc_surface if args.qc_plots else None,
        "qc_dpi": args.qc_dpi if args.qc_plots else None,
    }
    print_progress("[AGGREGATE] Writing cohort tables and region-difference report...", started)
    failed_subjects.update(
        aggregate(
            output_root,
            subjects,
            atlases,
            run_metadata,
            atlas_region_hashes,
            qc_integrity_cache,
        )
    )
    failures = len(failed_subjects)
    statuses = Counter(row["status"] for row in read_tsv(output_root / "subjects.tsv"))
    print_progress(
        f"[DONE] Finished: {len(subjects) - failures} OK, {failures} non-OK across all requested phases.",
        started,
    )
    print("Table status: " + ", ".join(f"{key}={statuses[key]}" for key in ("OK", "PARTIAL", "FAILED", "NOT_RUN")), flush=True)
    if failures:
        print("Available data are retained; review subjects.tsv and region_differences.tsv for reported problems.", flush=True)
    print(f"Output: {output_root}\nSubject logs: {output_root / 'per_subject'}/<folder_id>/extract.log", flush=True)
    if args.qc_plots:
        print(f"QC report: {output_root / 'all_qc.html'}", flush=True)
    return 0 if failures == 0 else 2


def main(argv: Optional[list[str]] = None) -> int:
    resources = RunResources()
    started = time.monotonic()
    try:
        return _main(argv, resources, started)
    except (Exception, KeyboardInterrupt):
        print_progress("[STOPPED] Run ended before completion.", started, error=True)
        raise
    finally:
        resources.cleanup()


def run_logged(argv: list[str], launcher: Optional[str] = None) -> int:
    """Capture the complete CLI, including shell setup, without user-script tee."""
    args = parse_args(argv)
    output_root = validate_output_directory(args.subjects_dir, args.output_dir)
    log_dir = output_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    log_path = log_dir / f"run_{stamp}_{uuid.uuid4().hex[:8]}.log"
    command = ["bash", launcher] if launcher else [sys.executable, str(Path(__file__).resolve())]
    environment = dict(os.environ, FSHARVEST_RUN_LOG_ACTIVE="1", PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    with log_path.open("x", encoding="utf-8") as log:
        def emit(text: str) -> None:
            log.write(text)
            log.flush()
            sys.stdout.write(text)
            sys.stdout.flush()

        emit(f"Run log: {log_path}\n")
        with subprocess.Popen(
            [*command, *argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", env=environment,
            start_new_session=os.name != "nt",
        ) as process:
            def forward_termination(signum: int, _frame: Any) -> None:
                if process.poll() is None:
                    if sys.platform == "win32":
                        process.terminate()
                    else:
                        os.killpg(process.pid, signum)

            previous_termination = signal.signal(signal.SIGTERM, forward_termination)
            try:
                assert process.stdout is not None
                for line in process.stdout:
                    emit(line)
                result = process.wait()
            except KeyboardInterrupt:
                forward_termination(signal.SIGINT, None)
                emit("ERROR: interrupted\n")
                result = 130
            finally:
                signal.signal(signal.SIGTERM, previous_termination)
                if process.poll() is None:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        if sys.platform == "win32":
                            process.kill()
                        else:
                            os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
        if result < 0:
            result = 128 - result
        emit(f"Run exit code: {result}\nRun log: {log_path}\n")
        return result


def cli(argv: Optional[list[str]] = None, launcher: Optional[str] = None) -> int:
    try:
        arguments = list(sys.argv[1:] if argv is None else argv)
        if os.environ.pop("FSHARVEST_RUN_LOG_ACTIVE", "") == "1":
            return main(arguments)
        return run_logged(arguments, launcher)
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        if os.environ.get("FSHARVEST_DEBUG"):
            raise
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())

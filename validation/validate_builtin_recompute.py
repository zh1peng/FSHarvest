#!/usr/bin/env python3
"""Compare native DK68/Destrieux stats with fresh mris_anatomical_stats output."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import fs_extract_all as fsh  # noqa: E402


BUILTIN_ATLASES = {
    "dk68": ("aparc", "aparc"),
    "destrieux": ("aparc.a2009s", "aparc.a2009s"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subjects_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--freesurfer-home", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--atol", type=float, default=1e-12)
    parser.add_argument("--rtol", type=float, default=1e-12)
    args = parser.parse_args()
    if args.limit < 1 or args.jobs < 1:
        parser.error("--limit and --jobs must be positive")
    if args.atol < 0 or args.rtol < 0:
        parser.error("--atol and --rtol must be non-negative")
    return args


def required_paths(subject: Path) -> list[Path]:
    paths: list[Path] = []
    for _atlas, (stats_stem, annot_stem) in BUILTIN_ATLASES.items():
        for hemi in fsh.HEMISPHERES:
            paths.extend(
                (
                    subject / "stats" / f"{hemi}.{stats_stem}.stats",
                    subject / "label" / f"{hemi}.{annot_stem}.annot",
                    subject / "label" / f"{hemi}.cortex.label",
                    subject / "surf" / f"{hemi}.white",
                    subject / "surf" / f"{hemi}.pial",
                    subject / "surf" / f"{hemi}.thickness",
                )
            )
    return paths


def recompute_one(
    executable: Path,
    subjects_dir: Path,
    output_dir: Path,
    subject: Path,
    atlas: str,
    hemi: str,
    env: dict[str, str],
) -> tuple[Path, Path]:
    stats_stem, annot_stem = BUILTIN_ATLASES[atlas]
    native = subject / "stats" / f"{hemi}.{stats_stem}.stats"
    generated = output_dir / "recomputed" / subject.name / f"{hemi}.{stats_stem}.stats"
    generated.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(executable),
        "-th3",
        "-mgz",
        "-cortex",
        str(subject / "label" / f"{hemi}.cortex.label"),
        "-f",
        str(generated),
        "-b",
        "-a",
        str(subject / "label" / f"{hemi}.{annot_stem}.annot"),
        subject.name,
        hemi,
        "white",
    ]
    completed = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
    log_path = generated.with_suffix(".log")
    log_path.write_text(
        "COMMAND " + " ".join(command) + "\n" + completed.stdout + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{subject.name}/{atlas}/{hemi} failed; see {log_path}")
    return native, generated


def relative_error(left: float, right: float) -> float:
    scale = max(abs(left), abs(right))
    return 0.0 if scale == 0 else abs(left - right) / scale


def compare_pair(
    subject: str,
    atlas: str,
    hemi: str,
    native_path: Path,
    generated_path: Path,
    atol: float,
    rtol: float,
) -> list[dict[str, Any]]:
    native = {
        row["region"]: row for row in fsh.parse_cortical_stats(native_path, atlas, hemi)
    }
    generated = {
        row["region"]: row
        for row in fsh.parse_cortical_stats(generated_path, atlas, hemi)
    }
    if native.keys() != generated.keys():
        missing = sorted(native.keys() - generated.keys())
        extra = sorted(generated.keys() - native.keys())
        raise RuntimeError(
            f"{subject}/{atlas}/{hemi} region mismatch: missing={missing}, extra={extra}"
        )
    comparisons = []
    for region in sorted(native):
        for metric in fsh.CORTICAL_COLUMNS:
            left = float(native[region][metric])
            right = float(generated[region][metric])
            absolute = abs(left - right)
            comparisons.append(
                {
                    "folder_id": subject,
                    "atlas": atlas,
                    "hemisphere": hemi,
                    "region": region,
                    "measure": metric,
                    "native": left,
                    "recomputed": right,
                    "absolute_error": absolute,
                    "relative_error": relative_error(left, right),
                    "exact_equal": left == right,
                    "within_tolerance": math.isclose(left, right, abs_tol=atol, rel_tol=rtol),
                }
            )
    return comparisons


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    subjects_dir = args.subjects_dir.resolve()
    output_dir = args.output_dir.resolve()
    executable = args.freesurfer_home.resolve() / "bin" / "mris_anatomical_stats"
    if not subjects_dir.is_dir():
        raise NotADirectoryError(subjects_dir)
    if (
        output_dir == subjects_dir
        or output_dir.is_relative_to(subjects_dir)
        or subjects_dir.is_relative_to(output_dir)
    ):
        raise ValueError("Input and output directories must not contain one another.")
    if not executable.is_file():
        raise FileNotFoundError(executable)
    output_dir.mkdir(parents=True, exist_ok=False)

    candidates = [path for path in sorted(subjects_dir.iterdir()) if path.is_dir()]
    subjects = [subject for subject in candidates if all(path.is_file() for path in required_paths(subject))]
    subjects = subjects[: args.limit]
    if len(subjects) < args.limit:
        raise RuntimeError(f"Found only {len(subjects)} complete subjects; requested {args.limit}")

    env = os.environ.copy()
    env["FREESURFER_HOME"] = str(args.freesurfer_home.resolve())
    env["SUBJECTS_DIR"] = str(subjects_dir)
    env["OMP_NUM_THREADS"] = "1"
    env["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"] = "1"
    jobs = []
    for subject in subjects:
        for atlas in BUILTIN_ATLASES:
            for hemi in fsh.HEMISPHERES:
                jobs.append((subject, atlas, hemi))

    generated_pairs = []
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {
            executor.submit(
                recompute_one,
                executable,
                subjects_dir,
                output_dir,
                subject,
                atlas,
                hemi,
                env,
            ): (subject, atlas, hemi)
            for subject, atlas, hemi in jobs
        }
        for count, future in enumerate(as_completed(futures), start=1):
            subject, atlas, hemi = futures[future]
            native, generated = future.result()
            generated_pairs.append((subject, atlas, hemi, native, generated))
            print(f"[{count}/{len(jobs)}] {subject.name}/{atlas}/{hemi}", flush=True)

    comparisons = []
    for subject, atlas, hemi, native, generated in generated_pairs:
        comparisons.extend(
            compare_pair(
                subject.name, atlas, hemi, native, generated, args.atol, args.rtol
            )
        )
    comparisons.sort(
        key=lambda row: (
            row["folder_id"], row["atlas"], row["hemisphere"], row["region"], row["measure"]
        )
    )

    summary = []
    for atlas in BUILTIN_ATLASES:
        for metric in fsh.CORTICAL_COLUMNS:
            rows = [
                row
                for row in comparisons
                if row["atlas"] == atlas and row["measure"] == metric
            ]
            worst = max(rows, key=lambda row: row["absolute_error"])
            summary.append(
                {
                    "atlas": atlas,
                    "measure": metric,
                    "comparisons": len(rows),
                    "exact_equal": sum(bool(row["exact_equal"]) for row in rows),
                    "within_tolerance": sum(bool(row["within_tolerance"]) for row in rows),
                    "max_absolute_error": worst["absolute_error"],
                    "max_relative_error": max(row["relative_error"] for row in rows),
                    "worst_location": "/".join(
                        str(worst[key])
                        for key in ("folder_id", "hemisphere", "region")
                    ),
                }
            )

    comparison_fields = list(comparisons[0])
    summary_fields = list(summary[0])
    write_tsv(output_dir / "comparisons.tsv", comparisons, comparison_fields)
    write_tsv(output_dir / "summary.tsv", summary, summary_fields)
    metadata = {
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "subjects_dir": str(subjects_dir),
        "subject_count": len(subjects),
        "native_stats_versions": sorted(
            {
                str(fsh.header_value(native, "cvs_version"))
                for _subject, _atlas, _hemi, native, _generated in generated_pairs
            }
        ),
        "recomputed_stats_versions": sorted(
            {
                str(fsh.header_value(generated, "cvs_version"))
                for _subject, _atlas, _hemi, _native, generated in generated_pairs
            }
        ),
        "atlases": list(BUILTIN_ATLASES),
        "hemispheres": list(fsh.HEMISPHERES),
        "measures": list(fsh.CORTICAL_COLUMNS),
        "comparison_count": len(comparisons),
        "atol": args.atol,
        "rtol": args.rtol,
        "all_exact": all(row["exact_equal"] for row in comparisons),
        "all_within_tolerance": all(row["within_tolerance"] for row in comparisons),
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2), flush=True)
    return 0 if metadata["all_within_tolerance"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

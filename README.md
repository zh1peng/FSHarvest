# FSHarvest

<p align="center">
  <img src="assets/fsharvest-logo.png" alt="FSHarvest" width="420">
</p>

<p align="center">
  <a href="https://zh1peng.github.io/FSHarvest/">中文文档</a> ·
  <a href="https://zh1peng.github.io/FSHarvest/en/">English</a> ·
  <a href="VALIDATION.md">验证记录</a>
</p>

**Harvest complete, analysis-ready features from a directory of FreeSurfer subjects.**

FSHarvest is a standalone Linux command-line tool. It takes one directory containing FreeSurfer subject output folders and extracts, in parallel:

- subject ID, folder ID, absolute subject path, reconstruction FreeSurfer version/build stamp, and `recon-all.done` status;
- all nine cortical columns (`NumVert`, `SurfArea`, `GrayVol`, `ThickAvg`, `ThickStd`, `MeanCurv`, `GausCurv`, `FoldInd`, `CurvInd`);
- Desikan-Killiany/DK68 (`aparc`, default), plus optional Destrieux, DK308/NSPN500, Schaefer 100–1000 (100-parcel increments), Glasser360, von Economo-Koskinas, and Vos de Wael 300 atlases;
- every structure row in `aseg.stats`, rather than a short hard-coded subcortical list;
- every global `# Measure` record in `aseg.stats`, including eTIV;
- left/right surface holes, left/right Euler number, and their sum.

Input FreeSurfer folders are read-only by default. Subject-specific external annotations and stats are written under the output directory, making runs resumable and auditable. The explicit `--export-to-freesurfer` compatibility option can additionally copy validated external-atlas files into the input reconstruction.

## Install

Requirements: Linux, Python 3.9+, a licensed FreeSurfer installation, and `curl` only if re-downloading atlases. Core extraction has no Python package dependencies. QC PNG rendering additionally needs NumPy, Nibabel, Matplotlib, and Pillow (`python3 -m pip install -r requirements-qc.txt`).

A pre-release baseline was end-to-end tested with a FreeSurfer 7.4.1 runtime against reconstructions produced by FreeSurfer 7.2.0. FSHarvest 1.0.0rc1 is a release candidate whose integrity fixes are covered by the automated regression suite; repeat the representative-subject FreeSurfer smoke test on the exact release commit before publishing 1.0.0. Validate other FreeSurfer releases on representative subjects before study-wide use.

```bash
cd /path/to/FSHarvest
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
```

`install.sh` stages the complete tool, documentation, and pinned atlas assets in an immutable version directory under `~/.local/lib/fsharvest/`, then atomically switches `current` and creates `~/.local/bin/fsharvest`. The installed command is independent of the source checkout. Supply a different prefix as the first argument if needed, for example `bash install.sh /opt/fsharvest`. Use `bash install.sh --check [PREFIX]` for self-check and `bash install.sh --uninstall [PREFIX]` to remove launch links while retaining version directories.

Installation is optional. The tool can always be run directly with `bash /path/to/FSHarvest/fsharvest ...`.

## Quick start

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1

fsharvest /path/to/dir_to_all_subj /path/to/output --jobs 12
```

Check the installation without initializing FreeSurfer:

```bash
fsharvest --version
fsharvest --help
```

The input directory should look like:

```text
dir_to_all_subj/
├── sub-001/
│   ├── label/
│   ├── mri/
│   ├── scripts/
│   ├── stats/
│   └── surf/
└── sub-002/
    └── ...
```

Folder names do not have to start with `sub-`. A child directory is recognized by FreeSurfer signatures such as `stats/aseg.stats`, `surf/lh.white`, or `scripts/recon-all.log`. For nested layouts, add `--recursive`. Duplicate folder names in a recursive search are rejected because they would create ambiguous output IDs.

Useful options:

```bash
# First ten sorted subjects for a smoke test
fsharvest INPUT OUTPUT --jobs 4 --limit 10

# Recompute cached projections and statistics
fsharvest INPUT OUTPUT --jobs 8 --overwrite

# Select additional atlases (the default is dk68 only)
fsharvest INPUT OUTPUT --atlases dk68 destrieux schaefer400 schaefer1000 glasser360 economo vosdewael300

# Also render four-view PNGs for selected atlases
fsharvest INPUT OUTPUT --qc-plots --qc-atlases dk68 schaefer100

# Explicitly export validated external annotations/stats into each FreeSurfer subject
fsharvest INPUT OUTPUT --atlases dk68 schaefer100 --export-to-freesurfer
```

`--freesurfer-home /path/to/freesurfer` initializes that installation when FreeSurfer is not already on `PATH`. Cached outputs are reused only when the cache schema, non-downgrade tool version, source files, atlas assets, FreeSurfer runtime/template, successful status, TSV schemas, semantic checks, and recorded output checksums all match. External annotations are structurally parsed, checked against the pinned region schema and surface vertex count, and protected together with their statistics by per-artifact SHA-256 records. `PARTIAL`, `FAILED`, and damaged cached subjects are retried automatically; `--overwrite` ignores private caches and reusable subject annotations, forcing fresh projection and statistics generation.

Without `--atlases`, FSHarvest extracts only `dk68`. Every other atlas is opt-in so routine runs remain fast and produce compact tables.

## Slurm/VACC

The supplied Slurm wrapper requests 12 CPUs and runs 12 subjects concurrently inside one job:

```bash
export FREESURFER_HOME=/path/to/freesurfer
bash ./submit_slurm.sh /path/to/dir_to_all_subj /path/to/output
```

Additional arguments are forwarded to FSHarvest, for example
`bash ./submit_slurm.sh INPUT OUTPUT --atlases dk68 schaefer100 --limit 10`.

Adjust time, memory, CPUs, account, and partition in `slurm/extract.sbatch` for the local cluster. Direct execution with `run_extract.sh` is preferable inside an existing allocation.

## Atlas definitions

`dk308` is the **NSPN500 / `500.aparc`** cortical atlas: 308 contiguous regions constrained within Desikan-Killiany boundaries, with each parcel designed to be no larger than approximately 500 mm². The `500` in its upstream name is a target parcel area, not a parcel count. The package deliberately has no `dk300` alias, to prevent confusing DK308 with unrelated 300-parcel atlases.

Schaefer 100/200/300/400/500/600/700/800/900/1000 use Yeo 7-network names. All ten bundled representations come from one pinned micapipe revision and are defined on `fsaverage5`. CBIG remains the methodological reference for projection to an individual FreeSurfer subject.

`glasser360`, `economo`, and `vosdewael300` are also pinned micapipe `fsaverage5` annotations. Glasser360 is the 360-area HCP-MMP1.0 multimodal atlas; Economo is the 86-region MRI implementation of the von Economo-Koskinas cytoarchitectonic atlas; Vos de Wael 300 is an anatomical 300-region subdivision constrained by Desikan-Killiany boundaries and is not an alias for Schaefer300 or DK308.

There are two deliberately separate extraction paths:

1. **FreeSurfer built-ins:** `dk68` reads `stats/{lh,rh}.aparc.stats`; `destrieux` reads `stats/{lh,rh}.aparc.a2009s.stats`. QC reads their existing files under `label/`. FSHarvest does not project, copy, rebuild, or save a second subject-level annotation for either atlas.
2. **External atlases:** `mri_surf2surf --sval-annot` maps the bundled `fsaverage` or `fsaverage5` annotation to the subject using `sphere.reg`, following the CBIG project-to-individual workflow. `mris_anatomical_stats` then calculates parcel statistics on native white/pial/thickness surfaces. Generated annotations and stats are kept under `OUTPUT/per_subject/`; they are copied into the input reconstruction only when `--export-to-freesurfer` is explicitly selected.
3. For both paths, background/medial-wall rows are excluded where applicable. Expected parcel totals and pinned region-name sets are validated independently for every subject, atlas, and hemisphere.

No MNI-volume atlas, smoothing, `mri_aparc2aseg`, or re-running of `recon-all` is involved.

See [`atlases/README.md`](atlases/README.md) for pinned upstream revisions, source URLs, licenses, checksums, and re-download instructions.

## Outputs

```text
OUTPUT/
├── subjects.tsv                 # one row per discovered subject; status/QC/provenance
├── cortical_long.tsv            # canonical cortical table
├── aseg_long.tsv                # all aseg structure rows
├── global_measures_long.tsv     # all aseg global measures
├── all_features_wide.tsv        # one row per subject, all feature families
├── atlas_manifest.tsv           # atlas definitions and completeness counts
├── run_metadata.json
├── all_qc.html                   # portable cohort-level QC gallery
├── wide/
│   ├── dk68.tsv
│   └── ATLAS.tsv                # one file for every selected optional atlas
└── per_subject/FOLDER_ID/
    ├── label/                    # projected external annotations; absent for built-ins only
    ├── stats/                    # external-atlas anatomical stats; absent for built-ins only
    ├── cortical.tsv
    ├── aseg.tsv
    ├── global.tsv
    ├── qc/ATLAS_inflated_4view.png
    ├── qc/ATLAS_inflated_4view.png.json  # current-input/run sidecar
    ├── extract.log
    └── status.json
```

`cortical_long.tsv` is the source of truth. Atlas-specific wide files use existing-project-compatible fields such as `L_bankssts_thickavg`. `all_features_wide.tsv` prefixes these with the atlas key, for example `dk68__L_bankssts_thickavg`, so atlas names cannot collide.

The process returns exit code 0 only when every selected subject passes atlas region-set, ROI-count, `aseg`, serialized-output, and optional requested QC/export checks. Partial results are retained under `per_subject/` and reported in `subjects.tsv` with `PARTIAL` status and an error string; trusted cohort feature tables include only current-run subjects whose extraction status is `OK` and whose serialized outputs and external artifacts pass revalidation. Every run has a unique `run_id`.

The long and wide tables are aggregated as streams, keeping only one subject's feature row in memory. `all_features_wide.tsv` can still be large on disk, but the complete cohort matrix is no longer retained in RAM.

## Surface QC PNGs

`--qc-plots` creates one compact horizontal PNG per requested atlas containing left lateral, left medial, right lateral, and right medial views. White margins are cropped before the views are joined. The default uses the inflated surface; `--qc-surface pial` and `--qc-surface white` are also available. Rendering is headless and works on compute nodes without an X server. Use `--qc-atlases` to limit runtime and storage for large cohorts.

`all_qc.html` is regenerated at the end of every run. It scans all existing four-view images and creates one tab per atlas; each tab shows every subject in a compact grid and retains subject-ID filtering. Missing images are called out explicitly. All image URLs are relative to the HTML file, so the complete output directory can be moved or archived without breaking the gallery. Open an image to inspect it at full resolution.

These images detect gross projection or reconstruction problems; they do not replace interactive inspection of white/pial boundaries in Freeview.

For `dk68` and `destrieux`, the normal FreeSurfer subject outputs are already the final inputs: no extra subject-level `.annot` is needed or created. For external atlases, FSHarvest may reuse a subject annotation only after validating its structure, regions, and vertex count against the current surface. Subject-level `.stats` files are not trusted without controlled provenance and are recalculated by default. Generated annotation and statistics are saved under `OUTPUT/per_subject/SUBJECT/` with content hashes and reused automatically on later runs after full validation. An older output-cache `annotations/` directory is imported into the canonical `label/` directory without deleting the old files.

## Optional export to FreeSurfer subjects

`--export-to-freesurfer` is off by default because it writes into the input reconstruction. When enabled, FSHarvest first completes extraction and validates the expected ROI count for every requested external atlas and hemisphere. It then copies the normalized files to:

```text
SUBJECTS_DIR/SUBJECT/label/{lh,rh}.ATLAS.annot
SUBJECTS_DIR/SUBJECT/stats/{lh,rh}.ATLAS.stats
```

Built-in DK68 and Destrieux files are not duplicated. Existing byte-identical destinations are accepted, which makes repeated exports idempotent. Any different existing destination is treated as a conflict: FSHarvest reports the subject as an export failure and does not replace the file. `--overwrite` applies only to the private output cache and never authorizes overwriting a FreeSurfer subject. Per-subject `status.json`, cohort `subjects.tsv`, and `run_metadata.json` record export status and counts.

## Euler number

FreeSurfer records pre-topology-fix left and right surface-hole counts in `aseg.stats`. Per hemisphere, the Euler characteristic is:

```text
Euler = 2 - 2 × SurfaceHoles
```

The package outputs `lh_euler`, `rh_euler`, and `euler_sum`. More negative values indicate more topological defects; thresholds should be defined within the study/site and FreeSurfer version rather than treated as universal constants.

## Reproducibility notes

- Do not mix FreeSurfer reconstruction versions without recording and modeling version effects. `fs_version` describes the reconstruction; `run_metadata.json` separately records the FreeSurfer executable used for extraction.
- The external stats command deliberately follows the standard FreeSurfer `-th3 -mgz -cortex ... white` form used by FreeSurfer 7.x outputs.
- External annotations use FreeSurfer's default `mri_surf2surf` mapping method from their declared source template. Schaefer, Glasser, Economo, and Vos de Wael use micapipe's `fsaverage5` files; DK308 uses `fsaverage`.
- `run_metadata.json` records the run ID, input/output roots, atlas and source-file SHA-256 values, pinned region-set hashes, runtime/template fingerprints, options, and timestamps. Per-subject cache fingerprints use file size and nanosecond modification time for large FreeSurfer inputs and SHA-256 for bundled atlas assets. Cached TSV files are independently protected by SHA-256 and semantic revalidation.
- Inspect surface reconstruction quality before interpreting any atlas. Automated ROI counts do not replace visual QC.
- Parse/join regions by atlas, hemisphere, and the `region` field. Never assume row order is stable across unrelated atlases.

## Citation and licenses

FSHarvest source code is MIT-licensed. Bundled atlas files keep their upstream licenses; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`atlases/README.md`](atlases/README.md). Research users should also cite the relevant atlas publications. Machine-readable software citation metadata is provided in [`CITATION.cff`](CITATION.cff).

Output tables, status files, run metadata, logs, and QC HTML can contain subject identifiers and absolute local paths. Treat the output directory as restricted data and review/de-identify it before sharing or publishing.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs the unit and CLI integration suite on Python 3.9–3.12 together with coverage, Ruff, mypy, Bash syntax, and ShellCheck gates.

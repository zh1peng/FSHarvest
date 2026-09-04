# Validation report — FSHarvest 1.0.0rc1

Date: 2026-09-04

## 1.0.0rc1 remediation verification

This verification used the current uncommitted remediation working tree based on commit
`43e8760223b036c9cd4de513ef6d2e5a711e2b23`. It is evidence for the candidate changes,
not a release-commit attestation. The tested source hashes were:

- `fs_extract_all.py`: `83e109f8990349a5390ae7acd9a7ef0f17f9c6b43f25609b6549da58cc47f5b4`
- `fs_render_qc.py`: `39763fd0bfbf5aed4a39bf646c800b03c345a67979ea69aa84a1c3f68c23b31d`

On `linux212`, all 40 tests passed. Bash syntax checks and a staged immutable-prefix install,
`--check`, and `--uninstall` passed. Ruff and mypy passed locally; those modules were not
installed in the remote system Python. ShellCheck passed on `linux212` using the
`koalaman/shellcheck:stable` container image.

A real cold run used FreeSurfer 7.4.1 and the lexically first CHCP_FS72 subject with DK68,
Schaefer100, and 100-DPI QC. It completed `OK` in 41.88 seconds with 856,608 KiB maximum
RSS and created two fingerprinted QC images. An unchanged extraction rerun completed in
0.76 seconds with 67,704 KiB maximum RSS and reported `cache_hit=1`. Running without QC
did not include the old PNGs in the new HTML. No `work/` links or output lock remained.
After a cached cortical value was altered, the next run rejected and repaired the cache.

Independent numeric comparisons passed with zero observed difference at the serialized
precision: 34 left-hemisphere DK thickness values against `aparcstats2table`, 45 aseg
volumes shared with `asegstats2table`, and all nine fields of 100 Schaefer rows generated
by a separate `mris_anatomical_stats` invocation.

## Environment

- Host: Linux x86_64 (`linux212`)
- Runtime: FreeSurfer 7.4.1 (`freesurfer-linux-ubuntu22_x86_64-7.4.1-20230614-7eb8460`)
- Input reconstructions: FreeSurfer 7.2.0
- Dataset root: `/media/NAS/MRIdata/CHCP_FS72`
- Subjects: the first 10 lexically sorted subject directories (`sub-3001_T1w_cropped` through `sub-3010_T1w_cropped`)

## Checks performed

- Python unit/integration tests: 19 passed locally and on `linux212`.
- Ruff and mypy: passed.
- Bash syntax checks for launch, install, download, and Slurm scripts: passed.
- Standalone-prefix installation and bundled atlas availability: passed.
- All 28 bundled annotation SHA-256 values matched `atlases/manifest.json`; the pinned download script reproduced and reverified them. This includes both hemispheres of micapipe's `fsaverage5` Schaefer 100–1000 files.
- The command default was verified to select only DK68; all other atlases require explicit `--atlases` selection.
- A dedicated built-in-atlas test verified that DK68 reads the existing `aparc.stats` files without invoking `mri_surf2surf` or `mris_anatomical_stats` and without creating output annotation/stat directories.
- Real extraction with all six atlases and four concurrent subjects: 10/10 subjects `OK`.
- Cortical output: 11,240 rows; all 60 subject-atlas combinations complete and unique.
- Expected rows per hemisphere were observed for every subject: DK68 34/34, Destrieux 74/74, DK308 152/156, Schaefer100 50/50, Schaefer200 100/100, and Schaefer300 150/150.
- All nine cortical measurements parsed as finite numbers.
- `all_features_wide.tsv`: 10 subjects and 10,190 columns.
- Cold extraction: 531.27 seconds; maximum reported RSS 617,896 KiB.
- Valid-cache rerun including streamed aggregation: 0.87 seconds; maximum reported RSS 31,420 KiB.
- Real extraction of DK68 plus the four newly added atlases (`schaefer400`, `glasser360`, `economo`, and `vosdewael300`) with four concurrent subjects: 10/10 subjects `OK`; 4:36.93 elapsed and maximum reported RSS 617,696 KiB.
- New-atlas cortical output: 12,140 unique rows. Every subject was complete with Schaefer400 200/200, Glasser360 180/180, Economo 43/43, and Vos de Wael 300 150/150 rows per hemisphere.
- The new-atlas run contained no non-finite cortical measurements; `all_features_wide.tsv` contained 10 subjects and 11,000 columns.
- All four new atlases rendered successfully as compact four-view PNGs for a real subject at 100 DPI; 52.68 seconds total and maximum reported RSS 912,428 KiB in the single sequential renderer process.
- Headless integrated DK68 four-view rendering: passed; the compact PNG was 949×150 pixels (84,258 bytes), with 13.81 seconds elapsed and maximum reported RSS 791,852 KiB at 100 DPI on a warm filesystem cache.
- Historical baseline only: subject-level external annotation/statistics reuse was tested in the pre-remediation code. In 1.0.0rc1, only fully validated annotations may be reused; subject-level statistics without controlled FSHarvest provenance are recalculated.
- Output annotations now use `per_subject/SUBJECT/label/`; legacy `annotations/` caches are imported without deleting the old files.
- `--export-to-freesurfer` is disabled by default. Unit coverage verifies validated annotation/stat export, idempotent repeat export, and refusal to overwrite a conflicting subject file.
- Real Schaefer100 validation used a writable `/tmp` wrapper around `sub-3001_T1w_cropped`; the NAS reconstruction remained untouched. The default cold run wrote annotations to `OUTPUT/per_subject/SUBJECT/label/` and completed in 14.42 seconds with 555,024 KiB maximum RSS.
- Enabling `--export-to-freesurfer` copied four files (left/right annotation and stats) into the temporary subject in 0.14 seconds with 23,296 KiB maximum RSS. Source/output SHA-256 values matched; an immediate repeated export reported `0 new, 4 existing` and did not overwrite them.
- A fresh-prefix `install.sh` installation of the pre-release baseline exposed the export option in `--help` and retained the bundled atlas manifest.
- A pre-release run over the first 10 CHCP subjects with DK68, Schaefer400, Glasser360, Economo, and Vos de Wael 300 completed 10/10 `OK` in 267 seconds. It produced 12,140 cortical rows with exact atlas totals (680, 4,000, 3,600, 860, and 3,000 respectively) and 80 external annotations under the new per-subject `label/` directories. The 80 legacy `annotations/` files remained untouched, export was false, and no normalized external-atlas files appeared in the NAS subjects.
- Real Schaefer100 extraction on one subject: cold run 17.54 seconds; unchanged rerun 0.47 seconds and 22,528 KiB maximum RSS, with no second extraction recorded.
- `all_qc.html`: relative image paths verified, no absolute output path embedded, and atlas tabs/tab-local subject filtering verified in a browser.
- Current-source Schaefer 100–1000 extraction (micapipe `fsaverage5` annotations, CBIG projection procedure) with four concurrent subjects: 10/10 subjects `OK`; 12:56.96 elapsed and maximum reported RSS 617,772 KiB.
- Current-source Schaefer output contained exactly 55,000 unique cortical rows. Every scale had exactly `N/2` rows per hemisphere per subject, all nine cortical measurements were finite, and `all_features_wide.tsv` contained 49,574 columns.
- Integrated Schaefer1000 extraction plus compact 100-DPI four-view QC passed on a real subject. The PNG was 1423×224 pixels (167,664 bytes), `all_qc.html` used a relative image URL, and the process peaked at 805,632 KiB RSS.

## Interpretation and limits

This validates extraction and rendering for the environment above. It is not evidence of compatibility with every FreeSurfer release. In particular, FreeSurfer 8.x must be tested separately before being added to the supported runtime matrix. Four-view rendering is intentionally optional because full-resolution surface rendering requires substantially more memory than extraction or aggregation.

## 1.0.0rc1 regression checks

The 1.0.0rc1 release candidate separates tool/cache/output versions, rejects downgrade cache reuse, validates `aseg.stats` headers, disables unproven subject-level stats reuse, locks each output directory, removes temporary subject links, and fingerprints current-run QC images. The local regression suite contains 40 tests and passes with Ruff and mypy on Python 3.12. The verification above must be repeated on the final committed source before the 1.0.0 release tag; it does not claim that an uncommitted working tree is a stable release.

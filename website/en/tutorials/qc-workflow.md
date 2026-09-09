# Reviewing QC images

This tutorial generates quality-control (QC) images for ten subjects using DK68 and Schaefer100, then explains how to inspect unusual results.

## 1. Generate images for a small sample

```bash
export SUBJECTS_ROOT=/data/study/freesurfer
export OUTPUT_QC_TEST=/data/derived/fsharvest-qc-test

fsharvest "$SUBJECTS_ROOT" "$OUTPUT_QC_TEST" \
  --jobs 4 \
  --limit 10 \
  --atlases dk68 schaefer100 \
  --qc-plots \
  --qc-atlases dk68 schaefer100 \
  --qc-surface inflated \
  --qc-dpi 100
```

Use a separate `OUTPUT_QC_TEST`, apart from the output containing the full dataset's results.
FSHarvest rewrites `subjects.tsv`, long tables, and wide tables for these ten subjects. `--limit 10` does not merely append images.

After each subject completes successfully, the terminal reports the number of PNGs:

```text
[QC 1/10] example-01: 2 PNGs
```

## 2. Open the QC overview

```bash
xdg-open "$OUTPUT_QC_TEST/all_qc.html"
```

Switch between atlases and search by subject ID. Browse images from several subjects, then focus on results that look markedly different.

![Actual all_qc.html report](/examples/qc-report-example.png)

## 3. Inspect individual images and logs

```text
$OUTPUT_QC_TEST/per_subject/FOLDER_ID/qc/ATLAS_inflated_4view.png
$OUTPUT_QC_TEST/per_subject/FOLDER_ID/qc/ATLAS_inflated_4view.png.json
$OUTPUT_QC_TEST/per_subject/FOLDER_ID/extract.log
$OUTPUT_QC_TEST/per_subject/FOLDER_ID/status.json
```

The PNG's `.json` records the input surfaces, annotations, DPI, and run ID, helping establish whether the image matches the current inputs and run.

## 4. Address the problem

- No image generated: check QC dependencies, `qc_status`, and logs.
- Unexpected parcellation coverage: check `.annot`, `sphere.reg`, and FreeSurfer versions.
- Suspicious white/pial boundaries: inspect them further in Freeview.
- Higher image resolution needed: increase `--qc-dpi`; the extraction measures do not need to be redefined.

::: info Reserve enough memory
Generating surface images usually needs more memory than extracting tables. For large datasets, generate images only for
the necessary atlases, or test a small sample with `--limit` first.
:::

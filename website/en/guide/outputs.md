<script setup>
import subjects from '../../public/examples/v1.0.4/dk68-subjects.tsv?raw'
import cortical from '../../public/examples/v1.0.4/dk68-cortical_long.tsv?raw'
import wide from '../../public/examples/v1.0.4/dk68-all_features_wide.tsv?raw'
</script>

# Outputs and data tables

FSHarvest produces long-format and wide-format tables, per-subject caches, and run records.
The example data below come from **1.0.4** runs on the first ten subjects on `linux212` on 2026-09-09.
Subject names and paths have been replaced for publication. See the [commands and full records](../tutorials/ten-subject-example).

## Output directory

The DK68-only quick start, without QC images, produces this structure:

```text
OUTPUT/
├── subjects.tsv
├── cortical_long.tsv
├── aseg_long.tsv
├── global_measures_long.tsv
├── all_features_wide.tsv
├── atlas_manifest.tsv
├── region_differences.tsv
├── run_metadata.json
├── logs/
│   ├── run_20260909T011641_543148Z_74b3105e.log  # First run
│   └── run_20260909T011724_394267Z_0da06c7f.log  # Cache reuse
├── all_qc.html                 # No images rendered; explains QC status only
├── wide/
│   └── dk68.tsv
└── per_subject/example-01/
    ├── cortical.tsv
    ├── aseg.tsv
    ├── global.tsv
    ├── extract.log
    └── status.json
```

Directories for the other nine subjects are omitted. External atlases also create `label/` and `stats/` directories under
`per_subject/`. `qc/*.png` files and companion JSON records are generated only when QC is explicitly enabled.
When fewer atlases are selected, old wide tables may be archived to `archive/RUN_ID/wide/`.

External-atlas processing creates a uniquely named `.fsharvest-work-*` temporary directory. It and its symlinks are
removed after success, failure, or interruption. The program does not delete a pre-existing `work/` or other directory in the output location.

## Summary files for all selected subjects

| File | Contents |
| --- | --- |
| `subjects.tsv` | Overall status, FreeSurfer version, Euler numbers, row counts, and errors for each subject |
| `cortical_long.tsv` | All cortical regions and nine cortical measures for selected atlases; recommended for region-level analysis |
| `aseg_long.tsv` | Volume and other original fields for every structure in `aseg.stats` |
| `global_measures_long.tsv` | `# Measure` records such as eTIV, BrainSegVol, and surface holes |
| `wide/ATLAS.tsv` | One wide table per atlas, with one row per subject |
| `all_features_wide.tsv` | Nine cortical measures for selected atlases, aseg structure volumes, and global measures; other non-volume aseg columns are not copied |
| `atlas_manifest.tsv` | Atlas definitions, annot paths, expected left/right region counts, and complete-subject counts; bundled atlases also record region-name SHA-256 checksums |
| `region_differences.tsv` | Names missing from the atlas definition, unexpected names, and names observed in other subjects but absent from a given subject |
| `run_metadata.json` | Run ID, times, parameters, software versions, atlas checksums, and input fingerprints |
| `logs/run_*.log` | Banner, environment setup, progress, errors, and exit code for each separate invocation |

## Actual results for ten subjects

In the default DK68 example, `subjects.tsv` has 10 rows and 30 columns, all with `OK` status. Each subject has 68 cortical
rows and 45 aseg rows: 680 cortical, 450 aseg, and 200 global-measure rows in total. `all_features_wide.tsv` has
10 rows × 687 columns; `wide/dk68.tsv` has 10 rows × 622 columns. Row counts exclude headers. Aseg and global-measure counts depend on the inputs.

The status data below come from the second invocation of the same command, hence `cache_hit=1`.
Empty `qc_status` means QC was not enabled; it does not mean QC passed. [Download status example TSV](/examples/v1.0.4/dk68-subjects.tsv).

<ExampleTable :tsv="subjects" caption="DK68: ten subjects' processing status (7 fields)" download="/examples/v1.0.4/dk68-subjects.tsv" />

## cortical_long.tsv example

The table shows selected fields from the first three rows. Search for a region name or click a column heading to sort:

<ExampleTable :tsv="cortical" caption="Cortical long table: first 3 rows, 8 fields" download="/examples/v1.0.4/dk68-cortical_long.tsv" />

These values come directly from the extraction results. [Download the example data](/examples/v1.0.4/dk68-cortical_long.tsv).

`folder_id` is the input subject-directory name and must be unique within a run. `subject_id` comes from the FreeSurfer
statistics-file header and may repeat across directories or scans.

Join subject-level regional result tables using `folder_id`, `atlas`, `hemisphere`, and `region` together, and verify
that the combination is unique in each table. Use only `atlas`, `hemisphere`, and `region` when joining a region-description
table without a subject dimension. For repeated scans, `folder_id` must uniquely identify the scan; a participant ID alone is insufficient.

## Wide-table column names

Selected values for the first three subjects are shown below:

<ExampleTable :tsv="wide" caption="Combined wide table: first 3 subjects, 5 fields" download="/examples/v1.0.4/dk68-all_features_wide.tsv" />

[Download the wide-table example](/examples/v1.0.4/dk68-all_features_wide.tsv). `thickavg` is in mm; hippocampal volume here is in mm³.

An individual atlas wide table combines hemisphere, region, and measure in each column name:

```text
L_bankssts_thickavg
R_bankssts_thickavg
```

`all_features_wide.tsv` adds an atlas prefix to avoid collisions between parcellations:

```text
dk68__L_bankssts_thickavg
schaefer100__L_7Networks_LH_Vis_1_thickavg
aseg__Left-Hippocampus__volume_mm3
global__eTIV
```

## Which results enter the summary tables? {#aggregation}

`subjects.tsv`, long and wide tables, the atlas manifest, and run metadata always describe the subjects and atlases selected
by the **current command**. They are not automatically appended to historical results. After processing all subjects,
running `--limit 10` in the same output directory rewrites those summaries for just ten subjects. Per-subject caches may remain available for later reuse.

Aggregation retains successfully parsed data with unambiguous identifiers, including data from subjects with `PARTIAL`
or `FAILED` status. Long and wide tables carry `status` and `errors`. Inclusion does not mean reconstruction, atlas checks,
or QC passed. `NOT_RUN` subjects and data left by other runs are excluded from the current summary. Non-OK statuses still result in a nonzero exit code.

Original region names are preserved. Wide columns are built from the union of names in retained records, and missing values
remain empty. They are not replaced with zero, and `&` and `_and_` are not automatically merged. `region_differences.tsv`
stores JSON name lists in `missing_expected`, `unexpected_names`, and `absent_from_subject` (seen in other subjects but absent
from this one). `reference` indicates whether an atlas definition is available for comparison. Different names do not
necessarily identify different anatomical regions. Expected regions absent from every subject appear only in the differences report; no empty wide columns are invented for them.

Damaged or missing files, checksum mismatches, and unparseable headers exclude only the affected subject file. Malformed rows,
invalid numbers, and duplicate keys exclude the affected records. All records sharing an ambiguous duplicate key are excluded;
one is not arbitrarily selected to overwrite another. Aseg segmentation IDs and structure names, and global measure/metric
pairs, are checked for ambiguity. Other files, regions, and subjects continue to be aggregated. Reasons are recorded in `errors`,
and original per-subject TSVs are not rewritten.

`subjects.tsv` currently records overall subject status, not a separate subject × atlas status table. For multi-atlas failures,
use `errors`, each subject's `status.json`, and `extract.log` to locate the atlas and hemisphere.

When fewer atlases are selected, FSHarvest checks SHA-256 records from the preceding run before moving deselected wide tables
from `wide/` to `archive/PREVIOUS_RUN_ID/wide/`. Modified tables or tables without generation records are not moved automatically.
The program stops and asks you to move the file manually, preventing an unverified table from being mistaken for current results.

::: info Multiple atlases can produce very wide tables
Temporary TSVs, cleaned up after the run, ensure that long and wide tables use the same records without loading the entire
subject-by-feature matrix into memory. Reserve disk space for temporary tables; multiple high-resolution atlases can still produce tens of thousands of output columns.
:::

::: warning Review before sharing
Tables, status files, metadata, logs, and QC HTML may contain subject identifiers and absolute local paths.
Treat the output directory as restricted data and review and de-identify it before sharing or publication.
:::

<script setup>
import subjects from '../../public/examples/v1.0.4/six-atlas-subjects.tsv?raw'
</script>

# Ten-subject worked example

This page brings together runnable commands, terminal output, and result tables. The example was run on **2026-09-09**
on **linux212**, using the official **FSHarvest 1.0.4** release and the first ten discovered subjects in directory-name order.
Public examples replace subject names with `example-01` through `example-10` and private paths with example paths.
Actual values, times, and parallel completion order are preserved.

| Item | Setting |
| --- | --- |
| Extraction environment | Linux; FreeSurfer 7.4.1 |
| Input reconstruction version | FreeSurfer 7.2.0 |
| Subjects / parallel workers | 10 / 5 |
| DK68 extraction | First run and cache reuse |
| Six-atlas extraction | DK68, DK308, Destrieux, Schaefer100/200/300 |
| QC / export to FreeSurfer | Both disabled |

The two examples use separate output directories. DK68 reads existing statistics; the six-atlas example also performs
external-atlas projection and statistics computation. Runtime depends on hardware, filesystems, and caches; these timings are not a performance guarantee.

## DK68: from command to run log

The [quick start](../guide/quick-start) provides matching CLI and SH options. No extra logging wrapper is needed:

```bash
fsharvest /data/study/freesurfer /data/derived/fsharvest-dk68-example \
  --freesurfer-home /usr/local/freesurfer/7.4.1 \
  --atlases dk68 --jobs 5 --limit 10
```

The first run processed ten subjects, all `OK`, and produced 680 cortical rows. Its run log was saved automatically.

::: details Complete terminal output from the first run
<<< @/public/examples/v1.0.4/dk68-run.log{text}
:::

Repeating the same command immediately reused the cache for all ten subjects, with `(cached)` in progress lines:

::: details Second run: cache hits and a separate run log
<<< @/public/examples/v1.0.4/dk68-cached-run.log{text}
:::

`[completed/total]` is a completion count; the following subject name identifies the subject. With parallel workers,
`example-02` may finish before `example-01`, without affecting aggregation by region name.
Even with cache hits, summary tables are rewritten for the current selection.

## Six-atlas run including DK308 {#six-atlas}

The CLI and SH options below perform the same task. Edit the paths before running. The SH version is also
<a href="/FSHarvest/examples/run_fsharvest_multi_atlas.sh" download>available to download</a>.

::: code-group

```bash [CLI: six atlases]
fsharvest /data/study/freesurfer /data/derived/fsharvest-six-atlas-example \
  --freesurfer-home /usr/local/freesurfer/7.4.1 \
  --atlases dk68 dk308 destrieux schaefer100 schaefer200 schaefer300 \
  --jobs 5 --limit 10
```

<<< @/public/examples/run_fsharvest_multi_atlas.sh{bash} [SH: run_fsharvest_multi_atlas.sh]

:::

Save the script, edit its paths, and run:

```bash
bash run_fsharvest_multi_atlas.sh
```

External-atlas projection and statistics happen before each subject completes, so several minutes may pass between
`[EXTRACT]` and the first `[1/10]`. Inspect the run log shown in the terminal or the subject's `extract.log` for individual commands.

## Actual six-atlas results

The six-atlas run finished with **10/10 `OK`**, exit code **0**, and a `[DONE]` elapsed time of **00:19:37**.
This was measured under the host's load at the time and includes actual projection, statistics, and aggregation; it is not an estimate.

::: details Complete six-atlas run log
<<< @/public/examples/v1.0.4/six-atlas-run.log{text}
:::

### How many regions were extracted per atlas?

These counts come directly from `atlas_manifest.tsv`. Left/right counts are the expected statistical rows in each atlas definition.

| Atlas | Left | Right | Total per subject | Complete subjects |
| --- | ---: | ---: | ---: | ---: |
| `dk68` | 34 | 34 | 68 | 10/10 |
| `dk308` | 152 | 156 | 308 | 10/10 |
| `destrieux` | 74 | 74 | 148 | 10/10 |
| `schaefer100` | 50 | 50 | 100 | 10/10 |
| `schaefer200` | 100 | 100 | 200 | 10/10 |
| `schaefer300` | 150 | 150 | 300 | 10/10 |

The bundled DK308 has 152 valid statistical regions on the left and 156 on the right, totaling 308; it does not require 154 per hemisphere.
The six atlases contain 1,124 cortical regions per subject, producing 11,240 rows for ten subjects.

### Which files grow compared with DK68 alone?

The dimensions below are measured from the files and exclude header rows. Adding cortical atlases does not duplicate
aseg or global measures six times; each subject retains one set.

| File | DK68 | Six atlases |
| --- | ---: | ---: |
| `subjects.tsv` | 10 × 30 | 10 × 30 |
| `cortical_long.tsv` | 680 × 18 | 11,240 × 18 |
| `aseg_long.tsv` | 450 × 16 | 450 × 16 |
| `global_measures_long.tsv` | 200 × 11 | 200 × 11 |
| `all_features_wide.tsv` | 10 × 687 | 10 × 10,191 |
| `region_differences.tsv` | 0 × 7 | 0 × 7 |

Both name-differences reports contain only headers. Each atlas wide table has ten rows. The six-atlas run's `wide/` directory
contains `dk68.tsv`, `dk308.tsv`, `destrieux.tsv`, `schaefer100.tsv`, `schaefer200.tsv`, and `schaefer300.tsv`.
No QC PNGs were generated; `all_qc.html` states that no QC images are available.

### Status of the first ten subjects

These selected fields are from the first six-atlas run: `cache_hit=0`. `qc_status` is empty because QC was not enabled.

<ExampleTable :tsv="subjects" caption="Six atlases: ten subjects' processing status (7 fields)" download="/examples/v1.0.4/six-atlas-subjects.tsv" />

The original `subjects.tsv` also contains `subject_id`, paths, Euler numbers, errors, and runtime versions.
See [Outputs and data tables](../guide/outputs) for actual long/wide values and field definitions.

## Download scripts, logs, and example data

These files come from the real runs above. TSVs contain selected rows and fields; JSON files summarize run details and
result counts. They do not replace the complete original outputs. Subject names and private paths were replaced;
input images and identity mappings are not published.

| File | Purpose |
| --- | --- |
| <a href="/FSHarvest/examples/run_fsharvest_example.sh" download>DK68 SH script</a> | Edit paths and process the first ten subjects |
| <a href="/FSHarvest/examples/run_fsharvest_multi_atlas.sh" download>Six-atlas SH script</a> | Includes DK308; no QC |
| <a href="/FSHarvest/examples/v1.0.4/dk68-run.log" download>First DK68 log</a> / <a href="/FSHarvest/examples/v1.0.4/dk68-cached-run.log" download>Cached-run log</a> | Compare startup, progress, cache reuse, and log filenames |
| <a href="/FSHarvest/examples/v1.0.4/six-atlas-run.log" download>Six-atlas log</a> | Actual completion order and elapsed time |
| [Six-atlas status example](/examples/v1.0.4/six-atlas-subjects.tsv) | Status, row counts, cache, and QC fields |
| [Six-atlas manifest example](/examples/v1.0.4/six-atlas-atlas_manifest.tsv) | Expected regions and completion counts per atlas |
| [DK68 run summary](/examples/v1.0.4/dk68-summary.json) / [Six-atlas run summary](/examples/v1.0.4/six-atlas-summary.json) | Versions, parameters, dimensions, and public-example provenance |

Determine success using the exit code, `subjects.tsv`, and error details together. If region names differ from expectations,
align by actual names, retain available data, and inspect the specific differences in `region_differences.tsv`.

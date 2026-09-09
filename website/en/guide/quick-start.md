# Five-minute quick start

This example uses a real **FSHarvest 1.0.4** run on the first ten subjects on linux212.
It reads DK68 with five parallel workers and generates no QC images. Complete the [installation](./installation)
and confirm that `fsharvest --version` reports 1.0.4 or later.

## 1. Copy a command or save a script

Edit the input, output, and FreeSurfer paths before running. The input directory should directly contain subject directories;
place the output outside it. Use the copy button at the top right of each code block. Both options perform the same extraction.

::: code-group

```bash [CLI: run in a terminal]
subjects_dir=/data/study/freesurfer
output_dir=/data/derived/fsharvest-dk68-example
freesurfer_home=/usr/local/freesurfer/7.4.1

fsharvest "$subjects_dir" "$output_dir" \
  --freesurfer-home "$freesurfer_home" \
  --atlases dk68 --jobs 5 --limit 10
```

<<< @/public/examples/run_fsharvest_example.sh{bash} [SH: run_fsharvest_example.sh]

:::

You can also <a href="/FSHarvest/examples/run_fsharvest_example.sh" download>download the same SH script</a>, edit its paths, and run:

```bash
bash run_fsharvest_example.sh
```

After substituting the paths, we ran this script on linux212: all ten subjects were `OK`.
Its three long tables and combined wide table were identical to the CLI outputs.

`--limit 10` selects the first ten discovered subjects in directory-name order. Parallel workers report progress in completion order.
`--atlases dk68` is explicit here; DK68 is also the default when omitted. You do not need to add `echo`, `tee`,
or FreeSurfer initialization to the script: FSHarvest prepares the environment, reports progress, and saves logs.

## 2. What you will see

This is the first run from 2026-09-09. Original subject names and private paths have been replaced with
`example-01` through `example-10` and example paths. Times, completion order, and status are unchanged.
The extraction runtime was FreeSurfer 7.4.1; input reconstructions were generated with 7.2.0.

::: details Full terminal output: banner, ten subjects, and summary
<<< @/public/examples/v1.0.4/dk68-run.log{text}
:::

The key results were:

```text
[DONE] Finished: 10 OK, 0 non-OK across all requested phases.
Table status: OK=10, PARTIAL=0, FAILED=0, NOT_RUN=0
Run exit code: 0
```

These lines are an excerpt; the timestamp before `[DONE]` is omitted. `[CHECK]` and `[PREPARE]` indicate input
and template checks. `[EXTRACT]` appears before the first subject finishes; `[1/10]` through `[10/10]` report completed
subjects. `[AGGREGATE]` means the summary tables are being written. `OK` is a processing status and does not replace manual review of reconstruction boundaries.

## 3. The run log is saved automatically

`Run log:` appears at the beginning and end of the terminal output. Each invocation creates a new log in the output directory,
containing the banner, environment setup, progress, errors, and exit code. Repeating a run does not overwrite its previous log.

```bash
# List logs from each run
ls -lt /data/derived/fsharvest-dk68-example/logs/

# Use the actual path printed after Run log: in your terminal
less /data/derived/fsharvest-dk68-example/logs/run_20260909T011641_543148Z_74b3105e.log
```

The filename above is from this example; your timestamp and suffix will differ.
Download the <a href="/FSHarvest/examples/v1.0.4/dk68-run.log" download>first-run log</a>
or <a href="/FSHarvest/examples/v1.0.4/dk68-cached-run.log" download>cached-run log</a> for comparison.
Detailed subject commands remain in `per_subject/FOLDER_ID/extract.log`.

## 4. Check the output tables

The ten-subject run produced:

| File | Data rows, excluding header | Columns |
| --- | ---: | ---: |
| `subjects.tsv` | 10 | 30 |
| `cortical_long.tsv` | 680 | 18 |
| `aseg_long.tsv` | 450 | 16 |
| `global_measures_long.tsv` | 200 | 11 |
| `wide/dk68.tsv` | 10 | 622 |
| `all_features_wide.tsv` | 10 | 687 |
| `region_differences.tsv` | 0 | 7 |

680 = 10 subjects × 68 DK regions. The differences report contains only its header, indicating that no name differences were reported.
These counts were measured on this dataset; aseg and global-measure counts may differ for other inputs.

```bash
column -t -s $'\t' /data/derived/fsharvest-dk68-example/subjects.tsv | less -S
```

For `PARTIAL` or `FAILED` status, inspect `errors` in `subjects.tsv`, each subject's `status.json`, and `extract.log`.
Successfully parsed measurements with unambiguous identifiers are still aggregated; missing regions have empty cells.
See [outputs and real example data](./outputs) and the [ten-subject worked example](../tutorials/ten-subject-example).

## 5. Repeat the run or process all subjects

Repeating the command from step 1 reused the cache for all ten subjects in this example, adding `(cached)` to progress lines.
Summary tables are still rewritten, and a separate run log is saved.

For the full dataset, use another output directory and remove `--limit 10`:

```bash
fsharvest /data/study/freesurfer /data/derived/fsharvest-dk68-full \
  --freesurfer-home /usr/local/freesurfer/7.4.1 \
  --atlases dk68 --jobs 5
```

Summary tables always represent the subjects and atlases selected for the current run. Running `--limit 10` again in
the full dataset's output directory rewrites the summaries to contain only those ten subjects. A separate trial directory avoids confusion.

For DK308, Destrieux, and Schaefer, see the [six-atlas CLI and SH example](../tutorials/ten-subject-example#six-atlas).

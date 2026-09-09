# Batch extraction of FreeSurfer measures

Start with ten subjects to check paths and the runtime environment, then process the full dataset.

## 1. Initialize FreeSurfer

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
source "$FREESURFER_HOME/SetUpFreeSurfer.sh"
```

Confirm that these commands are available:

```bash
command -v recon-all
command -v mri_surf2surf
command -v mris_anatomical_stats
```

Example output:

```text
/usr/local/freesurfer/7.4.1/bin/recon-all
/usr/local/freesurfer/7.4.1/bin/mri_surf2surf
/usr/local/freesurfer/7.4.1/bin/mris_anatomical_stats
```

## 2. Try DK68 on ten subjects

```bash
fsharvest /data/study/freesurfer \
  /data/derived/fsharvest \
  --jobs 4 \
  --limit 10
```

The final summary reports the number of `OK` and non-`OK` subjects. Timestamps are omitted here:

```text
[DONE] Finished: 10 OK, 0 non-OK across all requested phases.
Table status: OK=10, PARTIAL=0, FAILED=0, NOT_RUN=0
Run exit code: 0
```

The terminal also prints `Run log:` with the path of the log automatically saved by FSHarvest.
See the [full measured outputs, CLI commands, and SH scripts](./ten-subject-example) for the ten-subject 1.0.4 example.

## 3. Check status

```bash
cut -f1,2,7,17 /data/derived/fsharvest/subjects.tsv | column -t -s $'\t'
```

The following illustrates the error format; it is not the actual ten-subject result, where all subjects were `OK`:

| subject_id | folder_id | status | errors |
| --- | --- | --- | --- |
| example-01 | example-01 | OK | |
| example-02 | example-02 | PARTIAL | dk68/rh: missing standard FreeSurfer stats |

Ideally, every subject's `status` is `OK`. For `PARTIAL` or `FAILED`, inspect the corresponding `extract.log` and `status.json`.
Investigate failure reasons before using the combined wide table for analysis.

## 4. Process all subjects

Remove `--limit`:

```bash
fsharvest /data/study/freesurfer \
  /data/derived/fsharvest \
  --jobs 12
```

Caches from the first ten subjects are reused if they pass validation.

## 5. Choose a results table

- Region-level inspection or long-format analysis: `cortical_long.tsv`.
- Modeling with one row per subject: `all_features_wide.tsv`.
- All subcortical structure records: `aseg_long.tsv`.
- Global measures such as eTIV: `global_measures_long.tsv`.

::: tip Joining region-level results
Use `folder_id`, `atlas`, `hemisphere`, and `region` together, and confirm that the combined key is unique in both tables.
Omit `folder_id` only for region-description tables without a subject dimension. Do not join by row number or assume different atlases share an ordering.
:::

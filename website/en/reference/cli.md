# Command-line reference

```text
fsharvest SUBJECTS_DIR OUTPUT_DIR [options]
```

## Positional arguments

| Argument | Description |
| --- | --- |
| `SUBJECTS_DIR` | Input directory directly containing FreeSurfer subject directories; use `--recursive` to search nested directories |
| `OUTPUT_DIR` | Separate FSHarvest output directory; must not be inside the input directory |

## Execution options

| Option | Default | Description |
| --- | --- | --- |
| `--jobs N` | `min(8, CPU count)` | Concurrent subjects; a positive integer |
| `--limit N` | Unlimited | Process the first N subjects sorted by directory name; useful for small trials |
| `--recursive` | Off | Search recursively for FreeSurfer subject directories |
| `--overwrite` | Off | Ignore reusable caches and existing external-atlas files in subject directories; project and compute statistics again |
| `--force-unlock` | Off | Remove a stale output lock after confirming the recorded process on the same host has ended |
| `--freesurfer-home PATH` | `$FREESURFER_HOME` | FreeSurfer installation directory |
| `--atlas-dir PATH` | Repository `atlases/` | Bundled atlas-resource directory; custom annot paths are defined in JSON |

`--overwrite` does not overwrite input files. Only explicit `--export-to-freesurfer` attempts to copy files into the input directories.

## Parcellations

| Option | Default | Description |
| --- | --- | --- |
| `--atlases NAME_OR_JSON ...` | `dk68` | Built-in atlas names or custom atlas JSON paths; they may be mixed |
| `--export-to-freesurfer` | Off | Copy validated external-atlas `.annot` and statistics files into input subject directories; existing same-named files are not replaced |

Available atlas names:

```text
dk68 destrieux dk308
schaefer100 schaefer200 schaefer300 schaefer400 schaefer500
schaefer600 schaefer700 schaefer800 schaefer900 schaefer1000
glasser360 economo vosdewael300
```

Custom atlas example:

```bash
fsharvest INPUT OUTPUT --atlases dk68 /path/to/lab-atlas.json --qc-plots --qc-atlases lab
```

The JSON defines left/right `.annot` files, an atlas `key`, and a source template (`fsaverage5` or `fsaverage`).
`--qc-atlases` uses the JSON's `key`, not its path. See the [custom atlas tutorial](../tutorials/multi-atlas#custom-annot) for the full format.

## QC images

| Option | Default | Description |
| --- | --- | --- |
| `--qc-plots` | Off | Generate four-view PNGs for cortical atlases and update the HTML report |
| `--qc-atlases KEY ...` | All selected atlases | Render only the specified selected atlases |
| `--qc-surface` | `inflated` | Surface to render: `inflated`, `pial`, or `white` |
| `--qc-dpi N` | `150` | Image resolution; minimum 72 |

## Help and version

```bash
fsharvest --help
fsharvest --version
```

The current version reports:

```text
fsharvest 1.0.4
```

## Startup banner, progress, and logs

Normal runs automatically display an ASCII logo, version, developer `zh1peng`, license, and repository URL.
The installed `fsharvest` command shows the banner once, followed by FreeSurfer environment setup.
`--help` and `--version` remain concise: they show no banner and do not initialize FreeSurfer.

During a run, FSHarvest prints input/output paths, selected atlases, and worker count. Stage messages report checks,
subject discovery, extraction, optional export and QC, and aggregation. Each completed subject produces `[completed/total]`,
status, and cache-hit information. Progress includes timestamps and elapsed time and is flushed immediately for terminal
monitoring and batch logs. A starting-extraction message appears even before the first subject finishes; scripts do not need their own echo statements.

The final output includes the overall result across enabled phases, separate table-status counts, elapsed time, output directory,
and subject-log location. The QC report path appears only when QC is enabled. Partial results are retained with a nonzero
exit code and are not presented as complete success. Progress uses plain text without a color-terminal or extra Python-package dependency.

Standard output and errors are automatically saved together in `OUTPUT_DIR/logs/run_TIMESTAMP_UNIQUE_SUFFIX.log`.
The path appears at startup and completion. Each invocation gets its own log covering the banner, environment setup,
progress, errors, and exit code; per-subject `extract.log` files retain detailed command output.
The installed `fsharvest`, `run_extract.sh`, and direct `python fs_extract_all.py` entry points all save logs automatically,
so user scripts do not need `tee`. Help and version queries create no logs. Argument-parsing failures, input/output path
conflicts, or inability to create a log file are reported directly in the terminal.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All subjects are `OK` |
| `2` | Run completed, but at least one subject is `PARTIAL`, `FAILED`, or `NOT_RUN` |
| `1` | Argument, environment, or runtime-stage error |
| `130` | User interruption, such as `Ctrl+C` |

Automation should inspect both the exit code and `subjects.tsv`; the existence of a summary table alone does not establish success.

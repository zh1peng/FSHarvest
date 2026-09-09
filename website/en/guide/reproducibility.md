# Caching and run records

## Run logs and subject logs

Since 1.0.4, each invocation automatically saves `OUTPUT/logs/run_TIMESTAMP_UNIQUE_SUFFIX.log` while showing the same output
in the terminal. The log includes startup, environment setup, stage progress, errors, and the exit code. You do not need to add `tee`.
Help and version queries do not create logs.

`per_subject/FOLDER_ID/extract.log` records detailed FreeSurfer commands and output for each subject. Use the run log to monitor
overall progress and subject logs to inspect individual extraction steps. Errors occurring before argument parsing or log-directory creation may appear only in the terminal.

In the [ten-subject example](../tutorials/ten-subject-example), the same DK68 command ran twice and all ten subjects reused their
caches on the second run. Both logs remain available. `run_metadata.json` and summary tables describe the latest run; they are not an append-only history.

## When caches can be reused

Caches are reused only when input files, selected atlases, the FreeSurfer environment, run parameters, and existing outputs
are unchanged. FSHarvest rechecks TSV structure, region names, numeric values, and SHA-256 checksums before reuse.

Checks cover:

- Input FreeSurfer files.
- Atlas files and region-name lists.
- FreeSurfer version and templates.
- Selected atlases and run parameters.
- Cache format version, producing tool version, previous status, and output checksums.

Older tool versions do not automatically reuse caches produced by newer versions. `PARTIAL`, `FAILED`, or damaged caches are not used as successful results.

## Force recomputation

```bash
fsharvest INPUT OUTPUT --jobs 8 --overwrite
```

`--overwrite` ignores caches in the output directory and existing external-atlas annotations in subject directories.
Atlases are projected and statistics computed again. Subject `.stats` files without FSHarvest provenance are not reused by default.
This option still does not overwrite files with different contents in the original FreeSurfer directories.

## What run records contain

`run_metadata.json` records:

- A unique `run_id` and start/end times.
- Input and output root directories.
- Selected parameters and parcellations.
- SHA-256 checksums of atlas files, region-name lists, and program source.
- The extraction runtime's FreeSurfer version and template fingerprints.
- Tool, cache-format, and output-schema versions.

Each subject's `status.json` also records input fingerprints, cache reuse, output checksums, and failure reasons.

## Distinguish the two FreeSurfer versions

`fs_version` identifies the FreeSurfer version that generated the original reconstruction.
`runtime_freesurfer_version` identifies the version called during FSHarvest extraction.
Record and assess version effects when combining reconstructions from different versions.

Real-data testing has used FreeSurfer 7.4.1 to extract from reconstructions generated with FreeSurfer 7.2.0.
Validate other versions on a small representative sample first. FreeSurfer 8.x has not been tested.

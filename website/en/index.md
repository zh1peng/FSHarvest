<img class="fsharvest-doc-logo" src="/fsharvest-logo.png" alt="FSHarvest logo">

# Batch extraction of FreeSurfer regional measures

FSHarvest is a Linux command-line tool for collecting measurements from multiple FreeSurfer subject directories.
Given input and output directories, it extracts cortical, subcortical, and global measures, computes Euler numbers,
and records FreeSurfer versions and run parameters. Results are saved as long and wide tables for statistical analysis;
quality-control (QC) images can be generated on request.

## Processing workflow

<div class="harvest-path">
FreeSurfer results → Discover subjects → Extract selected parcellations → Check completeness → Write TSV tables and run records (optional QC images)
</div>

FSHarvest leaves the original FreeSurfer results unchanged by default. External-atlas `.annot` and `.stats` files
and caches are stored in the output directory. Files that pass validation are copied into the subject directories
only when `--export-to-freesurfer` is explicitly enabled; existing files with different contents are never overwritten.

## Run after installation

Follow the [installation guide](./guide/installation) to obtain the repository, install the command, and configure `PATH`. Then run:

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
fsharvest /path/to/subjects /path/to/output --jobs 12
```

Version 1.0.4 automatically displays an ASCII banner, version, and developer attribution, reports progress,
and saves a log for the entire run. The excerpt below comes from the real ten-subject DK68 run on linux212.
Timestamps and intermediate lines are omitted, and paths have been replaced:

```text
FSHarvest v1.0.4 | FreeSurfer regional feature extraction
Developer: zh1peng
[EXTRACT] Starting 10 subjects; progress is reported after each subject finishes.
...
[10/10] example-10: OK
[DONE] Finished: 10 OK, 0 non-OK across all requested phases.
Table status: OK=10, PARTIAL=0, FAILED=0, NOT_RUN=0
Run exit code: 0
Run log: /data/derived/fsharvest-dk68-example/logs/run_20260909T011641_543148Z_74b3105e.log
```

## Documentation

- Getting started: [Five-minute quick start](./guide/quick-start).
- Copy CLI commands or download SH scripts and compare real outputs: [Ten-subject worked example](./tutorials/ten-subject-example).
- Input requirements and scope: [Overview](./guide/introduction).
- Select Schaefer, Glasser, or other atlases: [Parcellations and extraction](./guide/atlases).
- Understand each output table: [Outputs and data tables](./guide/outputs).
- Generate and review QC images: [Reviewing QC images](./tutorials/qc-workflow).
- Run on a computing cluster: [Running on Slurm](./tutorials/slurm).

::: tip DK68 is the default
Without `--atlases`, FSHarvest reads only DK68. Select other parcellations explicitly.
:::

::: warning Automated checks do not replace Freeview QC
Region counts and names can reveal obvious omissions or mismatches. Inspect white and pial boundaries in Freeview.
:::

# Running on a Slurm cluster

FSHarvest includes `submit_slurm.sh` and `slurm/extract.sbatch`. One job processes an input directory and writes results
to a separate output directory. Copy the script below and adjust the account, partition, and FreeSurfer path to match your cluster.

## Option 1: Use the bundled submission script

Enter the repository and set the FreeSurfer installation directory:

```bash
cd /path/to/FSHarvest
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1

bash ./submit_slurm.sh \
  /data/freesurfer/subjects \
  /data/results/fsharvest \
  --atlases dk68 schaefer100 \
  --qc-plots \
  --qc-atlases dk68 schaefer100
```

`submit_slurm.sh` resolves the first two arguments to absolute paths and calls `sbatch`. Remaining arguments are passed
unchanged to FSHarvest. Successful submission returns a Slurm job ID:

```text
Submitted batch job 482731
```

The bundled job requests 12 CPUs, 24 GB of memory, and 24 hours. FSHarvest reads `SLURM_CPUS_PER_TASK`, making this equivalent to `--jobs 12`.

## Option 2: Write a Slurm submission script

If your cluster requires an account or partition in the job script, create `fsharvest_job.sbatch`:

```bash
#!/usr/bin/env bash
#SBATCH --job-name=fsharvest
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --partition=YOUR_PARTITION
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=12
#SBATCH --mem=24G
#SBATCH --output=logs/fsharvest_%j.out
#SBATCH --error=logs/fsharvest_%j.err

set -euo pipefail

REPO=/path/to/FSHarvest
INPUT=/data/freesurfer/subjects
OUTPUT=/data/results/fsharvest
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1

mkdir -p "$OUTPUT" logs

bash "$REPO/run_extract.sh" "$INPUT" "$OUTPUT" \
  --jobs "${SLURM_CPUS_PER_TASK:-1}" \
  --atlases dk68 schaefer100 \
  --qc-plots \
  --qc-atlases dk68 schaefer100
```

Check the paths before submitting, then run:

```bash
mkdir -p logs
sbatch fsharvest_job.sbatch
```

If FreeSurfer is provided through environment modules, replace `export FREESURFER_HOME=...` with the required module command,
such as `module load freesurfer/7.4.1`. Confirm that `FREESURFER_HOME` is set and `recon-all`, `mri_surf2surf`, and `mris_anatomical_stats` are available.

## Monitor progress and logs

```bash
squeue -j 482731
sacct -j 482731 --format=JobID,State,Elapsed,AllocCPUS,MaxRSS,ExitCode
tail -f logs/fsharvest_482731.out
```

Compute-node logs include the hostname, command, and progress. This is an illustrative format with timestamps omitted,
not a Slurm record from the linux212 example:

```text
Host: compute-17
FreeSurfer: /usr/local/freesurfer/7.4.1
Discovered 10 subjects; jobs=12; FreeSurfer=freesurfer-linux-ubuntu22_x86_64-7.4.1-20230614-7eb8460
[1/10] example-01: OK
...
[DONE] Finished: 10 OK, 0 non-OK across all requested phases.
Table status: OK=10, PARTIAL=0, FAILED=0, NOT_RUN=0
Run exit code: 0
```

Version 1.0.4 also saves a separate run log under `OUTPUT/logs/` and prints its `Run log:` path.
Slurm `.out` and `.err` files capture job startup and scheduler-related output; the FSHarvest run log records each extraction invocation.

After a normal job completion, also inspect `OUTPUT/subjects.tsv`. Slurm's `COMPLETED` means the process exited normally;
use the table's `status` to establish whether each subject succeeded.

## Interactive debugging with salloc and srun

On a new cluster, first request a compute node and process a small sample:

```bash
salloc --time=01:00:00 --cpus-per-task=4 --mem=12G

srun bash /path/to/FSHarvest/run_extract.sh \
  /data/freesurfer/subjects \
  /data/results/fsharvest-test \
  --jobs 4 \
  --limit 2 \
  --atlases dk68 schaefer100
```

Alternatively, let `srun` request resources and execute directly:

```bash
srun --time=01:00:00 --cpus-per-task=4 --mem=12G \
  bash /path/to/FSHarvest/run_extract.sh \
  /data/freesurfer/subjects \
  /data/results/fsharvest-test \
  --jobs 4 --limit 2
```

Use `srun` to check the FreeSurfer environment, license, mounted paths, and memory use. Once trial outputs are correct,
submit the full extraction with `sbatch`.

## CPUs, memory, and concurrency

- `--jobs` is the number of subjects processed concurrently; it should generally not exceed `--cpus-per-task`.
- External-atlas projection and QC rendering increase memory requirements. If memory runs out, reduce `--jobs`, then adjust `--mem` using `MaxRSS` from `sacct`.
- Do not let two jobs write to the same output directory; an output lock prevents this. Use separate directories for different datasets or parameter combinations.
- Summary tables include only the subjects selected for the current run. For job arrays, give each task a separate output directory and design a separate aggregation step; do not write concurrently to one directory.

::: warning Test on a compute node
Login and compute nodes may use different modules, licenses, and mounts. Before a full submission, validate `--limit 2` or `--limit 10` on an actual compute node.
:::

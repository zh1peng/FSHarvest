#!/usr/bin/env bash
#SBATCH --job-name=fs_extract_all
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=12
#SBATCH --mem=24G
#SBATCH --output=fs_extract_all_%j.out
#SBATCH --error=fs_extract_all_%j.err

set -euo pipefail
: "${FS_EXTRACT_SCRIPT:?FS_EXTRACT_SCRIPT is required}"
: "${FS_INPUT_DIR:?FS_INPUT_DIR is required}"
: "${FS_OUTPUT_DIR:?FS_OUTPUT_DIR is required}"
: "${FREESURFER_HOME:?FREESURFER_HOME is required}"

bash "${FS_EXTRACT_SCRIPT}" "${FS_INPUT_DIR}" "${FS_OUTPUT_DIR}" \
  --jobs "${SLURM_CPUS_PER_TASK:-1}" \
  --freesurfer-home "${FREESURFER_HOME}"

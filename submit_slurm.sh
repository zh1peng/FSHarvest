#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 2 ]]; then
  echo "Usage: FREESURFER_HOME=/path/to/freesurfer $0 DIR_TO_ALL_SUBJ OUTPUT_DIR [FSHarvest options]" >&2
  exit 64
fi
: "${FREESURFER_HOME:?Export FREESURFER_HOME before submission}"

INPUT_DIR="$(cd "$1" && pwd)"
mkdir -p "$2"
OUTPUT_DIR="$(cd "$2" && pwd)"

sbatch --export="ALL,FS_EXTRACT_SCRIPT=${SCRIPT_DIR}/run_extract.sh,FS_INPUT_DIR=${INPUT_DIR},FS_OUTPUT_DIR=${OUTPUT_DIR},FREESURFER_HOME=${FREESURFER_HOME}" \
  "${SCRIPT_DIR}/slurm/extract.sbatch" "${@:3}"

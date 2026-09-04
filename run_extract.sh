#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 2 ]]; then
  echo "Usage: fsharvest DIR_TO_ALL_SUBJ OUTPUT_DIR [--jobs N] [other options]" >&2
  exit 64
fi

FS_HOME_ARG=""
EXPECT_FS_HOME=0
for arg in "$@"; do
  if [[ ${EXPECT_FS_HOME} -eq 1 ]]; then
    FS_HOME_ARG="${arg}"
    EXPECT_FS_HOME=0
    continue
  fi
  case "${arg}" in
    --freesurfer-home) EXPECT_FS_HOME=1 ;;
    --freesurfer-home=*) FS_HOME_ARG="${arg#*=}" ;;
  esac
done

NEED_SETUP=0
for command in mri_surf2surf mris_anatomical_stats recon-all; do
  command -v "${command}" >/dev/null 2>&1 || NEED_SETUP=1
done
[[ -n "${FS_HOME_ARG}" ]] && NEED_SETUP=1

if [[ ${NEED_SETUP} -eq 1 ]]; then
  if [[ -n "${FS_HOME_ARG}" ]]; then
    FREESURFER_HOME="${FS_HOME_ARG}"
  fi
  if [[ -z "${FREESURFER_HOME:-}" ]]; then
    echo "ERROR: FreeSurfer is not initialized. Export FREESURFER_HOME, or source SetUpFreeSurfer.sh." >&2
    exit 69
  fi
  if [[ ! -r "${FREESURFER_HOME}/SetUpFreeSurfer.sh" ]]; then
    echo "ERROR: Missing ${FREESURFER_HOME}/SetUpFreeSurfer.sh" >&2
    exit 69
  fi
  # SetUpFreeSurfer.sh requires FREESURFER_HOME to be exported before sourcing.
  export FREESURFER_HOME
  # Some FreeSurfer releases contain benign commands that return non-zero and
  # reference optional unset variables while initializing the environment.
  set +e
  set +u
  # shellcheck source=/dev/null
  source "${FREESURFER_HOME}/SetUpFreeSurfer.sh" >/dev/null
  set -e
  set -u
fi

for command in mri_surf2surf mris_anatomical_stats recon-all; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "ERROR: FreeSurfer command is unavailable after setup: ${command}" >&2
    exit 69
  fi
done

exec python3 "${SCRIPT_DIR}/fs_extract_all.py" "$@"

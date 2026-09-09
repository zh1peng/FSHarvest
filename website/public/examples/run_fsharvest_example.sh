#!/usr/bin/env bash
set -euo pipefail

# Requires FSHarvest >= 1.0.4. Edit these paths for your machine.
subjects_dir=/data/study/freesurfer
output_dir=/data/derived/fsharvest-dk68-example
freesurfer_home=/usr/local/freesurfer/7.4.1

# The package displays progress and saves a separate run log automatically.
# Read the first 10 subjects; no QC plots or export to the input directories.
exec fsharvest "$subjects_dir" "$output_dir" \
  --freesurfer-home "$freesurfer_home" \
  --atlases dk68 --jobs 5 --limit 10

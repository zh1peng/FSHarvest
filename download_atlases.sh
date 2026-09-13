#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATLAS_DIR="${SCRIPT_DIR}/atlases"
mkdir -p "${ATLAS_DIR}"
STAGING_DIR="$(mktemp -d "${SCRIPT_DIR}/.atlases.download.XXXXXX")"
BACKUP_ROOT="$(mktemp -d "${SCRIPT_DIR}/.atlases.backup.XXXXXX")"
BACKUP_DIR="${BACKUP_ROOT}/atlases"
SWAP_STARTED=0
SWAP_COMPLETE=0

cleanup() {
  status=$?
  trap - EXIT
  if [[ ${SWAP_STARTED} -eq 1 && ${SWAP_COMPLETE} -eq 0 && -d "${BACKUP_DIR}" ]]; then
    rm -rf -- "${ATLAS_DIR}"
    mv -- "${BACKUP_DIR}" "${ATLAS_DIR}"
  fi
  [[ -d "${STAGING_DIR}" ]] && rm -rf -- "${STAGING_DIR}"
  [[ -d "${BACKUP_ROOT}" ]] && rm -rf -- "${BACKUP_ROOT}"
  exit "${status}"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

cp -a "${ATLAS_DIR}/." "${STAGING_DIR}/"

DK308_COMMIT="b4f8e8a3a56cee6a25187c075ed82157a3a1e67a"
DK308_BASE="https://raw.githubusercontent.com/KirstieJane/UCHANGE_ProcessingPipeline/${DK308_COMMIT}/FS_SUBJECTS/fsaverageSubP/label"
MICAPIPE_COMMIT="4227ee660f216387df4310088dde026d1278dd8e"
MICAPIPE_BASE="https://raw.githubusercontent.com/MICA-MNI/micapipe/${MICAPIPE_COMMIT}"

# Remove obsolete files only in the staged replacement.
for n in 100 200 300 400; do
  for hemi in lh rh; do
    rm -f -- "${STAGING_DIR}/${hemi}.Schaefer2018_${n}Parcels_7Networks_order.annot"
  done
done

for n in 100 200 300 400 500 600 700 800 900 1000; do
  for hemi in lh rh; do
    file="${hemi}.schaefer-${n}_mics.annot"
    curl --fail --location --retry 3 "${MICAPIPE_BASE}/parcellations/${file}" --output "${STAGING_DIR}/${file}"
  done
done

for hemi in lh rh; do
  file="${hemi}.500.aparc.annot"
  curl --fail --location --retry 3 "${DK308_BASE}/${file}" --output "${STAGING_DIR}/${file}"
done

for atlas in economo glasser-360 vosdewael-300; do
  for hemi in lh rh; do
    file="${hemi}.${atlas}_mics.annot"
    curl --fail --location --retry 3 "${MICAPIPE_BASE}/parcellations/${file}" --output "${STAGING_DIR}/${file}"
  done
done

curl --fail --location --retry 3 \
  "${MICAPIPE_BASE}/LICENSE" \
  --output "${STAGING_DIR}/LICENSE_MICAPIPE_GPL3.txt"

# netneurotools Cammoun2012 full-resolution fsaverage archive (fixed OSF file).
curl --fail --location --retry 3 \
  "https://files.osf.io/v1/resources/udpv8/providers/osfstorage/67326ef5c41abfb7cd0ddf1d" \
  --output "${STAGING_DIR}/cammoun-fsaverage.tar.gz"
curl --fail --location --retry 3 \
  "https://raw.githubusercontent.com/LTS5/cmp/93094ce227bda9064512290dd505a7ba75cf7072/COPYRIGHT" \
  --output "${STAGING_DIR}/LICENSE_CAMMOUN.txt"

python3 - "${STAGING_DIR}" <<'PY'
import hashlib
import json
import sys
import tarfile
from pathlib import Path

root = Path(sys.argv[1])
manifest_path = root / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
cammoun_files = [item for item in manifest["files"] if item["atlas"].startswith("cammoun")]
archive = root / "cammoun-fsaverage.tar.gz"
archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
if any(item["source_archive_sha256"] != archive_sha256 for item in cammoun_files):
    raise SystemExit("Cammoun archive checksum mismatch")
with tarfile.open(archive) as bundle:
    for item in cammoun_files:
        with bundle.extractfile(item["source_member"]) as source:
            (root / item["file"]).write_bytes(source.read())
archive.unlink()
expected = {item["file"]: item["sha256"] for item in manifest["files"]}
failed = []
for name, digest in expected.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != digest:
        failed.append(f"{name}: expected {digest}, got {actual}")
if failed:
    raise SystemExit("Atlas verification failed:\n" + "\n".join(failed))
print(f"Verified {len(expected)} atlas files in {root}")
PY

# Replace the complete directory only after every staged file has passed verification.
SWAP_STARTED=1
mv -- "${ATLAS_DIR}" "${BACKUP_DIR}"
mv -- "${STAGING_DIR}" "${ATLAS_DIR}"
SWAP_COMPLETE=1
rm -rf -- "${BACKUP_ROOT}"
printf 'Installed verified atlas bundle: %s\n' "${ATLAS_DIR}"

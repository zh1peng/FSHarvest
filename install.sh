#!/usr/bin/env bash
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PREFIX="${1:-${HOME}/.local}"
BIN_DIR="${INSTALL_PREFIX}/bin"
INSTALL_ROOT="${INSTALL_PREFIX}/lib/fsharvest"

mkdir -p "${BIN_DIR}" "${INSTALL_ROOT}"
cp -f \
  "${TOOL_DIR}/fs_extract_all.py" \
  "${TOOL_DIR}/fs_render_qc.py" \
  "${TOOL_DIR}/fsharvest" \
  "${TOOL_DIR}/run_extract.sh" \
  "${TOOL_DIR}/requirements-qc.txt" \
  "${TOOL_DIR}/README.md" \
  "${TOOL_DIR}/VALIDATION.md" \
  "${TOOL_DIR}/CHANGELOG.md" \
  "${TOOL_DIR}/CITATION.cff" \
  "${TOOL_DIR}/THIRD_PARTY_NOTICES.md" \
  "${TOOL_DIR}/SECURITY.md" \
  "${TOOL_DIR}/LICENSE" \
  "${TOOL_DIR}/VERSION" \
  "${INSTALL_ROOT}/"
cp -R "${TOOL_DIR}/atlases" "${INSTALL_ROOT}/"
chmod +x "${INSTALL_ROOT}/fsharvest" "${INSTALL_ROOT}/run_extract.sh" "${INSTALL_ROOT}/fs_extract_all.py" "${INSTALL_ROOT}/fs_render_qc.py"
ln -sfn "${INSTALL_ROOT}/fsharvest" "${BIN_DIR}/fsharvest"

printf 'Installed: %s\n' "${BIN_DIR}/fsharvest"
printf 'Package files: %s\n' "${INSTALL_ROOT}"
if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
  printf 'Add this directory to PATH:\n  export PATH="%s:$PATH"\n' "${BIN_DIR}"
fi

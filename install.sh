#!/usr/bin/env bash
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="install"
if [[ "${1:-}" == "--check" || "${1:-}" == "--uninstall" ]]; then
  MODE="${1#--}"
  shift
fi
INSTALL_PREFIX="${1:-${HOME}/.local}"
BIN_DIR="${INSTALL_PREFIX}/bin"
INSTALL_BASE="${INSTALL_PREFIX}/lib/fsharvest"
CURRENT_LINK="${INSTALL_BASE}/current"

if [[ "${MODE}" == "check" ]]; then
  [[ -L "${CURRENT_LINK}" ]] || { echo "ERROR: FSHarvest is not installed under ${INSTALL_PREFIX}" >&2; exit 1; }
  "${CURRENT_LINK}/fsharvest" --version
  python3 "${CURRENT_LINK}/fs_extract_all.py" --help >/dev/null
  echo "Installation check passed: $(readlink -f "${CURRENT_LINK}")"
  exit 0
fi

if [[ "${MODE}" == "uninstall" ]]; then
  rm -f "${BIN_DIR}/fsharvest" "${CURRENT_LINK}"
  echo "Removed FSHarvest launch links from ${INSTALL_PREFIX}; version directories were retained."
  exit 0
fi

VERSION="$(tr -d '[:space:]' < "${TOOL_DIR}/VERSION")"
[[ -n "${VERSION}" ]] || { echo "ERROR: VERSION is empty" >&2; exit 1; }
VERSION_DIR="${INSTALL_BASE}/${VERSION}"
mkdir -p "${BIN_DIR}" "${INSTALL_BASE}"
STAGE_DIR="$(mktemp -d "${INSTALL_BASE}/.stage-${VERSION}.XXXXXX")"
NEXT_LINK="${INSTALL_BASE}/.current-${VERSION}-$$"
cleanup() {
  [[ -z "${STAGE_DIR}" ]] || rm -rf -- "${STAGE_DIR}"
  rm -f -- "${NEXT_LINK}"
}
trap cleanup EXIT

cp \
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
  "${STAGE_DIR}/"
cp -R "${TOOL_DIR}/atlases" "${STAGE_DIR}/atlases"
chmod +x "${STAGE_DIR}/fsharvest" "${STAGE_DIR}/run_extract.sh" \
  "${STAGE_DIR}/fs_extract_all.py" "${STAGE_DIR}/fs_render_qc.py"

if [[ -e "${VERSION_DIR}" ]]; then
  echo "ERROR: immutable version directory already exists: ${VERSION_DIR}" >&2
  echo "Run install.sh --check ${INSTALL_PREFIX}, or remove the version explicitly before reinstalling." >&2
  exit 1
fi
mv "${STAGE_DIR}" "${VERSION_DIR}"
STAGE_DIR=""
ln -s "${VERSION}" "${NEXT_LINK}"
mv -Tf "${NEXT_LINK}" "${CURRENT_LINK}"
ln -sfn "${CURRENT_LINK}/fsharvest" "${BIN_DIR}/fsharvest"

"${CURRENT_LINK}/fsharvest" --version
printf 'Installed: %s\n' "${BIN_DIR}/fsharvest"
printf 'Package files: %s\n' "${VERSION_DIR}"
if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
  # shellcheck disable=SC2016
  printf 'Add this directory to PATH:\n  export PATH="%s:$PATH"\n' "${BIN_DIR}"
fi

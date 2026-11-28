#!/usr/bin/env bash
# Disable optional third-party APT sources that must not block merge-authority Git builds.
set -euo pipefail
shopt -s nullglob
for list_path in /etc/apt/sources.list.d/*microsoft*; do
  if [[ "${list_path}" == *.hxforge-disabled ]]; then
    continue
  fi
  if [ -e "${list_path}" ]; then
    sudo mv "${list_path}" "${list_path}.hxforge-disabled"
    echo "disabled-apt-source=${list_path}"
  fi
done
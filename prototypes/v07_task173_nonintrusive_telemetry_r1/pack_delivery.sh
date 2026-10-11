#!/usr/bin/env bash
# Package the six primary prototype files + SHA256 manifest for off-VM storage.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="${1:-/opt/cursor/artifacts}"
TASK_ID="V07_TASK173_NONINTRUSIVE_TELEMETRY_R1"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE="${OUT_DIR}/${TASK_ID}_${STAMP}"
mkdir -p "$BUNDLE"

FILES=(
  EVENT_CONTRACT.md
  telemetry.py
  mock_runner.py
  PRODUCTION_HOOK_INTEGRATION.md
  test_telemetry_prototype.py
  README.md
)

for f in "${FILES[@]}"; do
  cp "${ROOT}/${f}" "${BUNDLE}/${f}"
done
cp "${ROOT}/FROZEN_IDENTITY_REFERENCES.md" "${BUNDLE}/" 2>/dev/null || true
cp "${ROOT}/LOG_RECOVERY_NOT_CHECKPOINT.md" "${BUNDLE}/" 2>/dev/null || true

(
  cd "$BUNDLE"
  sha256sum "${FILES[@]}" > MANIFEST.sha256
)

tar -czf "${BUNDLE}.tar.gz" -C "$OUT_DIR" "$(basename "$BUNDLE")"
sha256sum "${BUNDLE}.tar.gz" > "${BUNDLE}.tar.gz.sha256"

python3 "${ROOT}/mock_runner.py" --artifact-dir "${BUNDLE}/mock_run_artifacts" > "${BUNDLE}/mock_run_report.json"

export BUNDLE TASK_ID
python3 <<'PY'
import json
import os
from pathlib import Path

bundle = os.environ["BUNDLE"]
files = [
    "EVENT_CONTRACT.md",
    "telemetry.py",
    "mock_runner.py",
    "PRODUCTION_HOOK_INTEGRATION.md",
    "test_telemetry_prototype.py",
    "README.md",
]
idx = {
    "task_id": os.environ["TASK_ID"],
    "baseline_git": "84c5f38b74fd26eacefee260af7be26c12cb2e31",
    "bundle_dir": bundle,
    "tarball": f"{bundle}.tar.gz",
    "tarball_sha256_file": f"{bundle}.tar.gz.sha256",
    "manifest": f"{bundle}/MANIFEST.sha256",
    "primary_files": files,
}
Path(f"{bundle}/DELIVERY_INDEX.json").write_text(json.dumps(idx, indent=2), encoding="utf-8")
PY

echo "DELIVERED: ${BUNDLE}.tar.gz"
echo "MANIFEST: ${BUNDLE}/MANIFEST.sha256"

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

# Delivery artifacts before tarball.
python3 "${ROOT}/mock_runner.py" --artifact-dir "${BUNDLE}/mock_run_artifacts" > "${BUNDLE}/mock_run_report.json"

export BUNDLE TASK_ID ROOT STAMP
python3 <<'PY'
import hashlib
import json
import os
import subprocess
from pathlib import Path

bundle = Path(os.environ["BUNDLE"])
root = Path(os.environ["ROOT"])
files = [
    "EVENT_CONTRACT.md",
    "telemetry.py",
    "mock_runner.py",
    "PRODUCTION_HOOK_INTEGRATION.md",
    "test_telemetry_prototype.py",
    "README.md",
]
manifest_lines = []
for name in files:
    digest = hashlib.sha256((bundle / name).read_bytes()).hexdigest()
    manifest_lines.append(f"{digest}  {name}\n")
(bundle / "MANIFEST.sha256").write_text("".join(manifest_lines), encoding="utf-8")

tarball = Path(f"{bundle}.tar.gz")
idx = {
    "task_id": os.environ["TASK_ID"],
    "baseline_git": "84c5f38b74fd26eacefee260af7be26c12cb2e31",
    "bundle_dir": str(bundle),
    "stamp_utc": os.environ["STAMP"],
    "primary_files": files,
    "companion_files": [
        "FROZEN_IDENTITY_REFERENCES.md",
        "LOG_RECOVERY_NOT_CHECKPOINT.md",
        "MANIFEST.sha256",
        "mock_run_report.json",
        "DELIVERY_INDEX.json",
        "PACK_VERIFY.json",
    ],
    "mock_run_report": str(bundle / "mock_run_report.json"),
    "manifest": str(bundle / "MANIFEST.sha256"),
}
(bundle / "DELIVERY_INDEX.json").write_text(json.dumps(idx, indent=2), encoding="utf-8")
PY

(
  cd "$BUNDLE"
  sha256sum -c MANIFEST.sha256
)

# Tarball after pre-pack artifacts + manifest check.
tar -czf "${BUNDLE}.tar.gz" -C "$OUT_DIR" "$(basename "$BUNDLE")"
TARBALL_SHA="$(sha256sum "${BUNDLE}.tar.gz" | awk '{print $1}')"
echo "${TARBALL_SHA}  ${BUNDLE}.tar.gz" > "${BUNDLE}.tar.gz.sha256"

python3 <<'PY'
import hashlib
import json
import os
import subprocess
import tarfile
from pathlib import Path

bundle = Path(os.environ["BUNDLE"])
tarball = Path(f"{bundle}.tar.gz")
prefix = bundle.name + "/"
required = {
    "EVENT_CONTRACT.md",
    "telemetry.py",
    "mock_runner.py",
    "PRODUCTION_HOOK_INTEGRATION.md",
    "test_telemetry_prototype.py",
    "README.md",
    "MANIFEST.sha256",
    "DELIVERY_INDEX.json",
    "mock_run_report.json",
}
members = set()
with tarfile.open(tarball, "r:gz") as archive:
    for item in archive.getmembers():
        if item.isfile():
            members.add(item.name.removeprefix(prefix))
missing = sorted(required - members)
verify = {
    "tarball": str(tarball),
    "tarball_sha256": Path(f"{tarball}.sha256").read_text().strip().split()[0],
    "archive_member_count": len(members),
    "required_members_present": missing == [],
    "missing_required_members": missing,
    "manifest_check": "passed",
}
(bundle / "PACK_VERIFY.json").write_text(json.dumps(verify, indent=2), encoding="utf-8")
if missing:
    raise SystemExit(f"tarball missing required members: {missing}")
PY

# Refresh index with tarball paths after pack verify.
python3 <<'PY'
import json
import os
from pathlib import Path

bundle = Path(os.environ["BUNDLE"])
idx = json.loads((bundle / "DELIVERY_INDEX.json").read_text(encoding="utf-8"))
idx["tarball"] = f"{bundle}.tar.gz"
idx["tarball_sha256"] = Path(f"{bundle}.tar.gz.sha256").read_text().strip().split()[0]
idx["tarball_sha256_file"] = f"{bundle}.tar.gz.sha256"
idx["pack_verify"] = str(bundle / "PACK_VERIFY.json")
(bundle / "DELIVERY_INDEX.json").write_text(json.dumps(idx, indent=2), encoding="utf-8")
PY

# Repack so PACK_VERIFY + refreshed DELIVERY_INDEX are archive members.
tar -czf "${BUNDLE}.tar.gz" -C "$OUT_DIR" "$(basename "$BUNDLE")"
TARBALL_SHA="$(sha256sum "${BUNDLE}.tar.gz" | awk '{print $1}')"
echo "${TARBALL_SHA}  ${BUNDLE}.tar.gz" > "${BUNDLE}.tar.gz.sha256"

cp "${BUNDLE}.tar.gz" "${ROOT}/V07_TASK173_NONINTRUSIVE_TELEMETRY_R1_${STAMP}.tar.gz"
cp "${BUNDLE}/MANIFEST.sha256" "${ROOT}/MANIFEST_${STAMP}.sha256"

echo "DELIVERED: ${BUNDLE}.tar.gz"
echo "SHA256: ${TARBALL_SHA}"
echo "MANIFEST: ${BUNDLE}/MANIFEST.sha256"

#!/usr/bin/env bash
# Package prototype delivery: all bundle files first, single final tar.gz, external checksum.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="${1:-/opt/cursor/artifacts}"
TASK_ID="V07_TASK173_NONINTRUSIVE_TELEMETRY_R1"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE="${OUT_DIR}/${TASK_ID}_${STAMP}"
TARBALL="${OUT_DIR}/${TASK_ID}_${STAMP}.tar.gz"
TARBALL_SHA_FILE="${TARBALL}.sha256"
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

python3 "${ROOT}/mock_runner.py" --artifact-dir "${BUNDLE}/mock_run_artifacts" > "${BUNDLE}/mock_run_report.json"

export BUNDLE TASK_ID ROOT STAMP OUT_DIR TARBALL TARBALL_SHA_FILE
python3 <<'PY'
import hashlib
import json
import os
from pathlib import Path

bundle = Path(os.environ["BUNDLE"])
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

companion = [
    "FROZEN_IDENTITY_REFERENCES.md",
    "LOG_RECOVERY_NOT_CHECKPOINT.md",
    "MANIFEST.sha256",
    "mock_run_report.json",
    "DELIVERY_INDEX.json",
    "PACK_VERIFY.json",
]
member_hashes: dict[str, str] = {}
for name in files + companion:
    path = bundle / name
    if path.is_file():
        member_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()

tarball_name = Path(os.environ["TARBALL"]).name
idx = {
    "task_id": os.environ["TASK_ID"],
    "baseline_git": "84c5f38b74fd26eacefee260af7be26c12cb2e31",
    "bundle_dir": str(bundle),
    "stamp_utc": os.environ["STAMP"],
    "primary_files": files,
    "companion_files": companion,
    "mock_run_report": str(bundle / "mock_run_report.json"),
    "manifest": str(bundle / "MANIFEST.sha256"),
    "tarball": os.environ["TARBALL"],
    "tarball_checksum_file": os.environ["TARBALL_SHA_FILE"],
    "tarball_checksum_note": "SHA256 sidecar is outside the archive; not embedded in DELIVERY_INDEX hash fields.",
}
(bundle / "DELIVERY_INDEX.json").write_text(json.dumps(idx, indent=2), encoding="utf-8")
member_hashes["DELIVERY_INDEX.json"] = hashlib.sha256(
    (bundle / "DELIVERY_INDEX.json").read_bytes()
).hexdigest()

required_members = sorted(member_hashes.keys()) + ["PACK_VERIFY.json"]
verify = {
    "schema": "task173.telemetry.pack-verify.v1",
    "bundle_stamp_utc": os.environ["STAMP"],
    "required_archive_members": sorted(set(required_members)),
    "member_sha256": member_hashes,
    "manifest_check": "passed_pre_tar",
}
(bundle / "PACK_VERIFY.json").write_text(json.dumps(verify, indent=2), encoding="utf-8")
PY

(
  cd "$BUNDLE"
  sha256sum -c MANIFEST.sha256
)

tar -czf "${TARBALL}" -C "$OUT_DIR" "$(basename "$BUNDLE")"
TARBALL_SHA="$(sha256sum "${TARBALL}" | awk '{print $1}')"
echo "${TARBALL_SHA}  $(basename "${TARBALL}")" > "${TARBALL_SHA_FILE}"

python3 <<'PY'
import hashlib
import json
import os
import tarfile
from pathlib import Path

bundle = Path(os.environ["BUNDLE"])
tarball = Path(os.environ["TARBALL"])
prefix = bundle.name + "/"
verify = json.loads((bundle / "PACK_VERIFY.json").read_text(encoding="utf-8"))
expected = verify["member_sha256"]
members = set()
mismatches: list[str] = []
pack_verify_bytes = (bundle / "PACK_VERIFY.json").read_bytes()
with tarfile.open(tarball, "r:gz") as archive:
    for item in archive.getmembers():
        if not item.isfile():
            continue
        rel = item.name.removeprefix(prefix)
        members.add(rel)
        data = archive.extractfile(item)
        if data is None:
            mismatches.append(f"{rel}:missing_payload")
            continue
        payload = data.read()
        if rel == "PACK_VERIFY.json":
            if payload != pack_verify_bytes:
                mismatches.append("PACK_VERIFY.json:byte_mismatch")
            continue
        if rel not in expected:
            continue
        digest = hashlib.sha256(payload).hexdigest()
        if digest != expected[rel]:
            mismatches.append(f"{rel}:sha256_mismatch")
missing = sorted(set(verify["required_archive_members"]) - members)
result = {
    "tarball": str(tarball),
    "tarball_checksum_file": os.environ["TARBALL_SHA_FILE"],
    "required_members_present": missing == [],
    "missing_required_members": missing,
    "member_hash_mismatches": mismatches,
    "archive_member_count": len(members),
    "verification_passed": missing == [] and mismatches == [],
}
out = Path(os.environ["OUT_DIR"]) / f"{os.environ['TASK_ID']}_{os.environ['STAMP']}_PACK_VERIFY_RESULT.json"
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
if not result["verification_passed"]:
    raise SystemExit(f"tarball verification failed: {result}")
PY

cp "${TARBALL}" "${ROOT}/${TASK_ID}_${STAMP}.tar.gz"
cp "${TARBALL_SHA_FILE}" "${ROOT}/${TASK_ID}_${STAMP}.tar.gz.sha256"
cp "${BUNDLE}/MANIFEST.sha256" "${ROOT}/MANIFEST_${STAMP}.sha256"

echo "DELIVERED: ${TARBALL}"
echo "SHA256: ${TARBALL_SHA}"
echo "SHA256_FILE: ${TARBALL_SHA_FILE}"
echo "MANIFEST: ${BUNDLE}/MANIFEST.sha256"

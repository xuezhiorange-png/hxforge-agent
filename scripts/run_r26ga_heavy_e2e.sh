#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p /opt/cursor/artifacts
HEAD="$(git rev-parse HEAD)"
START=$(date +%s)
CMD=(uv run --locked pytest -q
  tests/prototypes/test_r26g_authorized_full_path_hydraulic.py::test_r26g_representative_full_path_study_slow
  -m slow --timeout=7200)
printf '%q ' "${CMD[@]}" > /opt/cursor/artifacts/r26ga-heavy-e2e-command.txt
echo >> /opt/cursor/artifacts/r26ga-heavy-e2e-command.txt
"${CMD[@]}" 2>&1 | tee /opt/cursor/artifacts/r26ga-heavy-e2e-pytest.log
EXIT=$?
END=$(date +%s)
cat > /opt/cursor/artifacts/r26ga-heavy-e2e-manifest.json <<EOF
{
  "task_id": "V07_R26G_A_FULL_PATH_PHYSICAL_CONSISTENCY_GATE",
  "git_head": "$HEAD",
  "exit_code": $EXIT,
  "wall_seconds": $((END - START)),
  "pytest_log": "/opt/cursor/artifacts/r26ga-heavy-e2e-pytest.log"
}
EOF
exit "$EXIT"

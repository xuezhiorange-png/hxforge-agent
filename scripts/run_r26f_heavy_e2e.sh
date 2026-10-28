#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p /opt/cursor/artifacts
HEAD="$(git rev-parse HEAD)"
START=$(date +%s)
CMD=(uv run --locked pytest -q
  tests/prototypes/test_r26f_engineering_hydraulic_path.py::test_r26f_representative_hydraulic_path_study_slow
  -m slow --timeout=7200)
printf '%q ' "${CMD[@]}" > /opt/cursor/artifacts/r26f-heavy-e2e-command.txt
echo >> /opt/cursor/artifacts/r26f-heavy-e2e-command.txt
"${CMD[@]}" 2>&1 | tee /opt/cursor/artifacts/r26f-heavy-e2e-pytest.log
EXIT=$?
END=$(date +%s)
cat > /opt/cursor/artifacts/r26f-heavy-e2e-manifest.json <<EOF
{
  "task_id": "V07_R26F_ENGINEERING_HYDRAULIC_PATH_COMPLETION",
  "git_head": "$HEAD",
  "exit_code": $EXIT,
  "wall_seconds": $((END - START)),
  "pytest_log": "/opt/cursor/artifacts/r26f-heavy-e2e-pytest.log"
}
EOF
exit "$EXIT"

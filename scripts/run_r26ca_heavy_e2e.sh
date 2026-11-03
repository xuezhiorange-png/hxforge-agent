#!/usr/bin/env bash
# R26C-A independent heavy engineering E2E (310/295 K mesh ladder + live hydraulic).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p /opt/cursor/artifacts
HEAD="$(git rev-parse HEAD)"
START=$(date +%s)
CMD=(uv run --locked pytest -q
  tests/prototypes/test_r26c_engineering_rating_live_hydraulic_bridge.py::test_r26c_primary_310_295_mesh_ladder_and_live_hydraulic
  -m slow --timeout=3600)
printf '%q ' "${CMD[@]}" > /opt/cursor/artifacts/r26ca-heavy-e2e-command.txt
echo >> /opt/cursor/artifacts/r26ca-heavy-e2e-command.txt
"${CMD[@]}" 2>&1 | tee /opt/cursor/artifacts/r26ca-heavy-e2e-pytest.log
EXIT=$?
END=$(date +%s)
WALL=$((END - START))
cat > /opt/cursor/artifacts/r26ca-heavy-e2e-manifest.json <<EOF
{
  "task_id": "V07_R26C_A_MINIMAL_ENGINEERING_CLOSEOUT",
  "git_head": "$HEAD",
  "command": "$(tr -d '\n' < /opt/cursor/artifacts/r26ca-heavy-e2e-command.txt)",
  "exit_code": $EXIT,
  "wall_seconds": $WALL,
  "pytest_log": "/opt/cursor/artifacts/r26ca-heavy-e2e-pytest.log",
  "delivery_receipt_script": "uv run python -m prototypes.v07_general_rating_sizing_mvp.run_r26ca_delivery_receipt"
}
EOF
exit "$EXIT"

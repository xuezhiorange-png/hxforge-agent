#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p /opt/cursor/artifacts
HEAD="$(git rev-parse HEAD)"
START=$(date +%s)
CMD=(uv run --locked pytest -q
  tests/prototypes/test_r26e_multi_candidate_engineering_sizing.py::test_r26e_full_multi_candidate_tradeoff_and_baseline_preservation_slow
  tests/prototypes/test_r26e_multi_candidate_engineering_sizing.py::test_r26e_n1_cache_reuse_matches_screening_duty_slow
  -m slow --timeout=7200)
printf '%q ' "${CMD[@]}" > /opt/cursor/artifacts/r26e-heavy-e2e-command.txt
echo >> /opt/cursor/artifacts/r26e-heavy-e2e-command.txt
"${CMD[@]}" 2>&1 | tee /opt/cursor/artifacts/r26e-heavy-e2e-pytest.log
EXIT=$?
END=$(date +%s)
cat > /opt/cursor/artifacts/r26e-heavy-e2e-manifest.json <<EOF
{
  "task_id": "V07_R26E_ENGINEERING_TRADEOFF_AND_CANDIDATE_EXPANSION",
  "git_head": "$HEAD",
  "exit_code": $EXIT,
  "wall_seconds": $((END - START)),
  "pytest_log": "/opt/cursor/artifacts/r26e-heavy-e2e-pytest.log"
}
EOF
exit "$EXIT"

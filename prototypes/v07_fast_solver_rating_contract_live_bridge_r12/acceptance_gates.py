"""R12 acceptance flags derived from real checks (not replay side effects)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    R11_RATING_JSON_REL,
    R11_RATING_JSON_SHA256,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.compact_rating import (
    build_compact_from_full,
    compact_rating_hash,
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_contract_live_bridge_r12.r11_artifact_verify import (
    verify_r11_full_rating_artifact,
)

ROOT = Path(__file__).resolve().parents[2]


def run_ruff_format_check() -> dict[str, Any]:
    proc = subprocess.run(
        ["uv", "run", "--locked", "ruff", "format", "--check", "."],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "pass": proc.returncode == 0,
        "stdout": proc.stdout[-2000:] if proc.stdout else "",
        "stderr": proc.stderr[-2000:] if proc.stderr else "",
    }


def evaluate_r12_acceptance_flags(
    *,
    fail_closed_trajectory_test_passed: bool,
    fail_closed_cell_count_test_passed: bool,
    fail_closed_wall_extrema_test_passed: bool,
) -> dict[str, Any]:
    ruff = run_ruff_format_check()
    r11 = verify_r11_full_rating_artifact()
    rating_path = ROOT / R11_RATING_JSON_REL
    full = ExperimentalCandidateRatingResult.model_validate_json(
        rating_path.read_text(encoding="utf-8"),
        strict=True,
    )
    import importlib.util
    import json

    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        CandidateRatingRequest,
    )
    from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID

    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _c, req_raw = mod._build_candidate_requests()[CANDIDATE_B_ID]
    if type(req_raw) is not CandidateRatingRequest:
        req_raw = CandidateRatingRequest.model_validate_json(
            json.dumps(req_raw, separators=(",", ":"), ensure_ascii=False),
            strict=True,
        )
    geom = geometry_summary_from_request(req_raw)
    compact = build_compact_from_full(
        full,
        trajectory_artifact_path=R11_RATING_JSON_REL,
        trajectory_file_sha256=R11_RATING_JSON_SHA256,
        geometry_summary=geom,
    )
    compact_recomputed = compact_rating_hash(compact)
    compact_parity = compact.compact_result_hash == compact_recomputed

    # Cell count / wall extrema on frozen full artifact accepted mesh metadata only
    cell_count_ok = full.accepted_mesh_n == 32 and full.task172_cell_closure_verified
    wall_ok = full.wall_temperature_extrema_verified

    return {
        "r11_ci_format_fixed": ruff["pass"],
        "ruff_format_check": ruff,
        "full_trajectory_fail_closed": fail_closed_trajectory_test_passed,
        "accepted_cell_count_verified": fail_closed_cell_count_test_passed and cell_count_ok,
        "wall_extrema_recomputed": fail_closed_wall_extrema_test_passed and wall_ok,
        "r11_result_hash_parity": r11["result_hash_parity"],
        "r11_artifact_roundtrip_pass": r11.get("model_roundtrip_pass") == "PASS",
        "compact_result_hash_parity": "PASS" if compact_parity else "FAIL",
        "compact_result_hash": compact.compact_result_hash,
        "compact_result_hash_recomputed": compact_recomputed,
    }

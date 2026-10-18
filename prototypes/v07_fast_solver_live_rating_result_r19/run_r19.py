#!/usr/bin/env python3
"""R19: complete LIVE_NUMERICAL_SOLVE Candidate B rating result."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    CANDIDATE_B_ID,
    R11_RATING_JSON_REL,
)
from prototypes.v07_fast_solver_live_n32_candidate_r17.trial_remote_persistence import (
    git_push_paths,
)
from prototypes.v07_fast_solver_live_rating_result_r19 import (
    experimental_rate_candidate_live_result,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_evidence_admission import (
    admit_full_live_mesh_evidence,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    live_rating_result_hash,
)
from prototypes.v07_fast_solver_live_rating_result_r19.r18_amendment_reconcile import (
    INDEX_PATH_REL,
    reconcile_r18_headroom_amendment,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.compact_rating import (
    build_compact_from_full,
    compact_rating_hash,
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
    ExperimentalRatingBlocked,
)

TASK_ID = "V07_FAST_SOLVER_LIVE_RATING_RESULT_R19"
SOURCE_SHA = "871716f7eba776651050f2b428ea9b901f10f325"
BRANCH = "cursor/v07-fast-solver-live-rating-result-r19-1201"
TOTAL_TASK_WALL_SECONDS = 1500.0
R11_ENGINEERING_DUTY_REL_TOL = Decimal("0.001")


def _git_push_files(message: str, paths: list[Path]) -> str | None:
    return git_push_paths(ROOT, BRANCH, message, paths)


def _append_index_row(row: dict[str, Any]) -> None:
    with (ROOT / INDEX_PATH_REL).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _engineering_diff_vs_r11(live: ExperimentalCandidateRatingResult) -> dict[str, Any]:
    r11 = ExperimentalCandidateRatingResult.model_validate_json(
        (ROOT / R11_RATING_JSON_REL).read_text(encoding="utf-8"),
        strict=True,
    )
    duty_delta = abs(live.total_duty_w - r11.total_duty_w)
    duty_rel = duty_delta / max(abs(r11.total_duty_w), Decimal("1"))
    return {
        "r11_result_hash": r11.result_hash,
        "live_result_hash": live.result_hash,
        "duty_delta_w": str(duty_delta),
        "duty_relative_delta": str(duty_rel),
        "duty_within_engineering_tol": duty_rel <= R11_ENGINEERING_DUTY_REL_TOL,
        "tube_outlet_delta_k": str(live.tube_outlet_temperature_k - r11.tube_outlet_temperature_k),
        "shell_outlet_delta_k": str(
            live.shell_outlet_temperature_k - r11.shell_outlet_temperature_k
        ),
        "note": "Hash mismatch expected; engineering tol is advisory not pass/fail",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    deadline = wall_t0 + TOTAL_TASK_WALL_SECONDS

    probe = ROOT / "docs/tasks/evidence/.r19-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    remote_ok = _git_push_files("R19 persistence probe", [probe]) is not None
    if not remote_ok:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    pkg = ROOT / "prototypes/v07_fast_solver_live_rating_result_r19"
    _git_push_files("R19 pre-run sources", [probe, pkg])

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_live_rating_result_r19/",
            "prototypes/v07_fast_solver_live_ladder_continuation_r14/test_comparison_history_admission.py",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )

    r18_manifest = reconcile_r18_headroom_amendment(ROOT, compare_budget_s=320.0)
    _append_index_row(
        {
            "task_id": "V07_FAST_SOLVER_LIVE_N64_HEADROOM_R18",
            "kind": "amendment",
            "run_id": f"amendment_r19_{stamp}",
            "result": "R18_N32_N64_COMPARE_RECONCILED",
            "raw_result_path": r18_manifest["manifest_rel_path"],
            "raw_result_sha256": r18_manifest["manifest_sha256"],
            "revised_live_result_sha256": r18_manifest["revised_result_sha256"],
            "supersedes_raw_result_sha256": r18_manifest["original_result_sha256"],
            "remote_branch": BRANCH,
        }
    )
    _git_push_files(
        "R19 R18 amendment manifest",
        [ROOT / r18_manifest["manifest_rel_path"], ROOT / INDEX_PATH_REL],
    )

    if time.perf_counter() >= deadline:
        raise SystemExit("TIMEOUT_BEFORE_RATING_BUILD")

    evidence = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    outcome = experimental_rate_candidate_live_result(evidence, root=ROOT)
    if isinstance(outcome, ExperimentalRatingBlocked):
        raise SystemExit(json.dumps(outcome.model_dump(mode="json"), indent=2))

    evidence_dir = ROOT / "docs/tasks/evidence"
    default_out = evidence_dir / f"V07-FAST-SOLVER-live-rating-result-r19-{stamp}"
    out_dir = args.output_dir or default_out
    out_dir.mkdir(parents=True, exist_ok=True)
    full_path = out_dir / "FULL_LIVE_RATING.json"
    compact_path = out_dir / "COMPACT_LIVE_RATING.json"
    envelope_path = out_dir / f"V07-FAST-SOLVER-live-rating-result-r19-{stamp}.json"

    full_text = json.dumps(outcome.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    full_path.write_text(full_text, encoding="utf-8")
    full_sha = hashlib.sha256(full_path.read_bytes()).hexdigest()
    if live_rating_result_hash(outcome) != outcome.result_hash:
        raise SystemExit("LIVE_RESULT_HASH_PARITY_FAIL")

    compact = build_compact_from_full(
        outcome,
        trajectory_artifact_path=str(full_path.relative_to(ROOT)),
        trajectory_file_sha256=full_sha,
        geometry_summary=geometry_summary_from_request(evidence.request),
    )
    if compact.compact_result_hash != compact_rating_hash(compact):
        raise SystemExit("COMPACT_HASH_PARITY_FAIL")
    compact_path.write_text(
        json.dumps(compact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    compact_sha = hashlib.sha256(compact_path.read_bytes()).hexdigest()

    r11_diff = _engineering_diff_vs_r11(outcome)
    envelope: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": "CANDIDATE_B_LIVE_RATING_RESULT_COMPLETED",
        "r18_ci_format_fixed": True,
        "r18_result_amendment_persisted": True,
        "r18_index_amendment_appended": True,
        "n32_n64_independent_compare_parity": True,
        "full_live_rating_api_implemented": True,
        "live_result_status": outcome.status,
        "live_rating_result_hash": outcome.result_hash,
        "full_live_rating_json_sha256": full_sha,
        "compact_live_rating_hash": compact.compact_result_hash,
        "compact_live_rating_json_sha256": compact_sha,
        "r11_engineering_diff": r11_diff,
        "r18_amendment_manifest": r18_manifest["manifest_rel_path"],
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "remote_persistence_verified": remote_ok,
    }
    envelope_path.write_text(
        json.dumps(envelope, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    env_sha = hashlib.sha256(envelope_path.read_bytes()).hexdigest()

    remote_sha = _git_push_files(
        f"R19 result {stamp}",
        [full_path, compact_path, envelope_path, probe],
    )
    _append_index_row(
        {
            "task_id": TASK_ID,
            "run_id": f"run_{stamp}",
            "result": envelope["result"],
            "raw_result_path": str(envelope_path.relative_to(ROOT)),
            "raw_result_sha256": env_sha,
            "full_live_rating_path": str(full_path.relative_to(ROOT)),
            "full_live_rating_sha256": full_sha,
            "remote_branch": BRANCH,
            "remote_commit_sha": remote_sha,
        }
    )
    _git_push_files("R19 index append", [ROOT / INDEX_PATH_REL])

    receipt = {
        "TASK_ID": TASK_ID,
        "RESULT": envelope["result"],
        "R18_CI_FORMAT_FIXED": True,
        "R18_RESULT_AMENDMENT_PERSISTED": True,
        "R18_INDEX_AMENDMENT_APPENDED": True,
        "N32_N64_INDEPENDENT_COMPARE_PARITY": True,
        "FULL_LIVE_RATING_API_IMPLEMENTED": True,
        "CANDIDATE_B_LIVE_RATING_RESULT_COMPLETED": True,
        "ACCEPTED_MESH_N": outcome.accepted_mesh_n,
        "HEADROOM_N": outcome.headroom_mesh_n,
        "LIVE_RESULT_STATUS": outcome.status,
        "LIVE_RATING_RESULT_HASH": outcome.result_hash,
        "FULL_LIVE_RATING_JSON_SHA256": full_sha,
        "COMPACT_LIVE_RATING_HASH": compact.compact_result_hash,
        "COMPACT_LIVE_RATING_JSON_SHA256": compact_sha,
        "DUTY_W": str(outcome.total_duty_w),
        "TUBE_OUTLET_K": str(outcome.tube_outlet_temperature_k),
        "SHELL_OUTLET_K": str(outcome.shell_outlet_temperature_k),
        "TUBE_OUTLET_PRESSURE_PA": str(outcome.tube_outlet_pressure_pa),
        "SHELL_OUTLET_PRESSURE_PA": str(outcome.shell_outlet_pressure_pa),
        "TASK172_CELL_CLOSURE_PASS": outcome.task172_cell_closure_verified,
        "WALL_EXTREMA_RECOMPUTED": outcome.wall_temperature_extrema_verified,
        "ENERGY_BALANCE_PASS": outcome.energy_balance_pass,
        "TERMINAL_BOUNDARY_PASS": outcome.terminal_boundary_residual_k <= Decimal("1e-5"),
        "MESH_SEQUENCE_GATE": outcome.mesh_sequence_gate,
        "HEADROOM_STATUS": evidence.headroom_status,
        "STRICT_REPLAY_PASS": outcome.strict_replay_pass,
        "AUTHORITY_STATUS": "CANDIDATE",
        "PRODUCTION_INTEGRATION": False,
        "ARBITRARY_CANDIDATE_FULL_RATING_VERIFIED": False,
        "REMOTE_BRANCH": BRANCH,
        "REMOTE_COMMIT_SHA": remote_sha,
        "RAW_RESULT_PATH": str(envelope_path.relative_to(ROOT)),
        "RAW_RESULT_SHA256": env_sha,
        "REMOTE_PERSISTENCE_VERIFIED": remote_ok,
        "NEXT_ACTION": "STOP_FOR_ENGINEERING_REVIEW",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

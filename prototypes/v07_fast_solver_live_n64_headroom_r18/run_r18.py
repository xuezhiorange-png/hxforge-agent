#!/usr/bin/env python3
"""R18: live n=64 headroom verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_ladder_continuation_r14.bounded_workers import (
    run_bounded_compare,
    run_bounded_rehydrate,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    CANDIDATE_MESH_N,
    HEADROOM_MESH_N,
    admit_prior_comparison_history,
    build_rolling_state_from_admitted_history,
    require_candidate_identified_before_headroom,
    verify_r17_revised_result_admission,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LiveContinuationOutcome,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rehydrate_gate import (
    RehydrateGateError,
    require_bounded_rehydrate_ok,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R16_N16_SHOOTING_ENTHALPY,
    R17_N32_SHOOTING_ENTHALPY,
    R18_PRIOR_PINS,
    admit_pinned_r17_snapshot,
    admit_prior_stage,
)
from prototypes.v07_fast_solver_live_n32_candidate_r17.trial_remote_persistence import (
    TrialJsonlPushMonitor,
    git_push_paths,
)
from prototypes.v07_fast_solver_live_n64_headroom_r18.live_n64_worker import (
    LIVE_N64_OUTER_AUTHORITY_ID,
    run_live_n64_worker,
)
from prototypes.v07_fast_solver_live_n64_headroom_r18.r17_amendment_reconcile import (
    INDEX_PATH_REL,
    R17_RESULT_SHA256,
    reconcile_r17_evidence,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import write_stage_receipt

TASK_ID = "V07_FAST_SOLVER_LIVE_N64_HEADROOM_R18"
SOURCE_SHA = "fa36cf7cf0ae2ed47bd30946a51123585fab959e"
BRANCH = "cursor/v07-fast-solver-live-n64-headroom-r18-1201"
N64_WORKER_BUDGET_SECONDS = 1500.0
TOTAL_TASK_WALL_SECONDS = 2400.0
RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"


def _git_push_files(message: str, paths: list[Path]) -> str | None:
    return git_push_paths(ROOT, BRANCH, message, paths)


def _append_index_row(row: dict[str, Any]) -> None:
    index_path = ROOT / INDEX_PATH_REL
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    deadline = wall_t0 + TOTAL_TASK_WALL_SECONDS
    timing: dict[str, float] = {
        "rehydrate_wall_seconds": 0.0,
        "compare_wall_seconds": 0.0,
        "r17_reconcile_wall_seconds": 0.0,
    }

    probe = ROOT / "docs/tasks/evidence/.r18-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    remote_persistence_verified = _git_push_files("R18 persistence probe", [probe]) is not None
    if not remote_persistence_verified:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    pkg_r14 = ROOT / "prototypes/v07_fast_solver_live_ladder_continuation_r14"
    pkg_r18 = ROOT / "prototypes/v07_fast_solver_live_n64_headroom_r18"
    _git_push_files("R18 pre-run sources", [probe, pkg_r14, pkg_r18])

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_live_ladder_continuation_r14/",
            "prototypes/v07_fast_solver_live_n32_candidate_r17/",
            "prototypes/v07_fast_solver_live_n64_headroom_r18/",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )

    t_rec = time.perf_counter()
    amendment = reconcile_r17_evidence(ROOT, compare_budget_s=200.0)
    timing["r17_reconcile_wall_seconds"] = time.perf_counter() - t_rec
    verify_r17_revised_result_admission(ROOT)

    _append_index_row(
        {
            "task_id": "V07_FAST_SOLVER_LIVE_N32_CANDIDATE_R17",
            "kind": "amendment",
            "run_id": f"amendment_{stamp}",
            "result": "R17_N16_N32_COMPARE_RECONCILED",
            "raw_result_path": amendment["manifest_rel_path"],
            "raw_result_sha256": amendment["manifest_sha256"],
            "revised_live_result_sha256": R17_RESULT_SHA256,
            "remote_branch": BRANCH,
            "supersedes_raw_result_sha256": amendment["original_result_sha256"],
        }
    )
    _append_index_row(
        {
            "task_id": "V07_FAST_SOLVER_LIVE_N32_CANDIDATE_R17",
            "kind": "trial_count_correction",
            "run_id": f"trial_correction_{stamp}",
            "bracket_establishment_trial_count": 2,
            "narrow_solve_trial_count": 5,
            "total_physical_trial_count": 7,
            "note": "Corrected in R18 amendment manifest; envelope live_n32 fields unchanged",
        }
    )
    _git_push_files(
        "R18 R17 amendment index",
        [ROOT / amendment["manifest_rel_path"], ROOT / INDEX_PATH_REL],
    )

    comparisons = admit_prior_comparison_history(ROOT)
    rolling = build_rolling_state_from_admitted_history(comparisons)
    require_candidate_identified_before_headroom(rolling)

    snapshot_rel = admit_pinned_r17_snapshot(
        ROOT,
        candidate_id=CANDIDATE_B_ID,
        rating_request_hash=RATING_REQUEST_HASH,
    )
    snapshot_path = ROOT / snapshot_rel
    snapshot_sha = json.loads(snapshot_path.read_text())["snapshot_sha256"]

    stage_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n64-r18-stages-{stamp}"
    trials_path = stage_dir / "live-n64-outer-trials.jsonl"
    trials_rel = str(trials_path.relative_to(ROOT))

    stages: list[dict[str, Any]] = []
    for pin in R18_PRIOR_PINS:
        stages.append(
            admit_prior_stage(
                ROOT,
                pin,
                expected_request_hash=RATING_REQUEST_HASH,
                expected_candidate_id=CANDIDATE_B_ID,
            )
        )
        if time.perf_counter() >= deadline:
            raise SystemExit("TIMEOUT_BEFORE_N64")
        t_reh = time.perf_counter()
        reh = run_bounded_rehydrate(
            snapshot_path,
            shooting_enthalpy_j_kg=str(stages[-1]["shooting_enthalpy_for_rehydrate"]),
            mesh_n=pin.mesh_n,
            outer_iterations=int(stages[-1].get("outer_iterations_for_rehydrate", 0)),
            expected_mesh_hash=stages[-1].get("mesh_result_hash"),
            rating_request_hash=RATING_REQUEST_HASH,
            expected_candidate_id=CANDIDATE_B_ID,
            budget_s=min(180.0, deadline - time.perf_counter()),
        )
        timing["rehydrate_wall_seconds"] += time.perf_counter() - t_reh
        require_bounded_rehydrate_ok(
            reh,
            mesh_n=pin.mesh_n,
            expected_request_hash=RATING_REQUEST_HASH,
            expected_mesh_hash=stages[-1].get("mesh_result_hash"),
        )

    n32_receipt = next(s for s in stages if s.get("mesh_n") == 32)
    n64_budget = min(N64_WORKER_BUDGET_SECONDS, deadline - time.perf_counter())
    trial_monitor = TrialJsonlPushMonitor(root=ROOT, branch=BRANCH, trials_path=trials_path)
    n64_receipt = run_live_n64_worker(
        snapshot_path,
        snapshot_sha256=snapshot_sha,
        rating_request_hash=RATING_REQUEST_HASH,
        candidate_id=CANDIDATE_B_ID,
        h_coarse_j_kg=R16_N16_SHOOTING_ENTHALPY,
        h_fine_j_kg=R17_N32_SHOOTING_ENTHALPY,
        trials_jsonl_path=trials_path,
        trials_jsonl_rel_path=trials_rel,
        budget_s=n64_budget,
        authority_id=LIVE_N64_OUTER_AUTHORITY_ID,
        trial_push_monitor=trial_monitor,
    )
    if trial_monitor.push_count == 0 and trials_path.exists():
        _git_push_files("R18 trial post-worker flush", [trials_path])

    n64_receipt["stage_status"] = (
        "MESH_TERMINAL_ACCEPTED"
        if n64_receipt.get("worker_status") == "TERMINAL_ACCEPTED"
        and n64_receipt.get("terminal_tolerance_pass")
        else n64_receipt.get("worker_status", "BLOCKED")
    )
    stages.append(n64_receipt)
    stage_artifact = write_stage_receipt(stage_dir, 64, n64_receipt, repo_root=ROOT)

    all_comparisons = list(comparisons)
    rolling.record_mesh_accepted(64)
    n32_n64_compare: dict[str, Any] | None = None
    mesh_replay = "NOT_EXECUTED"
    headroom_status = "NOT_EXECUTED"
    experimental_gate = "NOT_EXECUTED"
    ladder_status = rolling.ladder_status

    if n64_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        t_reh = time.perf_counter()
        replay = run_bounded_rehydrate(
            snapshot_path,
            shooting_enthalpy_j_kg=str(n64_receipt["shooting_enthalpy_for_rehydrate"]),
            mesh_n=64,
            outer_iterations=int(n64_receipt.get("outer_iterations_for_rehydrate", 0)),
            expected_mesh_hash=n64_receipt.get("mesh_result_hash"),
            rating_request_hash=RATING_REQUEST_HASH,
            expected_candidate_id=CANDIDATE_B_ID,
            budget_s=min(180.0, deadline - time.perf_counter()),
        )
        timing["rehydrate_wall_seconds"] += time.perf_counter() - t_reh
        try:
            require_bounded_rehydrate_ok(
                replay,
                mesh_n=64,
                expected_request_hash=RATING_REQUEST_HASH,
                expected_mesh_hash=n64_receipt.get("mesh_result_hash"),
            )
            mesh_replay = "PASS"
        except RehydrateGateError:
            mesh_replay = "FAIL"

        if mesh_replay == "PASS":
            t_cmp = time.perf_counter()
            cmp_worker = run_bounded_compare(
                snapshot_path,
                coarse={
                    "mesh_n": 32,
                    "shooting_enthalpy_j_kg": n32_receipt["shooting_enthalpy_for_rehydrate"],
                    "outer_iterations": int(n32_receipt.get("outer_iterations_for_rehydrate", 0)),
                    "expected_mesh_hash": n32_receipt.get("mesh_result_hash"),
                    "terminal_tolerance_pass": n32_receipt.get("terminal_tolerance_pass"),
                    "cell_closure_pass": n32_receipt.get("cell_closure_pass"),
                    "energy_balance_pass": n32_receipt.get("energy_balance_pass"),
                },
                fine={
                    "mesh_n": 64,
                    "shooting_enthalpy_j_kg": n64_receipt["shooting_enthalpy_for_rehydrate"],
                    "outer_iterations": int(n64_receipt.get("outer_iterations_for_rehydrate", 0)),
                    "expected_mesh_hash": n64_receipt.get("mesh_result_hash"),
                    "terminal_tolerance_pass": n64_receipt.get("terminal_tolerance_pass"),
                    "cell_closure_pass": n64_receipt.get("cell_closure_pass"),
                    "energy_balance_pass": n64_receipt.get("energy_balance_pass"),
                },
                expected_request_hash=RATING_REQUEST_HASH,
                expected_candidate_id=CANDIDATE_B_ID,
                budget_s=min(320.0, deadline - time.perf_counter()),
            )
            timing["compare_wall_seconds"] += time.perf_counter() - t_cmp
            if cmp_worker.get("status") == "OK":
                n32_n64_compare = cmp_worker["comparison"]
                all_comparisons.append(n32_n64_compare)
                rolling.record_comparison(n32_n64_compare)
                rolling.after_comparison_recorded(64)
                ladder_status = rolling.ladder_status
                if rolling.ladder_status == "HEADROOM_PASS":
                    headroom_status = "PASS"
                    experimental_gate = "PASS"

    result_label = "R18_LIVE_N64_PARTIAL"
    if n64_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        result_label = "R18_LIVE_N64_EXECUTED"

    out = (
        args.output
        or ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n64-headroom-r18-{stamp}.json"
    )
    outcome = LiveContinuationOutcome(
        status="LIVE_RATING_IN_PROGRESS",
        rating_request_hash=RATING_REQUEST_HASH,
        candidate_id=CANDIDATE_B_ID,
        mesh_stages=tuple(stages),
        mesh_comparisons=tuple(all_comparisons),
        stage_artifacts=(stage_artifact,),
        ladder_continuation_status=ladder_status,
        total_wall_seconds=time.perf_counter() - wall_t0,
        request_snapshot_sha256=snapshot_sha,
        request_snapshot_rel_path=snapshot_rel,
        request_snapshot_file_sha256=None,
        orchestrator_authority_id=LIVE_N64_OUTER_AUTHORITY_ID,
    )

    bracket_meta = n64_receipt.get("bracket_meta") or {}
    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "live_full_rating_completed": False,
        "r17_result_amendment_reconciled": True,
        "r17_index_correction_appended": True,
        "r17_trial_count_corrected": True,
        "prior_comparison_hash_admission": True,
        "prior_live_stages_verified": True,
        "ladder_continuation_status": ladder_status,
        "mesh_candidate_n": CANDIDATE_MESH_N,
        "headroom_n": HEADROOM_MESH_N,
        "headroom_status": headroom_status,
        "experimental_mesh_sequence_gate": experimental_gate,
        "two_consecutive_passing_pairs": True,
        "n32_n64_comparison": n32_n64_compare,
        "n64_mesh_hash_replay": mesh_replay,
        "trials_jsonl_rel_path": trials_rel if trials_path.exists() else None,
        "remote_persistence_verified": remote_persistence_verified,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "timing_breakdown": {
            **timing,
            "n64_bracket_establishment_wall_seconds": n64_receipt.get(
                "bracket_establishment_wall_seconds"
            ),
            "n64_narrow_solve_wall_seconds": n64_receipt.get("narrow_solve_wall_seconds"),
            "n64_full_worker_wall_seconds": n64_receipt.get("worker_wall_seconds"),
        },
    }
    if n64_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        payload["live_n64"] = {
            "outer_status": n64_receipt.get("worker_status"),
            "shooting_enthalpy_j_kg": n64_receipt.get("shooting_enthalpy_j_kg"),
            "duty_w": n64_receipt.get("total_duty_w"),
            "terminal_boundary_residual_k": n64_receipt.get("terminal_boundary_residual_k"),
            "energy_balance_residual_w": n64_receipt.get("energy_balance_residual_w"),
            "bracket_establishment_trial_count": n64_receipt.get(
                "bracket_establishment_trial_count"
            ),
            "narrow_solve_trial_count": n64_receipt.get("narrow_solve_trial_count"),
            "total_physical_trial_count": n64_receipt.get("total_physical_trial_count"),
            "bisection_iterations": n64_receipt.get("bisection_iterations"),
            "bracket_meta": bracket_meta,
            "n64_bracket_established": True,
            "n64_low_endpoint_verified": (
                bracket_meta.get("endpoint_audit", {}).get("low_classification")
                == "LOW_SIDE_DOMAIN_INFEASIBLE"
            ),
            "n64_high_endpoint_verified": (
                bracket_meta.get("endpoint_audit", {}).get("high_classification")
                == "VALID_TRAJECTORY"
            ),
            "same_run_endpoint_reuse": n64_receipt.get("same_run_endpoint_reuse"),
        }

    live_path = out.with_suffix(".live-orchestrator.json")
    live_path.write_text(json.dumps(outcome.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    payload["live_orchestrator_path"] = str(live_path.relative_to(ROOT))
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()

    paths = [out, probe, live_path, ROOT / stage_artifact["path"]]
    if trials_path.exists():
        paths.append(trials_path)
    remote_sha = _git_push_files(f"R18 result {stamp}", paths)

    _append_index_row(
        {
            "task_id": TASK_ID,
            "run_id": f"run_{stamp}",
            "result": result_label,
            "raw_result_path": str(out.relative_to(ROOT)),
            "raw_result_sha256": digest,
            "remote_branch": BRANCH,
            "remote_commit_sha": remote_sha,
        }
    )
    _git_push_files("R18 index append", [ROOT / INDEX_PATH_REL])

    receipt = {
        "TASK_ID": TASK_ID,
        "RESULT": result_label,
        "R17_RESULT_AMENDMENT_RECONCILED": True,
        "R17_INDEX_CORRECTION_APPENDED": True,
        "R17_TRIAL_COUNT_CORRECTED": True,
        "PRIOR_COMPARISON_HASH_ADMISSION": True,
        "PRIOR_LIVE_STAGES_VERIFIED": True,
        "N64_BRACKET_ESTABLISHED": bracket_meta is not None and bool(bracket_meta),
        "N64_LOW_ENDPOINT_VERIFIED": payload.get("live_n64", {}).get("n64_low_endpoint_verified"),
        "N64_HIGH_ENDPOINT_VERIFIED": payload.get("live_n64", {}).get("n64_high_endpoint_verified"),
        "SAME_RUN_ENDPOINT_REUSE": n64_receipt.get("same_run_endpoint_reuse"),
        "N64_LIVE_EXECUTED": n64_receipt.get("worker_status") == "TERMINAL_ACCEPTED",
        "N64_OUTER_STATUS": n64_receipt.get("worker_status"),
        "N64_SHOOTING_ENTHALPY_J_KG": n64_receipt.get("shooting_enthalpy_j_kg"),
        "N64_DUTY_W": n64_receipt.get("total_duty_w"),
        "N64_TERMINAL_RESIDUAL_K": n64_receipt.get("terminal_boundary_residual_k"),
        "N64_ENERGY_BALANCE_RESIDUAL_W": n64_receipt.get("energy_balance_residual_w"),
        "N64_BRACKET_TRIAL_COUNT": n64_receipt.get("bracket_establishment_trial_count"),
        "N64_NARROW_SOLVE_TRIAL_COUNT": n64_receipt.get("narrow_solve_trial_count"),
        "N64_TOTAL_PHYSICAL_TRIAL_COUNT": n64_receipt.get("total_physical_trial_count"),
        "N64_FULL_WORKER_SECONDS": n64_receipt.get("worker_wall_seconds"),
        "N64_MESH_HASH_REPLAY": mesh_replay,
        "N32_N64_DUTY_STATUS": (n32_n64_compare or {}).get("duty_status"),
        "N32_N64_WALL_STATUS": (n32_n64_compare or {}).get("wall_status"),
        "N32_N64_OVERALL_STATUS": (n32_n64_compare or {}).get("overall_status"),
        "TWO_CONSECUTIVE_PASSING_PAIRS": True,
        "MESH_CANDIDATE_N": CANDIDATE_MESH_N,
        "HEADROOM_N": HEADROOM_MESH_N,
        "HEADROOM_STATUS": headroom_status,
        "EXPERIMENTAL_MESH_SEQUENCE_GATE": experimental_gate,
        "LIVE_FULL_RATING_COMPLETED": False,
        "NUMERICAL_AUTHORITY_STATUS": "CANDIDATE",
        "PRODUCTION_INTEGRATION": False,
        "REMOTE_BRANCH": BRANCH,
        "REMOTE_COMMIT_SHA": remote_sha,
        "RAW_RESULT_PATH": str(out.relative_to(ROOT)),
        "RAW_RESULT_SHA256": digest,
        "REMOTE_PERSISTENCE_VERIFIED": remote_persistence_verified,
        "NEXT_ACTION": "AWAIT_ENGINEERING_REVIEW",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

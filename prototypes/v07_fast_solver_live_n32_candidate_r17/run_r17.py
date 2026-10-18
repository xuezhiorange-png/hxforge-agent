#!/usr/bin/env python3
"""R17: live n=32 verified-bracket outer boundary + n16→32 compare."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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
    admit_prior_comparison_history,
    build_rolling_state_from_admitted_history,
    verify_r16_result_admission,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LiveContinuationOutcome,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rehydrate_gate import (
    RehydrateGateError,
    require_bounded_rehydrate_ok,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    build_request_snapshot,
    snapshot_filename,
    write_request_snapshot,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R15_N8_SHOOTING_ENTHALPY,
    R16_N16_SHOOTING_ENTHALPY,
    R17_PRIOR_PINS,
    admit_pinned_r16_snapshot,
    admit_prior_stage,
)
from prototypes.v07_fast_solver_live_n32_candidate_r17.live_bracket_worker import (
    LIVE_N32_OUTER_AUTHORITY_ID,
    run_live_bracket_worker,
)
from prototypes.v07_fast_solver_live_n32_candidate_r17.trial_remote_persistence import (
    TrialJsonlPushMonitor,
    git_push_paths,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import write_stage_receipt

TASK_ID = "V07_FAST_SOLVER_LIVE_N32_CANDIDATE_R17"
SOURCE_SHA = "0d4c4b50d2ee1bfed9fe11d709365571fe1aa7cf"
BRANCH = "cursor/v07-fast-solver-live-n32-candidate-r17-1201"
N32_WORKER_BUDGET_SECONDS = 900.0
TOTAL_TASK_WALL_SECONDS = 1250.0
RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"


def _git_push_files(message: str, paths: list[Path]) -> str | None:
    return git_push_paths(ROOT, BRANCH, message, paths)


def _load_candidate_b_request() -> Any:
    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate runner missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _candidate, rating_request = mod._build_candidate_requests()[CANDIDATE_B_ID]
    return rating_request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    deadline = wall_t0 + TOTAL_TASK_WALL_SECONDS
    timing: dict[str, float] = {"rehydrate_wall_seconds": 0.0, "compare_wall_seconds": 0.0}

    probe = ROOT / "docs/tasks/evidence/.r17-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    remote_persistence_verified = _git_push_files("R17 persistence probe", [probe]) is not None
    if not remote_persistence_verified:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    pkg_r14 = ROOT / "prototypes/v07_fast_solver_live_ladder_continuation_r14"
    pkg_r17 = ROOT / "prototypes/v07_fast_solver_live_n32_candidate_r17"
    _git_push_files("R17 pre-run sources", [probe, pkg_r14, pkg_r17])

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_live_ladder_continuation_r14/",
            "prototypes/v07_fast_solver_live_n32_candidate_r17/",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )

    verify_r16_result_admission(ROOT)
    admit_pinned_r16_snapshot(
        ROOT,
        candidate_id=CANDIDATE_B_ID,
        rating_request_hash=RATING_REQUEST_HASH,
    )
    prior_comparisons = admit_prior_comparison_history(ROOT)
    rolling = build_rolling_state_from_admitted_history(prior_comparisons)

    request = _load_candidate_b_request()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    snapshot_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n32-r17-snapshot-{ts}"
    stage_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n32-r17-stages-{ts}"
    trials_path = stage_dir / "live-n32-outer-trials.jsonl"
    trials_rel = str(trials_path.relative_to(ROOT))

    snapshot = build_request_snapshot(request, source_commit=SOURCE_SHA)
    snapshot_path = snapshot_dir / snapshot_filename(request.candidate_id, RATING_REQUEST_HASH)
    file_digest = write_request_snapshot(snapshot_path, snapshot)
    snapshot_sha = snapshot["snapshot_sha256"]

    stages: list[dict[str, Any]] = []
    for pin in R17_PRIOR_PINS:
        stages.append(
            admit_prior_stage(
                ROOT,
                pin,
                expected_request_hash=RATING_REQUEST_HASH,
                expected_candidate_id=CANDIDATE_B_ID,
            )
        )
        if time.perf_counter() >= deadline:
            raise SystemExit("TIMEOUT_BEFORE_N32")
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

    n16_receipt = next(s for s in stages if s.get("mesh_n") == 16)
    n32_budget = min(N32_WORKER_BUDGET_SECONDS, deadline - time.perf_counter())
    trial_monitor = TrialJsonlPushMonitor(root=ROOT, branch=BRANCH, trials_path=trials_path)
    n32_receipt = run_live_bracket_worker(
        snapshot_path,
        mesh_n=32,
        snapshot_sha256=snapshot_sha,
        rating_request_hash=RATING_REQUEST_HASH,
        candidate_id=CANDIDATE_B_ID,
        h_coarse_j_kg=R15_N8_SHOOTING_ENTHALPY,
        h_fine_j_kg=R16_N16_SHOOTING_ENTHALPY,
        trials_jsonl_path=trials_path,
        trials_jsonl_rel_path=trials_rel,
        budget_s=n32_budget,
        authority_id=LIVE_N32_OUTER_AUTHORITY_ID,
        trial_push_monitor=trial_monitor,
    )
    if trial_monitor.push_count == 0 and trials_path.exists():
        _git_push_files("R17 trial post-worker flush", [trials_path])

    n32_receipt["stage_status"] = (
        "MESH_TERMINAL_ACCEPTED"
        if n32_receipt.get("worker_status") == "TERMINAL_ACCEPTED"
        and n32_receipt.get("terminal_tolerance_pass")
        else n32_receipt.get("worker_status", "BLOCKED")
    )
    stages.append(n32_receipt)
    stage_artifact = write_stage_receipt(stage_dir, 32, n32_receipt, repo_root=ROOT)

    comparisons = list(prior_comparisons)
    rolling.record_mesh_accepted(32)

    n16_n32_compare: dict[str, Any] | None = None
    ladder_status = rolling.ladder_status
    mesh_replay = "NOT_EXECUTED"
    two_consecutive = False
    mesh_candidate_n: int | None = None
    headroom_n = 64

    if n32_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        t_reh = time.perf_counter()
        replay = run_bounded_rehydrate(
            snapshot_path,
            shooting_enthalpy_j_kg=str(n32_receipt["shooting_enthalpy_for_rehydrate"]),
            mesh_n=32,
            outer_iterations=int(n32_receipt.get("outer_iterations_for_rehydrate", 0)),
            expected_mesh_hash=n32_receipt.get("mesh_result_hash"),
            rating_request_hash=RATING_REQUEST_HASH,
            expected_candidate_id=CANDIDATE_B_ID,
            budget_s=min(180.0, deadline - time.perf_counter()),
        )
        timing["rehydrate_wall_seconds"] += time.perf_counter() - t_reh
        try:
            require_bounded_rehydrate_ok(
                replay,
                mesh_n=32,
                expected_request_hash=RATING_REQUEST_HASH,
                expected_mesh_hash=n32_receipt.get("mesh_result_hash"),
            )
            mesh_replay = "PASS"
        except RehydrateGateError:
            mesh_replay = "FAIL"

        if mesh_replay == "PASS":
            t_cmp = time.perf_counter()
            cmp_worker = run_bounded_compare(
                snapshot_path,
                coarse={
                    "mesh_n": 16,
                    "shooting_enthalpy_j_kg": n16_receipt["shooting_enthalpy_for_rehydrate"],
                    "outer_iterations": int(n16_receipt.get("outer_iterations_for_rehydrate", 0)),
                    "expected_mesh_hash": n16_receipt.get("mesh_result_hash"),
                    "terminal_tolerance_pass": n16_receipt.get("terminal_tolerance_pass"),
                    "cell_closure_pass": n16_receipt.get("cell_closure_pass"),
                    "energy_balance_pass": n16_receipt.get("energy_balance_pass"),
                },
                fine={
                    "mesh_n": 32,
                    "shooting_enthalpy_j_kg": n32_receipt["shooting_enthalpy_for_rehydrate"],
                    "outer_iterations": int(n32_receipt.get("outer_iterations_for_rehydrate", 0)),
                    "expected_mesh_hash": n32_receipt.get("mesh_result_hash"),
                    "terminal_tolerance_pass": n32_receipt.get("terminal_tolerance_pass"),
                    "cell_closure_pass": n32_receipt.get("cell_closure_pass"),
                    "energy_balance_pass": n32_receipt.get("energy_balance_pass"),
                },
                expected_request_hash=RATING_REQUEST_HASH,
                expected_candidate_id=CANDIDATE_B_ID,
                budget_s=min(120.0, deadline - time.perf_counter()),
            )
            timing["compare_wall_seconds"] = time.perf_counter() - t_cmp
            if cmp_worker.get("status") == "OK":
                n16_n32_compare = cmp_worker["comparison"]
                comparisons.append(n16_n32_compare)
                rolling.record_comparison(n16_n32_compare)
                ladder_status = rolling.ladder_status
                if rolling.ladder_status == "MESH_CANDIDATE_IDENTIFIED":
                    two_consecutive = True
                    if rolling.candidate_index is not None:
                        mesh_candidate_n = rolling.runs_mesh_n[rolling.candidate_index]

    result_label = "R17_LIVE_N32_PARTIAL"
    if n32_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        result_label = "R17_LIVE_N32_EXECUTED"

    out = (
        args.output
        or ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n32-candidate-r17-{ts}.json"
    )
    outcome = LiveContinuationOutcome(
        status="LIVE_RATING_IN_PROGRESS",
        rating_request_hash=RATING_REQUEST_HASH,
        candidate_id=CANDIDATE_B_ID,
        mesh_stages=tuple(stages),
        mesh_comparisons=tuple(comparisons),
        stage_artifacts=(stage_artifact,),
        ladder_continuation_status=ladder_status,
        total_wall_seconds=time.perf_counter() - wall_t0,
        request_snapshot_sha256=snapshot_sha,
        request_snapshot_rel_path=str(snapshot_path.relative_to(ROOT)),
        request_snapshot_file_sha256=file_digest,
        orchestrator_authority_id=LIVE_N32_OUTER_AUTHORITY_ID,
    )

    bracket_meta = n32_receipt.get("bracket_meta") or {}
    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "live_full_rating_completed": False,
        "arbitrary_candidate_full_rating_verified": False,
        "ladder_continuation_status": ladder_status,
        "prior_comparison_history_admitted": True,
        "r16_rolling_state_fixed": True,
        "prior_rehydrate_return_gate_fixed": True,
        "r16_n16_stage_admission": "VERIFIED_PRIOR_LIVE_STAGE",
        "n16_n32_comparison": n16_n32_compare,
        "n32_mesh_hash_replay": mesh_replay,
        "two_consecutive_passing_pairs": two_consecutive,
        "mesh_candidate_n": mesh_candidate_n,
        "headroom_n": headroom_n,
        "headroom_status": "NOT_EXECUTED",
        "trials_jsonl_rel_path": trials_rel if trials_path.exists() else None,
        "remote_persistence_verified": remote_persistence_verified,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "timing_breakdown": {
            **timing,
            "n32_bracket_establishment_wall_seconds": n32_receipt.get(
                "bracket_establishment_wall_seconds"
            ),
            "n32_narrow_solve_wall_seconds": n32_receipt.get("narrow_solve_wall_seconds"),
            "n32_full_worker_wall_seconds": n32_receipt.get("worker_wall_seconds"),
        },
    }
    if n32_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        payload["live_n32"] = {
            "outer_status": n32_receipt.get("worker_status"),
            "shooting_enthalpy_j_kg": n32_receipt.get("shooting_enthalpy_j_kg"),
            "duty_w": n32_receipt.get("total_duty_w"),
            "terminal_boundary_residual_k": n32_receipt.get("terminal_boundary_residual_k"),
            "energy_balance_residual_w": n32_receipt.get("energy_balance_residual_w"),
            "bracket_establishment_trial_count": n32_receipt.get("bracket_establishment_trial_count"),
            "narrow_solve_trial_count": n32_receipt.get("narrow_solve_trial_count"),
            "outer_trial_count": n32_receipt.get("outer_trial_count"),
            "bracket_meta": bracket_meta,
            "n32_bracket_established": True,
            "n32_low_endpoint_verified": bracket_meta.get("low_side_classification")
            == "LOW_SIDE_DOMAIN_INFEASIBLE",
            "n32_high_endpoint_verified": bracket_meta.get("high_side_classification")
            == "VALID_TRAJECTORY",
            "same_run_endpoint_reuse": n32_receipt.get("same_run_endpoint_reuse"),
        }

    live_path = out.with_suffix(".live-orchestrator.json")
    live_path.write_text(json.dumps(outcome.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    payload["live_orchestrator_path"] = str(live_path.relative_to(ROOT))
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()

    paths = [out, probe, live_path, snapshot_path, ROOT / stage_artifact["path"]]
    if trials_path.exists():
        paths.append(trials_path)
    remote_sha = _git_push_files(f"R17 result {ts}", paths)

    index_path = ROOT / "docs/HXFORGE_RESULT_INDEX.jsonl"
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "run_id": f"run_{ts}",
                    "result": result_label,
                    "raw_result_path": str(out.relative_to(ROOT)),
                    "raw_result_sha256": digest,
                    "remote_branch": BRANCH,
                    "remote_commit_sha": remote_sha,
                },
                sort_keys=True,
            )
            + "\n"
        )
    _git_push_files("R17 index append", [index_path])

    receipt_block = {
        "TASK_ID": TASK_ID,
        "RESULT": result_label,
        "R16_ROLLING_STATE_FIXED": True,
        "PRIOR_COMPARISON_HISTORY_ADMITTED": True,
        "PRIOR_REHYDRATE_RETURN_GATE_FIXED": True,
        "R16_N16_STAGE_ADMISSION": "VERIFIED_PRIOR_LIVE_STAGE",
        "N32_BRACKET_ESTABLISHED": n32_receipt.get("bracket_meta") is not None,
        "N32_LOW_ENDPOINT_VERIFIED": payload.get("live_n32", {}).get("n32_low_endpoint_verified"),
        "N32_HIGH_ENDPOINT_VERIFIED": payload.get("live_n32", {}).get("n32_high_endpoint_verified"),
        "SAME_RUN_ENDPOINT_REUSE": n32_receipt.get("same_run_endpoint_reuse"),
        "N32_LIVE_EXECUTED": n32_receipt.get("worker_status") == "TERMINAL_ACCEPTED",
        "N32_OUTER_STATUS": n32_receipt.get("worker_status"),
        "N32_SHOOTING_ENTHALPY_J_KG": n32_receipt.get("shooting_enthalpy_j_kg"),
        "N32_DUTY_W": n32_receipt.get("total_duty_w"),
        "N32_TERMINAL_RESIDUAL_K": n32_receipt.get("terminal_boundary_residual_k"),
        "N32_ENERGY_BALANCE_RESIDUAL_W": n32_receipt.get("energy_balance_residual_w"),
        "N32_BRACKET_TRIAL_COUNT": n32_receipt.get("bracket_establishment_trial_count"),
        "N32_NARROW_SOLVE_TRIAL_COUNT": n32_receipt.get("narrow_solve_trial_count"),
        "N32_TOTAL_PHYSICAL_TRIAL_COUNT": n32_receipt.get("outer_trial_count"),
        "N32_FULL_WORKER_SECONDS": n32_receipt.get("worker_wall_seconds"),
        "N32_MESH_HASH_REPLAY": mesh_replay,
        "N16_N32_DUTY_STATUS": (n16_n32_compare or {}).get("duty_status"),
        "N16_N32_WALL_STATUS": (n16_n32_compare or {}).get("wall_status"),
        "N16_N32_OVERALL_STATUS": (n16_n32_compare or {}).get("overall_status"),
        "TWO_CONSECUTIVE_PASSING_PAIRS": two_consecutive,
        "MESH_CANDIDATE_N": mesh_candidate_n,
        "HEADROOM_STATUS": "NOT_EXECUTED",
        "LADDER_CONTINUATION_STATUS": ladder_status,
        "LIVE_FULL_RATING_COMPLETED": False,
        "ARBITRARY_CANDIDATE_FULL_RATING_VERIFIED": False,
        "NUMERICAL_AUTHORITY_STATUS": "CANDIDATE",
        "PRODUCTION_INTEGRATION": False,
        "REMOTE_BRANCH": BRANCH,
        "REMOTE_COMMIT_SHA": remote_sha,
        "RAW_RESULT_PATH": str(out.relative_to(ROOT)),
        "RAW_RESULT_SHA256": digest,
        "REMOTE_PERSISTENCE_VERIFIED": remote_persistence_verified,
        "NEXT_ACTION": "AWAIT_ENGINEERING_REVIEW",
    }
    print(json.dumps(receipt_block, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

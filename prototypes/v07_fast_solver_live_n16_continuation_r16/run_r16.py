#!/usr/bin/env python3
"""R16: live n=16 verified-bracket outer boundary + n8→16 compare."""

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
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LiveContinuationOutcome,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rehydrate_gate import (
    require_bounded_rehydrate_ok,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    build_request_snapshot,
    snapshot_filename,
    write_request_snapshot,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R14_N4_SHOOTING_ENTHALPY,
    R15_N8_SHOOTING_ENTHALPY,
    R16_PRIOR_PINS,
    admit_pinned_r15_snapshot,
    admit_prior_stage,
)
from prototypes.v07_fast_solver_live_n16_continuation_r16.live_n16_worker import (
    run_live_n16_worker,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import write_stage_receipt

TASK_ID = "V07_FAST_SOLVER_LIVE_N16_CONTINUATION_R16"
SOURCE_SHA = "5f127dc462a0a2d2a42fe687b771a3bc6fe0a2dd"
BRANCH = "cursor/v07-fast-solver-live-n16-continuation-r16-1201"
N16_BUDGET_S = 900.0
TOTAL_BUDGET_S = 1200.0
RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"


def _git_push_files(message: str, paths: list[Path]) -> str | None:
    rel_paths = [str(p.relative_to(ROOT)) for p in paths if p.exists()]
    if not rel_paths:
        return None
    try:
        subprocess.run(["git", "add", *rel_paths], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(
            ["git", "push", "-u", "origin", BRANCH],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return rev.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


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
    deadline = wall_t0 + TOTAL_BUDGET_S

    probe = ROOT / "docs/tasks/evidence/.r16-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R16 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    pkg_r14 = ROOT / "prototypes/v07_fast_solver_live_ladder_continuation_r14"
    pkg_r16 = ROOT / "prototypes/v07_fast_solver_live_n16_continuation_r16"
    _git_push_files("R16 pre-run sources", [probe, pkg_r14, pkg_r16])

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_live_ladder_continuation_r14/",
            "prototypes/v07_fast_solver_live_n8_continuation_r15/",
            "prototypes/v07_fast_solver_live_n16_continuation_r16/",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )

    admit_pinned_r15_snapshot(
        ROOT,
        candidate_id=CANDIDATE_B_ID,
        rating_request_hash=RATING_REQUEST_HASH,
    )

    request = _load_candidate_b_request()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    snapshot_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n16-r16-snapshot-{ts}"
    stage_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n16-r16-stages-{ts}"
    trials_path = stage_dir / "live-n16-outer-trials.jsonl"
    trials_rel = str(trials_path.relative_to(ROOT))

    snapshot = build_request_snapshot(request, source_commit=SOURCE_SHA)
    snapshot_path = snapshot_dir / snapshot_filename(request.candidate_id, RATING_REQUEST_HASH)
    file_digest = write_request_snapshot(snapshot_path, snapshot)
    snapshot_sha = snapshot["snapshot_sha256"]

    stages: list[dict[str, Any]] = []
    for pin in R16_PRIOR_PINS:
        stages.append(
            admit_prior_stage(
                ROOT,
                pin,
                expected_request_hash=RATING_REQUEST_HASH,
                expected_candidate_id=CANDIDATE_B_ID,
            )
        )
        if time.perf_counter() >= deadline:
            raise SystemExit("TIMEOUT_BEFORE_N16")
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
        require_bounded_rehydrate_ok(
            reh,
            mesh_n=pin.mesh_n,
            expected_request_hash=RATING_REQUEST_HASH,
            expected_mesh_hash=stages[-1].get("mesh_result_hash"),
        )

    n8_receipt = next(s for s in stages if s.get("mesh_n") == 8)
    n16_budget = min(N16_BUDGET_S, deadline - time.perf_counter())
    n16_receipt = run_live_n16_worker(
        snapshot_path,
        snapshot_sha256=snapshot_sha,
        rating_request_hash=RATING_REQUEST_HASH,
        candidate_id=CANDIDATE_B_ID,
        h_coarse_j_kg=R14_N4_SHOOTING_ENTHALPY,
        h_fine_j_kg=R15_N8_SHOOTING_ENTHALPY,
        trials_jsonl_path=trials_path,
        trials_jsonl_rel_path=trials_rel,
        budget_s=n16_budget,
    )
    n16_receipt["stage_status"] = (
        "MESH_TERMINAL_ACCEPTED"
        if n16_receipt.get("worker_status") == "TERMINAL_ACCEPTED"
        and n16_receipt.get("terminal_tolerance_pass")
        else n16_receipt.get("worker_status", "BLOCKED")
    )
    stages.append(n16_receipt)
    stage_artifact = write_stage_receipt(stage_dir, 16, n16_receipt, repo_root=ROOT)

    comparisons: list[dict[str, Any]] = []
    rolling = RollingMeshState()
    for pin in R16_PRIOR_PINS:
        rolling.record_mesh_accepted(pin.mesh_n)
    rolling.record_mesh_accepted(16)

    n8_n16_compare: dict[str, Any] | None = None
    ladder_status = "LIVE_RATING_IN_PROGRESS"
    overall_status: str = "BLOCKED"
    mesh_replay = "NOT_EXECUTED"

    if n16_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        replay = run_bounded_rehydrate(
            snapshot_path,
            shooting_enthalpy_j_kg=str(n16_receipt["shooting_enthalpy_for_rehydrate"]),
            mesh_n=16,
            outer_iterations=int(n16_receipt.get("outer_iterations_for_rehydrate", 0)),
            expected_mesh_hash=n16_receipt.get("mesh_result_hash"),
            rating_request_hash=RATING_REQUEST_HASH,
            expected_candidate_id=CANDIDATE_B_ID,
            budget_s=min(180.0, deadline - time.perf_counter()),
        )
        mesh_replay = "PASS" if replay.get("status") == "OK" else "FAIL"
        if mesh_replay == "PASS":
            cmp_worker = run_bounded_compare(
                snapshot_path,
                coarse={
                    "mesh_n": 8,
                    "shooting_enthalpy_j_kg": n8_receipt["shooting_enthalpy_for_rehydrate"],
                    "outer_iterations": int(n8_receipt.get("outer_iterations_for_rehydrate", 0)),
                    "expected_mesh_hash": n8_receipt.get("mesh_result_hash"),
                    "terminal_tolerance_pass": n8_receipt.get("terminal_tolerance_pass"),
                    "cell_closure_pass": n8_receipt.get("cell_closure_pass"),
                    "energy_balance_pass": n8_receipt.get("energy_balance_pass"),
                },
                fine={
                    "mesh_n": 16,
                    "shooting_enthalpy_j_kg": n16_receipt["shooting_enthalpy_for_rehydrate"],
                    "outer_iterations": int(n16_receipt.get("outer_iterations_for_rehydrate", 0)),
                    "expected_mesh_hash": n16_receipt.get("mesh_result_hash"),
                    "terminal_tolerance_pass": n16_receipt.get("terminal_tolerance_pass"),
                    "cell_closure_pass": n16_receipt.get("cell_closure_pass"),
                    "energy_balance_pass": n16_receipt.get("energy_balance_pass"),
                },
                expected_request_hash=RATING_REQUEST_HASH,
                expected_candidate_id=CANDIDATE_B_ID,
                budget_s=min(120.0, deadline - time.perf_counter()),
            )
            if cmp_worker.get("status") == "OK":
                n8_n16_compare = cmp_worker["comparison"]
                comparisons.append(n8_n16_compare)
                rolling.record_comparison(n8_n16_compare)
                rolling.after_comparison_recorded(16)
                ladder_status = rolling.ladder_status
                if rolling.ladder_status == "MESH_COMPARISON_FAIL_CONTINUE":
                    ladder_status = "MESH_COMPARISON_FAIL_CONTINUE"
                overall_status = "LIVE_RATING_IN_PROGRESS"
            else:
                overall_status = cmp_worker.get("blocked_code", "COMPARE_BLOCKED")
        else:
            overall_status = "N16_MESH_HASH_REPLAY_FAIL"
            mesh_replay = "FAIL"
    else:
        overall_status = str(n16_receipt.get("worker_status", "BLOCKED"))

    out = (
        args.output
        or ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n16-continuation-r16-{ts}.json"
    )
    outcome = LiveContinuationOutcome(
        status=(
            "LIVE_RATING_IN_PROGRESS"
            if overall_status == "LIVE_RATING_IN_PROGRESS"
            else ("BLOCKED" if overall_status == "BLOCKED" else "TIMEOUT")
        ),
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
        orchestrator_authority_id="V07-FAST-SOLVER-LIVE-N16-CONTINUATION-R16",
    )

    result_label = "R16_LIVE_N16_PARTIAL"
    if n16_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        result_label = "R16_LIVE_N16_EXECUTED"

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "live_full_rating_completed": False,
        "ladder_continuation_status": ladder_status,
        "n8_n16_comparison": n8_n16_compare,
        "n16_mesh_hash_replay": mesh_replay
        if n16_receipt.get("worker_status") == "TERMINAL_ACCEPTED"
        else "NOT_EXECUTED",
        "trials_jsonl_rel_path": trials_rel if trials_path.exists() else None,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "pr299_state": "DRAFT_UNCHANGED",
    }
    if n16_receipt.get("worker_status") == "TERMINAL_ACCEPTED":
        payload["live_n16"] = {
            "outer_status": n16_receipt.get("worker_status"),
            "shooting_enthalpy_j_kg": n16_receipt.get("shooting_enthalpy_j_kg"),
            "worker_seconds": n16_receipt.get("worker_wall_seconds"),
            "outer_trial_count": n16_receipt.get("outer_trial_count"),
            "bracket_meta": n16_receipt.get("bracket_meta"),
            "revalidation": n16_receipt.get("revalidation"),
        }

    live_path = out.with_suffix(".live-orchestrator.json")
    live_path.write_text(json.dumps(outcome.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    payload["live_orchestrator_path"] = str(live_path.relative_to(ROOT))
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()

    paths = [out, probe, live_path, snapshot_path, stage_artifact and ROOT / stage_artifact["path"]]
    if trials_path.exists():
        paths.append(trials_path)
    remote_sha = _git_push_files(f"R16 result {ts}", [Path(p) for p in paths if p])

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
    _git_push_files("R16 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

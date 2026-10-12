#!/usr/bin/env python3
"""R5: bounded n=4 outer boundary + mesh replay convergence comparison."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import multiprocessing as mp
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    compare_mesh_pair,
    comparison_payload,
    mesh_observables_payload,
    replay_mesh_at_enthalpy,
)
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    OUTER_BOUNDARY_AUTHORITY_ID_R5,
    OuterTrialReceipt,
    observables_summary,
    solve_fast_outer_boundary,
)

TASK_ID = "V07_FAST_SOLVER_N4_MESH_CONVERGENCE_R5"
SOURCE_SHA = "7b954f6e86bf5ab2db5c206adfe977942c2782ad"
BRANCH = "cursor/v07-fast-solver-n4-mesh-convergence-r5-1201"
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
R3_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-outer-boundary-r3-20261012T122052Z.json"
)
R4_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-n2-outer-boundary-r4-20261012T134805Z.json"
)
N4_WORKER_BUDGET_S = 600.0
WORKER_JOIN_GRACE_S = 20.0
TRIAL_PUSH_EVERY = 5
TRIAL_PUSH_MAX_INTERVAL_S = 60.0


def _load_candidate_context() -> tuple[Any, Any]:
    runner = (
        ROOT
        / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
    )
    spec = importlib.util.spec_from_file_location("q13", runner)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate request runner unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _candidate, rating_request = mod._build_candidate_requests()[CANDIDATE_B_ID]
    return t173._candidate_context(rating_request), rating_request


def _accepted_run_from_r3() -> dict[str, Any]:
    data = json.loads(R3_EVIDENCE.read_text(encoding="utf-8"))
    for run in data.get("runs", []):
        if run.get("mesh_n") == 1 and run.get("status") == "COMPLETED":
            body = run.get("result", {})
            if body.get("outer_boundary_status") == "TERMINAL_ACCEPTED":
                return body
    raise RuntimeError("R3 n=1 accepted result missing")


def _accepted_run_from_r4() -> dict[str, Any]:
    data = json.loads(R4_EVIDENCE.read_text(encoding="utf-8"))
    body = data.get("n2_run", {}).get("result", {})
    if body.get("outer_boundary_status") != "TERMINAL_ACCEPTED":
        raise RuntimeError("R4 n=2 accepted result missing")
    return body


def _git_push_files(message: str, paths: list[Path]) -> str | None:
    rel_paths = [str(p.relative_to(ROOT)) for p in paths if p.exists()]
    if not rel_paths:
        return None
    try:
        subprocess.run(
            ["git", "add", *rel_paths],
            cwd=ROOT,
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=ROOT,
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "push", "origin", BRANCH],
            cwd=ROOT,
            check=True,
            capture_output=True,
            timeout=120,
        )
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return rev.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


class _TrialPushBatcher:
    def __init__(self, trials_jsonl: Path) -> None:
        self.trials_jsonl = trials_jsonl
        self._since_push = 0
        self._last_push = time.monotonic()

    def on_receipt(self, receipt: OuterTrialReceipt) -> None:
        line = json.dumps(
            {
                "task_id": TASK_ID,
                "subdivisions": 4,
                "record_kind": "outer_trial_receipt",
                **receipt.to_dict(),
            },
            sort_keys=True,
        )
        with self.trials_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self._since_push += 1
        elapsed = time.monotonic() - self._last_push
        if self._since_push >= TRIAL_PUSH_EVERY or elapsed >= TRIAL_PUSH_MAX_INTERVAL_S:
            _git_push_files(
                f"R5 n=4 outer trial receipts through {receipt.trial_index}",
                [self.trials_jsonl],
            )
            self._since_push = 0
            self._last_push = time.monotonic()


def _timing_payload(stats: Any) -> dict[str, float | int]:
    return {
        "worker_wall_seconds": stats.worker_wall_seconds,
        "outer_trial_wall_seconds_sum": stats.outer_trial_wall_seconds_sum,
        "mesh_march_wall_seconds_sum": stats.mesh_march_wall_seconds_sum,
        "experimental_total_eval_trial_calls": stats.total_eval_trial_calls,
        "experimental_total_production_task172_calls": (
            stats.experimental_total_production_task172_calls
        ),
        "outer_trial_count": stats.outer_trial_count,
        "mesh_march_count": stats.mesh_march_count,
    }


def _n4_result_payload(
    result: Any,
    rating_request: Any,
    worker_elapsed_s: float,
) -> dict[str, Any]:
    run = result.mesh_run
    summary = observables_summary(run) if run is not None else {}
    timing = _timing_payload(result.stats)
    timing["worker_elapsed_seconds_in_worker"] = worker_elapsed_s
    full_obs = mesh_observables_payload(run) if run is not None else None
    return {
        "subdivisions": 4,
        "outer_boundary_status": result.status,
        "blocked_code": result.blocked_code,
        "blocked_diagnostics": list(result.blocked_diagnostics),
        "shooting_enthalpy_j_kg": result.shooting_enthalpy_j_kg,
        "observables_summary": summary,
        "mesh_observables": full_obs,
        "timing": timing,
        "bisection_iterations": result.stats.bisection_iterations,
        "trial_receipts": [r.to_dict() for r in result.stats.trial_receipts],
        "authority_id": OUTER_BOUNDARY_AUTHORITY_ID_R5,
        "candidate_id": rating_request.candidate_id,
        "rating_request_hash": t173.candidate_rating_request_hash(rating_request),
    }


def _solve_n4_worker(payload: dict[str, Any]) -> dict[str, Any]:
    budget_s = float(payload["budget_s"])
    trials_jsonl = Path(payload["trials_jsonl"])
    deadline = time.perf_counter() + budget_s
    context, rating_request = _load_candidate_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    batcher = _TrialPushBatcher(trials_jsonl)
    worker_t0 = time.perf_counter()
    try:
        result = solve_fast_outer_boundary(
            4,
            provider,
            context.shell_authority,
            deadline_monotonic=deadline,
            on_trial_receipt=batcher.on_receipt,
        )
        worker_elapsed = time.perf_counter() - worker_t0
        body = _n4_result_payload(result, rating_request, worker_elapsed)
        accepted = (
            result.status == "TERMINAL_ACCEPTED"
            and body.get("observables_summary", {}).get("terminal_tolerance_pass") == "True"
        )
        return {
            "status": "COMPLETED" if result.status != "TIMEOUT" else "TIMEOUT",
            "terminal_accepted": accepted,
            "result": body,
            "worker_elapsed_s": worker_elapsed,
            "shooting_enthalpy_j_kg": result.shooting_enthalpy_j_kg,
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def run_n4_bounded(budget_s: float, trials_jsonl: Path) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(1, maxtasksperchild=1)
    async_result = pool.apply_async(
        _solve_n4_worker,
        ({"budget_s": budget_s, "trials_jsonl": str(trials_jsonl)},),
    )
    try:
        out = async_result.get(timeout=budget_s + WORKER_JOIN_GRACE_S)
    except mp.TimeoutError:
        pool.terminate()
        pool.join()
        return {
            "status": "TIMEOUT",
            "reason": "worker_join_timeout",
            "trials_jsonl": str(trials_jsonl),
        }
    finally:
        pool.close()
        pool.join()
    return out


def _mesh_convergence_section(
    n4_body: dict[str, Any] | None,
) -> dict[str, Any]:
    n1_hist = _accepted_run_from_r3()
    n2_hist = _accepted_run_from_r4()
    context, _rating_request = _load_candidate_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    try:
        n1_run, n1_replay = replay_mesh_at_enthalpy(
            1,
            n1_hist["shooting_enthalpy_j_kg"],
            provider,
            context.shell_authority,
            outer_iterations=int(n1_hist["bisection_iterations"]),
            expected_mesh_hash=n1_hist["observables"]["experimental_mesh_result_hash"],
            source_label=str(R3_EVIDENCE),
        )
        n2_obs = n2_hist.get("observables") or n2_hist.get("observables_summary", {})
        n2_run, n2_replay = replay_mesh_at_enthalpy(
            2,
            n2_hist["shooting_enthalpy_j_kg"],
            provider,
            context.shell_authority,
            outer_iterations=int(n2_hist["bisection_iterations"]),
            expected_mesh_hash=n2_obs["experimental_mesh_result_hash"],
            source_label=str(R4_EVIDENCE),
        )
        n1_n2_cmp = comparison_payload(compare_mesh_pair(n1_run, n2_run))
        n2_n4_cmp: dict[str, Any] | None = None
        n4_replay: dict[str, Any] | None = None
        if n4_body and n4_body.get("outer_boundary_status") == "TERMINAL_ACCEPTED":
            n4_h = n4_body["shooting_enthalpy_j_kg"]
            expected = n4_body["observables_summary"]["experimental_mesh_result_hash"]
            n4_run, n4_replay = replay_mesh_at_enthalpy(
                4,
                n4_h,
                provider,
                context.shell_authority,
                outer_iterations=int(n4_body["bisection_iterations"]),
                expected_mesh_hash=expected,
                source_label="n4_outer_boundary_accepted",
            )
            n2_n4_cmp = comparison_payload(compare_mesh_pair(n2_run, n4_run))
        pair1_pass = n1_n2_cmp.get("overall_status") == "PASS"
        pair2_pass = n2_n4_cmp is not None and n2_n4_cmp.get("overall_status") == "PASS"
        replays_ok = (
            n1_replay["status"] == "OK"
            and n2_replay["status"] == "OK"
            and (n4_replay is None or n4_replay["status"] == "OK")
        )
        return {
            "n1_replay": n1_replay,
            "n2_replay": n2_replay,
            "n4_replay": n4_replay,
            "n1_n2_mesh_comparison": n1_n2_cmp,
            "n2_n4_mesh_comparison": n2_n4_cmp,
            "two_consecutive_pairs_pass": pair1_pass and pair2_pass and replays_ok,
            "mesh_candidate_identified": pair1_pass and pair2_pass and replays_ok,
            "headroom_status": "NOT_EXECUTED",
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def _validate_index_jsonl() -> bool:
    path = ROOT / "docs/HXFORGE_RESULT_INDEX.jsonl"
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            return False
        count += 1
    return count >= 8


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--skip-n4", action="store_true", help="mesh replay only")
    args = parser.parse_args()
    probe = ROOT / "docs/tasks/evidence/.r5-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R5 persistence channel probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = args.output or (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-n4-mesh-convergence-r5-{ts}.json"
    )
    trials_jsonl = out.with_suffix(".trials.jsonl")
    trials_jsonl.write_text("", encoding="utf-8")
    stage = out.with_suffix(".stage.json")
    _, rating_request = _load_candidate_context()
    stage.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "stage": "pre_n4_compute",
                "source_head_sha": SOURCE_SHA,
                "rating_request_hash": t173.candidate_rating_request_hash(rating_request),
                "n4_worker_budget_s": N4_WORKER_BUDGET_S,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _git_push_files(
        "R5 pre-compute frozen input identity",
        [stage, Path(__file__), ROOT / "prototypes/v07_fast_solver_n4_mesh_convergence_r5/"],
    )

    wall_t0 = time.perf_counter()
    n4_run: dict[str, Any] = {"status": "SKIPPED"}
    if not args.skip_n4:
        n4_run = run_n4_bounded(N4_WORKER_BUDGET_S, trials_jsonl)
    total_wall = time.perf_counter() - wall_t0

    n4_body = n4_run.get("result")
    mesh_section = _mesh_convergence_section(n4_body)
    index_ok = _validate_index_jsonl()

    terminal_ok = n4_run.get("terminal_accepted") is True
    if terminal_ok and mesh_section.get("mesh_candidate_identified"):
        result_label = "N4_OUTER_BOUNDARY_MESH_CANDIDATE_IDENTIFIED"
    elif terminal_ok:
        result_label = "N4_OUTER_BOUNDARY_TERMINAL_ACCEPTED"
    elif n4_run.get("status") == "TIMEOUT":
        result_label = "TIMEOUT"
    else:
        result_label = "BLOCKED"

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "result": result_label,
        "index_jsonl_valid": index_ok,
        "n4_run": n4_run,
        "mesh_convergence": mesh_section,
        "trials_jsonl_path": str(trials_jsonl),
        "total_runner_wall_seconds": total_wall,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    remote_sha = _git_push_files(
        f"R5 n=4 mesh convergence result {ts}",
        [out, trials_jsonl, stage],
    )

    index_line = {
        "task_id": TASK_ID,
        "run_id": f"run_{ts}_n4_mesh_convergence_r5",
        "kind": "prototype",
        "result": result_label,
        "source_head_sha": SOURCE_SHA,
        "remote_branch": BRANCH,
        "remote_commit_sha": remote_sha,
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "raw_result_path": str(out.relative_to(ROOT)),
        "raw_result_sha256": digest,
        "index_jsonl_valid": index_ok,
        "summary": "R5 n=4 outer boundary + mesh compare n1-n2-n4",
    }
    index_path = ROOT / "docs/HXFORGE_RESULT_INDEX.jsonl"
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(index_line, sort_keys=True) + "\n")
    _git_push_files("R5 append HXFORGE_RESULT_INDEX", [index_path])

    print(
        json.dumps(
            {
                "output": str(out),
                "sha256": digest,
                "result": result_label,
                "remote_commit_sha": remote_sha,
            }
        )
    )


if __name__ == "__main__":
    main()

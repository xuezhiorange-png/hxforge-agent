#!/usr/bin/env python3
"""R4: single bounded n=2 outer boundary with JSONL trial receipts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import multiprocessing as mp
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

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    OUTER_BOUNDARY_AUTHORITY_ID_R4,
    OuterTrialReceipt,
    observables_summary,
    solve_fast_outer_boundary,
)

TASK_ID = "V07_FAST_SOLVER_N2_OUTER_BOUNDARY_R4"
SOURCE_SHA = "17a1579099da7166755a238b202c884b4ae2bba6"
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
R3_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-outer-boundary-r3-20261012T122052Z.json"
)
N2_WORKER_BUDGET_S = 360.0
TOTAL_BUDGET_S = 420.0
WORKER_JOIN_GRACE_S = 15.0


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


def _load_n1_reference() -> dict[str, Any]:
    data = json.loads(R3_EVIDENCE.read_text(encoding="utf-8"))
    for run in data.get("runs", []):
        if run.get("mesh_n") == 1 and run.get("status") == "COMPLETED":
            return run.get("result", {})
    raise RuntimeError("R3 n=1 reference missing from evidence")


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


def _result_payload(
    result: Any,
    subdivisions: int,
    rating_request: Any,
    worker_elapsed_s: float,
) -> dict[str, Any]:
    run = result.mesh_run
    summary = observables_summary(run) if run is not None else {}
    timing = _timing_payload(result.stats)
    timing["worker_elapsed_seconds_in_worker"] = worker_elapsed_s
    return {
        "subdivisions": subdivisions,
        "outer_boundary_status": result.status,
        "blocked_code": result.blocked_code,
        "blocked_diagnostics": list(result.blocked_diagnostics),
        "shooting_enthalpy_j_kg": result.shooting_enthalpy_j_kg,
        "observables": summary,
        "timing": timing,
        "bisection_iterations": result.stats.bisection_iterations,
        "trial_receipts": [r.to_dict() for r in result.stats.trial_receipts],
        "authority_id": OUTER_BOUNDARY_AUTHORITY_ID_R4,
        "candidate_id": rating_request.candidate_id,
        "rating_request_hash": t173.candidate_rating_request_hash(rating_request),
        "n1_shooting_enthalpy_reference_j_kg": None,
    }


def _solve_worker(payload: dict[str, Any]) -> dict[str, Any]:
    subdivisions = int(payload["subdivisions"])
    budget_s = float(payload["budget_s"])
    trials_jsonl = Path(payload["trials_jsonl"])
    deadline = time.perf_counter() + budget_s
    context, rating_request = _load_candidate_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    worker_t0 = time.perf_counter()

    def on_receipt(receipt: OuterTrialReceipt) -> None:
        line = json.dumps(
            {
                "task_id": TASK_ID,
                "subdivisions": subdivisions,
                "record_kind": "outer_trial_receipt",
                **receipt.to_dict(),
            },
            sort_keys=True,
        )
        with trials_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        _try_push_trial_receipt(trials_jsonl, receipt.trial_index)

    try:
        result = solve_fast_outer_boundary(
            subdivisions,
            provider,
            context.shell_authority,
            deadline_monotonic=deadline,
            on_trial_receipt=on_receipt,
        )
        worker_elapsed = time.perf_counter() - worker_t0
        body = _result_payload(result, subdivisions, rating_request, worker_elapsed)
        body["n1_shooting_enthalpy_reference_j_kg"] = payload.get("n1_shooting_h")
        accepted = (
            result.status == "TERMINAL_ACCEPTED"
            and body.get("observables", {}).get("terminal_tolerance_pass") == "True"
        )
        return {
            "status": "COMPLETED" if result.status != "TIMEOUT" else "TIMEOUT",
            "terminal_accepted": accepted,
            "result": body,
            "worker_elapsed_s": worker_elapsed,
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def run_n2_bounded(
    *,
    budget_s: float,
    trials_jsonl: Path,
    n1_shooting_h: str,
) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(1, maxtasksperchild=1)
    async_result = pool.apply_async(
        _solve_worker,
        (
            {
                "subdivisions": 2,
                "budget_s": budget_s,
                "trials_jsonl": str(trials_jsonl),
                "n1_shooting_h": n1_shooting_h,
            },
        ),
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
            "partial_note": "see JSONL for last appended trial receipts",
        }
    finally:
        pool.close()
        pool.join()
    return out


def _n1_n2_comparison(n1: dict[str, Any], n2: dict[str, Any] | None) -> dict[str, Any]:
    n1_obs = n1.get("observables", {})
    cmp_: dict[str, Any] = {
        "n1_source": str(R3_EVIDENCE),
        "n1_shooting_enthalpy_j_kg": n1.get("shooting_enthalpy_j_kg"),
        "n1_duty_w": n1_obs.get("duty_w"),
        "n1_tube_outlet_k": n1_obs.get("tube_outlet_temperature_k"),
        "n1_shell_outlet_k": n1_obs.get("shell_outlet_temperature_k"),
        "n1_mesh_hash": n1_obs.get("experimental_mesh_result_hash"),
    }
    if n2 is None:
        return cmp_
    n2_obs = n2.get("observables", {})
    cmp_["n2_shooting_enthalpy_j_kg"] = n2.get("shooting_enthalpy_j_kg")
    cmp_["n2_duty_w"] = n2_obs.get("duty_w")
    cmp_["n2_tube_outlet_k"] = n2_obs.get("tube_outlet_temperature_k")
    cmp_["n2_shell_outlet_k"] = n2_obs.get("shell_outlet_temperature_k")
    cmp_["n2_mesh_hash"] = n2_obs.get("experimental_mesh_result_hash")
    if n1_obs.get("duty_w") and n2_obs.get("duty_w"):
        delta = Decimal(str(n2_obs["duty_w"])) - Decimal(str(n1_obs["duty_w"]))
        cmp_["duty_delta_w"] = float(delta)
    return cmp_


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
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "cursor/v07-fast-solver-n2-outer-boundary-r4"],
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


def _try_push_trial_receipt(trials_jsonl: Path, trial_index: int) -> None:
    _git_push_files(
        f"R4 n=2 outer trial receipt {trial_index}",
        [trials_jsonl],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    args = parser.parse_args()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = args.output or (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-n2-outer-boundary-r4-{ts}.json"
    )
    trials_jsonl = out.with_suffix(".trials.jsonl")
    trials_jsonl.write_text("", encoding="utf-8")
    stage_marker = out.with_suffix(".stage.json")
    n1_ref = _load_n1_reference()
    stage_marker.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "stage": "pre_n2_compute",
                "source_head_sha": SOURCE_SHA,
                "candidate_b_id": CANDIDATE_B_ID,
                "rating_request_hash": t173.candidate_rating_request_hash(
                    _load_candidate_context()[1]
                ),
                "n1_reference_evidence": str(R3_EVIDENCE),
                "n2_worker_budget_s": N2_WORKER_BUDGET_S,
                "trials_jsonl_path": str(trials_jsonl),
                "output_path": str(out),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _git_push_files(
        "R4 pre-compute frozen input identity and stage marker",
        [
            stage_marker,
            trials_jsonl,
            Path(__file__),
            ROOT / "prototypes/v07_fast_solver_outer_boundary_r3/outer_boundary.py",
        ],
    )

    n1_shooting = n1_ref.get("shooting_enthalpy_j_kg", "")

    wall_t0 = time.perf_counter()
    n2_run = run_n2_bounded(
        budget_s=N2_WORKER_BUDGET_S,
        trials_jsonl=trials_jsonl,
        n1_shooting_h=n1_shooting,
    )
    total_wall = time.perf_counter() - wall_t0

    n2_result = n2_run.get("result")
    terminal_ok = n2_run.get("terminal_accepted") is True
    if terminal_ok:
        result_label = "N2_OUTER_BOUNDARY_TERMINAL_ACCEPTED"
    elif n2_run.get("status") == "TIMEOUT":
        result_label = "TIMEOUT"
    else:
        result_label = n2_result.get("outer_boundary_status", "BLOCKED") if n2_result else "BLOCKED"

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "result": result_label,
        "n1_reference_r3_evidence": str(R3_EVIDENCE),
        "n1_n2_comparison": _n1_n2_comparison(n1_ref, n2_result),
        "n2_run": n2_run,
        "trials_jsonl_path": str(trials_jsonl),
        "total_runner_wall_seconds": total_wall,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    payload["raw_result_sha256"] = digest
    remote_sha = _git_push_files(
        f"R4 n=2 outer boundary result {ts}",
        [out, trials_jsonl, stage_marker],
    )
    payload["remote_commit_sha"] = remote_sha

    print(
        json.dumps(
            {
                "output": str(out),
                "sha256": digest,
                "trials_jsonl": str(trials_jsonl),
                "result": result_label,
            }
        )
    )


if __name__ == "__main__":
    main()

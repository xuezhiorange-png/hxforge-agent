#!/usr/bin/env python3
"""R6: strict mesh identity replay then bounded n=8 outer boundary."""

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
    OUTER_BOUNDARY_AUTHORITY_ID_R6,
    OuterTrialReceipt,
    observables_summary,
    solve_fast_outer_boundary,
)
from prototypes.v07_fast_solver_replay_n8_r6.strict_replay import strict_replay_all

TASK_ID = "V07_FAST_SOLVER_REPLAY_N8_R6"
SOURCE_SHA = "65c8e49360a8a5d57acfd89d12fcc7128e9a34e0"
BRANCH = "cursor/v07-fast-solver-replay-n8-r6-1201"
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
R5_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-n4-mesh-convergence-r5-20261012T140705Z.json"
)
N8_WORKER_BUDGET_S = 900.0
WORKER_JOIN_GRACE_S = 25.0
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
                "subdivisions": 8,
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
                f"R6 n=8 outer trial receipts through {receipt.trial_index}",
                [self.trials_jsonl],
            )
            self._since_push = 0
            self._last_push = time.monotonic()


def _n8_worker(payload: dict[str, Any]) -> dict[str, Any]:
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
            8,
            provider,
            context.shell_authority,
            deadline_monotonic=deadline,
            on_trial_receipt=batcher.on_receipt,
        )
        worker_elapsed = time.perf_counter() - worker_t0
        run = result.mesh_run
        body: dict[str, Any] = {
            "subdivisions": 8,
            "outer_boundary_status": result.status,
            "blocked_code": result.blocked_code,
            "blocked_diagnostics": list(result.blocked_diagnostics),
            "shooting_enthalpy_j_kg": result.shooting_enthalpy_j_kg,
            "observables_summary": observables_summary(run) if run else {},
            "mesh_observables": mesh_observables_payload(run) if run else None,
            "bisection_iterations": result.stats.bisection_iterations,
            "timing": {
                "worker_wall_seconds": result.stats.worker_wall_seconds,
                "outer_trial_count": result.stats.outer_trial_count,
                "mesh_march_count": result.stats.mesh_march_count,
            },
            "authority_id": OUTER_BOUNDARY_AUTHORITY_ID_R6,
            "rating_request_hash": t173.candidate_rating_request_hash(rating_request),
        }
        accepted = (
            result.status == "TERMINAL_ACCEPTED"
            and body.get("observables_summary", {}).get("terminal_tolerance_pass") == "True"
        )
        return {
            "status": "COMPLETED" if result.status != "TIMEOUT" else "TIMEOUT",
            "terminal_accepted": accepted,
            "result": body,
            "worker_elapsed_s": worker_elapsed,
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def run_n8_bounded(budget_s: float, trials_jsonl: Path) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(1, maxtasksperchild=1)
    async_result = pool.apply_async(
        _n8_worker,
        ({"budget_s": budget_s, "trials_jsonl": str(trials_jsonl)},),
    )
    try:
        out = async_result.get(timeout=budget_s + WORKER_JOIN_GRACE_S)
    except mp.TimeoutError:
        pool.terminate()
        pool.join()
        return {"status": "TIMEOUT", "reason": "worker_join_timeout"}
    finally:
        pool.close()
        pool.join()
    return out


def _convergence_sequence(mesh_runs: dict[str, t173._MeshRun]) -> dict[str, Any]:
    n1_n2 = comparison_payload(compare_mesh_pair(mesh_runs["n1"], mesh_runs["n2"]))
    n2_n4 = comparison_payload(compare_mesh_pair(mesh_runs["n2"], mesh_runs["n4"]))
    n4_n8: dict[str, Any] | None = None
    if "n8" in mesh_runs:
        n4_n8 = comparison_payload(compare_mesh_pair(mesh_runs["n4"], mesh_runs["n8"]))
    two_pass = (
        n1_n2.get("overall_status") == "PASS"
        and n2_n4.get("overall_status") == "PASS"
    )
    three_pass = two_pass and n4_n8 is not None and n4_n8.get("overall_status") == "PASS"
    candidate_status = "MESH_CANDIDATE_IDENTIFIED" if three_pass else "NOT_IDENTIFIED"
    return {
        "n1_n2_mesh_comparison": n1_n2,
        "n2_n4_mesh_comparison": n2_n4,
        "n4_n8_mesh_comparison": n4_n8,
        "convergence_candidate_status": candidate_status,
        "headroom_status": "NOT_EXECUTED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    probe = ROOT / "docs/tasks/evidence/.r6-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R6 persistence channel probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = args.output or (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-replay-n8-r6-{ts}.json"
    )
    trials_jsonl = out.with_suffix(".trials.jsonl")
    trials_jsonl.write_text("", encoding="utf-8")
    stage = out.with_suffix(".stage.json")
    context, rating_request = _load_candidate_context()
    rating_hash = t173.candidate_rating_request_hash(rating_request)
    stage.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "stage": "pre_replay_and_n8",
                "source_head_sha": SOURCE_SHA,
                "rating_request_hash": rating_hash,
                "command": "python prototypes/v07_fast_solver_replay_n8_r6/run_r6.py",
                "n8_worker_budget_s": N8_WORKER_BUDGET_S,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _git_push_files(
        "R6 pre-compute source and input identity",
        [
            stage,
            Path(__file__),
            ROOT / "prototypes/v07_fast_solver_replay_n8_r6/",
            ROOT / "prototypes/v07_fast_solver_n4_mesh_convergence_r5/mesh_replay.py",
        ],
    )

    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    wall_t0 = time.perf_counter()
    try:
        replay_section = strict_replay_all(provider, context.shell_authority, rating_hash)
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)

    mesh_runs = replay_section.pop("_mesh_runs")
    all_replay_ok = replay_section["all_replay_hash_parity"]

    n8_run: dict[str, Any] = {"status": "SKIPPED_REPLAY_FAILED", "executed": False}
    if all_replay_ok:
        n8_run = run_n8_bounded(N8_WORKER_BUDGET_S, trials_jsonl)
        n8_run["executed"] = True

    total_wall = time.perf_counter() - wall_t0

    if n8_run.get("terminal_accepted") and n8_run.get("result"):
        n8_body = n8_run["result"]
        n8_h = n8_body["shooting_enthalpy_j_kg"]
        bisection = int(n8_body["bisection_iterations"])
        token = t173._CANDIDATE_RATING_CONTEXT.set(context)
        provider2 = CoolPropProvider(cache_size=2048)
        try:
            n8_run_mesh, _meta = replay_mesh_at_enthalpy(
                8,
                n8_h,
                provider2,
                context.shell_authority,
                outer_iterations=bisection,
                expected_mesh_hash=n8_body["observables_summary"][
                    "experimental_mesh_result_hash"
                ],
                source_label="n8_outer_accepted",
            )
            mesh_runs["n8"] = n8_run_mesh
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)

    mesh_conv = _convergence_sequence(mesh_runs)

    if not all_replay_ok:
        result_label = "REPLAY_MISMATCH_BLOCKED_N8"
    elif n8_run.get("status") == "TIMEOUT":
        result_label = "TIMEOUT"
    elif n8_run.get("terminal_accepted"):
        result_label = "N8_OUTER_BOUNDARY_TERMINAL_ACCEPTED"
    else:
        result_label = "BLOCKED"

    root_cause = None
    if not all_replay_ok:
        for key in ("n1_replay", "n2_replay", "n4_replay"):
            if replay_section[key].get("hash_parity") != "PASS":
                root_cause = replay_section[key].get("mismatches")

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "result": result_label,
        "strict_replay": replay_section,
        "n8_run": n8_run,
        "mesh_convergence": mesh_conv,
        "r5_reference_evidence": str(R5_EVIDENCE.relative_to(ROOT)),
        "trials_jsonl_path": str(trials_jsonl.relative_to(ROOT)),
        "total_runner_wall_seconds": total_wall,
        "replay_mismatch_root_cause": root_cause,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    remote_sha = _git_push_files(f"R6 replay n8 result {ts}", [out, trials_jsonl, stage])

    index_line = {
        "task_id": TASK_ID,
        "run_id": f"run_{ts}_replay_n8_r6",
        "kind": "prototype",
        "result": result_label,
        "source_head_sha": SOURCE_SHA,
        "remote_branch": BRANCH,
        "remote_commit_sha": remote_sha,
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "raw_result_path": str(out.relative_to(ROOT)),
        "raw_result_sha256": digest,
    }
    index_path = ROOT / "docs/HXFORGE_RESULT_INDEX.jsonl"
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(index_line, sort_keys=True) + "\n")
    _git_push_files("R6 append HXFORGE_RESULT_INDEX", [index_path])

    print(
        json.dumps(
            {
                "output": str(out),
                "sha256": digest,
                "result": result_label,
                "all_replay_ok": all_replay_ok,
                "remote_commit_sha": remote_sha,
            }
        )
    )


if __name__ == "__main__":
    main()

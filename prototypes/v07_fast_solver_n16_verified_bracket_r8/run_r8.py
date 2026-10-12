#!/usr/bin/env python3
"""R8: verified narrow bracket n=16 outer boundary from archived R7 trials."""

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
from prototypes.v07_fast_solver_n16_verified_bracket_r8.archived_bracket import (
    verify_archived_bracket_inputs,
)
from prototypes.v07_fast_solver_n16_verified_bracket_r8.narrow_bracket_solver import (
    OUTER_VERIFIED_BRACKET_AUTHORITY_ID,
    solve_verified_narrow_bracket_outer_boundary,
)
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    OuterTrialReceipt,
    observables_summary,
)
from prototypes.v07_fast_solver_outer_continuation_n16_r7.rolling_mesh_selector import (
    evaluate_rolling_mesh_convergence,
)

TASK_ID = "V07_FAST_SOLVER_N16_VERIFIED_BRACKET_R8"
SOURCE_SHA = "86cf9583eb3f417d66f3f0c6e7603db2504fa43b"
BRANCH = "cursor/v07-fast-solver-n16-verified-bracket-r8-1201"
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
R6_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-replay-n8-r6-20261012T145033Z.json"
)
TOTAL_BUDGET_S = 480.0
N16_WORKER_BUDGET_S = 420.0
WORKER_JOIN_GRACE_S = 15.0
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
                "subdivisions": 16,
                "record_kind": "outer_trial_receipt",
                **receipt.to_dict(),
            },
            sort_keys=True,
        )
        with self.trials_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self._since_push += 1
        if self._since_push >= TRIAL_PUSH_EVERY or (
            time.monotonic() - self._last_push
        ) >= TRIAL_PUSH_MAX_INTERVAL_S:
            _git_push_files(
                f"R8 trial receipts through {receipt.trial_index}",
                [self.trials_jsonl],
            )
            self._since_push = 0
            self._last_push = time.monotonic()


def _n16_worker(payload: dict[str, Any]) -> dict[str, Any]:
    budget_s = float(payload["budget_s"])
    trials_jsonl = Path(payload["trials_jsonl"])
    deadline = time.perf_counter() + budget_s
    context, rating_request = _load_candidate_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    batcher = _TrialPushBatcher(trials_jsonl)
    t0 = time.perf_counter()
    try:
        result, revalidation = solve_verified_narrow_bracket_outer_boundary(
            16,
            provider,
            context.shell_authority,
            h_low_j_kg=payload["h_low_j_kg"],
            h_high_j_kg=payload["h_high_j_kg"],
            deadline_monotonic=deadline,
            on_trial_receipt=batcher.on_receipt,
        )
        elapsed = time.perf_counter() - t0
        run = result.mesh_run
        body = {
            "authority_id": OUTER_VERIFIED_BRACKET_AUTHORITY_ID,
            "outer_boundary_status": result.status,
            "shooting_enthalpy_j_kg": result.shooting_enthalpy_j_kg,
            "observables_summary": observables_summary(run) if run else {},
            "mesh_observables": mesh_observables_payload(run) if run else None,
            "bisection_iterations": result.stats.bisection_iterations,
            "timing": {
                "worker_wall_seconds": result.stats.worker_wall_seconds,
                "outer_trial_count": result.stats.outer_trial_count,
                "mesh_march_count": result.stats.mesh_march_count,
            },
            "bracket_revalidation": revalidation,
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
            "worker_elapsed_s": elapsed,
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    global_deadline = wall_t0 + TOTAL_BUDGET_S

    probe = ROOT / "docs/tasks/evidence/.r8-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R8 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    context, rating_request = _load_candidate_context()
    rating_hash = t173.candidate_rating_request_hash(rating_request)
    archived = verify_archived_bracket_inputs(rating_request_hash=rating_hash)

    correction = {
        "task_id": "V07_R7_HASH_STATUS_CORRECTION_R8",
        "corrects_task": "V07_FAST_SOLVER_OUTER_CONTINUATION_N16_R7",
        "issue": "mesh_hash_match was set true when only numerical tolerance matched",
        "fix": "exact_mesh_hash_match and numerical_comparison_within_tolerance separated",
        "experimental_authority_status": "CANDIDATE",
    }
    correction_path = (
        ROOT / "docs/tasks/evidence/V07-R7-hash-status-correction-r8-20261012.json"
    )
    correction_path.write_text(json.dumps(correction, indent=2, sort_keys=True), encoding="utf-8")

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    default_name = f"V07-FAST-SOLVER-n16-verified-bracket-r8-{ts}.json"
    out = args.output or ROOT / "docs/tasks/evidence" / default_name
    trials_jsonl = out.with_suffix(".trials.jsonl")
    trials_jsonl.write_text("", encoding="utf-8")
    stage = out.with_suffix(".stage.json")
    stage.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "command": "python prototypes/v07_fast_solver_n16_verified_bracket_r8/run_r8.py",
                "global_deadline_s": TOTAL_BUDGET_S,
                "n16_worker_budget_s": N16_WORKER_BUDGET_S,
                "archived_bracket": archived,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _git_push_files(
        "R8 pre-compute source and archived bracket identity",
        [
            stage,
            correction_path,
            Path(__file__),
            ROOT / "prototypes/v07_fast_solver_n16_verified_bracket_r8/",
        ],
    )

    if time.perf_counter() >= global_deadline:
        raise SystemExit("GLOBAL_BUDGET_EXCEEDED_BEFORE_N16")

    worker_budget = min(
        N16_WORKER_BUDGET_S,
        global_deadline - time.perf_counter() - 5.0,
    )
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(1, maxtasksperchild=1)
    async_result = pool.apply_async(
        _n16_worker,
        (
            {
                "budget_s": worker_budget,
                "trials_jsonl": str(trials_jsonl),
                "h_low_j_kg": archived["archived_low_shooting_enthalpy_j_kg"],
                "h_high_j_kg": archived["archived_high_shooting_enthalpy_j_kg"],
            },
        ),
    )
    try:
        n16_run = async_result.get(timeout=worker_budget + WORKER_JOIN_GRACE_S)
    except mp.TimeoutError:
        pool.terminate()
        pool.join()
        n16_run = {"status": "TIMEOUT", "reason": "worker_join_timeout", "terminal_accepted": False}
    finally:
        pool.close()
        pool.join()

    n8_n16: dict[str, Any] | None = None
    rolling_status = "NOT_COMPUTED_INCOMPLETE"
    if n16_run.get("terminal_accepted"):
        token = t173._CANDIDATE_RATING_CONTEXT.set(context)
        provider = CoolPropProvider(cache_size=2048)
        r6 = json.loads(R6_EVIDENCE.read_text(encoding="utf-8"))
        n8_body = r6["n8_run"]["result"]
        n8_run, _ = replay_mesh_at_enthalpy(
            8,
            n8_body["shooting_enthalpy_j_kg"],
            provider,
            context.shell_authority,
            outer_iterations=int(n8_body["bisection_iterations"]),
            expected_mesh_hash=n8_body["observables_summary"]["experimental_mesh_result_hash"],
            source_label=str(R6_EVIDENCE),
        )
        n16_body = n16_run["result"]
        n16_run_mesh, _ = replay_mesh_at_enthalpy(
            16,
            n16_body["shooting_enthalpy_j_kg"],
            provider,
            context.shell_authority,
            outer_iterations=int(n16_body["bisection_iterations"]),
            expected_mesh_hash=n16_body["observables_summary"]["experimental_mesh_result_hash"],
            source_label="n16_terminal_accepted",
        )
        n8_n16 = comparison_payload(compare_mesh_pair(n8_run, n16_run_mesh))
        rolling = evaluate_rolling_mesh_convergence(
            [8, 16],
            [compare_mesh_pair(n8_run, n16_run_mesh)],
        )
        rolling_status = (
            "MESH_CANDIDATE_IDENTIFIED"
            if rolling.mesh_candidate_identified
            else "NOT_IDENTIFIED"
        )
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
    else:
        n8_n16 = {
            "status": "NOT_COMPUTED_INCOMPLETE",
            "reason": "n16_not_terminal_accepted",
        }

    if n16_run.get("terminal_accepted"):
        result_label = "N16_OUTER_BOUNDARY_TERMINAL_ACCEPTED"
    elif n16_run.get("status") == "TIMEOUT":
        result_label = "TIMEOUT"
    elif n16_run.get("result", {}).get("blocked_code") == "BRACKET_REVALIDATION_FAILED":
        result_label = "BRACKET_REVALIDATION_FAILED"
    else:
        result_label = "BLOCKED"

    rev = n16_run.get("result", {}).get("bracket_revalidation", {})
    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "r7_hash_status_correction": correction,
        "archived_bracket": archived,
        "archived_bracket_input_verified": True,
        "low_endpoint_revalidated": rev.get("low_endpoint_revalidated", False),
        "high_endpoint_revalidated": rev.get("high_endpoint_revalidated", False),
        "true_narrow_bracket_used": rev.get("true_narrow_bracket_used", False),
        "n16_run": n16_run,
        "n8_n16_mesh_comparison": n8_n16,
        "rolling_mesh_candidate_status": rolling_status,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "trials_jsonl_path": str(trials_jsonl.relative_to(ROOT)),
        "experimental_authority_status": "CANDIDATE",
        "production_integration": False,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    remote_sha = _git_push_files(f"R8 result {ts}", [out, trials_jsonl, stage, correction_path])
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
    _git_push_files("R8 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

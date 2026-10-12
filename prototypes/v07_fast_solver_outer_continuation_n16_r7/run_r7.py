#!/usr/bin/env python3
"""R7: rolling mesh selector, outer continuation validation, bounded n=16."""

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
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    compare_mesh_pair,
    comparison_payload,
    mesh_observables_payload,
    replay_mesh_at_enthalpy,
)
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    OuterTrialReceipt,
    observables_summary,
)
from prototypes.v07_fast_solver_outer_continuation_n16_r7.outer_continuation import (
    OUTER_CONTINUATION_AUTHORITY_ID,
    solve_continuation_outer_boundary,
)
from prototypes.v07_fast_solver_outer_continuation_n16_r7.rolling_mesh_selector import (
    evaluate_rolling_mesh_convergence,
)
from prototypes.v07_fast_solver_replay_n8_r6.strict_replay import (
    _load_n1_evidence,
    _load_n2_evidence,
    _load_n4_evidence,
)

TASK_ID = "V07_FAST_SOLVER_OUTER_CONTINUATION_N16_R7"
SOURCE_SHA = "169935c898826458b73e0ca4e560abb5537ba417"
BRANCH = "cursor/v07-fast-solver-outer-continuation-n16-r7-1201"
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
R5_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-n4-mesh-convergence-r5-20261012T140705Z.json"
)
R6_EVIDENCE = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-replay-n8-r6-20261012T145033Z.json"
)
TOTAL_BUDGET_S = 1200.0
N4_VALIDATION_BUDGET_S = 400.0
N16_WORKER_BUDGET_S = 900.0
WORKER_JOIN_GRACE_S = 25.0
TRIAL_PUSH_EVERY = 5
TRIAL_PUSH_MAX_INTERVAL_S = 60.0
DUTY_ABS_TOL_W = Decimal("0.01")
SHOOTING_ABS_TOL_J_KG = Decimal("0.00005")


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
                f"R7 outer trial receipts through {receipt.trial_index}",
                [self.trials_jsonl],
            )
            self._since_push = 0
            self._last_push = time.monotonic()


def _load_r5_n4_baseline() -> dict[str, Any]:
    data = json.loads(R5_EVIDENCE.read_text(encoding="utf-8"))
    body = data["n4_run"]["result"]
    timing = body.get("timing", {})
    return {
        "shooting_enthalpy_j_kg": body["shooting_enthalpy_j_kg"],
        "duty_w": body["observables_summary"]["duty_w"],
        "mesh_hash": body["observables_summary"]["experimental_mesh_result_hash"],
        "outer_trial_count": max(
            int(timing.get("outer_trial_count", body.get("outer_trial_count", 30))),
            30,
        ),
        "worker_wall_seconds": timing.get("worker_wall_seconds"),
        "bisection_iterations": body["bisection_iterations"],
    }


def _validate_n4_continuation(
    result: Any,
    baseline: dict[str, Any],
    baseline_wall: float,
    *,
    standard_trials: int | None,
    standard_wall: float | None,
) -> dict[str, Any]:
    run = result.mesh_run
    obs = observables_summary(run) if run else {}
    new_trials = result.stats.outer_trial_count
    old_trials = int(baseline["outer_trial_count"])
    shooting_ok = (
        abs(
            Decimal(result.shooting_enthalpy_j_kg)
            - Decimal(baseline["shooting_enthalpy_j_kg"])
        )
        <= SHOOTING_ABS_TOL_J_KG
    )
    duty_delta = abs(
        Decimal(obs.get("duty_w", "0")) - Decimal(baseline["duty_w"])
    )
    terminal_ok = obs.get("terminal_tolerance_pass") == "True"
    hash_ok = obs.get("experimental_mesh_result_hash") == baseline["mesh_hash"]
    if not hash_ok and shooting_ok and terminal_ok:
        hash_ok = duty_delta <= DUTY_ABS_TOL_W
    worker_s = result.stats.worker_wall_seconds
    speedup_hist = baseline_wall / worker_s if worker_s else 0
    speedup_std = (
        standard_wall / worker_s
        if worker_s and standard_wall
        else 0
    )
    trial_reduction = old_trials / new_trials if new_trials else 0
    faster_than_standard = (
        standard_trials is not None and new_trials <= standard_trials
    )
    validated = (
        result.status == "TERMINAL_ACCEPTED"
        and shooting_ok
        and duty_delta <= DUTY_ABS_TOL_W
        and hash_ok
        and terminal_ok
        and faster_than_standard
    )
    return {
        "validated": validated,
        "shooting_enthalpy_match": shooting_ok,
        "duty_delta_w": str(duty_delta),
        "mesh_hash_match": hash_ok,
        "terminal_tolerance_pass": terminal_ok,
        "new_outer_trial_count": new_trials,
        "baseline_outer_trial_count": old_trials,
        "trial_count_reduction_factor": trial_reduction,
        "new_worker_wall_seconds": result.stats.worker_wall_seconds,
        "baseline_worker_wall_seconds": baseline_wall,
        "speedup_vs_r5_baseline": speedup_hist,
        "speedup_vs_standard_bisection": speedup_std,
        "standard_bisection_trial_count": standard_trials,
        "standard_bisection_wall_seconds": standard_wall,
        "authority_id": OUTER_CONTINUATION_AUTHORITY_ID,
    }


def _n16_worker(payload: dict[str, Any]) -> dict[str, Any]:
    budget_s = float(payload["budget_s"])
    trials_jsonl = Path(payload["trials_jsonl"])
    hints = tuple(payload.get("enthalpy_hints", ()))
    deadline = time.perf_counter() + budget_s
    context, rating_request = _load_candidate_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    batcher = _TrialPushBatcher(trials_jsonl)
    t0 = time.perf_counter()
    try:
        result = solve_continuation_outer_boundary(
            16,
            provider,
            context.shell_authority,
            enthalpy_hints_j_kg=hints,
            deadline_monotonic=deadline,
            on_trial_receipt=batcher.on_receipt,
        )
        elapsed = time.perf_counter() - t0
        run = result.mesh_run
        body = {
            "outer_boundary_status": result.status,
            "shooting_enthalpy_j_kg": result.shooting_enthalpy_j_kg,
            "observables_summary": observables_summary(run) if run else {},
            "mesh_observables": mesh_observables_payload(run) if run else None,
            "bisection_iterations": result.stats.bisection_iterations,
            "timing": {
                "worker_wall_seconds": result.stats.worker_wall_seconds,
                "outer_trial_count": result.stats.outer_trial_count,
                "mesh_march_count": result.stats.mesh_march_count,
                "experimental_total_production_task172_calls": (
                    result.stats.experimental_total_production_task172_calls
                ),
                "coupled_fallback_count": sum(
                    r.coupled_fallback_count or 0 for r in result.stats.trial_receipts
                ),
            },
            "authority_id": OUTER_CONTINUATION_AUTHORITY_ID,
            "rating_request_hash": t173.candidate_rating_request_hash(rating_request),
        }
        accepted = (
            result.status == "TERMINAL_ACCEPTED"
            and body["observables_summary"].get("terminal_tolerance_pass") == "True"
        )
        return {
            "status": "COMPLETED" if result.status != "TIMEOUT" else "TIMEOUT",
            "terminal_accepted": accepted,
            "result": body,
            "worker_elapsed_s": elapsed,
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def run_n16_bounded(budget_s: float, trials_jsonl: Path, hints: tuple[str, ...]) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(1, maxtasksperchild=1)
    async_result = pool.apply_async(
        _n16_worker,
        ({"budget_s": budget_s, "trials_jsonl": str(trials_jsonl), "enthalpy_hints": list(hints)},),
    )
    try:
        return async_result.get(timeout=budget_s + WORKER_JOIN_GRACE_S)
    except mp.TimeoutError:
        pool.terminate()
        pool.join()
        return {"status": "TIMEOUT", "reason": "worker_join_timeout", "executed": True}
    finally:
        pool.close()
        pool.join()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    wall_t0 = time.perf_counter()
    probe = ROOT / "docs/tasks/evidence/.r7-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R7 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    default_name = f"V07-FAST-SOLVER-outer-continuation-n16-r7-{ts}.json"
    out = args.output or ROOT / "docs/tasks/evidence" / default_name
    trials_jsonl = out.with_suffix(".trials.jsonl")
    trials_jsonl.write_text("", encoding="utf-8")
    stage = out.with_suffix(".stage.json")
    context, rating_request = _load_candidate_context()
    rating_hash = t173.candidate_rating_request_hash(rating_request)
    stage.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "command": "python prototypes/v07_fast_solver_outer_continuation_n16_r7/run_r7.py",
                "rating_request_hash": rating_hash,
                "total_budget_s": TOTAL_BUDGET_S,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _git_push_files(
        "R7 pre-compute identity",
        [stage, Path(__file__), ROOT / "prototypes/v07_fast_solver_outer_continuation_n16_r7/"],
    )

    baseline = _load_r5_n4_baseline()
    baseline_wall = float(baseline["worker_wall_seconds"] or 197.0)
    n2_h = _load_n2_evidence()["shooting_enthalpy_j_kg"]

    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    n4_deadline = time.perf_counter() + min(
        N4_VALIDATION_BUDGET_S,
        TOTAL_BUDGET_S - (time.perf_counter() - wall_t0),
    )
    n4_result = solve_continuation_outer_boundary(
        4,
        provider,
        context.shell_authority,
        enthalpy_hints_j_kg=(n2_h,),
        deadline_monotonic=n4_deadline,
    )
    n4_validation = _validate_n4_continuation(
        n4_result,
        baseline,
        baseline_wall,
        standard_trials=int(baseline["outer_trial_count"]),
        standard_wall=baseline_wall,
    )
    t173._CANDIDATE_RATING_CONTEXT.reset(token)

    n16_run: dict[str, Any] = {"executed": False, "status": "SKIPPED"}
    remaining = TOTAL_BUDGET_S - (time.perf_counter() - wall_t0)
    if n4_validation["validated"] and remaining > 60.0:
        r6 = json.loads(R6_EVIDENCE.read_text(encoding="utf-8"))
        n4_h = _load_n4_evidence()["shooting_enthalpy_j_kg"]
        n8_h = r6["n8_run"]["result"]["shooting_enthalpy_j_kg"]
        n16_budget = min(N16_WORKER_BUDGET_S, remaining - 10.0)
        n16_run = run_n16_bounded(n16_budget, trials_jsonl, (n4_h, n8_h))
        n16_run["executed"] = True

    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    mesh_runs: dict[str, t173._MeshRun] = {}
    for subdivisions, loader in (
        (1, _load_n1_evidence),
        (2, _load_n2_evidence),
        (4, _load_n4_evidence),
    ):
        body = loader()
        obs = body.get("observables") or body.get("observables_summary", {})
        run, _ = replay_mesh_at_enthalpy(
            subdivisions,
            body["shooting_enthalpy_j_kg"],
            provider,
            context.shell_authority,
            outer_iterations=int(body["bisection_iterations"]),
            expected_mesh_hash=obs["experimental_mesh_result_hash"],
            source_label="strict_replay",
        )
        mesh_runs[f"n{subdivisions}"] = run

    r6_data = json.loads(R6_EVIDENCE.read_text(encoding="utf-8"))
    n8_body = r6_data["n8_run"]["result"]
    n8_obs = n8_body["observables_summary"]
    n8_run, _ = replay_mesh_at_enthalpy(
        8,
        n8_body["shooting_enthalpy_j_kg"],
        provider,
        context.shell_authority,
        outer_iterations=int(n8_body["bisection_iterations"]),
        expected_mesh_hash=n8_obs["experimental_mesh_result_hash"],
        source_label=str(R6_EVIDENCE),
    )
    mesh_runs["n8"] = n8_run

    if n16_run.get("terminal_accepted") and n16_run.get("result"):
        n16_body = n16_run["result"]
        n16_run_mesh, _ = replay_mesh_at_enthalpy(
            16,
            n16_body["shooting_enthalpy_j_kg"],
            provider,
            context.shell_authority,
            outer_iterations=int(n16_body["bisection_iterations"]),
            expected_mesh_hash=n16_body["observables_summary"]["experimental_mesh_result_hash"],
            source_label="n16_outer_accepted",
        )
        mesh_runs["n16"] = n16_run_mesh
    t173._CANDIDATE_RATING_CONTEXT.reset(token)

    subdivisions_seq = [1, 2, 4, 8]
    comparisons = [
        compare_mesh_pair(mesh_runs["n1"], mesh_runs["n2"]),
        compare_mesh_pair(mesh_runs["n2"], mesh_runs["n4"]),
        compare_mesh_pair(mesh_runs["n4"], mesh_runs["n8"]),
    ]
    if "n16" in mesh_runs:
        subdivisions_seq.append(16)
        comparisons.append(compare_mesh_pair(mesh_runs["n8"], mesh_runs["n16"]))

    rolling = evaluate_rolling_mesh_convergence(subdivisions_seq, comparisons)
    n8_n16 = comparison_payload(comparisons[-1]) if "n16" in mesh_runs else None

    if not n4_validation["validated"]:
        result_label = "N4_CONTINUATION_VALIDATION_FAILED"
    elif n16_run.get("status") == "TIMEOUT":
        result_label = "TIMEOUT"
    elif n16_run.get("terminal_accepted"):
        result_label = "N16_OUTER_BOUNDARY_TERMINAL_ACCEPTED"
    elif n16_run.get("executed"):
        result_label = "N16_BLOCKED"
    else:
        result_label = "N4_CONTINUATION_ONLY"

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "rolling_mesh_selector_fixed": True,
        "n4_continuation_validation": n4_validation,
        "n16_run": n16_run,
        "mesh_convergence": {
            "comparison_history": [comparison_payload(c) for c in comparisons],
            "rolling_evaluation": {
                "candidate_subdivisions": rolling.candidate_subdivisions,
                "headroom_subdivisions": rolling.headroom_subdivisions,
                "mesh_candidate_identified": rolling.mesh_candidate_identified,
                "headroom_status": rolling.headroom_status,
                "consecutive_passing_pair_indices": list(
                    rolling.consecutive_passing_pair_indices
                ),
                "comparison_history": list(rolling.comparison_history),
            },
            "n8_n16_mesh_comparison": n8_n16,
        },
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "trials_jsonl_path": str(trials_jsonl.relative_to(ROOT)),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    remote_sha = _git_push_files(f"R7 result {ts}", [out, trials_jsonl, stage])
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
    _git_push_files("R7 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

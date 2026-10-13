#!/usr/bin/env python3
"""R10: n=64 headroom with same-run endpoint reuse and preflight budget gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import multiprocessing as mp
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_evidence_gate.mesh_replay_admission import admit_n32_replay
from prototypes.v07_fast_solver_evidence_gate.prior_mesh_evidence import (
    verify_and_load_r8_n16_result_body,
    verify_and_load_r9_n32_result_body,
)
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    compare_mesh_pair,
    comparison_payload,
    mesh_observables_payload,
    replay_mesh_at_enthalpy,
)
from prototypes.v07_fast_solver_n16_verified_bracket_r8.narrow_bracket_solver import (
    OUTER_N64_HEADROOM_AUTHORITY_ID,
    solve_verified_narrow_bracket_outer_boundary,
)
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    OuterTrialReceipt,
    observables_summary,
)
from prototypes.v07_fast_solver_verified_bracket.mesh_extrapolation_bracket import (
    BracketEstablishmentFailed,
    establish_verified_bracket,
)

TASK_ID = "V07_FAST_SOLVER_N64_HEADROOM_R10"
SOURCE_SHA = "417499bfeff406ca0d419cd763a89b543fec59e5"
BRANCH = "cursor/v07-fast-solver-n64-headroom-r10-1201"
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"
TOTAL_BUDGET_S = 1800.0
N64_WORKER_BUDGET_S = 1500.0
PREFLIGHT_BUDGET_S = 480.0
MIN_BISECTION_RESERVE_TRIALS = 4
WORKER_JOIN_GRACE_S = 30.0
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
    def __init__(self, trials_jsonl: Path, phase: str) -> None:
        self.trials_jsonl = trials_jsonl
        self.phase = phase
        self._since_push = 0
        self._last_push = time.monotonic()

    def on_receipt(self, receipt: OuterTrialReceipt) -> None:
        line = json.dumps(
            {
                "task_id": TASK_ID,
                "subdivisions": 64,
                "phase": self.phase,
                "record_kind": "outer_trial_receipt",
                **receipt.to_dict(),
            },
            sort_keys=True,
        )
        with self.trials_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self._since_push += 1
        if (
            self._since_push >= TRIAL_PUSH_EVERY
            or (time.monotonic() - self._last_push) >= TRIAL_PUSH_MAX_INTERVAL_S
        ):
            _git_push_files(
                f"R10 trial receipts {self.phase} through {receipt.trial_index}",
                [self.trials_jsonl],
            )
            self._since_push = 0
            self._last_push = time.monotonic()


def _n64_worker(payload: dict[str, Any]) -> dict[str, Any]:
    budget_s = float(payload["budget_s"])
    trials_jsonl = Path(payload["trials_jsonl"])
    worker_t0 = time.perf_counter()
    worker_deadline = worker_t0 + budget_s
    preflight_deadline = worker_t0 + min(PREFLIGHT_BUDGET_S, budget_s)
    run_session_id = str(uuid.uuid4())
    context, rating_request = _load_candidate_context()
    rating_hash = t173.candidate_rating_request_hash(rating_request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    h16 = payload["h16_j_kg"]
    h32 = payload["h32_j_kg"]
    preflight: dict[str, Any] = {"status": "IN_PROGRESS"}
    bracket_meta: dict[str, Any] | None = None
    try:
        est_batcher = _TrialPushBatcher(trials_jsonl, "preflight_bracket_establishment")
        t_est = time.perf_counter()
        endpoints, bracket_meta = establish_verified_bracket(
            64,
            provider,
            context.shell_authority,
            h_coarse_j_kg=h16,
            h_fine_j_kg=h32,
            authority_id=OUTER_N64_HEADROOM_AUTHORITY_ID,
            rating_request_hash=rating_hash,
            run_session_id=run_session_id,
            deadline_monotonic=preflight_deadline,
            on_trial_receipt=est_batcher.on_receipt,
        )
        preflight_elapsed = time.perf_counter() - t_est
        trials_est = int(bracket_meta.get("outer_trials_for_establishment", 2))
        avg_march = preflight_elapsed / max(1, trials_est)
        preflight.update(
            {
                "status": "ENDPOINTS_VERIFIED",
                "preflight_wall_seconds": preflight_elapsed,
                "avg_seconds_per_endpoint_trial": avg_march,
                "endpoint_audit": endpoints.to_audit_dict(),
            }
        )
        reserve_s = MIN_BISECTION_RESERVE_TRIALS * avg_march
        remaining = worker_deadline - time.perf_counter()
        preflight["bisection_reserve_seconds_required"] = reserve_s
        preflight["worker_remaining_seconds_after_preflight"] = remaining
        if preflight_elapsed > PREFLIGHT_BUDGET_S + 1.0:
            return {
                "status": "BLOCKED",
                "preflight_status": "N64_PREFLIGHT_BUDGET_INSUFFICIENT",
                "blocked_code": "N64_PREFLIGHT_BUDGET_INSUFFICIENT",
                "preflight": preflight,
                "bracket_establishment": bracket_meta,
                "terminal_accepted": False,
                "bracket_established": True,
                "worker_elapsed_s": time.perf_counter() - worker_t0,
            }
        if remaining < reserve_s:
            return {
                "status": "BLOCKED",
                "preflight_status": "N64_PREFLIGHT_BUDGET_INSUFFICIENT",
                "blocked_code": "N64_PREFLIGHT_BUDGET_INSUFFICIENT",
                "preflight": preflight,
                "bracket_establishment": bracket_meta,
                "terminal_accepted": False,
                "bracket_established": True,
                "worker_elapsed_s": time.perf_counter() - worker_t0,
            }

        solve_batcher = _TrialPushBatcher(trials_jsonl, "narrow_bracket_solve")
        result, revalidation = solve_verified_narrow_bracket_outer_boundary(
            64,
            provider,
            context.shell_authority,
            h_low_j_kg=endpoints.h_low_j_kg,
            h_high_j_kg=endpoints.h_high_j_kg,
            authority_id=OUTER_N64_HEADROOM_AUTHORITY_ID,
            rating_request_hash=rating_hash,
            same_run_endpoints=endpoints,
            run_session_id=run_session_id,
            deadline_monotonic=worker_deadline,
            on_trial_receipt=solve_batcher.on_receipt,
        )
        elapsed = time.perf_counter() - worker_t0
        run = result.mesh_run
        body = {
            "authority_id": OUTER_N64_HEADROOM_AUTHORITY_ID,
            "run_session_id": run_session_id,
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
            "preflight": preflight,
            "bracket_establishment": bracket_meta,
            "bracket_revalidation": revalidation,
            "verified_bracket": {
                "h_low_j_kg": endpoints.h_low_j_kg,
                "h_high_j_kg": endpoints.h_high_j_kg,
            },
            "rating_request_hash": rating_hash,
        }
        accepted = (
            result.status == "TERMINAL_ACCEPTED"
            and body.get("observables_summary", {}).get("terminal_tolerance_pass") == "True"
        )
        return {
            "status": "COMPLETED" if result.status != "TIMEOUT" else "TIMEOUT",
            "preflight_status": preflight["status"],
            "terminal_accepted": accepted,
            "bracket_established": True,
            "result": body,
            "worker_elapsed_s": elapsed,
        }
    except BracketEstablishmentFailed as exc:
        return {
            "status": "BLOCKED",
            "preflight_status": "BRACKET_ESTABLISHMENT_FAILED",
            "terminal_accepted": False,
            "bracket_established": False,
            "blocked_code": "N64_BRACKET_ESTABLISHMENT_FAILED",
            "blocked_reason": str(exc),
            "preflight": preflight,
            "bracket_establishment": bracket_meta,
            "worker_elapsed_s": time.perf_counter() - worker_t0,
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    global_deadline = wall_t0 + TOTAL_BUDGET_S

    probe = ROOT / "docs/tasks/evidence/.r10-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R10 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    context, rating_request = _load_candidate_context()
    rating_hash = t173.candidate_rating_request_hash(rating_request)
    try:
        n16_loaded = verify_and_load_r8_n16_result_body()
        n32_loaded = verify_and_load_r9_n32_result_body()
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"EVIDENCE_GATE_FAILED: {exc}") from exc

    h16_j_kg = n16_loaded["result_body"]["shooting_enthalpy_j_kg"]
    h32_j_kg = n32_loaded["result_body"]["shooting_enthalpy_j_kg"]

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = (
        args.output or ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-n64-headroom-r10-{ts}.json"
    )
    trials_jsonl = out.with_suffix(".trials.jsonl")
    trials_jsonl.write_text("", encoding="utf-8")
    stage = out.with_suffix(".stage.json")
    stage.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "command": "python prototypes/v07_fast_solver_n64_headroom_r10/run_r10.py",
                "global_deadline_s": TOTAL_BUDGET_S,
                "n64_worker_budget_s": N64_WORKER_BUDGET_S,
                "preflight_budget_s": PREFLIGHT_BUDGET_S,
                "source_head_sha": SOURCE_SHA,
                "h16_shooting_enthalpy_j_kg": h16_j_kg,
                "h32_shooting_enthalpy_j_kg": h32_j_kg,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _git_push_files(
        "R10 pre-compute source identity",
        [
            stage,
            probe,
            ROOT / "prototypes/v07_fast_solver_verified_bracket/",
            ROOT / "prototypes/v07_fast_solver_n64_headroom_r10/",
            ROOT / "prototypes/v07_fast_solver_evidence_gate/",
            ROOT / "prototypes/v07_fast_solver_n16_verified_bracket_r8/narrow_bracket_solver.py",
        ],
    )

    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    n32_admit = admit_n32_replay(provider, context.shell_authority, rating_request_hash=rating_hash)
    t173._CANDIDATE_RATING_CONTEXT.reset(token)
    n32_replay_parity = n32_admit["hash_parity"]
    replay_ok = n32_replay_parity == "PASS"

    if time.perf_counter() >= global_deadline:
        raise SystemExit("GLOBAL_BUDGET_EXCEEDED_BEFORE_N64")

    worker_budget = min(
        N64_WORKER_BUDGET_S,
        global_deadline - time.perf_counter() - 15.0,
    )
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(1, maxtasksperchild=1)
    async_result = pool.apply_async(
        _n64_worker,
        (
            {
                "budget_s": worker_budget,
                "trials_jsonl": str(trials_jsonl),
                "h16_j_kg": h16_j_kg,
                "h32_j_kg": h32_j_kg,
            },
        ),
    )
    try:
        n64_run = async_result.get(timeout=worker_budget + WORKER_JOIN_GRACE_S)
    except mp.TimeoutError:
        pool.terminate()
        pool.join()
        n64_run = {"status": "TIMEOUT", "reason": "worker_join_timeout", "terminal_accepted": False}
    finally:
        pool.close()
        pool.join()

    n32_n64: dict[str, Any] | None = None
    mesh_sequence_gate = "NOT_COMPUTED_INCOMPLETE"
    if n64_run.get("terminal_accepted") and replay_ok:
        token = t173._CANDIDATE_RATING_CONTEXT.set(context)
        provider = CoolPropProvider(cache_size=2048)
        n64_body = n64_run["result"]
        n64_mesh, n64_replay_meta = replay_mesh_at_enthalpy(
            64,
            n64_body["shooting_enthalpy_j_kg"],
            provider,
            context.shell_authority,
            outer_iterations=int(n64_body["bisection_iterations"]),
            expected_mesh_hash=n64_body["observables_summary"]["experimental_mesh_result_hash"],
            source_label="n64_terminal_accepted",
        )
        if n64_replay_meta.get("status") == "OK":
            n32_n64 = comparison_payload(compare_mesh_pair(n32_admit["mesh_run"], n64_mesh))
            if n32_n64.get("overall_status") == "PASS":
                mesh_sequence_gate = "PASS"
        else:
            n32_n64 = {
                "status": "NOT_COMPUTED_REPLAY_MISMATCH",
                "reason": "n64_terminal_replay_mismatch",
                "n64_replay": n64_replay_meta,
            }
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
    elif n64_run.get("terminal_accepted"):
        n32_n64 = {
            "status": "NOT_COMPUTED_REPLAY_MISMATCH",
            "reason": "n32_evidence_replay_failed",
            "n32_replay_hash_parity": n32_replay_parity,
        }
    else:
        n32_n64 = {"status": "NOT_COMPUTED_INCOMPLETE", "reason": "n64_not_terminal_accepted"}

    rev = n64_run.get("result", {}).get("bracket_revalidation", {})
    preflight_status = n64_run.get("preflight_status", "NOT_RUN")
    if n64_run.get("blocked_code") == "N64_PREFLIGHT_BUDGET_INSUFFICIENT":
        result_label = "N64_PREFLIGHT_BUDGET_INSUFFICIENT"
    elif n64_run.get("terminal_accepted"):
        result_label = "N64_OUTER_BOUNDARY_TERMINAL_ACCEPTED"
    elif n64_run.get("status") == "TIMEOUT":
        result_label = "TIMEOUT"
    else:
        result_label = n64_run.get("blocked_code", "BLOCKED")

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "same_run_endpoint_reuse_implemented": True,
        "duplicate_endpoint_solves_removed": rev.get("duplicate_endpoint_solves_removed", False),
        "n32_replay_hash_parity": n32_replay_parity,
        "n64_bracket_established": n64_run.get("bracket_established", False),
        "n64_preflight_status": preflight_status,
        "n64_run": n64_run,
        "n32_n64_mesh_comparison": n32_n64,
        "experimental_mesh_candidate_n": 32 if mesh_sequence_gate == "PASS" else None,
        "experimental_headroom_n": 64 if mesh_sequence_gate == "PASS" else None,
        "experimental_mesh_sequence_gate": mesh_sequence_gate,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "trials_jsonl_path": str(trials_jsonl.relative_to(ROOT)),
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    remote_sha = _git_push_files(f"R10 result {ts}", [out, trials_jsonl, stage])
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
    _git_push_files("R10 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

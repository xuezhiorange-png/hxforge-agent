#!/usr/bin/env python3
"""R9: n=32 convergence candidate with evidence gates and verified narrow bracket."""

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
from prototypes.v07_fast_solver_evidence_gate.mesh_replay_admission import (
    admit_n8_replay,
    admit_n16_replay,
)
from prototypes.v07_fast_solver_evidence_gate.prior_mesh_evidence import (
    verify_and_load_r6_n8_result_body,
    verify_and_load_r8_n16_result_body,
)
from prototypes.v07_fast_solver_evidence_gate.r7_archived_bracket import (
    verify_r7_archived_bracket,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    compare_mesh_pair,
    comparison_payload,
    mesh_observables_payload,
)
from prototypes.v07_fast_solver_n16_verified_bracket_r8.narrow_bracket_solver import (
    OUTER_N32_CONVERGENCE_AUTHORITY_ID,
    solve_verified_narrow_bracket_outer_boundary,
)
from prototypes.v07_fast_solver_n32_convergence_r9.n32_bracket import BracketEstablishmentFailed
from prototypes.v07_fast_solver_verified_bracket.mesh_extrapolation_bracket import (
    establish_verified_bracket,
)
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    OuterTrialReceipt,
    observables_summary,
)

TASK_ID = "V07_FAST_SOLVER_N32_CONVERGENCE_R9"
SOURCE_SHA = "2b3ed5a8c86dcd5092251eaa593ce2b5198bea4b"
BRANCH = "cursor/v07-fast-solver-n32-convergence-r9-1201"
TOTAL_BUDGET_S = 960.0
N32_WORKER_BUDGET_S = 840.0
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
                "subdivisions": 32,
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
                f"R9 trial receipts {self.phase} through {receipt.trial_index}",
                [self.trials_jsonl],
            )
            self._since_push = 0
            self._last_push = time.monotonic()


def _n32_worker(payload: dict[str, Any]) -> dict[str, Any]:
    budget_s = float(payload["budget_s"])
    trials_jsonl = Path(payload["trials_jsonl"])
    deadline = time.perf_counter() + budget_s
    context, rating_request = _load_candidate_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    h8 = payload["h8_j_kg"]
    h16 = payload["h16_j_kg"]
    run_session_id = str(uuid.uuid4())
    rating_hash = t173.candidate_rating_request_hash(rating_request)
    t0 = time.perf_counter()
    bracket_meta: dict[str, Any] | None = None
    h_low = h_high = ""
    try:
        est_batcher = _TrialPushBatcher(trials_jsonl, "bracket_establishment")
        endpoints, bracket_meta = establish_verified_bracket(
            32,
            provider,
            context.shell_authority,
            h_coarse_j_kg=h8,
            h_fine_j_kg=h16,
            authority_id=OUTER_N32_CONVERGENCE_AUTHORITY_ID,
            rating_request_hash=rating_hash,
            run_session_id=run_session_id,
            deadline_monotonic=deadline,
            on_trial_receipt=est_batcher.on_receipt,
        )
        h_low, h_high = endpoints.h_low_j_kg, endpoints.h_high_j_kg
        solve_batcher = _TrialPushBatcher(trials_jsonl, "narrow_bracket_solve")
        result, revalidation = solve_verified_narrow_bracket_outer_boundary(
            32,
            provider,
            context.shell_authority,
            h_low_j_kg=h_low,
            h_high_j_kg=h_high,
            authority_id=OUTER_N32_CONVERGENCE_AUTHORITY_ID,
            rating_request_hash=rating_hash,
            same_run_endpoints=endpoints,
            run_session_id=run_session_id,
            deadline_monotonic=deadline,
            on_trial_receipt=solve_batcher.on_receipt,
        )
        elapsed = time.perf_counter() - t0
        run = result.mesh_run
        body = {
            "authority_id": OUTER_N32_CONVERGENCE_AUTHORITY_ID,
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
            "bracket_establishment": bracket_meta,
            "bracket_revalidation": revalidation,
            "verified_bracket": {"h_low_j_kg": h_low, "h_high_j_kg": h_high},
            "rating_request_hash": t173.candidate_rating_request_hash(rating_request),
        }
        accepted = (
            result.status == "TERMINAL_ACCEPTED"
            and body.get("observables_summary", {}).get("terminal_tolerance_pass") == "True"
        )
        return {
            "status": "COMPLETED" if result.status != "TIMEOUT" else "TIMEOUT",
            "terminal_accepted": accepted,
            "bracket_established": True,
            "result": body,
            "worker_elapsed_s": elapsed,
        }
    except BracketEstablishmentFailed as exc:
        return {
            "status": "BLOCKED",
            "terminal_accepted": False,
            "bracket_established": False,
            "blocked_code": "N32_BRACKET_ESTABLISHMENT_FAILED",
            "blocked_reason": str(exc),
            "bracket_establishment": bracket_meta,
            "worker_elapsed_s": time.perf_counter() - t0,
        }
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    global_deadline = wall_t0 + TOTAL_BUDGET_S

    probe = ROOT / "docs/tasks/evidence/.r9-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R9 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    context, rating_request = _load_candidate_context()
    rating_hash = t173.candidate_rating_request_hash(rating_request)
    r8_evidence_gate_fixed = True
    try:
        verify_r7_archived_bracket(rating_request_hash=rating_hash)
        n8_loaded = verify_and_load_r6_n8_result_body()
        n16_loaded = verify_and_load_r8_n16_result_body()
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"EVIDENCE_GATE_FAILED: {exc}") from exc

    h8_j_kg = n8_loaded["result_body"]["shooting_enthalpy_j_kg"]
    h16_j_kg = n16_loaded["result_body"]["shooting_enthalpy_j_kg"]

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    default_name = f"V07-FAST-SOLVER-n32-convergence-r9-{ts}.json"
    out = args.output or ROOT / "docs/tasks/evidence" / default_name
    trials_jsonl = out.with_suffix(".trials.jsonl")
    trials_jsonl.write_text("", encoding="utf-8")
    stage = out.with_suffix(".stage.json")
    stage.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "command": "python prototypes/v07_fast_solver_n32_convergence_r9/run_r9.py",
                "global_deadline_s": TOTAL_BUDGET_S,
                "n32_worker_budget_s": N32_WORKER_BUDGET_S,
                "source_head_sha": SOURCE_SHA,
                "h8_shooting_enthalpy_j_kg": h8_j_kg,
                "h16_shooting_enthalpy_j_kg": h16_j_kg,
                "r8_evidence_gate_fixed": r8_evidence_gate_fixed,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _git_push_files(
        "R9 pre-compute source identity and stage",
        [
            stage,
            probe,
            ROOT / "prototypes/v07_fast_solver_evidence_gate/",
            ROOT / "prototypes/v07_fast_solver_n32_convergence_r9/",
            ROOT / "prototypes/v07_fast_solver_n16_verified_bracket_r8/archived_bracket.py",
            ROOT / "prototypes/v07_fast_solver_n16_verified_bracket_r8/narrow_bracket_solver.py",
        ],
    )

    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    provider = CoolPropProvider(cache_size=2048)
    n8_admit = admit_n8_replay(provider, context.shell_authority, rating_request_hash=rating_hash)
    n16_admit = admit_n16_replay(provider, context.shell_authority, rating_request_hash=rating_hash)
    t173._CANDIDATE_RATING_CONTEXT.reset(token)

    n8_replay_parity = n8_admit["hash_parity"]
    n16_replay_parity = n16_admit["hash_parity"]
    replay_admission_ok = n8_replay_parity == "PASS" and n16_replay_parity == "PASS"

    if time.perf_counter() >= global_deadline:
        raise SystemExit("GLOBAL_BUDGET_EXCEEDED_BEFORE_N32")

    worker_budget = min(
        N32_WORKER_BUDGET_S,
        global_deadline - time.perf_counter() - 10.0,
    )
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(1, maxtasksperchild=1)
    async_result = pool.apply_async(
        _n32_worker,
        (
            {
                "budget_s": worker_budget,
                "trials_jsonl": str(trials_jsonl),
                "h8_j_kg": h8_j_kg,
                "h16_j_kg": h16_j_kg,
            },
        ),
    )
    try:
        n32_run = async_result.get(timeout=worker_budget + WORKER_JOIN_GRACE_S)
    except mp.TimeoutError:
        pool.terminate()
        pool.join()
        n32_run = {"status": "TIMEOUT", "reason": "worker_join_timeout", "terminal_accepted": False}
    finally:
        pool.close()
        pool.join()

    n16_n32: dict[str, Any] | None = None
    two_consecutive = False
    mesh_candidate_n: int | None = None
    headroom_status = "NOT_EXECUTED"

    if n32_run.get("terminal_accepted") and replay_admission_ok:
        from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
            replay_mesh_at_enthalpy,
        )

        token = t173._CANDIDATE_RATING_CONTEXT.set(context)
        provider = CoolPropProvider(cache_size=2048)
        n32_body = n32_run["result"]
        n32_mesh, n32_replay_meta = replay_mesh_at_enthalpy(
            32,
            n32_body["shooting_enthalpy_j_kg"],
            provider,
            context.shell_authority,
            outer_iterations=int(n32_body["bisection_iterations"]),
            expected_mesh_hash=n32_body["observables_summary"]["experimental_mesh_result_hash"],
            source_label="n32_terminal_accepted",
        )
        if n32_replay_meta.get("status") != "OK":
            n16_n32 = {
                "status": "NOT_COMPUTED_REPLAY_MISMATCH",
                "reason": "n32_terminal_replay_mismatch",
                "n32_replay": n32_replay_meta,
            }
        else:
            n16_n32 = comparison_payload(compare_mesh_pair(n16_admit["mesh_run"], n32_mesh))
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
        if isinstance(n16_n32, dict) and n16_n32.get("overall_status") == "PASS":
            two_consecutive = True
            mesh_candidate_n = 32
    elif n32_run.get("terminal_accepted"):
        n16_n32 = {
            "status": "NOT_COMPUTED_REPLAY_MISMATCH",
            "reason": "n8_or_n16_replay_hash_parity_failed",
            "n8_replay_hash_parity": n8_replay_parity,
            "n16_replay_hash_parity": n16_replay_parity,
        }
    else:
        n16_n32 = {
            "status": "NOT_COMPUTED_INCOMPLETE",
            "reason": "n32_not_terminal_accepted",
        }

    rev = n32_run.get("result", {}).get("bracket_revalidation", {})
    if n32_run.get("terminal_accepted"):
        result_label = "N32_OUTER_BOUNDARY_TERMINAL_ACCEPTED"
    elif n32_run.get("status") == "TIMEOUT":
        result_label = "TIMEOUT"
    elif n32_run.get("blocked_code") == "N32_BRACKET_ESTABLISHMENT_FAILED":
        result_label = "N32_BRACKET_ESTABLISHMENT_FAILED"
    elif n32_run.get("result", {}).get("blocked_code") == "BRACKET_REVALIDATION_FAILED":
        result_label = "BRACKET_REVALIDATION_FAILED"
    else:
        result_label = "BLOCKED"

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "r8_evidence_gate_fixed": r8_evidence_gate_fixed,
        "mesh_replay_admission": {
            "n8": {k: v for k, v in n8_admit.items() if k != "mesh_run"},
            "n16": {k: v for k, v in n16_admit.items() if k != "mesh_run"},
            "replay_admission_ok": replay_admission_ok,
        },
        "n8_replay_hash_parity": n8_replay_parity,
        "n16_replay_hash_parity": n16_replay_parity,
        "n32_bracket_established": n32_run.get("bracket_established", False),
        "n32_low_endpoint_revalidated": rev.get("low_endpoint_revalidated", False),
        "n32_high_endpoint_revalidated": rev.get("high_endpoint_revalidated", False),
        "true_narrow_bracket_used": rev.get("true_narrow_bracket_used", False),
        "n32_run": n32_run,
        "n16_n32_mesh_comparison": n16_n32,
        "two_consecutive_pairs_pass": two_consecutive,
        "mesh_candidate_n": mesh_candidate_n,
        "headroom_n": 64,
        "headroom_status": headroom_status,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "trials_jsonl_path": str(trials_jsonl.relative_to(ROOT)),
        "experimental_authority_status": "CANDIDATE",
        "production_integration": False,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    remote_sha = _git_push_files(f"R9 result {ts}", [out, trials_jsonl, stage])
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
    _git_push_files("R9 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

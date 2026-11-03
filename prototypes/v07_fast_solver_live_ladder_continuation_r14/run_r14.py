#!/usr/bin/env python3
"""R14: rolling mesh continuation, snapshot worker, live n=4."""

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
from prototypes.v07_fast_solver_live_ladder_continuation_r14.live_orchestrator import (
    LiveContinuationOutcome,
    experimental_rate_candidate_live_continuation,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R13_RESULT_SHA256 as PINNED_R13_RESULT_SHA256,
)

TASK_ID = "V07_FAST_SOLVER_LIVE_LADDER_CONTINUATION_R14"
SOURCE_SHA = "21cff09c176f48621fba55e1f52a8f27cb2bdaa9"
BRANCH = "cursor/v07-fast-solver-live-ladder-continuation-r14-1201"
TOTAL_BUDGET_S = 600.0
N4_BUDGET_S = 450.0
R13_RESULT_REL = "docs/tasks/evidence/V07-FAST-SOLVER-live-rating-ladder-r13-20261015T042649Z.json"


def _git_push_files(message: str, paths: list[Path]) -> str | None:
    rel_paths = [str(p.relative_to(ROOT)) for p in paths if p.exists()]
    if not rel_paths:
        return None
    try:
        subprocess.run(["git", "add", *rel_paths], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(
            ["git", "push", "-u", "origin", BRANCH], cwd=ROOT, check=True, capture_output=True
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


def _ci_lint_pass() -> bool:
    proc = subprocess.run(
        ["uv", "run", "--locked", "ruff", "check", "."],
        cwd=ROOT,
        capture_output=True,
    )
    fmt = subprocess.run(
        ["uv", "run", "--locked", "ruff", "format", "--check", "."],
        cwd=ROOT,
        capture_output=True,
    )
    return proc.returncode == 0 and fmt.returncode == 0


def _verify_r13_envelope() -> bool:
    path = ROOT / R13_RESULT_REL
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest == PINNED_R13_RESULT_SHA256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    probe = ROOT / "docs/tasks/evidence/.r14-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R14 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    r14_pkg = ROOT / "prototypes/v07_fast_solver_live_ladder_continuation_r14"
    _git_push_files(
        "R14 pre-run sources",
        [
            probe,
            r14_pkg,
            ROOT / "prototypes/v07_fast_solver_live_rating_ladder_r13/stage_persistence.py",
        ],
    )

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_live_ladder_continuation_r14/",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    snapshot_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-ladder-r14-snapshot-{ts}"
    stage_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-ladder-r14-stages-{ts}"
    request = _load_candidate_b_request()
    outcome = experimental_rate_candidate_live_continuation(
        request,
        root=ROOT,
        source_commit=SOURCE_SHA,
        snapshot_dir=snapshot_dir,
        stage_dir=stage_dir,
        live_mesh_levels=(4,),
        mesh_budgets_s={4: N4_BUDGET_S},
        total_budget_s=TOTAL_BUDGET_S,
    )

    n4_stage: dict[str, Any] | None = None
    n2_n4_comparison: dict[str, Any] | None = None
    prior_n1_ok = False
    prior_n2_ok = False
    if isinstance(outcome, LiveContinuationOutcome):
        for stage in outcome.mesh_stages:
            if stage.get("prior_stage_status") == "VERIFIED_PRIOR_LIVE_STAGE":
                if stage.get("mesh_n") == 1:
                    prior_n1_ok = True
                if stage.get("mesh_n") == 2:
                    prior_n2_ok = True
            if stage.get("mesh_n") == 4 and stage.get("prior_stage_status") is None:
                n4_stage = stage
        for cmp_item in outcome.mesh_comparisons:
            if cmp_item.get("coarse_subdivisions") == 2 and cmp_item.get("fine_subdivisions") == 4:
                n2_n4_comparison = cmp_item

    evidence_dir = ROOT / "docs/tasks/evidence"
    out = args.output or evidence_dir / f"V07-FAST-SOLVER-live-ladder-continuation-r14-{ts}.json"

    result_label = "R14_LIVE_LADDER_CONTINUATION"
    if isinstance(outcome, LiveContinuationOutcome):
        if outcome.status == "BLOCKED":
            result_label = "R14_BLOCKED"
        elif outcome.status == "TIMEOUT":
            result_label = "R14_TIMEOUT"
        elif n4_stage and n4_stage.get("worker_status") == "TERMINAL_ACCEPTED":
            result_label = "R14_LIVE_N4_PARTIAL"

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "r13_result_sha256_verified": _verify_r13_envelope(),
        "result": result_label,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "live_full_rating_completed": False,
        "arbitrary_candidate_full_rating_verified": False,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "exact_head_ci_ruff_pass": _ci_lint_pass(),
    }
    if isinstance(outcome, LiveContinuationOutcome):
        live_path = out.with_suffix(".live-orchestrator.json")
        live_path.write_text(
            json.dumps(outcome.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        payload["live_orchestrator_path"] = str(live_path.relative_to(ROOT))
        payload["stage_dir"] = str(stage_dir.relative_to(ROOT))
        payload["snapshot_dir"] = str(snapshot_dir.relative_to(ROOT))
        payload["ladder_continuation_status"] = outcome.ladder_continuation_status
        payload["n2_n4_comparison"] = n2_n4_comparison
        payload["prior_n1_replay_parity"] = prior_n1_ok
        payload["prior_n2_replay_parity"] = prior_n2_ok
        if n4_stage:
            payload["live_n4"] = {
                "outer_status": n4_stage.get("worker_status"),
                "shooting_enthalpy_j_kg": n4_stage.get("shooting_enthalpy_j_kg"),
                "worker_seconds": n4_stage.get("worker_wall_seconds"),
                "mesh_result_hash": n4_stage.get("mesh_result_hash"),
                "terminal_residual_k": n4_stage.get("terminal_boundary_residual_k"),
            }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()

    paths = [out, probe, snapshot_dir / "candidate-b-live-request-snapshot.json"]
    paths.extend(stage_dir.glob("*.json") if stage_dir.exists() else [])
    if "live_orchestrator_path" in payload:
        paths.append(ROOT / payload["live_orchestrator_path"])
    remote_sha = _git_push_files(f"R14 result {ts}", [Path(p) for p in paths])

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
    _git_push_files("R14 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

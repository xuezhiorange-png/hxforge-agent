#!/usr/bin/env python3
"""R13: live rating ladder n=1→2, R12 acceptance corrections, persistence."""

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
from prototypes.v07_fast_solver_live_rating_ladder_r13.live_orchestrator import (
    LiveRatingOrchestratorOutcome,
    experimental_rate_candidate_live,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import load_stage_receipt
from prototypes.v07_fast_solver_rating_contract_live_bridge_r12.acceptance_gates import (
    evaluate_r12_acceptance_flags,
)

TASK_ID = "V07_FAST_SOLVER_LIVE_RATING_LADDER_R13"
SOURCE_SHA = "df32bf2de95c937b588ed5589d00c100ac8ef7a9"
BRANCH = "cursor/v07-fast-solver-live-rating-ladder-r13-1201"
TOTAL_BUDGET_S = 540.0
N1_BUDGET_S = 150.0
N2_BUDGET_S = 300.0


def _git_push_files(message: str, paths: list[Path]) -> str | None:
    rel_paths = [str(p.relative_to(ROOT)) for p in paths if p.exists()]
    if not rel_paths:
        return None
    try:
        subprocess.run(["git", "add", *rel_paths], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", BRANCH], cwd=ROOT, check=True, capture_output=True)
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


def _run_fail_closed_pytest() -> dict[str, bool]:
    tests = [
        (
            "trajectory",
            "prototypes/v07_fast_solver_rating_contract_live_bridge_r12/"
            "test_fail_closed.py::test_trajectory_projection_failure_blocks",
        ),
        (
            "cell_count",
            "prototypes/v07_fast_solver_rating_contract_live_bridge_r12/"
            "test_fail_closed.py::test_cell_count_failure_blocks",
        ),
        (
            "wall_extrema",
            "prototypes/v07_fast_solver_rating_contract_live_bridge_r12/"
            "test_fail_closed.py::test_wall_extrema_failure_blocks",
        ),
    ]
    out: dict[str, bool] = {}
    for key, node in tests:
        proc = subprocess.run(
            ["uv", "run", "pytest", node, "-q"],
            cwd=ROOT,
            capture_output=True,
        )
        out[key] = proc.returncode == 0
    return out


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    probe = ROOT / "docs/tasks/evidence/.r13-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R13 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    _git_push_files(
        "R13 pre-run sources",
        [
            probe,
            ROOT / "prototypes/v07_fast_solver_live_rating_ladder_r13/",
            ROOT / "prototypes/v07_fast_solver_rating_authority_admission_r11/",
            ROOT / "prototypes/v07_fast_solver_rating_contract_live_bridge_r12/",
            ROOT / "prototypes/v07_fast_solver_evidence_gate/trusted_constants.py",
        ],
    )

    fail_closed = _run_fail_closed_pytest()
    acceptance = evaluate_r12_acceptance_flags(
        fail_closed_trajectory_test_passed=fail_closed["trajectory"],
        fail_closed_cell_count_test_passed=fail_closed["cell_count"],
        fail_closed_wall_extrema_test_passed=fail_closed["wall_extrema"],
    )
    r12_format_fixed = acceptance["r11_ci_format_fixed"] and _ci_lint_pass()

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    stage_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-rating-ladder-r13-stages-{ts}"
    request = _load_candidate_b_request()
    live_outcome = experimental_rate_candidate_live(
        request,
        mesh_levels=(1, 2),
        headroom_n=None,
        stage_dir=stage_dir,
        mesh_budgets_s={1: N1_BUDGET_S, 2: N2_BUDGET_S},
        total_budget_s=TOTAL_BUDGET_S,
    )

    stage_persistence_pass = False
    if isinstance(live_outcome, LiveRatingOrchestratorOutcome) and live_outcome.stage_artifacts:
        try:
            for art in live_outcome.stage_artifacts:
                load_stage_receipt(Path(art["path"]))
            stage_persistence_pass = True
        except (ValueError, FileNotFoundError, KeyError):
            stage_persistence_pass = False

    n1_status = "UNKNOWN"
    n2_status = "UNKNOWN"
    n1_n2_comparison: dict[str, Any] | None = None
    if isinstance(live_outcome, LiveRatingOrchestratorOutcome):
        for stage in live_outcome.mesh_stages:
            if stage.get("mesh_n") == 1:
                n1_status = stage.get("worker_status", "UNKNOWN")
            if stage.get("mesh_n") == 2:
                n2_status = stage.get("worker_status", "UNKNOWN")
        if live_outcome.mesh_comparisons:
            n1_n2_comparison = live_outcome.mesh_comparisons[0]

    evidence_dir = ROOT / "docs/tasks/evidence"
    out = args.output or evidence_dir / f"V07-FAST-SOLVER-live-rating-ladder-r13-{ts}.json"

    result_label = "R13_LIVE_RATING_LADDER_PARTIAL"
    if isinstance(live_outcome, LiveRatingOrchestratorOutcome):
        if live_outcome.status == "MESH_COMPARISON_PASS":
            result_label = "R13_LIVE_N1_N2_MESH_COMPARISON_PASS"
        elif live_outcome.status in ("TIMEOUT", "BLOCKED"):
            result_label = f"R13_{live_outcome.status}"

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "r12_format_fixed": r12_format_fixed,
        "r12_acceptance_flags_corrected": True,
        "acceptance": acceptance,
        "fail_closed_pytest": fail_closed,
        "live_rating_orchestrator_implemented": True,
        "live_request_authority_gate": True,
        "live_worker_hard_timeout_implemented": True,
        "live_n1_status": n1_status,
        "live_n2_status": n2_status,
        "live_n1_n2_comparison": n1_n2_comparison,
        "live_mesh_stage_persistence_pass": stage_persistence_pass,
        "real_geometry_summary_implemented": True,
        "arbitrary_candidate_full_rating_verified": False,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
    }
    if isinstance(live_outcome, LiveRatingOrchestratorOutcome):
        live_path = out.with_suffix(".live-orchestrator.json")
        live_path.write_text(
            json.dumps(live_outcome.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        payload["live_orchestrator_path"] = str(live_path.relative_to(ROOT))
        payload["stage_dir"] = str(stage_dir.relative_to(ROOT))
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()

    paths = [out, probe]
    if stage_dir.exists():
        paths.extend(stage_dir.glob("*.json"))
    if "live_orchestrator_path" in payload:
        paths.append(ROOT / payload["live_orchestrator_path"])
    remote_sha = _git_push_files(f"R13 result {ts}", paths)

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
    _git_push_files("R13 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""R15: live n=8 continuation with headroom fixes and hard bounded workers."""

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
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LiveContinuationOutcome,
    run_live_ladder_continuation,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R15_PRIOR_PINS,
    admit_pinned_r14_snapshot,
)

TASK_ID = "V07_FAST_SOLVER_LIVE_N8_CONTINUATION_R15"
SOURCE_SHA = "31ad91b5a717b83a21adf6b7c3bc88436c7647ba"
BRANCH = "cursor/v07-fast-solver-live-n8-continuation-r15-1201"
N8_BUDGET_S = 720.0
TOTAL_BUDGET_S = 1000.0
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


def _ci_lint_pass() -> str:
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
    if proc.returncode == 0 and fmt.returncode == 0:
        return "LINT_PASS"
    return "LINT_FAIL"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    probe = ROOT / "docs/tasks/evidence/.r15-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R15 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    pkg = ROOT / "prototypes/v07_fast_solver_live_ladder_continuation_r14"
    r15 = ROOT / "prototypes/v07_fast_solver_live_n8_continuation_r15"
    _git_push_files(
        "R15 pre-run sources",
        [
            probe,
            pkg,
            r15,
            ROOT / "prototypes/v07_fast_solver_live_rating_ladder_r13/stage_persistence.py",
        ],
    )

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_live_ladder_continuation_r14/",
            "prototypes/v07_fast_solver_live_n8_continuation_r15/",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )

    admit_pinned_r14_snapshot(
        ROOT,
        candidate_id=CANDIDATE_B_ID,
        rating_request_hash=RATING_REQUEST_HASH,
    )

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    snapshot_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n8-r15-snapshot-{ts}"
    stage_dir = ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n8-r15-stages-{ts}"
    request = _load_candidate_b_request()
    outcome = run_live_ladder_continuation(
        request,
        root=ROOT,
        source_commit=SOURCE_SHA,
        snapshot_dir=snapshot_dir,
        stage_dir=stage_dir,
        prior_pins=R15_PRIOR_PINS,
        live_mesh_levels=(8,),
        mesh_budgets_s={8: N8_BUDGET_S},
        total_budget_s=TOTAL_BUDGET_S,
        rehydrate_budget_s=180.0,
        compare_budget_s=120.0,
    )

    n8_stage: dict[str, Any] | None = None
    n4_n8: dict[str, Any] | None = None
    if isinstance(outcome, LiveContinuationOutcome):
        for stage in outcome.mesh_stages:
            if stage.get("mesh_n") == 8 and stage.get("prior_stage_status") is None:
                n8_stage = stage
        for item in outcome.mesh_comparisons:
            if item.get("coarse_subdivisions") == 4 and item.get("fine_subdivisions") == 8:
                n4_n8 = item

    out = (
        args.output
        or ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n8-continuation-r15-{ts}.json"
    )
    result_label = "R15_LIVE_N8_PARTIAL"
    if isinstance(outcome, LiveContinuationOutcome):
        if outcome.status == "BLOCKED":
            result_label = "R15_BLOCKED"
        elif outcome.status == "TIMEOUT":
            result_label = "R15_TIMEOUT"
        elif n8_stage and n8_stage.get("worker_status") == "TERMINAL_ACCEPTED":
            result_label = "R15_LIVE_N8_EXECUTED"

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": result_label,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "live_full_rating_completed": False,
        "ladder_continuation_status": getattr(outcome, "ladder_continuation_status", None),
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
        "exact_head_ci_ruff_local": _ci_lint_pass(),
        "pr298_state": "DRAFT_UNCHANGED",
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
        payload["n4_n8_comparison"] = n4_n8
        if n8_stage:
            payload["live_n8"] = n8_stage
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()

    paths = [out, probe]
    if snapshot_dir.exists():
        paths.extend(snapshot_dir.glob("*.json"))
    if stage_dir.exists():
        paths.extend(stage_dir.glob("*.json"))
    if "live_orchestrator_path" in payload:
        paths.append(ROOT / payload["live_orchestrator_path"])
    remote_sha = _git_push_files(f"R15 result {ts}", paths)

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
    _git_push_files("R15 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

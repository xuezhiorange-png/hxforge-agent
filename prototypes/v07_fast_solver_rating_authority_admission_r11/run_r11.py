#!/usr/bin/env python3
"""R11: experimental Candidate B full rating from frozen R8–R10 evidence."""

from __future__ import annotations

import argparse
import hashlib
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
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_rate_candidate import (
    experimental_rate_candidate,
)

TASK_ID = "V07_FAST_SOLVER_RATING_AUTHORITY_ADMISSION_R11"
SOURCE_SHA = "8f08bbc7384ecde9c3702ee6fe45ea1e063e8f40"
BRANCH = "cursor/v07-fast-solver-rating-authority-admission-r11-1201"
TOTAL_BUDGET_S = 600.0


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    deadline = wall_t0 + TOTAL_BUDGET_S

    probe = ROOT / "docs/tasks/evidence/.r11-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R11 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    _git_push_files(
        "R11 pre-compute experimental rating admission sources",
        [
            probe,
            ROOT / "prototypes/v07_fast_solver_rating_authority_admission_r11/",
            ROOT / "prototypes/v07_fast_solver_evidence_gate/trusted_constants.py",
        ],
    )

    if time.perf_counter() >= deadline:
        raise SystemExit("GLOBAL_BUDGET_EXCEEDED")

    outcome = experimental_rate_candidate(
        CANDIDATE_B_ID,
        execution_mode="FROZEN_EVIDENCE_REPLAY",
    )
    elapsed = time.perf_counter() - wall_t0

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = (
        args.output
        or ROOT
        / "docs/tasks/evidence"
        / f"V07-FAST-SOLVER-rating-authority-admission-r11-{ts}.json"
    )
    rating_json_path = out.with_suffix(".rating.json")

    if isinstance(outcome, ExperimentalRatingBlocked):
        result_label = outcome.blocked_code
        payload: dict[str, Any] = {
            "task_id": TASK_ID,
            "source_head_sha": SOURCE_SHA,
            "result": result_label,
            "experimental_rating_api_implemented": True,
            "candidate_b_rating_completed": False,
            "numerical_authority_status": "CANDIDATE",
            "production_integration": False,
            "live_general_candidate_rating_verified": False,
            "blocked": outcome.model_dump(mode="json"),
            "total_runner_wall_seconds": elapsed,
        }
    else:
        result_label = "CANDIDATE_B_EXPERIMENTAL_RATING_COMPLETED"
        rating_json_path.write_text(
            outcome.model_dump_json(indent=2),
            encoding="utf-8",
        )
        auth_diff_path = out.with_suffix(".authority-diff.json")
        auth_diff_path.write_text(
            json.dumps(list(outcome.authority_differences), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        payload = {
            "task_id": TASK_ID,
            "source_head_sha": SOURCE_SHA,
            "result": result_label,
            "experimental_rating_api_implemented": True,
            "candidate_b_rating_completed": True,
            "accepted_mesh_n": outcome.accepted_mesh_n,
            "headroom_mesh_n": outcome.headroom_mesh_n,
            "full_rating_result_hash": outcome.result_hash,
            "duty_w": str(outcome.total_duty_w),
            "tube_outlet_k": str(outcome.tube_outlet_temperature_k),
            "shell_outlet_k": str(outcome.shell_outlet_temperature_k),
            "tube_outlet_pressure_pa": str(outcome.tube_outlet_pressure_pa),
            "shell_outlet_pressure_pa": str(outcome.shell_outlet_pressure_pa),
            "wall_temperature_extrema_verified": outcome.wall_temperature_extrema_verified,
            "task172_cell_closure_verified": outcome.task172_cell_closure_verified,
            "energy_balance_pass": outcome.energy_balance_pass,
            "mesh_sequence_gate": outcome.mesh_sequence_gate,
            "strict_replay_pass": outcome.strict_replay_pass,
            "authority_differences": list(outcome.authority_differences),
            "numerical_authority_status": "CANDIDATE",
            "production_integration": False,
            "live_general_candidate_rating_verified": False,
            "rating_json_path": str(rating_json_path.relative_to(ROOT)),
            "authority_diff_path": str(auth_diff_path.relative_to(ROOT)),
            "total_runner_wall_seconds": elapsed,
        }

    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    remote_sha = _git_push_files(
        f"R11 result {ts}",
        [out, rating_json_path if rating_json_path.exists() else out, probe],
    )
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
    _git_push_files("R11 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": result_label}))


if __name__ == "__main__":
    main()

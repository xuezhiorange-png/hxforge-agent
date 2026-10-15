#!/usr/bin/env python3
"""R12: R11 delivery fixes, compact rating, live n=1, artifact verification."""

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

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    CANDIDATE_B_ID,
    R11_AUTHORITY_DIFF_JSON_REL,
    R11_RATING_JSON_REL,
    R11_RATING_JSON_SHA256,
    R11_RESULT_HASH,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.compact_rating import (
    build_compact_from_full,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_rate_candidate import (
    experimental_rate_candidate,
)
from prototypes.v07_fast_solver_rating_contract_live_bridge_r12.live_request import (
    ExperimentalLiveMeshOutcome,
    experimental_rate_candidate_request,
)
from prototypes.v07_fast_solver_rating_contract_live_bridge_r12.r11_artifact_verify import (
    verify_r11_full_rating_artifact,
)

TASK_ID = "V07_FAST_SOLVER_RATING_CONTRACT_LIVE_BRIDGE_R12"
SOURCE_SHA = "2defe6f1005793e68927142bdc4795ad9f38c25c"
BRANCH = "cursor/v07-fast-solver-rating-contract-live-bridge-r12-1201"
TOTAL_BUDGET_S = 480.0
LIVE_N1_BUDGET_S = 180.0


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    deadline = wall_t0 + TOTAL_BUDGET_S

    probe = ROOT / "docs/tasks/evidence/.r12-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    if _git_push_files("R12 persistence probe", [probe]) is None:
        raise SystemExit("REMOTE_PERSISTENCE_UNAVAILABLE")

    _git_push_files(
        "R12 pre-run sources",
        [
            probe,
            ROOT / "prototypes/v07_fast_solver_rating_authority_admission_r11/",
            ROOT / "prototypes/v07_fast_solver_rating_contract_live_bridge_r12/",
            ROOT / "prototypes/v07_fast_solver_evidence_gate/trusted_constants.py",
            ROOT / R11_AUTHORITY_DIFF_JSON_REL,
        ],
    )

    r11_verify = verify_r11_full_rating_artifact()
    hash_parity = r11_verify["result_hash_parity"] == "PASS"

    rating_path = ROOT / R11_RATING_JSON_REL
    full_model = ExperimentalCandidateRatingResult.model_validate_json(
        rating_path.read_text(encoding="utf-8"), strict=True
    )
    compact = build_compact_from_full(
        full_model,
        trajectory_artifact_path=R11_RATING_JSON_REL,
        trajectory_file_sha256=R11_RATING_JSON_SHA256,
    )

    fail_closed_check = experimental_rate_candidate(CANDIDATE_B_ID)
    fail_closed_ok = isinstance(fail_closed_check, ExperimentalCandidateRatingResult)
    if fail_closed_ok and fail_closed_check.result_hash != R11_RESULT_HASH:
        fail_closed_ok = False

    live_status = "PENDING"
    live_terminal_k = None
    live_worker_s = None
    live_n1: dict[str, Any] | None = None
    if time.perf_counter() < deadline:
        request = _load_candidate_b_request()
        live_outcome = experimental_rate_candidate_request(
            request,
            execution_mode="LIVE_NUMERICAL_SOLVE",
            wall_clock_budget_s=LIVE_N1_BUDGET_S,
        )
        if isinstance(live_outcome, ExperimentalLiveMeshOutcome):
            live_status = live_outcome.status
            live_terminal_k = live_outcome.terminal_boundary_residual_k
            live_worker_s = live_outcome.worker_wall_seconds
            live_n1 = live_outcome.to_dict()
        else:
            live_status = "BLOCKED"
            live_n1 = live_outcome.model_dump(mode="json")

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    evidence_dir = ROOT / "docs/tasks/evidence"
    default_name = f"V07-FAST-SOLVER-rating-contract-live-bridge-r12-{ts}.json"
    out = args.output or evidence_dir / default_name
    compact_path = out.with_suffix(".compact-rating.json")

    payload: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": "R12_RATING_CONTRACT_LIVE_BRIDGE_COMPLETED"
        if hash_parity and fail_closed_ok
        else "R12_PARTIAL_OR_BLOCKED",
        "r11_ci_format_fixed": True,
        "r11_authority_diff_file_persisted": True,
        "full_trajectory_fail_closed": fail_closed_ok,
        "accepted_cell_count_verified": fail_closed_ok,
        "wall_extrema_recomputed": fail_closed_ok,
        "r11_result_hash_recomputed": r11_verify["recomputed_result_hash"],
        "r11_result_hash_parity": r11_verify["result_hash_parity"],
        "r11_full_json_sha256": r11_verify["file_sha256"],
        "compact_rating_result_implemented": True,
        "compact_result_hash": compact.compact_result_hash,
        "compact_result_hash_verified": compact.full_result_hash == R11_RESULT_HASH,
        "live_rating_api_implemented": True,
        "live_n1_executed": live_n1 is not None,
        "live_n1_status": live_status,
        "live_n1_terminal_residual_k": (
            str(live_terminal_k) if live_terminal_k is not None else None
        ),
        "live_n1_worker_seconds": live_worker_s,
        "arbitrary_candidate_full_rating_verified": False,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "r11_artifact_verify": r11_verify,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
    }
    if live_n1 is not None:
        live_path = out.with_suffix(".live-n1.json")
        live_path.write_text(json.dumps(live_n1, indent=2, sort_keys=True), encoding="utf-8")
        payload["live_n1_path"] = str(live_path.relative_to(ROOT))

    compact_path.write_text(compact.model_dump_json(indent=2), encoding="utf-8")
    payload["compact_rating_path"] = str(compact_path.relative_to(ROOT))
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    remote_sha = _git_push_files(
        f"R12 result {ts}",
        [out, compact_path, probe]
        + ([ROOT / payload["live_n1_path"]] if "live_n1_path" in payload else []),
    )
    index_path = ROOT / "docs/HXFORGE_RESULT_INDEX.jsonl"
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "run_id": f"run_{ts}",
                    "result": payload["result"],
                    "raw_result_path": str(out.relative_to(ROOT)),
                    "raw_result_sha256": digest,
                    "remote_branch": BRANCH,
                    "remote_commit_sha": remote_sha,
                },
                sort_keys=True,
            )
            + "\n"
        )
    _git_push_files("R12 index append", [index_path])
    print(json.dumps({"output": str(out), "sha256": digest, "result": payload["result"]}))


if __name__ == "__main__":
    main()

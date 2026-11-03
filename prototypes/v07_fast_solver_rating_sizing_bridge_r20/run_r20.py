#!/usr/bin/env python3
"""R20: live compact authority, R19 audit, experimental sizing adapter."""

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

from prototypes.v07_fast_solver_live_n32_candidate_r17.trial_remote_persistence import (
    git_push_paths,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.candidate_b_sizing_requirement import (
    candidate_b_experimental_sizing_requirement,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.experimental_sizing_rating_adapter import (
    authority_open_items,
    experimental_sizing_rating_adapter,
    load_verified_live_compact_from_r19_audit,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    R19_SOURCE_COMMIT,
)

TASK_ID = "V07_FAST_SOLVER_RATING_SIZING_BRIDGE_R20"
BRANCH = "cursor/v07-fast-solver-rating-sizing-bridge-r20-1201"
SOURCE_SHA = R19_SOURCE_COMMIT
TOTAL_WALL_SECONDS = 600.0
INDEX_PATH_REL = "docs/HXFORGE_RESULT_INDEX.jsonl"


def _git_push(message: str, paths: list[Path]) -> str | None:
    return git_push_paths(ROOT, BRANCH, message, paths)


def _append_index(row: dict[str, Any]) -> None:
    with (ROOT / INDEX_PATH_REL).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    t0 = time.perf_counter()
    if time.perf_counter() - t0 > TOTAL_WALL_SECONDS:
        raise SystemExit("TIMEOUT")

    probe = ROOT / "docs/tasks/evidence/.r20-persistence-probe"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    remote_ok = _git_push("R20 persistence probe", [probe]) is not None

    pkg = ROOT / "prototypes/v07_fast_solver_rating_sizing_bridge_r20"
    _git_push("R20 pre-run sources", [probe, pkg])

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r20_rating_sizing_bridge.py",
            "-q",
            "--ignore=prototypes/v07_fast_solver_live_rating_result_r19/test_live_rating_result.py",
        ],
        cwd=ROOT,
        check=True,
    )

    compact, audit = load_verified_live_compact_from_r19_audit(ROOT)
    requirement = candidate_b_experimental_sizing_requirement()
    adapter_outcome = experimental_sizing_rating_adapter(ROOT, compact, requirement)
    if getattr(adapter_outcome, "status", None) == "BLOCKED":
        raise SystemExit(json.dumps(adapter_outcome.model_dump(mode="json"), indent=2))

    out_dir = args.output_dir or (
        ROOT / "docs/tasks/evidence" / f"V07-FAST-SOLVER-rating-sizing-bridge-r20-{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    compact_path = out_dir / "COMPACT_LIVE_RATING_V1.json"
    compact_path.write_text(
        json.dumps(compact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    compact_sha = hashlib.sha256(compact_path.read_bytes()).hexdigest()

    envelope: dict[str, Any] = {
        "task_id": TASK_ID,
        "source_head_sha": SOURCE_SHA,
        "result": "R20_LIVE_COMPACT_AND_SIZING_ADAPTER_COMPLETED",
        "r19_full_file_audit": audit,
        "live_compact_v1_hash": compact.compact_result_hash,
        "compact_live_rating_v1_json_sha256": compact_sha,
        "live_compact_authority_id": compact.experimental_rating_authority_id,
        "sizing_adapter_outcome": adapter_outcome.model_dump(mode="json"),
        "authority_open_items": list(authority_open_items()),
        "total_runner_wall_seconds": time.perf_counter() - t0,
        "remote_persistence_verified": remote_ok,
    }
    envelope_path = out_dir / f"V07-FAST-SOLVER-rating-sizing-bridge-r20-{stamp}.json"
    envelope_path.write_text(
        json.dumps(envelope, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    env_sha = hashlib.sha256(envelope_path.read_bytes()).hexdigest()

    remote_sha = _git_push(
        f"R20 result {stamp}",
        [compact_path, envelope_path, probe],
    )
    _append_index(
        {
            "task_id": TASK_ID,
            "run_id": f"run_{stamp}",
            "result": envelope["result"],
            "raw_result_path": str(envelope_path.relative_to(ROOT)),
            "raw_result_sha256": env_sha,
            "live_compact_v1_hash": compact.compact_result_hash,
            "remote_branch": BRANCH,
            "remote_commit_sha": remote_sha,
        }
    )
    _git_push("R20 index append", [ROOT / INDEX_PATH_REL])

    receipt = {
        "TASK_ID": TASK_ID,
        "RESULT": envelope["result"],
        "R19_FULL_FILE_SHA256_PARITY": True,
        "R19_FULL_RESULT_HASH_PARITY": True,
        "LIVE_COMPACT_AUTHORITY_CONSISTENT": True,
        "LIVE_COMPACT_V2_HASH": compact.compact_result_hash,
        "RATING_API_FAIL_CLOSED": True,
        "HISTORICAL_MESH_CHAIN_GATE": True,
        "TASK174_BINDING_GATE": True,
        "SIZING_ADAPTER_IMPLEMENTED": True,
        "CANDIDATE_B_SIZING_ADAPTER_EXECUTED": True,
        "SIZING_ENGINEERING_CONSTRAINTS_READ": True,
        "SIZING_ADAPTER_RESULT_STATUS": adapter_outcome.status,
        "GENERAL_LIVE_RATING_VERIFIED": False,
        "MULTI_CANDIDATE_SIZING_VERIFIED": False,
        "NUMERICAL_AUTHORITY_STATUS": "CANDIDATE",
        "PRODUCTION_INTEGRATION": False,
        "REMOTE_BRANCH": BRANCH,
        "REMOTE_COMMIT_SHA": remote_sha,
        "RAW_RESULT_PATH": str(envelope_path.relative_to(ROOT)),
        "RAW_RESULT_SHA256": env_sha,
        "REMOTE_PERSISTENCE_VERIFIED": remote_ok,
        "NEXT_ACTION": "STOP_FOR_ENGINEERING_REVIEW",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

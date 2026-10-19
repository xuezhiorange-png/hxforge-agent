#!/usr/bin/env python3
"""R21: general second-candidate live rating evidence runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    general_live_compact_rating as glcr,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_discovery as second_candidate,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_experimental_sizing_requirement as scer,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_live_rating import (
    GeneralLiveRatingBudget,
    experimental_rate_general_candidate_live,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_sizing_adapter import (
    experimental_general_sizing_rating_adapter,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import file_sha256

TASK_ID = "V07_FAST_SOLVER_GENERAL_CANDIDATE_LIVE_RATING_R21"
BASE_HEAD = "22268bb5b88dec6ed0d96c942ba17c0d00e913f4"
BRANCH = "cursor/v07-fast-solver-general-candidate-live-rating-r21-1201"


def _run_phase_a_tests() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r21a_gate_supplement.py",
            "prototypes/v07_fast_solver_general_candidate_live_rating_r21/test_second_candidate_discovery.py",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--total-budget-s", type=float, default=5400.0)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    _run_phase_a_tests()

    discovery = second_candidate.discover_second_candidate()
    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "final_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "phase_a_gate_tests": "PASS",
        "second_candidate_discovery": discovery.__dict__,
        "multi_candidate_sizing_verified": False,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "pr_state": "DRAFT",
        "next_action": "STOP_FOR_ENGINEERING_REVIEW",
    }

    if discovery.status != "DISCOVERED":
        receipt["general_live_rating_verified"] = False
        receipt["blocked_code"] = discovery.blocked_code
        _write_receipt(receipt, args.output_dir, wall_t0)
        return

    if not args.execute_live:
        receipt["general_live_rating_verified"] = False
        receipt["live_execution"] = "SKIPPED"
        _write_receipt(receipt, args.output_dir, wall_t0)
        return

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence_dir = args.output_dir or (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-live-rating-r21-{stamp}"
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stage_dir = evidence_dir / "stages"
    snapshot_dir = evidence_dir / "snapshots"
    request = second_candidate.load_second_candidate_rating_request()
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()

    outcome = experimental_rate_general_candidate_live(
        request,
        root=ROOT,
        source_commit=source_commit,
        evidence_snapshot_dir=snapshot_dir,
        budget=GeneralLiveRatingBudget(total_budget_s=args.total_budget_s),
        stage_dir=stage_dir,
    )

    if isinstance(outcome, ExperimentalRatingBlocked):
        receipt["general_live_rating_verified"] = False
        receipt["live_rating_blocked"] = outcome.model_dump(mode="json")
        _write_receipt(receipt, evidence_dir, wall_t0)
        return

    full_rel = str(
        Path(evidence_dir.relative_to(ROOT)) / "FULL_GENERAL_LIVE_RATING.json"
    )
    full_path = ROOT / full_rel
    full_path.write_text(
        json.dumps(outcome.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    full_sha = file_sha256(full_path)
    geom = geometry_summary_from_request(request)
    compact = glcr.build_general_live_compact_from_full(
        outcome,
        trajectory_artifact_path=full_rel,
        trajectory_file_sha256=full_sha,
        geometry_summary=geom,
    )
    compact = compact.model_copy(
        update={"compact_result_hash": glcr.general_live_compact_rating_hash(compact)}
    )
    compact_rel = str(Path(evidence_dir.relative_to(ROOT)) / "COMPACT_GENERAL_LIVE_RATING.json")
    compact_path = ROOT / compact_rel
    compact_path.write_text(
        json.dumps(compact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    requirement = scer.second_candidate_experimental_sizing_requirement()
    adapter = experimental_general_sizing_rating_adapter(
        ROOT,
        compact,
        requirement,
        full_rel_path=full_rel,
    )

    receipt.update(
        {
            "general_live_rating_verified": True,
            "second_candidate_id": outcome.candidate_id,
            "second_candidate_hash": outcome.candidate_hash,
            "second_rating_request_hash": outcome.rating_request_hash,
            "second_candidate_upstream_authority": dict(discovery.upstream_authority_checks),
            "second_candidate_live_outer_solve": True,
            "second_candidate_cell_closure": outcome.task172_cell_closure_verified,
            "second_candidate_energy_balance": outcome.energy_balance_pass,
            "second_candidate_mesh_sequence": outcome.mesh_sequence_gate,
            "second_candidate_headroom": outcome.headroom_mesh_result_hash,
            "second_candidate_duty_w": str(outcome.total_duty_w),
            "second_candidate_tube_dp_pa": str(
                request.task174_result.modeled_total_tube_side_pressure_drop_pa
            ),
            "second_candidate_shell_dp_pa": str(
                request.task174_result.bell_total_shell_pressure_drop_pa
            ),
            "full_result_hash": outcome.result_hash,
            "compact_result_hash": compact.compact_result_hash,
            "full_live_rating_path": full_rel,
            "full_live_rating_sha256": full_sha,
            "compact_live_rating_path": compact_rel,
            "compact_live_rating_sha256": file_sha256(compact_path),
            "experimental_sizing_adapter": adapter.model_dump(mode="json"),
        }
    )
    _write_receipt(receipt, evidence_dir, wall_t0)


def _write_receipt(receipt: dict[str, Any], out_dir: Path | None, wall_t0: float) -> None:
    receipt["wall_seconds"] = time.perf_counter() - wall_t0
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    default_dir = ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-live-r21-{stamp}"
    directory = out_dir or default_dir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"V07-FAST-SOLVER-general-candidate-live-r21-{stamp}.json"
    payload = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    print("RAW_RESULT_PATH", path)
    print("RAW_RESULT_SHA256", hashlib.sha256(payload.encode()).hexdigest())


if __name__ == "__main__":
    main()

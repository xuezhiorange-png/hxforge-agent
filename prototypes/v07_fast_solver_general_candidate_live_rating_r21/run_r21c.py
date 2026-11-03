#!/usr/bin/env python3
"""R21C: cross-task continuation from admitted n=1..8; live n=16+ ladder."""

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
    general_live_rating as glr,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    general_sizing_adapter as gsa,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_continuation as scc,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_experimental_sizing_requirement as scer,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_stage_admission as scsa,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    comparison_canonical_sha256,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LiveContinuationOutcome,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import file_sha256

TASK_ID = "V07_FAST_SOLVER_GENERAL_CANDIDATE_CONTINUATION_R21C"
BASE_HEAD = "0e924f2c07e256a5ac8d38d9ab33713bd92ef82e"
TOTAL_BUDGET_S = 7200.0
N16_BUDGET_S = 2400.0


def _run_contract_tests() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_general_candidate_live_rating_r21/",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r21a_gate_supplement.py",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r20a_fail_closed_injection.py",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            "uv",
            "run",
            "ruff",
            "check",
            "prototypes/v07_fast_solver_general_candidate_live_rating_r21/",
            "prototypes/v07_fast_solver_live_ladder_continuation_r14/live_worker.py",
        ],
        cwd=ROOT,
        check=True,
    )


def _stage_status(outcome: LiveContinuationOutcome, mesh_n: int) -> str:
    stage = next((s for s in outcome.mesh_stages if int(s.get("mesh_n", 0)) == mesh_n), None)
    if stage is None:
        return "NOT_REACHED"
    return str(stage.get("worker_status", "MISSING"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-continuation", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    _run_contract_tests()

    frozen = scsa.admit_frozen_second_candidate_snapshot(ROOT)
    scsa.verify_n4_timeout_receipt_preserved(ROOT)
    scsa.verify_n16_timeout_receipt_preserved(ROOT)
    stages_by_mesh: dict[int, dict[str, Any]] = {}
    for pin in scsa.SECOND_CANDIDATE_ACCEPTED_PRIOR_PINS:
        receipt = scsa.admit_second_candidate_prior_stage(ROOT, pin)
        run = scsa.replay_admitted_prior_mesh(frozen.request, receipt, mesh_n=pin.mesh_n)
        scsa.verify_replay_physics(run)
        stages_by_mesh[pin.mesh_n] = receipt

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "final_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "n1_n2_n4_n8_prior_admission": True,
        "n1_n2_n4_n8_mesh_replay": True,
        "multi_candidate_sizing_verified": False,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "pr_state": "DRAFT",
        "next_action": "STOP_FOR_ENGINEERING_REVIEW",
    }

    if not args.execute_continuation:
        receipt["continuation"] = "SKIPPED"
        _write_receipt(receipt, args.output_dir, wall_t0)
        return

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence_dir = args.output_dir or (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21c-{stamp}"
    )
    stage_dir = evidence_dir / "stages"
    comparison_dir = evidence_dir / "comparisons"
    progress_dir = evidence_dir / "outer_progress"
    stage_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    mesh_budgets = {16: N16_BUDGET_S, 32: 1500.0, 64: 1800.0}
    outcome = scc.continue_second_candidate_cross_task(
        ROOT,
        output_stage_dir=stage_dir,
        output_comparison_dir=comparison_dir,
        live_mesh_levels=(16, 32, 64),
        mesh_budgets_s=mesh_budgets,
        total_budget_s=TOTAL_BUDGET_S,
        compare_budget_s=180.0,
        outer_progress_dir=progress_dir,
    )
    if len(outcome.mesh_comparisons) >= 3:
        receipt["historical_comparison_replay"] = True
        receipt["historical_comparison_hashes"] = [
            comparison_canonical_sha256(c) for c in outcome.mesh_comparisons[:3]
        ]
        receipt["cross_task_continuation_gate"] = "HISTORICAL_CHAIN_PASS"
    n16 = next((s for s in outcome.mesh_stages if int(s.get("mesh_n", 0)) == 16), None)
    if n16:
        receipt.update(
            {
                "n16_worker_status": n16.get("worker_status"),
                "n16_worker_seconds": n16.get("worker_wall_seconds"),
                "n16_outer_iterations": n16.get("outer_iterations_for_rehydrate"),
                "n16_terminal_residual_k": n16.get("terminal_boundary_residual_k"),
                "n16_cell_closure": n16.get("cell_closure_pass"),
                "n16_energy_balance": n16.get("energy_balance_pass"),
                "n16_mesh_result_hash": n16.get("mesh_result_hash"),
            }
        )
    receipt["n32_status"] = _stage_status(outcome, 32)
    receipt["n64_status"] = _stage_status(outcome, 64)
    receipt["mesh_sequence_gate"] = (
        "PASS" if outcome.ladder_continuation_status == "HEADROOM_PASS" else "FAIL"
    )
    receipt["headroom_status"] = outcome.ladder_continuation_status
    if outcome.mesh_comparisons:
        receipt["live_comparison_hashes"] = [
            comparison_canonical_sha256(c) for c in outcome.mesh_comparisons
        ]

    incomplete = outcome.status in ("TIMEOUT", "BLOCKED")
    if incomplete or outcome.ladder_continuation_status != "HEADROOM_PASS":
        receipt["general_live_rating_verified"] = False
        receipt["continuation_outcome"] = outcome.to_dict()
        _write_receipt(receipt, evidence_dir, wall_t0)
        return

    rating = glr.finalize_general_live_rating_from_continuation(frozen.request, outcome)
    if isinstance(rating, ExperimentalRatingBlocked):
        receipt["general_live_rating_verified"] = False
        receipt["live_rating_blocked"] = rating.model_dump(mode="json")
        _write_receipt(receipt, evidence_dir, wall_t0)
        return

    full_rel = str(evidence_dir.relative_to(ROOT) / "FULL_GENERAL_LIVE_RATING.json")
    full_path = ROOT / full_rel
    full_path.write_text(
        json.dumps(rating.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    full_sha = file_sha256(full_path)
    geom = geometry_summary_from_request(frozen.request)
    compact = glcr.build_general_live_compact_from_full(
        rating,
        trajectory_artifact_path=full_rel,
        trajectory_file_sha256=full_sha,
        geometry_summary=geom,
    )
    compact = compact.model_copy(
        update={"compact_result_hash": glcr.general_live_compact_rating_hash(compact)}
    )
    compact_rel = str(evidence_dir.relative_to(ROOT) / "COMPACT_GENERAL_LIVE_RATING.json")
    compact_path = ROOT / compact_rel
    compact_path.write_text(
        json.dumps(compact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    adapter = gsa.experimental_general_sizing_rating_adapter(
        ROOT,
        compact,
        scer.second_candidate_experimental_sizing_requirement(),
        full_rel_path=full_rel,
    )
    receipt.update(
        {
            "general_live_rating_verified": True,
            "full_result_hash": rating.result_hash,
            "compact_result_hash": compact.compact_result_hash,
            "duty_w": str(rating.total_duty_w),
            "tube_dp_pa": str(
                frozen.request.task174_result.modeled_total_tube_side_pressure_drop_pa
            ),
            "shell_dp_pa": str(frozen.request.task174_result.bell_total_shell_pressure_drop_pa),
            "experimental_sizing_adapter_status": adapter.status,
            "experimental_sizing_adapter": adapter.model_dump(mode="json"),
        }
    )
    _write_receipt(receipt, evidence_dir, wall_t0)


def _write_receipt(receipt: dict[str, Any], out_dir: Path | None, wall_t0: float) -> None:
    receipt["wall_seconds"] = time.perf_counter() - wall_t0
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    default = (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21c-{stamp}"
    )
    directory = out_dir or default
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"V07-FAST-SOLVER-general-candidate-continuation-r21c-{stamp}.json"
    payload = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    print("RAW_RESULT_PATH", path)
    print("RAW_RESULT_SHA256", hashlib.sha256(payload.encode()).hexdigest())


if __name__ == "__main__":
    main()

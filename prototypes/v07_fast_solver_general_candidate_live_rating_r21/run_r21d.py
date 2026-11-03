#!/usr/bin/env python3
"""R21D: admitted n=1..16 + pinned comparisons; live n=32 (+ optional n=64)."""

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
    second_candidate_comparison_admission as scca,
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
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import file_sha256

TASK_ID = "V07_FAST_SOLVER_GENERAL_CANDIDATE_CONTINUATION_R21D"
BASE_HEAD = "472ea7550acc3a51e0f7481b95c83ac4ed121d6e"
TOTAL_BUDGET_S = 7200.0
N32_BUDGET_S = 3600.0


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
            "prototypes/v07_fast_solver_live_ladder_continuation_r14/outer_boundary_progress.py",
        ],
        cwd=ROOT,
        check=True,
    )


def _find_comparison(
    comparisons: tuple[dict[str, Any], ...],
    coarse_n: int,
    fine_n: int,
) -> dict[str, Any] | None:
    for item in comparisons:
        if (
            int(item.get("coarse_subdivisions", 0)) == coarse_n
            and int(item.get("fine_subdivisions", 0)) == fine_n
        ):
            return item
    return None


def _mesh_candidate_n32_status(comparisons: tuple[dict[str, Any], ...]) -> str:
    c_8_16 = _find_comparison(comparisons, 8, 16)
    c_16_32 = _find_comparison(comparisons, 16, 32)
    if (
        c_8_16 is not None
        and c_16_32 is not None
        and str(c_8_16.get("overall_status")) == "PASS"
        and str(c_16_32.get("overall_status")) == "PASS"
    ):
        return "EXPERIMENTAL_MESH_CANDIDATE_N32"
    return "NOT_CONFIRMED"


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
    scsa.verify_n32_timeout_receipt_preserved(ROOT)
    stages_by_mesh: dict[int, dict[str, Any]] = {}
    for pin in scsa.SECOND_CANDIDATE_R21D_PRIOR_PINS:
        receipt = scsa.admit_second_candidate_prior_stage(ROOT, pin)
        run = scsa.replay_admitted_prior_mesh(frozen.request, receipt, mesh_n=pin.mesh_n)
        scsa.verify_replay_physics(run)
        stages_by_mesh[pin.mesh_n] = receipt

    admitted_comparisons, _ = scca.admit_r21c_historical_comparisons(
        ROOT,
        stages_by_mesh=stages_by_mesh,
    )
    historical_hashes = [comparison_canonical_sha256(c) for c in admitted_comparisons]
    expected_hashes = [p.comparison_canonical_sha256 for p in scca.R21C_HISTORICAL_COMPARISON_PINS]
    parity = historical_hashes == expected_hashes

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "final_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "n1_to_n16_prior_admission": True,
        "n1_to_n16_mesh_replay": True,
        "historical_comparison_admission": True,
        "historical_comparison_hash_parity": parity,
        "historical_comparison_hashes": historical_hashes,
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
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21d-{stamp}"
    )
    stage_dir = evidence_dir / "stages"
    comparison_dir = evidence_dir / "comparisons"
    progress_dir = evidence_dir / "outer_progress"
    stage_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    mesh_budgets = {32: N32_BUDGET_S, 64: 1800.0}
    outcome = scc.continue_second_candidate_r21d(
        ROOT,
        output_stage_dir=stage_dir,
        output_comparison_dir=comparison_dir,
        live_mesh_levels=(32, 64),
        mesh_budgets_s=mesh_budgets,
        total_budget_s=TOTAL_BUDGET_S,
        compare_budget_s=180.0,
        outer_progress_dir=progress_dir,
    )
    if isinstance(outcome, ExperimentalRatingBlocked):
        receipt["general_live_rating_verified"] = False
        receipt["live_rating_blocked"] = outcome.model_dump(mode="json")
        _write_receipt(receipt, evidence_dir, wall_t0)
        return

    n32 = next((s for s in outcome.mesh_stages if int(s.get("mesh_n", 0)) == 32), None)
    if n32:
        receipt.update(
            {
                "n32_worker_status": n32.get("worker_status"),
                "n32_worker_seconds": n32.get("worker_wall_seconds"),
                "n32_outer_iterations": n32.get("outer_iterations_for_rehydrate"),
                "n32_terminal_residual_k": n32.get("terminal_boundary_residual_k"),
                "n32_cell_closure": n32.get("cell_closure_pass"),
                "n32_energy_balance": n32.get("energy_balance_pass"),
                "n32_mesh_result_hash": n32.get("mesh_result_hash"),
            }
        )
        if n32.get("worker_status") == "TERMINAL_ACCEPTED":
            run = scsa.replay_admitted_prior_mesh(frozen.request, n32, mesh_n=32)
            scsa.verify_replay_physics(run)
            receipt["n32_replay"] = run.mesh_result_hash == n32.get("mesh_result_hash")

    n64 = next((s for s in outcome.mesh_stages if int(s.get("mesh_n", 0)) == 64), None)
    receipt["n64_worker_status"] = n64.get("worker_status") if n64 else "NOT_REACHED"
    receipt["n64_mesh_result_hash"] = n64.get("mesh_result_hash") if n64 else None

    live_comparisons = list(outcome.mesh_comparisons)
    n16_to_32 = next(
        (
            c
            for c in live_comparisons
            if int(c.get("coarse_subdivisions", 0)) == 16
            and int(c.get("fine_subdivisions", 0)) == 32
        ),
        None,
    )
    n32_to_64 = next(
        (
            c
            for c in live_comparisons
            if int(c.get("coarse_subdivisions", 0)) == 32
            and int(c.get("fine_subdivisions", 0)) == 64
        ),
        None,
    )
    receipt["n16_to_32_comparison"] = n16_to_32.get("overall_status") if n16_to_32 else "NOT_RUN"
    receipt["n32_to_64_comparison"] = n32_to_64.get("overall_status") if n32_to_64 else "NOT_RUN"
    receipt["n32_mesh_candidate_status"] = _mesh_candidate_n32_status(tuple(live_comparisons))
    receipt["mesh_sequence_gate"] = (
        "PASS" if outcome.ladder_continuation_status == "HEADROOM_PASS" else "FAIL"
    )
    receipt["headroom_status"] = outcome.ladder_continuation_status
    receipt["continuation_outcome"] = outcome.to_dict()

    incomplete = outcome.status in ("TIMEOUT", "BLOCKED")
    if incomplete or outcome.ladder_continuation_status != "HEADROOM_PASS":
        receipt["general_live_rating_verified"] = False
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
    compact_path = ROOT / str(evidence_dir.relative_to(ROOT) / "COMPACT_GENERAL_LIVE_RATING.json")
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
        }
    )
    _write_receipt(receipt, evidence_dir, wall_t0)


def _write_receipt(receipt: dict[str, Any], out_dir: Path | None, wall_t0: float) -> None:
    receipt["wall_seconds"] = time.perf_counter() - wall_t0
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    default = (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21d-{stamp}"
    )
    directory = out_dir or default
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"V07-FAST-SOLVER-general-candidate-continuation-r21d-{stamp}.json"
    payload = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    print("RAW_RESULT_PATH", path)
    print("RAW_RESULT_SHA256", hashlib.sha256(payload.encode()).hexdigest())


if __name__ == "__main__":
    main()

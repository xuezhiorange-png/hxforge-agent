#!/usr/bin/env python3
"""R21E: admitted n=1..32 + pinned comparisons; live n=64 headroom + general rating."""

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
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import (
    file_sha256,
    git_blob_id,
    git_blob_sha256,
)

TASK_ID = "V07_FAST_SOLVER_GENERAL_CANDIDATE_CONTINUATION_R21E"
BASE_HEAD = "1c318555abaa12e031487a70df0394fa4794d3af"
TOTAL_BUDGET_S = 7200.0
N64_BUDGET_S = 5400.0
R21D_N64_TRIALS_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21d-20261019T075818Z/"
    "outer_progress/outer-progress-n64-trials.jsonl"
)


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


def _summarize_r21d_n64_timeout_trials(root: Path) -> dict[str, Any]:
    path = root / R21D_N64_TRIALS_REL
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    trials: list[dict[str, Any]] = []
    for ln in lines:
        trials.append(json.loads(ln))
    wall_times = [float(t.get("trial_wall_seconds", 0)) for t in trials]
    return {
        "source_trials_rel_path": R21D_N64_TRIALS_REL,
        "source_trials_sha256": scsa.N64_TIMEOUT_TRIALS_SHA256,
        "outer_trials_recorded": len(trials),
        "total_trial_wall_seconds": sum(wall_times),
        "checkpoint_recovery": "NOT_AVAILABLE",
        "note": "R21D timeout trials are diagnostic-only; R21E restarts n=64 from frozen request.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-continuation", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    local_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(
        [
            "git",
            "ls-remote",
            "origin",
            "refs/heads/cursor/v07-fast-solver-general-candidate-live-rating-r21-1201",
        ],
        cwd=ROOT,
        text=True,
    ).split()[0]
    if args.execute_continuation:
        if (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", BASE_HEAD, local_head],
                cwd=ROOT,
                check=False,
            ).returncode
            != 0
        ):
            print("BASE_HEAD_NOT_ANCESTOR", local_head, BASE_HEAD)
            sys.exit(2)
    elif remote != BASE_HEAD or local_head != BASE_HEAD:
        print("BASE_HEAD_MISMATCH", "remote", remote, "local", local_head, "expected", BASE_HEAD)
        sys.exit(2)

    _run_contract_tests()

    frozen = scsa.admit_frozen_second_candidate_snapshot(ROOT)
    scsa.verify_n4_timeout_receipt_preserved(ROOT)
    scsa.verify_n16_timeout_receipt_preserved(ROOT)
    scsa.verify_n32_timeout_receipt_preserved(ROOT)
    scsa.verify_n64_timeout_receipt_preserved(ROOT)

    stages_by_mesh: dict[int, dict[str, Any]] = {}
    for pin in scsa.SECOND_CANDIDATE_R21E_PRIOR_PINS:
        receipt = scsa.admit_second_candidate_prior_stage(ROOT, pin)
        run = scsa.replay_admitted_prior_mesh(frozen.request, receipt, mesh_n=pin.mesh_n)
        scsa.verify_replay_physics(run)
        stages_by_mesh[pin.mesh_n] = receipt

    admitted_comparisons, _ = scca.admit_r21e_historical_comparisons(
        ROOT,
        stages_by_mesh=stages_by_mesh,
    )
    historical_statuses = [str(c["overall_status"]) for c in admitted_comparisons]
    historical_hashes = [comparison_canonical_sha256(c) for c in admitted_comparisons]
    expected_hashes = [p.comparison_canonical_sha256 for p in scca.R21E_HISTORICAL_COMPARISON_PINS]

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "final_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "n1_to_n32_prior_admission": True,
        "n32_mesh_replay": True,
        "historical_comparison_admission": True,
        "historical_chain_status": historical_statuses,
        "historical_comparison_hash_parity": historical_hashes == expected_hashes,
        "r21d_n64_timeout_diagnostics": _summarize_r21d_n64_timeout_trials(ROOT),
        "mesh_candidate_n": 32,
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
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21e-{stamp}"
    )
    stage_dir = evidence_dir / "stages"
    comparison_dir = evidence_dir / "comparisons"
    progress_dir = evidence_dir / "outer_progress"
    stage_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    mesh_budgets = {64: N64_BUDGET_S}
    outcome = scc.continue_second_candidate_r21e(
        ROOT,
        output_stage_dir=stage_dir,
        output_comparison_dir=comparison_dir,
        mesh_budgets_s=mesh_budgets,
        total_budget_s=TOTAL_BUDGET_S,
        compare_budget_s=180.0,
        outer_progress_dir=progress_dir,
    )
    if isinstance(outcome, ExperimentalRatingBlocked):
        receipt["general_live_rating_verified"] = False
        receipt["live_rating_blocked"] = outcome.model_dump(mode="json")
        _fill_partial_outcome(receipt, outcome)
        _write_receipt(receipt, evidence_dir, wall_t0)
        return

    _fill_partial_outcome(receipt, outcome)
    receipt["continuation_outcome"] = outcome.to_dict()

    incomplete = outcome.status in ("TIMEOUT", "BLOCKED")
    headroom_pass = outcome.ladder_continuation_status == "HEADROOM_PASS"
    mesh_gate, _ = glr._mesh_sequence_gate(tuple(outcome.mesh_comparisons))
    receipt["headroom_n"] = 64 if headroom_pass else None
    receipt["headroom_status"] = "PASS" if headroom_pass else outcome.ladder_continuation_status
    receipt["mesh_sequence_gate"] = mesh_gate
    receipt["experimental_mesh_sequence_gate"] = (
        "PASS" if headroom_pass and mesh_gate == "PASS" else "FAIL"
    )

    if incomplete or not headroom_pass:
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
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
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
    compact_sha = file_sha256(compact_path)
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
            "full_file_sha256": full_sha,
            "full_git_blob": git_blob_id(ROOT, commit, full_rel) if full_path.is_file() else None,
            "full_git_blob_content_sha256": git_blob_sha256(ROOT, commit, full_rel)
            if full_path.is_file()
            else None,
            "compact_result_hash": compact.compact_result_hash,
            "compact_file_sha256": compact_sha,
            "duty_w": str(rating.total_duty_w),
            "tube_dp_pa": str(
                frozen.request.task174_result.modeled_total_tube_side_pressure_drop_pa
            ),
            "shell_dp_pa": str(frozen.request.task174_result.bell_total_shell_pressure_drop_pa),
            "experimental_sizing_adapter_status": adapter.status,
        }
    )
    _write_receipt(receipt, evidence_dir, wall_t0)


def _fill_partial_outcome(
    receipt: dict[str, Any],
    outcome: Any,
) -> None:
    n64 = next((s for s in outcome.mesh_stages if int(s.get("mesh_n", 0)) == 64), None)
    if n64:
        receipt.update(
            {
                "n64_worker_status": n64.get("worker_status"),
                "n64_worker_seconds": n64.get("worker_wall_seconds"),
                "n64_outer_iterations": n64.get("outer_iterations_for_rehydrate"),
                "n64_terminal_residual_k": n64.get("terminal_boundary_residual_k"),
                "n64_terminal_residual_j_kg": n64.get("terminal_enthalpy_residual_j_kg"),
                "n64_cell_closure": n64.get("cell_closure_pass"),
                "n64_energy_balance": n64.get("energy_balance_pass"),
                "n64_mesh_result_hash": n64.get("mesh_result_hash"),
            }
        )
    live_comparisons = list(outcome.mesh_comparisons)
    c_32_64 = _find_comparison(tuple(live_comparisons), 32, 64)
    receipt["n32_to_64_comparison"] = c_32_64.get("overall_status") if c_32_64 else "NOT_RUN"
    c_8_16 = _find_comparison(tuple(live_comparisons), 8, 16)
    c_16_32 = _find_comparison(tuple(live_comparisons), 16, 32)
    receipt["n8_to_n16_comparison"] = c_8_16.get("overall_status") if c_8_16 else "NOT_RUN"
    receipt["n16_to_32_comparison"] = c_16_32.get("overall_status") if c_16_32 else "NOT_RUN"
    if n64 and n64.get("worker_status") == "TERMINAL_ACCEPTED":
        frozen = scsa.admit_frozen_second_candidate_snapshot(ROOT)
        run = scsa.replay_admitted_prior_mesh(frozen.request, n64, mesh_n=64)
        scsa.verify_replay_physics(run)
        receipt["n64_mesh_replay"] = run.mesh_result_hash == n64.get("mesh_result_hash")
    else:
        receipt["n64_mesh_replay"] = False


def _write_receipt(receipt: dict[str, Any], out_dir: Path | None, wall_t0: float) -> None:
    receipt["wall_seconds"] = time.perf_counter() - wall_t0
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    default = (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-general-candidate-continuation-r21e-{stamp}"
    )
    directory = out_dir or default
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"V07-FAST-SOLVER-general-candidate-continuation-r21e-{stamp}.json"
    payload = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    print("RAW_RESULT_PATH", path)
    print("RAW_RESULT_SHA256", hashlib.sha256(payload.encode()).hexdigest())


if __name__ == "__main__":
    main()

"""Immutable R17 result amendment reconciliation (R18 preflight)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_ladder_continuation_r14.bounded_workers import (
    run_bounded_compare,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    R17_ORCHESTRATOR_PATH,
    R17_RESULT_COMMIT,
    R17_RESULT_PATH,
    R17_RESULT_SHA256,
    R17_RESULT_SHA256_ORIGINAL,
    comparison_canonical_sha256,
)

RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"
INDEX_PATH_REL = "docs/HXFORGE_RESULT_INDEX.jsonl"
R17_ORIGINAL_RESULT_COMMIT = "52ab519e7cb6819f8df9779578cfc2d48da9b789"
R17_TRIAL_COUNTS = {
    "bracket_establishment_trial_count": 2,
    "narrow_solve_trial_count": 5,
    "total_physical_trial_count": 7,
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_index_lines(root: Path) -> list[dict[str, Any]]:
    path = root / INDEX_PATH_REL
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            lines.append(json.loads(line))
    return lines


def verify_index_original_r17_row(root: Path) -> None:
    rows = _load_index_lines(root)
    matches = [
        r
        for r in rows
        if r.get("task_id") == "V07_FAST_SOLVER_LIVE_N32_CANDIDATE_R17"
        and r.get("raw_result_sha256") == R17_RESULT_SHA256_ORIGINAL
    ]
    if not matches:
        raise ValueError("R17 original index row missing")


def independent_n16_n32_compare(root: Path, *, budget_s: float = 200.0) -> dict[str, Any]:
    orch = json.loads((root / R17_ORCHESTRATOR_PATH).read_text(encoding="utf-8"))
    stages = {int(s["mesh_n"]): s for s in orch["mesh_stages"]}
    snap = root / orch["request_snapshot_rel_path"]
    n16, n32 = stages[16], stages[32]
    worker = run_bounded_compare(
        snap,
        coarse={
            "mesh_n": 16,
            "shooting_enthalpy_j_kg": n16["shooting_enthalpy_for_rehydrate"],
            "outer_iterations": int(n16.get("outer_iterations_for_rehydrate", 0)),
            "expected_mesh_hash": n16.get("mesh_result_hash"),
            "terminal_tolerance_pass": True,
            "cell_closure_pass": True,
            "energy_balance_pass": True,
        },
        fine={
            "mesh_n": 32,
            "shooting_enthalpy_j_kg": n32["shooting_enthalpy_for_rehydrate"],
            "outer_iterations": int(n32.get("outer_iterations_for_rehydrate", 0)),
            "expected_mesh_hash": n32.get("mesh_result_hash"),
            "terminal_tolerance_pass": True,
            "cell_closure_pass": True,
            "energy_balance_pass": True,
        },
        expected_request_hash=RATING_REQUEST_HASH,
        expected_candidate_id=CANDIDATE_B_ID,
        budget_s=budget_s,
    )
    return worker


def build_amendment_manifest(
    root: Path,
    *,
    compare_worker: dict[str, Any],
    reconciled_result_sha256: str,
) -> dict[str, Any]:
    comparison = compare_worker.get("comparison") or {}
    return {
        "task_id": "V07_FAST_SOLVER_LIVE_N32_CANDIDATE_R17",
        "amendment_kind": "N16_N32_COMPARE_AND_TRIAL_COUNT",
        "original_result_sha256": R17_RESULT_SHA256_ORIGINAL,
        "original_result_commit": R17_ORIGINAL_RESULT_COMMIT,
        "revised_result_sha256": reconciled_result_sha256,
        "revised_result_commit": R17_RESULT_COMMIT,
        "revised_result_rel_path": R17_RESULT_PATH,
        "n16_n32_comparison_canonical_sha256": comparison_canonical_sha256(comparison),
        "independent_compare_status": compare_worker.get("status"),
        "independent_compare_overall_status": comparison.get("overall_status"),
        "code_head_sha_at_reconcile": R17_RESULT_COMMIT,
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "trial_counts": R17_TRIAL_COUNTS,
    }


def reconcile_r17_evidence(root: Path, *, compare_budget_s: float = 200.0) -> dict[str, Any]:
    verify_index_original_r17_row(root)
    if file_sha256(root / R17_RESULT_PATH) != R17_RESULT_SHA256:
        raise ValueError("R17 revised result SHA256 mismatch before reconcile")
    compare_worker = independent_n16_n32_compare(root, budget_s=compare_budget_s)
    if compare_worker.get("status") != "OK":
        raise ValueError(f"R17 independent n16→32 compare failed: {compare_worker}")
    comparison = compare_worker["comparison"]
    pinned = json.loads((root / R17_RESULT_PATH).read_text())["n16_n32_comparison"]
    if comparison_canonical_sha256(pinned) != comparison_canonical_sha256(comparison):
        raise ValueError("R17 pinned vs independent n16→32 comparison mismatch")
    reconciled_sha = file_sha256(root / R17_RESULT_PATH)
    if reconciled_sha != R17_RESULT_SHA256:
        raise ValueError("R17 revised result SHA256 mismatch")
    manifest = build_amendment_manifest(
        root,
        compare_worker=compare_worker,
        reconciled_result_sha256=reconciled_sha,
    )
    stamp = manifest["recorded_at_utc"].replace(":", "")
    manifest_path = (
        root / "docs/tasks/evidence" / f"V07-FAST-SOLVER-live-n32-candidate-r17-amendment-{stamp}.json"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest["manifest_rel_path"] = str(manifest_path.relative_to(root))
    manifest["manifest_sha256"] = file_sha256(manifest_path)
    return manifest

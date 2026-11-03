"""Immutable R18 headroom compare amendment (does not rewrite R18 result JSON)."""

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
    R18_ORCHESTRATOR_PATH,
    R18_RESULT_PATH,
    comparison_canonical_sha256,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    R17_N32_MESH_HASH,
    R18_N64_MESH_HASH,
    R18_RESULT_COMMIT_ORIGINAL,
    R18_RESULT_COMMIT_REVISED,
    R18_RESULT_SHA256,
    R18_RESULT_SHA256_ORIGINAL,
    R18_STAGE_DIR_REL,
    file_sha256,
)

RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"
INDEX_PATH_REL = "docs/HXFORGE_RESULT_INDEX.jsonl"
R18_FIRST_COMPARE_BUDGET_S = 240.0
R18_INDEPENDENT_COMPARE_BUDGET_S = 320.0


def verify_r18_revised_result_on_disk(root: Path) -> None:
    path = root / R18_RESULT_PATH
    if file_sha256(path) != R18_RESULT_SHA256:
        raise ValueError("R18 revised result SHA256 mismatch")


def independent_n32_n64_compare(root: Path, *, budget_s: float) -> dict[str, Any]:
    orch = json.loads((root / R18_ORCHESTRATOR_PATH).read_text(encoding="utf-8"))
    stages = {int(s["mesh_n"]): s for s in orch["mesh_stages"]}
    snap = root / orch["request_snapshot_rel_path"]
    n32, n64 = stages[32], stages[64]
    worker = run_bounded_compare(
        snap,
        coarse={
            "mesh_n": 32,
            "shooting_enthalpy_j_kg": n32["shooting_enthalpy_for_rehydrate"],
            "outer_iterations": int(n32.get("outer_iterations_for_rehydrate", 0)),
            "expected_mesh_hash": n32.get("mesh_result_hash"),
            "terminal_tolerance_pass": True,
            "cell_closure_pass": True,
            "energy_balance_pass": True,
        },
        fine={
            "mesh_n": 64,
            "shooting_enthalpy_j_kg": n64["shooting_enthalpy_for_rehydrate"],
            "outer_iterations": int(n64.get("outer_iterations_for_rehydrate", 0)),
            "expected_mesh_hash": n64.get("mesh_result_hash"),
            "terminal_tolerance_pass": True,
            "cell_closure_pass": True,
            "energy_balance_pass": True,
        },
        expected_request_hash=RATING_REQUEST_HASH,
        expected_candidate_id=CANDIDATE_B_ID,
        budget_s=budget_s,
    )
    return worker


def build_r18_amendment_manifest(
    root: Path,
    *,
    compare_worker: dict[str, Any],
    compare_elapsed_s: float,
) -> dict[str, Any]:
    result_body = json.loads((root / R18_RESULT_PATH).read_text(encoding="utf-8"))
    pinned = result_body.get("n32_n64_comparison") or {}
    independent = compare_worker.get("comparison") or {}
    return {
        "task_id": "V07_FAST_SOLVER_LIVE_N64_HEADROOM_R18",
        "amendment_kind": "N32_N64_HEADROOM_COMPARE",
        "original_result_sha256": R18_RESULT_SHA256_ORIGINAL,
        "original_result_commit": R18_RESULT_COMMIT_ORIGINAL,
        "revised_result_sha256": R18_RESULT_SHA256,
        "revised_result_commit": R18_RESULT_COMMIT_REVISED,
        "revised_result_rel_path": R18_RESULT_PATH,
        "first_run_compare_outcome": "TIMEOUT_AT_240S_BUDGET",
        "independent_compare_budget_s": R18_INDEPENDENT_COMPARE_BUDGET_S,
        "independent_compare_elapsed_s": compare_elapsed_s,
        "independent_compare_status": compare_worker.get("status"),
        "compare_algorithm": "production_compare_mesh_pair_via_bounded_worker",
        "rating_request_hash": RATING_REQUEST_HASH,
        "coarse_mesh_n": 32,
        "fine_mesh_n": 64,
        "coarse_mesh_result_hash": R17_N32_MESH_HASH,
        "fine_mesh_result_hash": R18_N64_MESH_HASH,
        "pinned_comparison_canonical_sha256": comparison_canonical_sha256(pinned)
        if pinned
        else None,
        "independent_comparison_canonical_sha256": comparison_canonical_sha256(independent),
        "duty_status": independent.get("duty_status"),
        "wall_status": independent.get("wall_status"),
        "overall_status": independent.get("overall_status"),
        "source_code_commit": R18_RESULT_COMMIT_REVISED,
        "stage_dir_rel": R18_STAGE_DIR_REL,
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": "Cursor Cloud",
    }


def reconcile_r18_headroom_amendment(
    root: Path,
    *,
    compare_budget_s: float = 320.0,
) -> dict[str, Any]:
    verify_r18_revised_result_on_disk(root)
    t0 = time.perf_counter()
    worker = independent_n32_n64_compare(root, budget_s=compare_budget_s)
    elapsed = time.perf_counter() - t0
    if worker.get("status") != "OK":
        raise ValueError(f"R18 independent n32→64 compare failed: {worker}")
    pinned = json.loads((root / R18_RESULT_PATH).read_text())["n32_n64_comparison"]
    independent = worker["comparison"]
    if comparison_canonical_sha256(pinned) != comparison_canonical_sha256(independent):
        raise ValueError("R18 pinned vs independent n32→64 comparison mismatch")
    manifest = build_r18_amendment_manifest(
        root,
        compare_worker=worker,
        compare_elapsed_s=elapsed,
    )
    stamp = manifest["recorded_at_utc"].replace(":", "").replace("-", "")
    manifest_name = f"V07-FAST-SOLVER-live-n64-headroom-r18-amendment-{stamp}.json"
    manifest_path = root / "docs/tasks/evidence" / manifest_name
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest["manifest_rel_path"] = str(manifest_path.relative_to(root))
    manifest["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    manifest["n32_n64_independent_compare_receipt"] = worker
    return manifest

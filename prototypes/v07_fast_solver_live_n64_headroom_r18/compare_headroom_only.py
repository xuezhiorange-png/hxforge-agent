#!/usr/bin/env python3
"""Spawn-safe n32→64 bounded compare helper."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_ladder_continuation_r14.bounded_workers import (
    run_bounded_compare,
)

RATING_REQUEST_HASH = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"


def main() -> None:
    orch_path = Path(sys.argv[1])
    budget_s = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    orch = json.loads(orch_path.read_text(encoding="utf-8"))
    stages = {int(s["mesh_n"]): s for s in orch["mesh_stages"]}
    snap = ROOT / orch["request_snapshot_rel_path"]
    n32, n64 = stages[32], stages[64]
    t0 = time.perf_counter()
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
    print(json.dumps({"elapsed_s": time.perf_counter() - t0, **worker}, indent=2))


if __name__ == "__main__":
    main()

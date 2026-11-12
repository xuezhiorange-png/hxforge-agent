"""Replay and export the rating-fatal Task173 cell for candidate e1baa795."""
# ruff: noqa: E402

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from prototypes.v08_thermal_rating.fatal_cell_identity import load_fatal_cell_identity

CANDIDATE_ID = "e1baa795-9cf5-5718-8fa8-0688d2102c5c"
EVIDENCE = Path(f"/opt/cursor/artifacts/v08_03_blocked_cell_evidence_{CANDIDATE_ID}.json")


def _sign_pairs(valid: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = sorted(
        [r for r in valid if r.get("f_q_w") is not None],
        key=lambda r: float(r["q_trial_w"]),
    )
    pairs: list[dict[str, str]] = []
    for left, right in zip(rows, rows[1:], strict=False):
        fl, fr = Decimal(left["f_q_w"]), Decimal(right["f_q_w"])
        if fl <= 0 <= fr:
            pairs.append(
                {
                    "left_q_w": left["q_trial_w"],
                    "right_q_w": right["q_trial_w"],
                    "left_f_q_w": str(fl),
                    "right_f_q_w": str(fr),
                }
            )
    return pairs


def main() -> int:
    if not EVIDENCE.is_file():
        raise SystemExit(f"missing evidence: {EVIDENCE}")
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    fatal = load_fatal_cell_identity(payload)
    stats = payload.get("task173_cell_search_stats") or {}
    oi = int(fatal["outer_iteration"])
    sid = fatal["physical_support_id"]
    mesh = int(fatal["mesh_subdivisions"])
    trials = [
        r
        for r in stats.get("trial_receipts") or []
        if r["outer_iteration"] == oi
        and r["physical_support_id"] == sid
        and int(r.get("mesh_subdivisions", mesh)) == mesh
    ]
    levels = [
        r
        for r in stats.get("endpoint_hole_level_receipts") or []
        if r["outer_iteration"] == oi
        and r["physical_support_id"] == sid
        and int(r.get("mesh_subdivisions", mesh)) == mesh
    ]
    valid = [t for t in trials if t["classification"] == "VALID_CELL_EVALUATION"]
    valid_fatal = [t for t in valid if int(t.get("outer_iteration", oi)) == oi]
    holes = [t for t in trials if t["classification"] == "TASK172_NUMERICAL_HOLE"]
    out: dict[str, Any] = {
        "task_id": "V08_03_FIRST_FAILED_CELL_REPLAY",
        "candidate_id": CANDIDATE_ID,
        "geometry_projection_hash": payload.get("geometry_projection_hash"),
        "fatal_cell_identity": fatal,
        "outer_iteration": oi,
        "mesh_subdivisions": mesh,
        "outer_shooting_enthalpy_j_kg": fatal.get("outer_shooting_enthalpy_j_kg"),
        "physical_support_id": sid,
        "tube_cell_id": fatal.get("tube_cell_id"),
        "shell_cell_id": fatal.get("shell_cell_id"),
        "wall_interface_id": fatal.get("wall_interface_id"),
        "physical_q_interval": {
            "lower_q_w": fatal.get("physical_lower_q_w"),
            "upper_q_w": fatal.get("physical_upper_q_w"),
            "basis": "thermodynamic_cap_min(tube_capacity, shell_capacity) with enthalpy floor",
        },
        "hole_endpoint_side": fatal.get("hole_endpoint_side"),
        "initial_valid_anchor": {
            "q_w": fatal.get("initial_valid_anchor_q_w"),
            "f_q_w": fatal.get("initial_valid_anchor_f_q_w"),
        },
        "valid_f_q_points": [
            {
                "q_trial_w": t["q_trial_w"],
                "f_q_w": t["f_q_w"],
                "task172_request_hash": t.get("task172_request_hash"),
                "task172_result_hash": t.get("task172_result_hash"),
                "search_phase": t.get("search_phase"),
            }
            for t in sorted(valid, key=lambda x: float(x["q_trial_w"]))
        ],
        "numerical_holes": [
            {
                "q_trial_w": t["q_trial_w"],
                "failure_code": t.get("failure_code"),
                "task172_request_hash": t.get("task172_request_hash"),
                "blocked_result_hash": t.get("blocked_result_hash"),
            }
            for t in sorted(holes, key=lambda x: float(x["q_trial_w"]))
        ],
        "endpoint_hole_recovery_levels": levels,
        "valid_sign_bracket_exists_fatal_outer": bool(_sign_pairs(valid_fatal)),
        "valid_sign_brackets_observed_fatal_outer": _sign_pairs(valid_fatal),
        "valid_sign_bracket_exists_all_trials_at_mesh": bool(_sign_pairs(valid)),
        "valid_sign_brackets_observed_all_trials_at_mesh": _sign_pairs(valid),
        "task173_root_failure_code": payload.get("task173_failure_code"),
        "termination_failure_code": fatal.get("termination_failure_code"),
    }
    out_path = Path(f"/opt/cursor/artifacts/v08_03_first_failed_cell_replay_{CANDIDATE_ID}.json")
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

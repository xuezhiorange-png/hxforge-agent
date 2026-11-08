"""Select rating-fatal Task173 cell identity from blocked-cell evidence export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _parse_scalar_diagnostics(diagnostics: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in diagnostics:
        if "=" not in item or item.startswith("task173_cell_search_stats_json="):
            continue
        key, value = item.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def select_fatal_cell_from_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the cell context that terminated rating (not merely max outer endpoint summary)."""
    stats = payload.get("task173_cell_search_stats") or {}
    failed_mesh = payload.get("task173_failed_mesh_subdivisions")
    failure_code = payload.get("task173_failure_code")
    scalar_diag = _parse_scalar_diagnostics(list(payload.get("task173_diagnostics") or []))
    mesh_from_diag = scalar_diag.get("mesh_subdivisions")
    target_mesh = failed_mesh
    if target_mesh is None and mesh_from_diag is not None:
        target_mesh = int(mesh_from_diag)

    summaries = list(stats.get("endpoint_hole_summaries") or [])
    candidates = summaries
    if target_mesh is not None:
        candidates = [
            s
            for s in summaries
            if int(s.get("mesh_subdivisions", -1)) == int(target_mesh)
        ]
    if not candidates and summaries:
        candidates = summaries

    if not candidates:
        raise ValueError("no endpoint_hole_summaries for fatal selection")

    fatal = max(candidates, key=lambda s: (int(s["outer_iteration"]), int(s["mesh_subdivisions"])))
    return {
        "task_id": "V08_03_FATAL_CELL_IDENTITY",
        "candidate_id": payload.get("candidate_id"),
        "geometry_projection_hash": payload.get("geometry_projection_hash"),
        "candidate_hash": payload.get("candidate_hash"),
        "candidate_rating_request_hash": payload.get("candidate_rating_request_hash"),
        "termination_failure_code": failure_code,
        "failed_mesh_subdivisions": failed_mesh,
        "termination_scalar_diagnostics": scalar_diag,
        "mesh_subdivisions": int(fatal["mesh_subdivisions"]),
        "outer_iteration": int(fatal["outer_iteration"]),
        "outer_shooting_enthalpy_j_kg": fatal.get("shooting_enthalpy_j_kg"),
        "physical_support_id": fatal.get("physical_support_id"),
        "tube_cell_id": fatal.get("tube_cell_id"),
        "shell_cell_id": fatal.get("shell_cell_id"),
        "wall_interface_id": fatal.get("wall_interface_id"),
        "physical_lower_q_w": fatal.get("physical_lower_q_w"),
        "physical_upper_q_w": fatal.get("physical_upper_q_w"),
        "hole_endpoint_side": fatal.get("hole_endpoint_side"),
        "initial_valid_anchor_q_w": fatal.get("initial_valid_anchor_q_w"),
        "initial_valid_anchor_f_q_w": fatal.get("initial_valid_anchor_f_q_w"),
    }


def load_fatal_cell_identity(evidence: Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(evidence, dict):
        payload = evidence
    else:
        payload = json.loads(evidence.read_text(encoding="utf-8"))
    return select_fatal_cell_from_evidence(payload)

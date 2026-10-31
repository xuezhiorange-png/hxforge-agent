"""Serialize hxforge.low-mesh-result.v1 documents from workflow rows."""

from __future__ import annotations

from typing import Any


def solver_status_from_row(row: dict[str, Any]) -> str | None:
    """Return the Task173 mesh solver status string (NUMERIC_VALID, BLOCKED, ...)."""
    if row.get("status") is not None:
        return str(row["status"])
    if row.get("mesh_status") is not None:
        return str(row["mesh_status"])
    return None


def low_mesh_result_document(row: dict[str, Any], *, mesh_level: int = 1) -> dict[str, Any]:
    status = solver_status_from_row(row)
    if status is None:
        raise ValueError("row missing status/mesh_status for low-mesh-result")
    doc: dict[str, Any] = {
        "schema_version": "hxforge.low-mesh-result.v1",
        "status": status,
        "mesh_status": status,
        "mesh_level": mesh_level,
        "mesh_result_hash": row.get("mesh_result_hash"),
        "total_duty_w": row.get("total_duty_w"),
        "energy_balance_residual_w": row.get("energy_balance_residual_w"),
        "terminal_boundary_residual_k": row.get("terminal_boundary_residual_k"),
        "task172_local_evaluation_count": row.get("task172_local_evaluation_count"),
        "wall_seconds": row.get("wall_seconds"),
        "failure_code": row.get("failure_code"),
        "tube_outlet_temperature_k": row.get("tube_outlet_temperature_k"),
        "shell_outlet_temperature_k": row.get("shell_outlet_temperature_k"),
        "low_mesh_numeric_valid": status == "NUMERIC_VALID",
        "full_rating_converged": False,
    }
    return {k: v for k, v in doc.items() if v is not None}

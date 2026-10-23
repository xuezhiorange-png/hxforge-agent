"""Live multi-mesh rating ladder for a single real candidate (R16)."""

# ruff: noqa: E501

from __future__ import annotations

import time
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_constraint_preview import (
    build_experimental_constraint_preview,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    postpass_from_mesh_row,
)
from prototypes.v07_general_rating_sizing_mvp.mesh_comparison import compare_mesh_observables_duty
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    NativeCellContext,
    run_mesh_numeric_with_profile,
)

# R13 evidence id (historical); current Task168 hash for same 0.56 m / 3.0 m / 0.6 m geometry
# may differ without changing physical rating envelope.
R13_EVIDENCE_PINNED_CANDIDATE_ID = "a409a550-4d1d-5b71-b3f5-0f1b665e2fe5"
PINNED_R16_CANDIDATE_ID = "39681fe8-bbde-5e5e-97ac-5341c239a776"


def mesh_level_public_row(
    *,
    mesh_level: int,
    mesh: dict[str, Any],
    profile: dict[str, Any],
    obs: Any | None,
) -> dict[str, Any]:
    status = mesh.get("status") or mesh.get("mesh_status")
    row: dict[str, Any] = {
        "schema_version": "hxforge.live-mesh-level-result.v1",
        "mesh_level": mesh_level,
        "mesh_status": status,
        "status": status,
        "mesh_result_hash": mesh.get("mesh_result_hash"),
        "total_duty_w": mesh.get("total_duty_w"),
        "energy_balance_residual_w": mesh.get("energy_balance_residual_w"),
        "terminal_boundary_residual_k": mesh.get("terminal_boundary_residual_k"),
        "task172_local_evaluation_count": mesh.get("task172_local_evaluation_count"),
        "wall_seconds": mesh.get("wall_seconds"),
        "failure_code": mesh.get("failure_code"),
        "solver_performance_profile": profile,
        "property_provider_state_lookup_count": profile.get("property_provider_state_lookup_count"),
    }
    if obs is not None:
        row["tube_outlet_temperature_k"] = str(obs.tube_outlet_temperature_k)
        row["shell_outlet_temperature_k"] = str(obs.shell_outlet_temperature_k)
    return row


def run_mesh_levels_for_candidate(
    case: EngineeringCase,
    native: NativeCellContext,
    *,
    mesh_levels: Sequence[int],
    budget_s: float,
    t0: float | None = None,
    enable_ephemeral_tp_cache: bool = False,
) -> tuple[list[dict[str, Any]], dict[int, Any]]:
    if t0 is None:
        t0 = time.perf_counter()
    rows: list[dict[str, Any]] = []
    observations: dict[int, Any] = {}
    for level in mesh_levels:
        if time.perf_counter() - t0 >= budget_s:
            rows.append(
                {
                    "schema_version": "hxforge.live-mesh-level-result.v1",
                    "mesh_level": level,
                    "mesh_status": "BUDGET_STOP",
                    "status": "BUDGET_STOP",
                    "failure_code": "NUMERICAL_BUDGET_EXCEEDED",
                }
            )
            break
        mesh, profile, obs = run_mesh_numeric_with_profile(
            native,
            subdivisions=level,
            case=case,
            enable_live_thermal_boundary=True,
            enable_ephemeral_tp_cache=enable_ephemeral_tp_cache,
        )
        row = mesh_level_public_row(mesh_level=level, mesh=mesh, profile=profile, obs=obs)
        if mesh.get("status") == "NUMERIC_VALID" and obs is not None:
            row["tube_outlet_temperature_k"] = str(obs.tube_outlet_temperature_k)
            row["shell_outlet_temperature_k"] = str(obs.shell_outlet_temperature_k)
            observations[level] = obs
        rows.append(row)
    return rows, observations


def _level_by_mesh(rows: list[dict[str, Any]], level: int) -> dict[str, Any] | None:
    for row in rows:
        if int(row.get("mesh_level", -1)) == level:
            return row
    return None


def highest_numeric_valid_mesh_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [
        row
        for row in rows
        if row.get("mesh_status") == "NUMERIC_VALID" or row.get("status") == "NUMERIC_VALID"
    ]
    if not valid:
        return None
    return max(valid, key=lambda row: int(row["mesh_level"]))


def build_live_multi_mesh_analysis(
    *,
    candidate_id: str,
    rating_request_hash: str,
    mesh_level_rows: list[dict[str, Any]],
    coarse_obs: Any | None,
    fine_obs: Any | None,
) -> dict[str, Any]:
    n1 = _level_by_mesh(mesh_level_rows, 1)
    n2 = _level_by_mesh(mesh_level_rows, 2)
    n4 = _level_by_mesh(mesh_level_rows, 4)

    n1_ok = n1 is not None and n1.get("mesh_status") == "NUMERIC_VALID"
    n2_ok = n2 is not None and n2.get("mesh_status") == "NUMERIC_VALID"

    comparison: dict[str, Any] | None = None
    if n1_ok and n2_ok and coarse_obs is not None and fine_obs is not None:
        comparison = compare_mesh_observables_duty(
            Decimal(str(n1["total_duty_w"])),
            Decimal(str(n1["terminal_boundary_residual_k"])),
            fine_obs,
            coarse_mesh_hash=str(n1.get("mesh_result_hash")),
            fine_mesh_hash=str(n2.get("mesh_result_hash")),
            coarse_level=1,
            fine_level=2,
            comparable=True,
        )
        comparison["tube_outlet_temperature_delta_k"] = str(
            abs(
                Decimal(str(fine_obs.tube_outlet_temperature_k))
                - Decimal(str(coarse_obs.tube_outlet_temperature_k))
            )
        )
        comparison["shell_outlet_temperature_delta_k"] = str(
            abs(
                Decimal(str(fine_obs.shell_outlet_temperature_k))
                - Decimal(str(coarse_obs.shell_outlet_temperature_k))
            )
        )
        if n1.get("task172_local_evaluation_count") is not None and n2.get(
            "task172_local_evaluation_count"
        ):
            comparison["task172_evaluation_count_ratio_n2_over_n1"] = str(
                Decimal(str(n2["task172_local_evaluation_count"]))
                / Decimal(str(n1["task172_local_evaluation_count"]))
            )
        if n1.get("wall_seconds") and n2.get("wall_seconds"):
            comparison["wall_seconds_ratio_n2_over_n1"] = str(
                Decimal(str(n2["wall_seconds"])) / Decimal(str(n1["wall_seconds"]))
            )

    mesh_convergence_status = "NOT_EVALUATED"
    if n1 is not None and n1.get("mesh_status") == "BLOCKED":
        mesh_convergence_status = "NUMERICAL_BLOCKED"
    elif any(row.get("mesh_status") == "BUDGET_STOP" for row in mesh_level_rows):
        mesh_convergence_status = "BUDGET_STOP"
    elif n1_ok and n2_ok and comparison is not None:
        mesh_convergence_status = "MESH_COMPARISON_AVAILABLE"
    elif n1_ok and n2 is not None and n2.get("mesh_status") != "NUMERIC_VALID":
        mesh_convergence_status = "NUMERICAL_BLOCKED"
    elif n1_ok:
        mesh_convergence_status = "MESH_CONVERGENCE_NOT_ESTABLISHED"

    highest = highest_numeric_valid_mesh_row(mesh_level_rows)
    highest_level = int(highest["mesh_level"]) if highest else None

    return {
        "schema_version": "hxforge.live-multi-mesh-analysis.v1",
        "candidate_id": candidate_id,
        "rating_request_hash": rating_request_hash,
        "REAL_N1_RATING_STATUS": n1.get("mesh_status") if n1 else "NOT_EVALUATED",
        "REAL_N2_RATING_STATUS": n2.get("mesh_status") if n2 else "NOT_EVALUATED",
        "REAL_N4_RATING_STATUS": n4.get("mesh_status") if n4 else "NOT_EVALUATED",
        "MESH_CONVERGENCE_STATUS": mesh_convergence_status,
        "MESH_COMPARISON_AVAILABLE": mesh_convergence_status == "MESH_COMPARISON_AVAILABLE",
        "HIGHEST_VALID_MESH_LEVEL": highest_level,
        "mesh_level_results": mesh_level_rows,
        "n1_n2_comparison": comparison,
        "full_rating_converged": False,
        "production_sizing_verified": False,
        "disclosure": (
            "Experimental live mesh ladder only; MESH_COMPARISON_AVAILABLE does not imply "
            "production rating convergence or sizing authority."
        ),
    }


def attach_live_hydraulic_postpass_for_mesh(
    case: EngineeringCase,
    native: NativeCellContext,
    mesh_row: dict[str, Any],
    *,
    candidate_id: str,
) -> dict[str, Any] | None:
    mesh = {
        "status": mesh_row.get("mesh_status"),
        "tube_outlet_temperature_k": mesh_row.get("tube_outlet_temperature_k"),
        "shell_outlet_temperature_k": mesh_row.get("shell_outlet_temperature_k"),
        "total_duty_w": mesh_row.get("total_duty_w"),
    }
    preview = build_experimental_constraint_preview(case, mesh=mesh, native=native)
    return postpass_from_mesh_row(
        case,
        candidate_id=candidate_id,
        mesh=mesh,
        native_reference_tube_dp=preview.get("modeled_tube_dp_pa"),
        native_reference_shell_dp=preview.get("modeled_shell_dp_pa"),
    )


def render_multi_mesh_markdown_table(
    analysis: dict[str, Any],
    *,
    levels: Sequence[int] = (1, 2, 4),
) -> list[str]:
    lines = [
        "## Live multi-mesh rating comparison (experimental)",
        "",
        "| Metric | n=1 | n=2 | n=4 |",
        "| --- | --- | --- | --- |",
    ]
    rows_by_level = {int(row["mesh_level"]): row for row in analysis.get("mesh_level_results", [])}

    def cell(level: int, key: str) -> str:
        row = rows_by_level.get(level)
        if row is None:
            return "NOT_EVALUATED"
        if row.get("mesh_status") not in {"NUMERIC_VALID", None} and key != "mesh_status":
            return str(row.get("mesh_status", "NOT_EVALUATED"))
        val = row.get(key)
        return str(val) if val is not None else "NOT_EVALUATED"

    for label, key in [
        ("Duty (W)", "total_duty_w"),
        ("Tube outlet (K)", "tube_outlet_temperature_k"),
        ("Shell outlet (K)", "shell_outlet_temperature_k"),
        ("Energy balance residual (W)", "energy_balance_residual_w"),
        ("Terminal boundary residual (K)", "terminal_boundary_residual_k"),
        ("Task172 eval count", "task172_local_evaluation_count"),
        ("CoolProp lookups", "property_provider_state_lookup_count"),
        ("Wall seconds", "wall_seconds"),
        ("Mesh status", "mesh_status"),
    ]:
        lines.append(f"| {label} | {cell(1, key)} | {cell(2, key)} | {cell(4, key)} |")
    cmp_doc = analysis.get("n1_n2_comparison") or {}
    lines.extend(
        [
            "",
            f"- Mesh convergence status: **{analysis.get('MESH_CONVERGENCE_STATUS')}**",
            f"- Highest valid mesh level: **{analysis.get('HIGHEST_VALID_MESH_LEVEL')}**",
            f"- n1/n2 duty delta: {cmp_doc.get('duty_delta_w')} W "
            f"({cmp_doc.get('duty_delta_percent')} %)",
            f"- n1/n2 duty comparison: **{cmp_doc.get('duty_comparison_status')}**",
            "- full_rating_converged: **false**",
            "",
        ]
    )
    return lines

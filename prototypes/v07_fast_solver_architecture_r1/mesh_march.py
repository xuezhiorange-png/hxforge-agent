"""Fast mesh march using coupled cells (experimental authority)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime.models import mesh_level_identity
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    H_MIN_J_KG,
    T_MIN_K,
    MeshObservables,
)
from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_architecture_r1.coupled_cell import (
    FAST_CELL_AUTHORITY_ID,
    CoupledCellStats,
    solve_coupled_cell,
)


@dataclass
class FastMeshStats:
    wall_seconds: float = 0.0
    cell_count: int = 0
    coupled_fallback_count: int = 0
    total_eval_trial_calls: int = 0
    total_least_squares_nfev: int = 0
    per_cell: list[CoupledCellStats] = field(default_factory=list)
    authority_id: str = FAST_CELL_AUTHORITY_ID


def fast_valid_trajectory(
    subdivisions: int,
    shell_outlet_enthalpy: Decimal,
    provider: PropertyProvider,
    shell_authority: Any,
    outer_iterations: int = 0,
) -> tuple[Any, FastMeshStats]:
    """Production-equivalent mesh topology with coupled cell closure."""
    t0 = time.perf_counter()
    mesh_stats = FastMeshStats()
    candidate_context = t173._CANDIDATE_RATING_CONTEXT.get()
    hole_neighborhoods: list[dict[str, str]] = []
    mesh_id = (
        t173._candidate_mesh_identity(candidate_context, subdivisions)
        if candidate_context is not None
        else mesh_level_identity(subdivisions)
    )
    interval_count = candidate_context.interval_count if candidate_context is not None else 5
    face_count = interval_count * subdivisions
    if candidate_context is not None:
        topology_definition = candidate_context.request.task171_result.topology_definition
        if topology_definition is None:
            raise t173._Stage3Failure("BLOCKED_CANDIDATE_TASK171_BINDING")
        first_coordinate = Decimal(topology_definition.intervals[0].start_m)
    else:
        first_coordinate = Decimal("0")
    tube_face_thermo = t173._state_at_inlet(provider, t173.TUBE_INLET_T_K)
    shell_face_thermo = t173._state_from_enthalpy(provider, shell_outlet_enthalpy)
    tube_faces: list[t173.FaceState] = [
        t173._face_state(
            tube_face_thermo,
            side="TUBE",
            face_index=0,
            coordinate_m=first_coordinate,
            face_count=face_count,
            producer_authority_id="V07-T173-CASE-BOUNDARY-STATE-PROVIDER-R1",
        )
    ]
    shell_faces: list[t173.FaceState] = [
        t173._face_state(
            shell_face_thermo,
            side="SHELL",
            face_index=0,
            coordinate_m=first_coordinate,
            face_count=face_count,
            producer_authority_id=t173.OUTER_BOUNDARY_SOLVER_AUTHORITY_ID,
        )
    ]
    cells: list[t173._CellRecord] = []
    interval_duties: list[Decimal] = []
    for interval_index in range(interval_count):
        interval_duty = Decimal(0)
        for subdivision_index in range(subdivisions):
            support = (
                t173._build_candidate_local_support(
                    candidate_context, interval_index, subdivisions, subdivision_index
                )
                if candidate_context is not None
                else t173.build_local_support(interval_index, subdivisions, subdivision_index)
            )
            cell_stat = CoupledCellStats()
            solution = solve_coupled_cell(
                support=support,
                tube_upstream=tube_face_thermo,
                shell_physical_left=shell_face_thermo,
                provider=provider,
                shell_authority=shell_authority,
                stats=cell_stat,
            )
            mesh_stats.per_cell.append(cell_stat)
            mesh_stats.cell_count += 1
            if cell_stat.fallback_to_production_cell_root:
                mesh_stats.coupled_fallback_count += 1
            mesh_stats.total_eval_trial_calls += cell_stat.eval_trial_calls
            mesh_stats.total_least_squares_nfev += cell_stat.least_squares_nfev
            coordinate = support.support_end_m
            face_index = len(tube_faces)
            tube_right = t173._face_state(
                solution.tube_downstream,
                side="TUBE",
                face_index=face_index,
                coordinate_m=coordinate,
                face_count=face_count,
                producer_authority_id="V07-T173-FACE-ENTHALPY-PROPAGATION-R1",
            )
            shell_right = t173._face_state(
                solution.shell_next_physical,
                side="SHELL",
                face_index=face_index,
                coordinate_m=coordinate,
                face_count=face_count,
                producer_authority_id="V07-T173-FACE-ENTHALPY-PROPAGATION-R1",
            )
            record = t173._make_rated_cell(
                support=support,
                solution=solution,
                tube_left_face=tube_faces[-1],
                tube_right_face=tube_right,
                shell_left_face=shell_faces[-1],
                shell_right_face=shell_right,
            )
            if record.tube_approach_k < 0 or record.shell_approach_k < 0:
                raise t173._Stage3Failure(
                    "BLOCKED_HOT_COLD_TEMPERATURE_CROSSING",
                    support.tube_cell_id,
                )
            cells.append(record)
            interval_duty += solution.q_w
            tube_face_thermo = solution.tube_downstream
            shell_face_thermo = solution.shell_next_physical
            tube_faces.append(tube_right)
            shell_faces.append(shell_right)
        interval_duties.append(interval_duty)

    interval_count = candidate_context.interval_count if candidate_context is not None else 5
    if (
        len(cells) != interval_count * subdivisions
        or len(tube_faces) != interval_count * subdivisions + 1
    ):
        raise t173._Stage3Failure("BLOCKED_MESH_SUPPORT_CARDINALITY")
    if len(shell_faces) != len(tube_faces):
        raise t173._Stage3Failure("BLOCKED_MESH_FACE_CARDINALITY")
    for index, (tube_face, shell_face) in enumerate(zip(tube_faces, shell_faces, strict=True)):
        if (
            tube_face.face_index != shell_face.face_index
            or tube_face.physical_coordinate_m != shell_face.physical_coordinate_m
            or tube_face.topology_id != shell_face.topology_id
            or tube_face.case_revision_id != shell_face.case_revision_id
        ):
            raise t173._Stage3Failure("BLOCKED_COMMON_FACE_IDENTITY_MISMATCH", str(index))
        if tube_face.temperature_k < shell_face.temperature_k:
            raise t173._Stage3Failure("BLOCKED_HOT_COLD_TEMPERATURE_CROSSING", str(index))

    q_wall = sum((cell.solution.q_w for cell in cells), Decimal(0))
    hot_loss = t173.TUBE_MASS_FLOW_KG_S * (
        tube_faces[0].enthalpy_j_kg - tube_faces[-1].enthalpy_j_kg
    )
    cold_gain = t173.SHELL_MASS_FLOW_KG_S * (
        shell_faces[0].enthalpy_j_kg - shell_faces[-1].enthalpy_j_kg
    )
    energy_residual = max(
        abs(hot_loss - q_wall),
        abs(cold_gain - q_wall),
        abs(hot_loss - cold_gain),
    )
    total_roundoff_floor = sum(
        (cell.rated_cell.local_duty_roundoff_bound_w for cell in cells), Decimal(0)
    )
    energy_tolerance = max(t173.ENERGY_ACCEPTANCE_FLOOR_W, total_roundoff_floor)
    if energy_residual > energy_tolerance:
        raise t173._Stage3Failure(
            "BLOCKED_WHOLE_EXCHANGER_ENERGY_BALANCE",
            f"residual_w={energy_residual}",
            f"tolerance_w={energy_tolerance}",
        )
    all_walls_inner = tuple(cell.rated_cell.wall_temperature_inner_k for cell in cells)
    all_walls_outer = tuple(cell.rated_cell.wall_temperature_outer_k for cell in cells)
    wall_floor = max(
        (cell.rated_cell.local_wall_temperature_roundoff_bound_k for cell in cells),
        default=Decimal(0),
    )
    duty_floor = total_roundoff_floor
    min_approach = min(
        (face_t.temperature_k - face_s.temperature_k)
        for face_t, face_s in zip(tube_faces, shell_faces, strict=True)
    )
    terminal_residual_h = shell_faces[-1].enthalpy_j_kg - H_MIN_J_KG
    terminal_residual_t = shell_faces[-1].temperature_k - T_MIN_K
    if terminal_residual_h < 0 or terminal_residual_t < 0:
        raise t173._Stage3Failure("BLOCKED_TERMINAL_BOUNDARY_BELOW_PRESCRIBED_STATE")
    if any(
        not value.is_finite()
        for value in (
            q_wall,
            hot_loss,
            cold_gain,
            energy_residual,
            terminal_residual_h,
            terminal_residual_t,
            min_approach,
        )
    ):
        raise t173._Stage3Failure("BLOCKED_NONFINITE_MESH_OBSERVABLE")

    tube_count = interval_count * subdivisions
    shell_count = interval_count * subdivisions
    wall_count = interval_count * subdivisions
    stats = t173._CellSearchStats()
    projection = t173._mesh_rating_projection(
        subdivisions=subdivisions,
        mesh_id=mesh_id,
        shell_outlet_enthalpy=shell_outlet_enthalpy,
        outer_iterations=outer_iterations,
        tube_faces=tube_faces,
        shell_faces=shell_faces,
        cells=cells,
        interval_duties=interval_duties,
        total_duty=q_wall,
        hot_loss=hot_loss,
        cold_gain=cold_gain,
        energy_residual=energy_residual,
        terminal_residual_t=terminal_residual_t,
        terminal_residual_h=terminal_residual_h,
        stats=stats,
        hole_neighborhoods=hole_neighborhoods,
    )
    rating_hash = canonical_sha256(projection)
    observables = MeshObservables(
        subdivisions_per_interval=subdivisions,
        mesh_level_identity=mesh_id,
        tube_cell_count=tube_count,
        shell_cell_count=shell_count,
        total_numerical_cell_count=tube_count + shell_count,
        wall_interface_count=wall_count,
        total_duty_w=q_wall,
        interval_duty_w=tuple(interval_duties),
        tube_outlet_temperature_k=tube_faces[-1].temperature_k,
        shell_outlet_temperature_k=shell_faces[0].temperature_k,
        wall_inner_min_k=min(all_walls_inner),
        wall_inner_max_k=max(all_walls_inner),
        wall_outer_min_k=min(all_walls_outer),
        wall_outer_max_k=max(all_walls_outer),
        minimum_approach_temperature_k=min_approach,
        hot_energy_loss_w=hot_loss,
        cold_energy_gain_w=cold_gain,
        wall_duty_sum_w=q_wall,
        energy_balance_residual_w=energy_residual,
        terminal_boundary_residual_k=terminal_residual_t,
        terminal_boundary_residual_j_kg=terminal_residual_h,
        duty_roundoff_floor_w=duty_floor,
        wall_temperature_roundoff_floor_k=wall_floor,
        task172_local_evaluation_count=stats.task172_local_evaluation_count,
        task172_numerical_hole_count=stats.task172_numerical_hole_count,
        task172_numerical_hole_counts_by_code=dict(stats.task172_numerical_hole_counts_by_code),
        task172_numerical_hole_neighborhoods=tuple(hole_neighborhoods),
        rating_result_hash=rating_hash,
        local_task172_result_hashes=tuple(cell.rated_cell.task172_result_hash for cell in cells),
    )
    mesh_run = t173._MeshRun(
        subdivisions=subdivisions,
        faces_tube=tuple(tube_faces),
        faces_shell=tuple(shell_faces),
        cells=tuple(cells),
        observables=observables,
        mesh_result_hash=rating_hash,
        shooting_enthalpy=shell_outlet_enthalpy,
        bisection_iterations=outer_iterations,
        task172_numerical_hole_neighborhoods=tuple(hole_neighborhoods),
    )
    mesh_stats.wall_seconds = time.perf_counter() - t0
    return mesh_run, mesh_stats

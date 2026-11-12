"""Per-mesh isolated outer solve diagnostics (N1/N2/N4)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import _MeshRun
from hexagent.properties.base import PropertyProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    final_trajectory_task172_holes,
    isolated_mesh_acceptance_gate,
    production_terminal_tolerance_pass,
)
from prototypes.v08_thermal_rating.outer_shooting_isolated_v1 import IsolatedOuterBoundaryResult


@dataclass(frozen=True)
class IsolatedMeshLevelDiagnostic:
    subdivisions: int
    gate: str
    N_OUTER_STATUS: str
    N_FAILURE_CODE: str | None
    N_FAILURE_DIAGNOSTICS: tuple[str, ...]
    N_FIRST_FAILED_CELL: str | None
    N_FIRST_FAILED_EQUATION: str | None
    N_TERMINAL_RESIDUAL_K: str | None
    N_TERMINAL_RESIDUAL_J_KG: str | None
    N_TASK172_HOLES: int
    N_SEARCH_TRACE: tuple[str, ...]
    N_SHOOTING_BRACKET: tuple[str | None, str | None]
    N_ITERATIONS: int
    N_RUN_HASH: str | None
    N_SHOOTING_ENTHALPY_J_KG: str | None
    outer_result: IsolatedOuterBoundaryResult


def _audit_run(result: IsolatedOuterBoundaryResult) -> _MeshRun | None:
    return result.accepted_run or result.best_valid_run


def _first_hole_neighborhood(run: _MeshRun | None) -> tuple[str | None, str | None]:
    if run is None:
        return None, None
    hoods = run.task172_numerical_hole_neighborhoods
    if not hoods:
        hoods = tuple(
            dict(x) if not isinstance(x, dict) else x
            for x in run.observables.task172_numerical_hole_neighborhoods
        )
    if not hoods:
        return None, None
    first = dict(hoods[0])
    cell = first.get("numerical_cell_id") or first.get("cell_id")
    eq = first.get("failure_code") or first.get("residual_code") or first.get("blocked_equation")
    return cell, eq


def build_mesh_level_diagnostic(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    result: IsolatedOuterBoundaryResult,
) -> IsolatedMeshLevelDiagnostic:
    gate = isolated_mesh_acceptance_gate(bindings, provider, result)
    run = _audit_run(result)
    cell, eq = _first_hole_neighborhood(run)
    obs = run.observables if run is not None else None
    holes = (
        final_trajectory_task172_holes(
            bindings,
            provider,
            subdivisions=result.subdivisions,
            shooting_enthalpy_j_kg=result.shooting_enthalpy_j_kg,
        )
        if result.shooting_enthalpy_j_kg and gate == "BLOCKED"
        else (
            result.stats.task172_numerical_hole_count
            if result.shooting_enthalpy_j_kg is None
            else final_trajectory_task172_holes(
                bindings,
                provider,
                subdivisions=result.subdivisions,
                shooting_enthalpy_j_kg=result.shooting_enthalpy_j_kg,
            )
        )
    )
    trace = tuple(
        f"iter={s.iteration}:{s.decision_update}:{s.classification}:term={s.terminal_tolerance_pass}"
        for s in result.search_trace
    )
    if gate == "BLOCKED" and result.status != "ACCEPTED":
        if run is not None and not production_terminal_tolerance_pass(run):
            extra = "TERMINAL_TOLERANCE"
        elif holes:
            extra = "TASK172_HOLES"
        else:
            extra = result.failure_code or result.status
        diagnostics = result.diagnostics + (f"gate_blocker={extra}",)
    else:
        diagnostics = result.diagnostics

    return IsolatedMeshLevelDiagnostic(
        subdivisions=result.subdivisions,
        gate=gate,
        N_OUTER_STATUS=result.status,
        N_FAILURE_CODE=result.failure_code,
        N_FAILURE_DIAGNOSTICS=diagnostics,
        N_FIRST_FAILED_CELL=cell,
        N_FIRST_FAILED_EQUATION=eq,
        N_TERMINAL_RESIDUAL_K=str(obs.terminal_boundary_residual_k) if obs else None,
        N_TERMINAL_RESIDUAL_J_KG=str(obs.terminal_boundary_residual_j_kg) if obs else None,
        N_TASK172_HOLES=holes,
        N_SEARCH_TRACE=trace,
        N_SHOOTING_BRACKET=(result.h_low_final, result.h_high_final),
        N_ITERATIONS=len(result.search_trace),
        N_RUN_HASH=run.mesh_result_hash if run is not None else None,
        N_SHOOTING_ENTHALPY_J_KG=result.shooting_enthalpy_j_kg,
        outer_result=result,
    )


def experimental_mesh_convergence_pass(
    n1: IsolatedMeshLevelDiagnostic,
    n2: IsolatedMeshLevelDiagnostic,
    n4: IsolatedMeshLevelDiagnostic,
    *,
    duty_tolerance: Decimal | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Coarse checks when all gates ACCEPTED — duty drift N1→N2→N4."""
    if not (n1.gate == "ACCEPTED" and n2.gate == "ACCEPTED" and n4.gate == "ACCEPTED"):
        return False, ("MESH_GATE_NOT_ALL_ACCEPTED",)
    notes: list[str] = []

    def _duty(d: IsolatedMeshLevelDiagnostic) -> Decimal | None:
        r = d.outer_result.accepted_run
        if r is None:
            return None
        return r.observables.total_duty_w

    d1, d2, d4 = _duty(n1), _duty(n2), _duty(n4)
    if d1 is None or d2 is None or d4 is None:
        return False, ("MISSING_ACCEPTED_DUTY",)
    if duty_tolerance is None:
        from prototypes.v08_general_user_case.physical_feasibility import (
            THERMODYNAMIC_DUTY_TOLERANCE,
        )

        duty_tolerance = THERMODYNAMIC_DUTY_TOLERANCE
    ref = d4
    for label, d in (("N1", d1), ("N2", d2)):
        rel = abs(d - ref) / ref if ref != 0 else abs(d - ref)
        notes.append(f"{label}_duty_w={d}:rel_delta_to_N4={rel}")
        if rel > Decimal("0.02"):
            return False, tuple(notes + [f"DUTY_DRIFT_{label}_VS_N4_EXCEEDS_2PCT"])
    notes.append(f"N4_duty_w={d4}")
    return True, tuple(notes)


__all__ = [
    "IsolatedMeshLevelDiagnostic",
    "build_mesh_level_diagnostic",
    "experimental_mesh_convergence_pass",
]

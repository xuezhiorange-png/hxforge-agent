"""Task174 hydraulic feasibility screen for HXFORGE_330KW_STRICT_DP (no design-space expansion)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.properties.base import PropertyProvider
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
)

NozzleVelocityStatus = Literal["unresolved", "not_in_task174_chain"]


@dataclass(frozen=True)
class HydraulicScreenRow:
    candidate_id: str
    geometry_projection_hash: str
    tube_dp_pa: Decimal
    shell_dp_pa: Decimal
    tube_dp_limit_pa: Decimal
    shell_dp_limit_pa: Decimal
    tube_dp_pass: bool
    shell_dp_pass: bool
    hydraulic_pass: bool
    nozzle_velocity_status: NozzleVelocityStatus
    nozzle_velocity_note: str


@dataclass(frozen=True)
class HydraulicScreenReport:
    case_id: str
    candidates_screened: int
    distinct_geometry_screened: int
    hydraulic_feasible_count: int
    distinct_hydraulic_feasible_geometry: int
    rows: tuple[HydraulicScreenRow, ...]


def screen_task174_hydraulic_row(bindings: CandidateRatingBindings) -> HydraulicScreenRow:
    t174 = bindings.rating_request.task174_result
    norm = bindings.normalized
    tube_dp = t174.modeled_total_tube_side_pressure_drop_pa
    shell_dp = t174.bell_total_shell_pressure_drop_pa
    tube_lim = norm.max_tube_side_pressure_drop_pa
    shell_lim = norm.max_shell_side_pressure_drop_pa
    tube_ok = tube_dp <= tube_lim
    shell_ok = shell_dp <= shell_lim
    return HydraulicScreenRow(
        candidate_id=bindings.rating_request.candidate_id,
        geometry_projection_hash=bindings.geometry_projection_hash,
        tube_dp_pa=tube_dp,
        shell_dp_pa=shell_dp,
        tube_dp_limit_pa=tube_lim,
        shell_dp_limit_pa=shell_lim,
        tube_dp_pass=tube_ok,
        shell_dp_pass=shell_ok,
        hydraulic_pass=tube_ok and shell_ok,
        nozzle_velocity_status="not_in_task174_chain",
        nozzle_velocity_note=(
            "1–3 m/s nozzle check requires nozzle flow area from Task020/Task021 nozzle "
            "projection; Task174 fixed-geometry rating does not emit tube_nozzle_velocity_m_s "
            "or shell_nozzle_velocity_m_s."
        ),
    )


def run_hydraulic_feasibility_screen(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: PropertyProvider | None = None,
    max_candidates: int = 64,
) -> HydraulicScreenReport:
    active = provider or CoolPropProvider()
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=max_candidates
    )
    rows: list[HydraulicScreenRow] = []
    for bundle in bundles:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=space_hash,
            t168_digest=t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=active,
            geometry_projection_hash=geom.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is None:
            continue
        rows.append(screen_task174_hydraulic_row(bindings))

    feasible = [r for r in rows if r.hydraulic_pass]
    geo_all = {r.geometry_projection_hash for r in rows if r.geometry_projection_hash}
    geo_ok = {r.geometry_projection_hash for r in feasible if r.geometry_projection_hash}
    return HydraulicScreenReport(
        case_id=normalized.engineering_case_id,
        candidates_screened=len(rows),
        distinct_geometry_screened=len(geo_all),
        hydraulic_feasible_count=len(feasible),
        distinct_hydraulic_feasible_geometry=len(geo_ok),
        rows=tuple(rows),
    )


__all__ = ["HydraulicScreenReport", "HydraulicScreenRow", "run_hydraulic_feasibility_screen"]

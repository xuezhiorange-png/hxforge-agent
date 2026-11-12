"""Hydraulic-feasible candidate → production / isolated thermal closeout bridge."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from hexagent.properties.base import PropertyProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.generator import enumerate_structural_geometry
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateMeshCloseout,
    CandidateRatingBindings,
    build_candidate_rating_bindings,
    engineering_distinct_fully_converged,
    enumerate_structural_bundles,
    experimental_mesh_converged,
    run_candidate_mesh_closeout,
)
from prototypes.v08_thermal_rating.boundary_precision_audit_v1 import (
    BoundaryPrecisionAudit,
    run_boundary_precision_audit,
)
from prototypes.v08_thermal_rating.hydraulic_feasibility_v08 import (
    HydraulicScreenRow,
    run_hydraulic_feasibility_screen,
    screen_task174_hydraulic_row,
)
from prototypes.v08_thermal_rating.nozzle_velocity_v08 import (
    NozzleVelocityReport,
    assess_nozzle_velocities,
)

ThermalHydraulicClass = Literal[
    "THERMAL_AND_HYDRAULIC_FEASIBLE",
    "THERMAL_DUTY_INSUFFICIENT",
    "THERMAL_NUMERICAL_BLOCKED",
    "HYDRAULIC_FEASIBLE_NOZZLE_UNRESOLVED",
]


@dataclass(frozen=True)
class CandidateSpaceInventory:
    combinations_evaluated: int
    manufacturable_valid_count: int
    distinct_geometry_manufacturable: int
    rating_bindings_built: int
    hydraulic_feasible_count: int
    distinct_hydraulic_feasible_geometry: int


@dataclass(frozen=True)
class FeasibleThermalCloseout:
    hydraulic_row: HydraulicScreenRow
    mesh_closeout: CandidateMeshCloseout
    nozzle: NozzleVelocityReport
    classification: ThermalHydraulicClass
    precision_blocker: str | None
    precision_audit: BoundaryPrecisionAudit | None


@dataclass(frozen=True)
class FeasibleCandidateThermalBridgeReport:
    inventory: CandidateSpaceInventory
    selected: FeasibleThermalCloseout | None
    thermal_runs: tuple[FeasibleThermalCloseout, ...]
    experimental_mesh_converged_count: int
    production_validated_count: int
    distinct_fully_converged_geometry: int


def _inventory_counts(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: PropertyProvider,
    max_candidates: int,
) -> tuple[CandidateSpaceInventory, dict[str, CandidateRatingBindings]]:
    space = load_v08_discrete_space(DEFAULT_V08_DISCRETE_SPACE_PATH)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    enum = enumerate_structural_geometry(
        t168, filtered, (), max_combinations=512, max_valid_candidates=max_candidates
    )
    geom_by_id = {row.candidate_id: row.geometry_projection_hash for row in enum.candidate_records}
    bindings_by_id: dict[str, CandidateRatingBindings] = {}
    rows: list[HydraulicScreenRow] = []
    for bundle in enum.valid_structural:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=enum.space_hash,
            t168_digest=bundle.task168_request_hash_digest,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=geom_by_id.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is None:
            continue
        bindings_by_id[bindings.rating_request.candidate_id] = bindings
        rows.append(screen_task174_hydraulic_row(bindings))

    feasible = [r for r in rows if r.hydraulic_pass]
    geo_mfg = {r.geometry_projection_hash for r in rows if r.geometry_projection_hash}
    geo_ok = {r.geometry_projection_hash for r in feasible if r.geometry_projection_hash}
    inventory = CandidateSpaceInventory(
        combinations_evaluated=len(enum.candidate_records) + len(enum.rejections),
        manufacturable_valid_count=len(enum.valid_structural),
        distinct_geometry_manufacturable=len(geo_mfg),
        rating_bindings_built=len(rows),
        hydraulic_feasible_count=len(feasible),
        distinct_hydraulic_feasible_geometry=len(geo_ok),
    )
    return inventory, bindings_by_id


def classify_thermal_hydraulic(
    closeout: CandidateMeshCloseout,
    nozzle: NozzleVelocityReport,
) -> ThermalHydraulicClass:
    if not closeout.hydraulic_pass:
        return "THERMAL_NUMERICAL_BLOCKED"
    if closeout.n1 != "ACCEPTED" or closeout.n2 != "ACCEPTED" or closeout.n4 != "ACCEPTED":
        return "THERMAL_NUMERICAL_BLOCKED"
    if closeout.target_330kw_met == "false":
        return "THERMAL_DUTY_INSUFFICIENT"
    if nozzle.status != "VERIFIED":
        return "HYDRAULIC_FEASIBLE_NOZZLE_UNRESOLVED"
    if closeout.production_task173_gate != "RATING_SUCCESS":
        if closeout.n4 != "ACCEPTED":
            return "THERMAL_NUMERICAL_BLOCKED"
        return "HYDRAULIC_FEASIBLE_NOZZLE_UNRESOLVED"
    if closeout.target_330kw_met == "true" and nozzle.status == "VERIFIED":
        return "THERMAL_AND_HYDRAULIC_FEASIBLE"
    return "HYDRAULIC_FEASIBLE_NOZZLE_UNRESOLVED"


def run_feasible_candidate_thermal_bridge(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: PropertyProvider,
    max_candidates: int = 64,
    run_production: bool = True,
) -> FeasibleCandidateThermalBridgeReport:
    """Screen full set, then thermal-closeout **only** hydraulically feasible candidates."""
    inventory, bindings_by_id = _inventory_counts(
        normalized, handoff, provider=provider, max_candidates=max_candidates
    )
    hydraulic = run_hydraulic_feasibility_screen(
        normalized, handoff, provider=provider, max_candidates=max_candidates
    )
    feasible_ids = [r.candidate_id for r in hydraulic.rows if r.hydraulic_pass]
    runs: list[FeasibleThermalCloseout] = []
    for cid in feasible_ids:
        bindings = bindings_by_id.get(cid)
        if bindings is None:
            continue
        row = screen_task174_hydraulic_row(bindings)
        closeout = run_candidate_mesh_closeout(
            bindings, provider, run_production_gate=run_production
        )
        nozzle = assess_nozzle_velocities(bindings, provider)
        classification = classify_thermal_hydraulic(closeout, nozzle)
        audit = run_boundary_precision_audit(bindings, provider, subdivisions=1)
        blocker = audit.first_numerical_blocker if closeout.n1 != "ACCEPTED" else None
        runs.append(
            FeasibleThermalCloseout(
                hydraulic_row=row,
                mesh_closeout=closeout,
                nozzle=nozzle,
                classification=classification,
                precision_blocker=blocker,
                precision_audit=audit,
            )
        )

    selected = runs[0] if runs else None
    exp = sum(1 for r in runs if experimental_mesh_converged(r.mesh_closeout))
    prod_val = sum(1 for r in runs if r.mesh_closeout.production_task173_gate == "RATING_SUCCESS")
    distinct = len(
        {
            r.mesh_closeout.geometry_projection_hash
            for r in runs
            if r.mesh_closeout.geometry_projection_hash
            and engineering_distinct_fully_converged(
                r.mesh_closeout, nozzle=r.nozzle, target_met=r.mesh_closeout.target_330kw_met
            )
        }
    )
    return FeasibleCandidateThermalBridgeReport(
        inventory=inventory,
        selected=selected,
        thermal_runs=tuple(runs),
        experimental_mesh_converged_count=exp,
        production_validated_count=prod_val,
        distinct_fully_converged_geometry=distinct,
    )


def bindings_for_first_enumerated(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: PropertyProvider,
) -> CandidateRatingBindings | None:
    """Legacy path: first manufacturable bundle (for regression diffs only)."""
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=1
    )
    if not bundles:
        return None
    return build_candidate_rating_bindings(
        bundles[0],
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geom.get(bundles[0].candidate.candidate_id, ""),
    )


__all__ = [
    "CandidateSpaceInventory",
    "FeasibleCandidateThermalBridgeReport",
    "FeasibleThermalCloseout",
    "run_feasible_candidate_thermal_bridge",
    "classify_thermal_hydraulic",
]

"""Full-chain validation for the single recovered 0.52 m Task168 layout (no 0.45 m re-search)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import Task174SuccessResult
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    authoritative_baffle_cut_fraction,
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
    resolve_baffle_authority,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    AutonomousNozzleFullPathReport,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    RecoveredShell052Bundle,
    resolve_recovered_shell_052_bundle,
)
from prototypes.v08_thermal_rating.shell_hydraulic_lower_bound_v08 import (
    analyze_shell_hydraulic_lower_bound,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import (
    ThermalPrescreenResult,
    run_thermal_prescreen,
)

FROZEN_SHELL_052_CANDIDATE_ID = "6d78897b-77b7-545d-8b49-38a569b1c86e"
FROZEN_SHELL_052_GEOMETRY_V2 = "aba3161014a6a9f16c47797eb2e23b63203e8ccf2a5fe70e80ec869d6b00d98e"

DesignDecision = Literal["MID_FEASIBLE_FOUND", "RECOVERED_LAYOUT_HYDRAULIC_BLOCKED"]
MidHydraulic = Literal["PASS", "BLOCKED", "NOT_RUN_PROVEN_INFEASIBLE"]
HighHydraulic = Literal["PASS", "BLOCKED", "NOT_RUN"]


@dataclass(frozen=True)
class RecoveredShell052FullChainReport:
    recovered: RecoveredShell052Bundle | None
    shell_052_task168: Literal["PASS", "BLOCKED"]
    geometry_identity_v2: str | None
    geometry_projection_hash_v1: str | None
    candidate_id: str | None
    task168_request_digest: str | None
    physical_tube_count: int | None
    baffle_count: int | None
    baffle_cut_fraction: str | None
    placement_envelope_m: str | None
    layout_hash: str | None
    task024_geometry_hash: str | None
    task166_applicability: str
    task166_status: str
    task174_status: str
    bell_dp_pa: str | None
    tube_full_dp_pa: str | None
    shell_full_dp_pa: str | None
    mid_hydraulic: MidHydraulic
    high_hydraulic: HighHydraulic
    nozzle_velocity_check: str
    first_hydraulic_blocker: str | None
    proven_infeasible_lower_bound: bool
    lower_bound_mid_shell_min_pa: str | None
    geometry_identity_v2_bound_to_results: bool
    thermal: ThermalPrescreenResult | None
    hydraulic_report: AutonomousNozzleFullPathReport | None
    design_decision: DesignDecision
    next_required_engineering_change: str


def run_recovered_shell_052_full_chain(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> RecoveredShell052FullChainReport:
    active = provider or CoolPropProvider()
    recovered = resolve_recovered_shell_052_bundle(normalized, handoff)
    if recovered is None:
        return RecoveredShell052FullChainReport(
            recovered=None,
            shell_052_task168="BLOCKED",
            geometry_identity_v2=None,
            geometry_projection_hash_v1=None,
            candidate_id=None,
            task168_request_digest=None,
            physical_tube_count=None,
            baffle_count=None,
            baffle_cut_fraction=None,
            placement_envelope_m=None,
            layout_hash=None,
            task024_geometry_hash=None,
            task166_applicability="NOT_EVALUATED",
            task166_status="NOT_RUN",
            task174_status="NOT_RUN",
            bell_dp_pa=None,
            tube_full_dp_pa=None,
            shell_full_dp_pa=None,
            mid_hydraulic="NOT_RUN_PROVEN_INFEASIBLE",
            high_hydraulic="NOT_RUN",
            nozzle_velocity_check="NOT_RUN",
            first_hydraulic_blocker="TASK168_NO_RECOVERED_0P52_LAYOUT",
            proven_infeasible_lower_bound=False,
            lower_bound_mid_shell_min_pa=None,
            geometry_identity_v2_bound_to_results=False,
            thermal=None,
            hydraulic_report=None,
            design_decision="RECOVERED_LAYOUT_HYDRAULIC_BLOCKED",
            next_required_engineering_change="No Task168-valid 0.52 m layout to validate.",
        )

    bundle = recovered.structural_bundle
    v1 = geometry_projection_hash_v1(bundle)
    v2 = geometry_identity_v2_hash(bundle)
    baffle = resolve_baffle_authority(candidate=bundle.candidate, bundle=bundle.bundle)
    layout = bundle.bundle.task021_layout
    t024 = bundle.bundle.task024_geometry
    cut = authoritative_baffle_cut_fraction(candidate=bundle.candidate, bundle=bundle.bundle)

    bindings = build_candidate_rating_bindings(
        bundle,
        space_hash=recovered.candidate_space_hash,
        t168_digest=bundle.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=active,
        geometry_projection_hash=v2,
    )
    if bindings is None:
        return RecoveredShell052FullChainReport(
            recovered=recovered,
            shell_052_task168="PASS",
            geometry_identity_v2=v2,
            geometry_projection_hash_v1=v1,
            candidate_id=bundle.candidate.candidate_id,
            task168_request_digest=bundle.task168_request_hash_digest,
            physical_tube_count=int(layout.physical_tube_count),
            baffle_count=baffle.baffle_count_authoritative,
            baffle_cut_fraction=cut,
            placement_envelope_m=recovered.placement_envelope_diameter_m,
            layout_hash=str(layout.layout_hash),
            task024_geometry_hash=str(getattr(t024, "geometry_hash", "")),
            task166_applicability="NOT_EVALUATED",
            task166_status="NOT_RUN",
            task174_status="BLOCKED",
            bell_dp_pa=None,
            tube_full_dp_pa=None,
            shell_full_dp_pa=None,
            mid_hydraulic="NOT_RUN",
            high_hydraulic="NOT_RUN",
            nozzle_velocity_check="NOT_RUN",
            first_hydraulic_blocker="TASK174_OR_BINDINGS_BLOCKED",
            proven_infeasible_lower_bound=False,
            lower_bound_mid_shell_min_pa=None,
            geometry_identity_v2_bound_to_results=False,
            thermal=None,
            hydraulic_report=None,
            design_decision="RECOVERED_LAYOUT_HYDRAULIC_BLOCKED",
            next_required_engineering_change="Task174 binding failed on recovered bundle.",
        )

    t166 = bundle.bundle.task166_result
    task166_app = "NOT_EVALUATED"
    task166_status = "NOT_RUN"
    bell_dp: str | None = None
    if isinstance(t166, Task166Result):
        task166_status = "SUCCESS"
        if t166.applicability is not None:
            task166_app = str(t166.applicability.status.value)
        bell_dp = str(t166.total_shell_pressure_drop)

    t174 = bindings.rating_request.task174_result
    task174_status = "VALIDATED" if isinstance(t174, Task174SuccessResult) else "BLOCKED"

    lb = analyze_shell_hydraulic_lower_bound(bindings)
    proven = lb.all_proven_infeasible
    mid_lb = next(s for s in lb.scenarios if s.scenario_key == "mid_band")
    lb_min = (
        str(Decimal(mid_lb.shell_bell_internal_dp_pa) + Decimal(mid_lb.shell_external_min_dp_pa))
        if mid_lb.shell_bell_internal_dp_pa
        else None
    )

    hydraulic_report: AutonomousNozzleFullPathReport | None = None
    mid_h: MidHydraulic = "NOT_RUN_PROVEN_INFEASIBLE" if proven else "BLOCKED"
    high_h: HighHydraulic = "NOT_RUN"
    tube_fp: str | None = None
    shell_fp: str | None = None
    nozzle_check = "NOT_RUN"
    blocker: str | None = None
    v2_bound = False

    if proven:
        blocker = "PROVEN_HYDRAULIC_INFEASIBLE_UNDER_ASSUMED_K"
        if Decimal(mid_lb.shell_dp_limit_pa) < Decimal(lb_min or "1e12"):
            excess = Decimal(lb_min or "0") - Decimal(mid_lb.shell_dp_limit_pa)
            blocker = f"SHELL_LOWER_BOUND_EXCESS_PA={excess}"
    else:
        hydraulic_report = run_autonomous_nozzle_full_path(bindings)
        v2_bound = hydraulic_report.structural_geometry_hash == v2
        mid = next(s for s in hydraulic_report.scenarios if s.scenario_key == "mid_band")
        high = next(
            s for s in hydraulic_report.scenarios if s.scenario_key == "high_loss_sensitivity"
        )
        tube_fp = mid.tube_full_path_dp_pa
        shell_fp = mid.shell_full_path_dp_pa
        nozzle_check = str(hydraulic_report.nozzle_velocity_check)
        mid_h = "PASS" if mid.hydraulic_check == "PASS" else "BLOCKED"
        high_h = "PASS" if high.hydraulic_check == "PASS" else "BLOCKED"
        if mid_h != "PASS":
            if shell_fp:
                excess = Decimal(shell_fp) - normalized.max_shell_side_pressure_drop_pa
                blocker = f"SHELL_FULL_PATH_EXCESS_PA={excess}"
            elif tube_fp and Decimal(tube_fp) > normalized.max_tube_side_pressure_drop_pa:
                excess = Decimal(tube_fp) - normalized.max_tube_side_pressure_drop_pa
                blocker = f"TUBE_FULL_PATH_EXCESS_PA={excess}"
            else:
                blocker = "FULL_PATH_NOT_COMPUTED"

    thermal = run_thermal_prescreen(bindings, normalized, provider=active)

    decision: DesignDecision = (
        "MID_FEASIBLE_FOUND" if mid_h == "PASS" else "RECOVERED_LAYOUT_HYDRAULIC_BLOCKED"
    )
    if decision == "MID_FEASIBLE_FOUND":
        next_change = (
            "Recovered 0.52 m mid-band full-path feasible under experimental authority; "
            "manufacturing and production Task172/173 remain blocked."
        )
    elif proven:
        next_change = (
            f"Bell+min-nozzle lower bound exceeds 1180 Pa on 0.52 m recovered layout "
            f"(~{lb_min} Pa); single-segmental shell model upgrade required before further sizing."
        )
    else:
        next_change = (
            f"0.52 m recovered layout computed: mid shell FP={shell_fp or 'not_run'} Pa "
            f"vs 1180 Pa; first blocker={blocker or 'unknown'}."
        )

    return RecoveredShell052FullChainReport(
        recovered=recovered,
        shell_052_task168="PASS",
        geometry_identity_v2=v2,
        geometry_projection_hash_v1=v1,
        candidate_id=bundle.candidate.candidate_id,
        task168_request_digest=bundle.task168_request_hash_digest,
        physical_tube_count=int(layout.physical_tube_count),
        baffle_count=baffle.baffle_count_authoritative,
        baffle_cut_fraction=cut,
        placement_envelope_m=recovered.placement_envelope_diameter_m,
        layout_hash=str(layout.layout_hash),
        task024_geometry_hash=str(getattr(t024, "geometry_hash", "")),
        task166_applicability=task166_app,
        task166_status=task166_status,
        task174_status=task174_status,
        bell_dp_pa=bell_dp,
        tube_full_dp_pa=tube_fp,
        shell_full_dp_pa=shell_fp,
        mid_hydraulic=mid_h,
        high_hydraulic=high_h,
        nozzle_velocity_check=nozzle_check,
        first_hydraulic_blocker=blocker,
        proven_infeasible_lower_bound=proven,
        lower_bound_mid_shell_min_pa=lb_min,
        geometry_identity_v2_bound_to_results=v2_bound,
        thermal=thermal,
        hydraulic_report=hydraulic_report,
        design_decision=decision,
        next_required_engineering_change=next_change,
    )


__all__ = ["RecoveredShell052FullChainReport", "run_recovered_shell_052_full_chain"]

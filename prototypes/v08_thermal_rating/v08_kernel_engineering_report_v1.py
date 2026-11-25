"""V08-04/05 engineering report on independent rating kernel (not Task173)."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
    load_case_bindings,
)
from prototypes.v08_thermal_rating.v08_04_hydraulic_feasibility_gate import (
    evaluate_v08_04_candidate_hydraulics,
)
from prototypes.v08_thermal_rating.v08_independent_engineering_rating_kernel_v1 import (
    KERNEL_AUTHORITY_ID,
    rate_candidate_engineering_kernel_v1,
)
from prototypes.v08_thermal_rating.v08_kernel_hydraulic_integration_v1 import (
    HYDRAULIC_AUTHORITY_ID,
    KernelJointHydraulicRecord,
    candidate_geometry_snapshot,
    evaluate_kernel_joint_hydraulics,
)

TASK_ID = "V08-04"
EXECUTION_STAGE = "NEW_RATING_KERNEL_ENGINEERING_INTEGRATION"
RATING_AUTHORITY_TIER = "V08_INDEPENDENT_KERNEL_V1"
FORMAL_ENGINEERING_LIST_REQUIRES = "V08_KERNEL_RATING_ACCEPTANCE_V1_AND_FORMAL_REVIEW"

FinalQualification = Literal[
    "KERNEL_JOINT_E2E_SUCCESS",
    "KERNEL_ROBUST_THREE_K",
    "KERNEL_CONDITIONAL_MID_K",
    "THERMAL_ONLY",
    "HYDRAULIC_OR_NOZZLE_BLOCKED",
    "THERMAL_BLOCKED",
    "BINDINGS_BLOCKED",
]


@dataclass(frozen=True)
class KernelCandidateEngineeringRow:
    case_id: str
    candidate_id: str
    geometry: dict[str, str]
    target_q_w: str
    actual_q_w: str | None
    u_clean_outer_w_m2_k: str | None
    area_outer_m2: str | None
    ua_w_per_k: str | None
    tube_outlet_t_k: str | None
    shell_outlet_t_k: str | None
    energy_balance_residual_w: str | None
    energy_balance_pass: bool
    tube_dp_limit_pa: str
    shell_dp_limit_pa: str
    k_scenarios: tuple[dict[str, Any], ...]
    nozzle_ports: tuple[dict[str, str], ...]
    final_qualification: FinalQualification
    joint_class: str
    failed_constraints: tuple[str, ...]
    thermal_authority_id: str
    hydraulic_authority_id: str
    # legacy path without kernel outlet / four-port — for E2E=0 explanation
    legacy_v08_04_blockers: tuple[str, ...]


@dataclass(frozen=True)
class KernelCaseEngineeringReport:
    fixture_path: str
    case_id: str
    normalization_hash: str
    candidate_space_hash: str
    rows: tuple[KernelCandidateEngineeringRow, ...]
    successful_e2e_count: int
    thermal_duty_pass_count: int
    hydraulic_pass_count: int
    nozzle_velocity_pass_count: int
    joint_hard_constraint_pass_count: int
    first_successful_e2e_candidate_id: str | None
    report_hash: str


def _k_rows(joint: KernelJointHydraulicRecord) -> tuple[dict[str, Any], ...]:
    hyd = joint.hydraulic_report
    rows: list[dict[str, Any]] = []
    for sc in hyd.scenarios:
        rows.append(
            {
                "scenario_key": sc.scenario_key,
                "hydraulic_check": sc.hydraulic_check,
                "tube_total_dp_pa": sc.tube_full_path_dp_pa,
                "shell_total_dp_pa": sc.shell_full_path_dp_pa,
                "tube_margin_pa": sc.tube_margin_pa,
                "shell_margin_pa": sc.shell_margin_pa,
                "full_path_feasible": sc.full_path_feasible,
                "tube_breakdown": dict(sc.tube_breakdown),
                "shell_breakdown": dict(sc.shell_breakdown),
            }
        )
    return tuple(rows)


def _qualify(
    joint: KernelJointHydraulicRecord, thermal_status: str, duty_ok: bool
) -> FinalQualification:
    if thermal_status != "RATING_SUCCESS":
        return "THERMAL_BLOCKED"
    if joint.joint_class == "FULL_E2E_SUCCESS":
        return "KERNEL_JOINT_E2E_SUCCESS"
    if joint.joint_class == "ROBUST_THREE_K_PASS":
        return "KERNEL_ROBUST_THREE_K"
    if joint.joint_class == "CONDITIONAL_MID_K_ONLY":
        return "KERNEL_CONDITIONAL_MID_K"
    if joint.joint_class == "THERMAL_ONLY":
        return "THERMAL_ONLY"
    return "HYDRAULIC_OR_NOZZLE_BLOCKED"


def run_kernel_case_engineering_matrix(
    fixture: Path,
    *,
    provider: CoolPropProvider | None = None,
    max_candidates: int = 64,
) -> KernelCaseEngineeringReport:
    active = provider or CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(fixture, provider=active)
    space_hash, t168_digest, bundles, geom_hashes = enumerate_structural_bundles(
        normalized, handoff, max_valid=max_candidates
    )
    norm_hash = canonical_sha256(
        json.loads(fixture.read_text(encoding="utf-8"))
        if False
        else {"engineering_case_id": normalized.engineering_case_id}
    )
    rows: list[KernelCandidateEngineeringRow] = []
    for bundle in bundles:
        cid = bundle.candidate.candidate_id
        gh = geom_hashes.get(cid, "")
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=space_hash,
            t168_digest=t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=active,
            geometry_projection_hash=gh,
        )
        if bindings is None:
            rows.append(
                KernelCandidateEngineeringRow(
                    case_id=normalized.engineering_case_id,
                    candidate_id=cid,
                    geometry={"candidate_id": cid, "geometry_projection_hash": gh},
                    target_q_w=str(normalized.target_duty_w),
                    actual_q_w=None,
                    u_clean_outer_w_m2_k=None,
                    area_outer_m2=None,
                    ua_w_per_k=None,
                    tube_outlet_t_k=None,
                    shell_outlet_t_k=None,
                    energy_balance_residual_w=None,
                    energy_balance_pass=False,
                    tube_dp_limit_pa=str(normalized.max_tube_side_pressure_drop_pa),
                    shell_dp_limit_pa=str(normalized.max_shell_side_pressure_drop_pa),
                    k_scenarios=(),
                    nozzle_ports=(),
                    final_qualification="BINDINGS_BLOCKED",
                    joint_class="BINDINGS_BLOCKED",
                    failed_constraints=("TASK174_BINDINGS_BLOCKED",),
                    thermal_authority_id=KERNEL_AUTHORITY_ID,
                    hydraulic_authority_id=HYDRAULIC_AUTHORITY_ID,
                    legacy_v08_04_blockers=(),
                )
            )
            continue
        thermal = rate_candidate_engineering_kernel_v1(bindings, normalized, provider=active)
        joint = evaluate_kernel_joint_hydraulics(bindings, thermal, provider=active)
        legacy = evaluate_v08_04_candidate_hydraulics(bindings, provider=active)
        legacy_blockers = tuple(legacy.hard_gate.blockers or ())
        res = thermal.resistance
        ports = tuple(
            {
                "port_id": p.port_id,
                "inside_diameter_m": str(p.inside_diameter_m),
                "velocity_m_s": str(p.velocity_m_s),
            }
            for p in joint.hydraulic_report.ports
        )
        qual = _qualify(joint, thermal.status, thermal.duty_meets_target)
        fails: list[str] = []
        if qual not in (
            "KERNEL_JOINT_E2E_SUCCESS",
            "KERNEL_ROBUST_THREE_K",
            "KERNEL_CONDITIONAL_MID_K",
        ):
            fails = list(joint.blockers)
        if not thermal.duty_meets_target:
            fails.append("DUTY_BELOW_TARGET")
        if not thermal.energy_balance_pass:
            fails.append("ENERGY_BALANCE")
        rows.append(
            KernelCandidateEngineeringRow(
                case_id=normalized.engineering_case_id,
                candidate_id=cid,
                geometry=candidate_geometry_snapshot(bindings),
                target_q_w=str(normalized.target_duty_w),
                actual_q_w=thermal.q_w,
                u_clean_outer_w_m2_k=res.u_clean_outer_w_m2_k if res else None,
                area_outer_m2=res.area_outer_m2 if res else None,
                ua_w_per_k=thermal.ua_w_per_k,
                tube_outlet_t_k=thermal.tube_outlet_t_k,
                shell_outlet_t_k=thermal.shell_outlet_t_k,
                energy_balance_residual_w=thermal.energy_balance_residual_w,
                energy_balance_pass=thermal.energy_balance_pass,
                tube_dp_limit_pa=str(normalized.max_tube_side_pressure_drop_pa),
                shell_dp_limit_pa=str(normalized.max_shell_side_pressure_drop_pa),
                k_scenarios=_k_rows(joint),
                nozzle_ports=ports,
                final_qualification=qual,
                joint_class=joint.joint_class,
                failed_constraints=tuple(dict.fromkeys(fails)),
                thermal_authority_id=thermal.authority_id,
                hydraulic_authority_id=joint.authority_id,
                legacy_v08_04_blockers=legacy_blockers,
            )
        )
    e2e = [r for r in rows if r.final_qualification == "KERNEL_JOINT_E2E_SUCCESS"]
    thermal_ok = sum(
        1 for r in rows if r.actual_q_w and Decimal(r.actual_q_w) >= Decimal(r.target_q_w)
    )
    hyd_ok = sum(
        1
        for r in rows
        if r.final_qualification
        in ("KERNEL_JOINT_E2E_SUCCESS", "KERNEL_ROBUST_THREE_K", "KERNEL_CONDITIONAL_MID_K")
    )
    nozzle_ok = sum(
        1
        for r in rows
        if r.nozzle_ports
        and not any("NOZZLE" in f for f in r.failed_constraints)
        and r.joint_class in ("FULL_E2E_SUCCESS", "ROBUST_THREE_K_PASS", "CONDITIONAL_MID_K_ONLY")
    )
    joint_ok = len(e2e)
    first_e2e = e2e[0].candidate_id if e2e else None
    stable = {
        "case_id": normalized.engineering_case_id,
        "space_hash": space_hash,
        "rows": [asdict(r) for r in rows],
    }
    return KernelCaseEngineeringReport(
        fixture_path=str(fixture),
        case_id=normalized.engineering_case_id,
        normalization_hash=norm_hash,
        candidate_space_hash=space_hash,
        rows=tuple(rows),
        successful_e2e_count=joint_ok,
        thermal_duty_pass_count=thermal_ok,
        hydraulic_pass_count=hyd_ok,
        nozzle_velocity_pass_count=nozzle_ok,
        joint_hard_constraint_pass_count=joint_ok,
        first_successful_e2e_candidate_id=first_e2e,
        report_hash=canonical_sha256(stable),
    )


def kernel_web_payload(case_report: KernelCaseEngineeringReport) -> dict[str, Any]:
    """Minimal web API payload (experimental kernel authority)."""
    ranked = sorted(
        case_report.rows,
        key=lambda r: (
            0
            if r.final_qualification == "KERNEL_JOINT_E2E_SUCCESS"
            else 1
            if r.final_qualification.startswith("KERNEL_")
            else 2,
            -(Decimal(r.actual_q_w or "0")),
        ),
    )
    top = [r for r in ranked if r.final_qualification.startswith("KERNEL_")][:5]
    return {
        "schema": "hxforge.kernel-engineering-report.v1",
        "task_id": TASK_ID,
        "execution_stage": EXECUTION_STAGE,
        "rating_authority_tier": RATING_AUTHORITY_TIER,
        "thermal_authority_id": KERNEL_AUTHORITY_ID,
        "hydraulic_authority_id": HYDRAULIC_AUTHORITY_ID,
        "production_task173_validated": False,
        "case_id": case_report.case_id,
        "case_report_hash": case_report.report_hash,
        "top_kernel_qualified": [asdict(r) for r in top],
        "all_candidates": [asdict(r) for r in case_report.rows],
        "engineering_design_status": "EXPERIMENTAL_KERNEL_JOINT",
    }


__all__ = [
    "KernelCandidateEngineeringRow",
    "KernelCaseEngineeringReport",
    "run_kernel_case_engineering_matrix",
    "kernel_web_payload",
    "RATING_AUTHORITY_TIER",
]

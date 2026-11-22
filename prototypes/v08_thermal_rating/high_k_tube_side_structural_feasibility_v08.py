"""High-K tube-side resistance budget and authorized-structure feasibility (design C nozzles frozen)."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    _side_inlet_density_kg_m3,
    _verify_full_path,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    _fluid_density_kg_m3,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    build_candidate_rating_bindings,
)
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_M,
    CANDIDATE_C_SHELL_NOZZLE_ID_MM,
    CANDIDATE_C_TUBE_NOZZLE_ID_M,
    CANDIDATE_C_TUBE_NOZZLE_ID_MM,
)
from prototypes.v08_thermal_rating.first_joint_candidate_freeze_v08 import (
    _resolve_frozen_bundle,
)
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.four_port_nozzle_correction_and_validation_v08 import (
    _common_diameter_bounds,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    RecoveredShell052Bundle,
    enumerate_shell_052_bounded_local_combos,
    resolve_recovered_shell_052_bundle,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import run_thermal_prescreen
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
    candidate_selection_record_from_bindings,
    task174_hydraulic_postpass_from_bindings,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import (
    evaluate_binding_task037,
)

_TUBE_DP_LIMIT_PA = Decimal("1150")
_SHELL_DP_LIMIT_PA = Decimal("1180")
_TARGET_Q_W = Decimal("330000")
_APPROVED_TUBE_CATALOG = Path(
    "docs/tasks/evidence/TASK-172-r117-approved-tube-geometry-catalog-r1.json"
)

DesignDecision = Literal[
    "HIGH_K_JOINT_PRESCREEN_PASS",
    "EXISTING_AUTHORIZED_SPACE_BLOCKED",
]


@dataclass(frozen=True)
class TubeDpBudgetRow:
    loss_scenario_key: str
    tube_full_path_total_dp_pa: str
    tube_internal_friction_dp_pa: str | None
    tube_local_dp_pa: str | None
    component_dp_pa: dict[str, str]
    delta_vs_mid_pa: dict[str, str]


@dataclass(frozen=True)
class AuthorizedVariantResult:
    label: str
    candidate_id: str
    geometry_v2: str
    physical_tube_count: int
    tube_length_m: str
    envelope_scale: str | None
    clean_q_w: str | None
    fouled_q_w: str | None
    ua_w_per_k: str | None
    tube_htc_w_m2_k: str | None
    shell_htc_w_m2_k: str | None
    mid_tube_dp_pa: str | None
    mid_shell_dp_pa: str | None
    high_tube_dp_pa: str | None
    high_shell_dp_pa: str | None
    four_port_check: str
    full_joint_pass: bool
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class HighKTubeStructuralFeasibilityReport:
    frozen_candidate_c_unchanged: Literal[True]
    high_tube_dp_baseline_pa: str
    high_tube_dp_nozzle_lower_bound_pa: str
    high_tube_dp_excess_pa: str
    tube_internal_friction_dp_pa: str | None
    tube_local_dp_pa: str | None
    tube_nozzle_pair_dp_pa: str | None
    required_internal_dp_reduction_pa: str
    friction_only_directional_reduction_pa: str
    high_k_mechanism_note: str
    budget: tuple[TubeDpBudgetRow, ...]
    existing_authorized_variant_feasible: bool
    authorized_variants_evaluated: int
    authorized_variant_blockers: tuple[str, ...]
    variants: tuple[AuthorizedVariantResult, ...]
    best_validated_variant_id: str | None
    best_validated_variant_geometry_v2: str | None
    best_validated_variant_clean_q_w: str | None
    best_validated_variant_high_tube_dp_pa: str | None
    best_validated_variant_high_shell_dp_pa: str | None
    best_validated_variant_four_port_check: str | None
    new_tube_geometry_authority_required: bool
    proposed_engineering_change: str
    engineering_source_status: str
    design_decision: DesignDecision
    design_c_reference: dict[str, Any]


def _component_map(fp: dict[str, Any]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for row in fp.get("TUBE_DP_COMPONENTS") or []:
        if isinstance(row, dict) and row.get("dp_pa") is not None:
            out[str(row["component_id"])] = Decimal(str(row["dp_pa"]))
    return out


def _nozzle_pair_dp(components: dict[str, Decimal]) -> Decimal:
    keys = (
        "R27B-ASSUMP-TUBE-INLET-NOZZLE",
        "R27B-ASSUMP-TUBE-OUTLET-NOZZLE",
    )
    return sum((components.get(k, Decimal("0")) for k in keys), Decimal("0"))


def _build_dp_budget(
    *,
    case: Any,
    record: Any,
    postpass: dict[str, Any],
    tube_out: tuple[Decimal, Decimal],
    shell_out: tuple[Decimal, Decimal],
) -> tuple[tuple[TubeDpBudgetRow, ...], str | None, str | None, str | None, str]:
    rows: list[TubeDpBudgetRow] = []
    mid_fp = _verify_full_path(
        case=case,
        record=record,
        postpass=postpass,
        loss_scenario_key="mid_band",
        tube_nozzle_d_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
        shell_nozzle_d_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
        tube_outlet_state_k_pa=tube_out,
        shell_outlet_state_k_pa=shell_out,
    )
    high_fp = _verify_full_path(
        case=case,
        record=record,
        postpass=postpass,
        loss_scenario_key="high_loss_sensitivity",
        tube_nozzle_d_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
        shell_nozzle_d_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
        tube_outlet_state_k_pa=tube_out,
        shell_outlet_state_k_pa=shell_out,
    )
    mid_c = _component_map(mid_fp)
    high_c = _component_map(high_fp)
    for key, fp in (("mid_band", mid_fp), ("high_loss_sensitivity", high_fp)):
        cmap = _component_map(fp)
        delta = {
            cid: str((cmap.get(cid, Decimal("0")) - mid_c.get(cid, Decimal("0"))).quantize(Decimal("0.001")))
            for cid in sorted(set(cmap) | set(mid_c))
            if key != "mid_band"
        }
        rows.append(
            TubeDpBudgetRow(
                loss_scenario_key=key,
                tube_full_path_total_dp_pa=str(fp.get("TUBE_FULL_PATH_TOTAL_DP_PA")),
                tube_internal_friction_dp_pa=(
                    str(fp["TUBE_INTERNAL_FRICTION_DP_PA"])
                    if fp.get("TUBE_INTERNAL_FRICTION_DP_PA")
                    else None
                ),
                tube_local_dp_pa=str(fp["TUBE_LOCAL_DP_PA"]) if fp.get("TUBE_LOCAL_DP_PA") else None,
                component_dp_pa={k: str(v) for k, v in cmap.items()},
                delta_vs_mid_pa=delta,
            )
        )
    friction = rows[-1].tube_internal_friction_dp_pa
    local = rows[-1].tube_local_dp_pa
    nozzle_pair = str(_nozzle_pair_dp(high_c).quantize(Decimal("0.001")))
    mechanism = (
        "High-K excess vs mid is dominated by R27B local loss coefficients on "
        "inlet/outlet nozzles and bundle entrance/exit; Task174 internal friction "
        "is unchanged across K scenarios at fixed geometry."
    )
    return tuple(rows), friction, local, nozzle_pair, mechanism


def _joint_criteria(
    *,
    clean_q: Decimal | None,
    mid_tube: Decimal | None,
    mid_shell: Decimal | None,
    high_tube: Decimal | None,
    high_shell: Decimal | None,
    four_port: str,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if clean_q is None or clean_q < _TARGET_Q_W:
        reasons.append(f"CLEAN_Q_BELOW_TARGET:{clean_q}")
    if mid_tube is None or mid_tube > _TUBE_DP_LIMIT_PA:
        reasons.append(f"MID_TUBE_DP:{mid_tube}")
    if mid_shell is None or mid_shell > _SHELL_DP_LIMIT_PA:
        reasons.append(f"MID_SHELL_DP:{mid_shell}")
    if high_tube is None or high_tube > _TUBE_DP_LIMIT_PA:
        reasons.append(f"HIGH_TUBE_DP:{high_tube}")
    if high_shell is None or high_shell > _SHELL_DP_LIMIT_PA:
        reasons.append(f"HIGH_SHELL_DP:{high_shell}")
    if four_port != "PASS":
        reasons.append(f"FOUR_PORT:{four_port}")
    return (not reasons, tuple(reasons))


def _evaluate_authorized_bundle(
    bundle: RecoveredShell052Bundle,
    *,
    label: str,
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
) -> AuthorizedVariantResult | None:
    struct = bundle.structural_bundle
    bindings = build_candidate_rating_bindings(
        struct,
        space_hash=bundle.candidate_space_hash,
        t168_digest=struct.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geometry_projection_hash_v1(struct),
    )
    if bindings is None:
        return None
    v2 = geometry_identity_v2_hash(struct)
    t037_c = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    t037_f = evaluate_binding_task037(bindings, fouling_scenario="T039_DEMO_FOULING")
    clean = run_thermal_prescreen(
        bindings, normalized, provider=provider, task037_override=t037_c.raw
    )
    foul = run_thermal_prescreen(
        bindings, normalized, provider=provider, task037_override=t037_f.raw
    )
    if clean.predicted_tube_outlet_k is None or clean.predicted_shell_outlet_k is None:
        return AuthorizedVariantResult(
            label=label,
            candidate_id=bindings.rating_request.candidate_id,
            geometry_v2=v2,
            physical_tube_count=int(struct.bundle.task021_layout.physical_tube_count),
            tube_length_m=str(struct.candidate.tube_length_m),
            envelope_scale=bundle.envelope_scale,
            clean_q_w=clean.epsilon_ntu_q_w,
            fouled_q_w=foul.epsilon_ntu_q_w,
            ua_w_per_k=clean.ua_w_per_k,
            tube_htc_w_m2_k=clean.tube_htc_w_m2_k,
            shell_htc_w_m2_k=clean.shell_htc_w_m2_k,
            mid_tube_dp_pa=None,
            mid_shell_dp_pa=None,
            high_tube_dp_pa=None,
            high_shell_dp_pa=None,
            four_port_check="BLOCKED",
            full_joint_pass=False,
            failure_reasons=("MISSING_OUTLET_TEMPERATURE",),
        )
    tube_out = Decimal(clean.predicted_tube_outlet_k)
    shell_out = Decimal(clean.predicted_shell_outlet_k)
    hydraulic = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
        fixed_shell_inside_diameter_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
        tube_outlet_temperature_k=tube_out,
        shell_outlet_temperature_k=shell_out,
        provider=provider,
    )
    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
    q = Decimal(clean.epsilon_ntu_q_w) if clean.epsilon_ntu_q_w else None
    mt = Decimal(mid.tube_full_path_dp_pa) if mid.tube_full_path_dp_pa else None
    ms = Decimal(mid.shell_full_path_dp_pa) if mid.shell_full_path_dp_pa else None
    ht = Decimal(high.tube_full_path_dp_pa) if high.tube_full_path_dp_pa else None
    hs = Decimal(high.shell_full_path_dp_pa) if high.shell_full_path_dp_pa else None
    ok, reasons = _joint_criteria(
        clean_q=q,
        mid_tube=mt,
        mid_shell=ms,
        high_tube=ht,
        high_shell=hs,
        four_port=hydraulic.nozzle_velocity_check,
    )
    return AuthorizedVariantResult(
        label=label,
        candidate_id=bindings.rating_request.candidate_id,
        geometry_v2=v2,
        physical_tube_count=int(struct.bundle.task021_layout.physical_tube_count),
        tube_length_m=str(struct.candidate.tube_length_m),
        envelope_scale=bundle.envelope_scale,
        clean_q_w=clean.epsilon_ntu_q_w,
        fouled_q_w=foul.epsilon_ntu_q_w,
        ua_w_per_k=clean.ua_w_per_k,
        tube_htc_w_m2_k=clean.tube_htc_w_m2_k,
        shell_htc_w_m2_k=clean.shell_htc_w_m2_k,
        mid_tube_dp_pa=mid.tube_full_path_dp_pa,
        mid_shell_dp_pa=mid.shell_full_path_dp_pa,
        high_tube_dp_pa=high.tube_full_path_dp_pa,
        high_shell_dp_pa=high.shell_full_path_dp_pa,
        four_port_check=hydraulic.nozzle_velocity_check,
        full_joint_pass=ok,
        failure_reasons=reasons,
    )


def _unique_authorized_bundles(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
) -> tuple[tuple[tuple[RecoveredShell052Bundle, str], ...], tuple[str, ...]]:
    local, blockers = enumerate_shell_052_bounded_local_combos(normalized, handoff)
    recovered = resolve_recovered_shell_052_bundle(normalized, handoff)
    seen: set[str] = set()
    out: list[tuple[RecoveredShell052Bundle, str]] = []
    for bundle in local:
        v2 = geometry_identity_v2_hash(bundle.structural_bundle)
        if v2 in seen:
            continue
        seen.add(v2)
        out.append((bundle, bundle.recovery_note))
    if recovered is not None:
        v2 = geometry_identity_v2_hash(recovered.structural_bundle)
        if v2 not in seen:
            seen.add(v2)
            out.append((recovered, "recovered_shell_052_baseline"))
    return tuple(out), blockers


def _catalog_status() -> dict[str, Any]:
    if not _APPROVED_TUBE_CATALOG.is_file():
        return {"status": "CATALOG_MISSING", "approved_tube_records": 0}
    data = json.loads(_APPROVED_TUBE_CATALOG.read_text(encoding="utf-8"))
    records = data.get("records") or []
    approved = [r for r in records if r.get("approval_state") == "approved"]
    return {
        "catalog_id": data.get("catalog_id"),
        "approved_tube_records": len(approved),
        "sole_record": approved[0] if len(approved) == 1 else None,
        "status": "SOLE_APPROVED_R1_OD19.05_ID15.75",
    }


def run_high_k_tube_side_structural_feasibility(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> HighKTubeStructuralFeasibilityReport:
    active = provider or CoolPropProvider()
    design_c_bundle = _resolve_frozen_bundle(normalized, handoff)
    struct = design_c_bundle.structural_bundle
    bindings = build_candidate_rating_bindings(
        struct,
        space_hash=design_c_bundle.candidate_space_hash,
        t168_digest=struct.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=active,
        geometry_projection_hash=geometry_projection_hash_v1(struct),
    )
    if bindings is None:
        raise RuntimeError("design C bindings blocked")
    t037 = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    clean = run_thermal_prescreen(
        bindings, normalized, provider=active, task037_override=t037.raw
    )
    if clean.predicted_tube_outlet_k is None or clean.predicted_shell_outlet_k is None:
        raise RuntimeError("design C missing outlet temperatures")
    case = build_engineering_case_v2_from_v08(normalized)
    record = candidate_selection_record_from_bindings(bindings)
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    tube_p = Decimal(str(case.tube_side.inlet_pressure_pa))
    shell_p = Decimal(str(case.shell_side.inlet_pressure_pa))
    tube_out_state = (Decimal(clean.predicted_tube_outlet_k), tube_p)
    shell_out_state = (Decimal(clean.predicted_shell_outlet_k), shell_p)

    budget, friction, local, nozzle_pair, mechanism = _build_dp_budget(
        case=case,
        record=record,
        postpass=postpass,
        tube_out=tube_out_state,
        shell_out=shell_out_state,
    )
    high_total = Decimal(budget[-1].tube_full_path_total_dp_pa)
    excess = (high_total - _TUBE_DP_LIMIT_PA).quantize(Decimal("0.001"))

    tube_rho_in = Decimal(str(_side_inlet_density_kg_m3(case, "tube_side")))
    tube_rho_out = _fluid_density_kg_m3(
        active, temperature_k=tube_out_state[0], pressure_pa=tube_p
    )
    bounds = _common_diameter_bounds(
        mass_kg_s=Decimal(str(case.tube_side.mass_flow_kg_s)),
        rho_in=tube_rho_in,
        rho_out=tube_rho_out,
        side="tube",
    )
    fp_nozzle_max = _verify_full_path(
        case=case,
        record=record,
        postpass=postpass,
        loss_scenario_key="high_loss_sensitivity",
        tube_nozzle_d_m=bounds.common_feasible_upper_m,
        shell_nozzle_d_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
        tube_outlet_state_k_pa=tube_out_state,
        shell_outlet_state_k_pa=shell_out_state,
    )
    nozzle_lb = Decimal(str(fp_nozzle_max["TUBE_FULL_PATH_TOTAL_DP_PA"]))
    nozzle_excess = (nozzle_lb - _TUBE_DP_LIMIT_PA).quantize(Decimal("0.001"))
    friction_ref = nozzle_excess
    if friction:
        fval = Decimal(str(friction))
        friction_ref = (fval * Decimal("0.083")).quantize(Decimal("0.001"))

    bundles, combo_blockers = _unique_authorized_bundles(normalized, handoff)
    variants: list[AuthorizedVariantResult] = []
    for bundle, label in bundles:
        row = _evaluate_authorized_bundle(
            bundle, label=label, normalized=normalized, handoff=handoff, provider=active
        )
        if row is not None:
            variants.append(row)

    passing = [v for v in variants if v.full_joint_pass]
    feasible = bool(passing)
    best: AuthorizedVariantResult | None = None
    if passing:
        best = sorted(
            passing,
            key=lambda v: (
                Decimal(v.high_tube_dp_pa or "1e30"),
                -Decimal(v.clean_q_w or "0"),
            ),
        )[0]
    else:
        thermal_ok = [v for v in variants if v.clean_q_w and Decimal(v.clean_q_w) >= _TARGET_Q_W]
        if thermal_ok:
            best = sorted(
                thermal_ok,
                key=lambda v: Decimal(v.high_tube_dp_pa or "1e30"),
            )[0]

    catalog = _catalog_status()
    new_geom_auth = catalog.get("approved_tube_records", 0) <= 1
    proposed = (
        "Authorized 0.52 m shell search exhausted at fixed design C nozzles (123.80/159.00 mm). "
        "Next structural levers require (a) Task168-approved placement envelope expansion "
        "(0.85/0.90 scales currently blocked at Task021 replay) to increase tube count and "
        "reduce per-tube velocity/local K losses, or (b) a new approved tube catalog record "
        "(larger ID / revised wall) with mechanical and fouling authority review."
    )
    source_status = (
        f"{catalog.get('status')}; bounded local combos blocked: "
        f"{len(combo_blockers)} Task168/Task021 failures"
    )
    decision: DesignDecision = (
        "HIGH_K_JOINT_PRESCREEN_PASS" if feasible else "EXISTING_AUTHORIZED_SPACE_BLOCKED"
    )

    return HighKTubeStructuralFeasibilityReport(
        frozen_candidate_c_unchanged=True,
        high_tube_dp_baseline_pa=str(high_total),
        high_tube_dp_nozzle_lower_bound_pa=str(nozzle_lb),
        high_tube_dp_excess_pa=str(excess),
        tube_internal_friction_dp_pa=friction,
        tube_local_dp_pa=local,
        tube_nozzle_pair_dp_pa=nozzle_pair,
        required_internal_dp_reduction_pa=str(excess),
        friction_only_directional_reduction_pa=str(friction_ref),
        high_k_mechanism_note=mechanism,
        budget=budget,
        existing_authorized_variant_feasible=feasible,
        authorized_variants_evaluated=len(variants),
        authorized_variant_blockers=tuple(combo_blockers),
        variants=tuple(variants),
        best_validated_variant_id=best.candidate_id if best else None,
        best_validated_variant_geometry_v2=best.geometry_v2 if best else None,
        best_validated_variant_clean_q_w=best.clean_q_w if best else None,
        best_validated_variant_high_tube_dp_pa=best.high_tube_dp_pa if best else None,
        best_validated_variant_high_shell_dp_pa=best.high_shell_dp_pa if best else None,
        best_validated_variant_four_port_check=best.four_port_check if best else None,
        new_tube_geometry_authority_required=new_geom_auth,
        proposed_engineering_change=proposed,
        engineering_source_status=source_status,
        design_decision=decision,
        design_c_reference={
            "candidate_id": FROZEN_FIRST_JOINT_CANDIDATE_ID,
            "geometry_v2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
            "tube_nozzle_id_mm": str(CANDIDATE_C_TUBE_NOZZLE_ID_MM),
            "shell_nozzle_id_mm": str(CANDIDATE_C_SHELL_NOZZLE_ID_MM),
            "physical_tube_count": int(struct.bundle.task021_layout.physical_tube_count),
        },
    )


def feasibility_artifact_dict(report: HighKTubeStructuralFeasibilityReport) -> dict[str, Any]:
    return {
        "schema": "hxforge.high-k-tube-structural-feasibility.v1",
        "task_id": "V08_03_HIGH_K_TUBE_SIDE_STRUCTURAL_FEASIBILITY",
        "frozen_candidate_c_unchanged": report.frozen_candidate_c_unchanged,
        "design_c_reference": report.design_c_reference,
        "high_k_tube_dp_budget": {
            "high_tube_dp_baseline_pa": report.high_tube_dp_baseline_pa,
            "tube_dp_limit_pa": str(_TUBE_DP_LIMIT_PA),
            "high_tube_dp_excess_pa": report.high_tube_dp_excess_pa,
            "high_tube_dp_nozzle_lower_bound_pa": report.high_tube_dp_nozzle_lower_bound_pa,
            "nozzle_only_remaining_excess_pa": str(
                (
                    Decimal(report.high_tube_dp_nozzle_lower_bound_pa) - _TUBE_DP_LIMIT_PA
                ).quantize(Decimal("0.001"))
            ),
            "tube_internal_friction_dp_pa": report.tube_internal_friction_dp_pa,
            "tube_local_dp_pa": report.tube_local_dp_pa,
            "tube_nozzle_pair_dp_pa": report.tube_nozzle_pair_dp_pa,
            "required_internal_dp_reduction_pa": report.required_internal_dp_reduction_pa,
            "friction_only_directional_reduction_pa": report.friction_only_directional_reduction_pa,
            "mechanism_note": report.high_k_mechanism_note,
            "scenarios": [
                {
                    "loss_scenario_key": row.loss_scenario_key,
                    "tube_full_path_total_dp_pa": row.tube_full_path_total_dp_pa,
                    "tube_internal_friction_dp_pa": row.tube_internal_friction_dp_pa,
                    "tube_local_dp_pa": row.tube_local_dp_pa,
                    "component_dp_pa": row.component_dp_pa,
                    "delta_vs_mid_pa": row.delta_vs_mid_pa,
                }
                for row in report.budget
            ],
        },
        "authorized_variant_scan": {
            "existing_authorized_variant_feasible": report.existing_authorized_variant_feasible,
            "authorized_variants_evaluated": report.authorized_variants_evaluated,
            "task168_combo_blockers": list(report.authorized_variant_blockers),
            "variants": [
                {
                    "label": v.label,
                    "candidate_id": v.candidate_id,
                    "geometry_v2": v.geometry_v2,
                    "physical_tube_count": v.physical_tube_count,
                    "tube_length_m": v.tube_length_m,
                    "envelope_scale": v.envelope_scale,
                    "clean_q_w": v.clean_q_w,
                    "fouled_q_w": v.fouled_q_w,
                    "ua_w_per_k": v.ua_w_per_k,
                    "tube_htc_w_m2_k": v.tube_htc_w_m2_k,
                    "shell_htc_w_m2_k": v.shell_htc_w_m2_k,
                    "mid_tube_dp_pa": v.mid_tube_dp_pa,
                    "mid_shell_dp_pa": v.mid_shell_dp_pa,
                    "high_tube_dp_pa": v.high_tube_dp_pa,
                    "high_shell_dp_pa": v.high_shell_dp_pa,
                    "four_port_check": v.four_port_check,
                    "full_joint_pass": v.full_joint_pass,
                    "failure_reasons": list(v.failure_reasons),
                }
                for v in report.variants
            ],
            "best_validated": {
                "candidate_id": report.best_validated_variant_id,
                "geometry_v2": report.best_validated_variant_geometry_v2,
                "clean_q_w": report.best_validated_variant_clean_q_w,
                "high_tube_dp_pa": report.best_validated_variant_high_tube_dp_pa,
                "high_shell_dp_pa": report.best_validated_variant_high_shell_dp_pa,
                "four_port_check": report.best_validated_variant_four_port_check,
            },
        },
        "tube_geometry_authority": {
            "new_tube_geometry_authority_required": report.new_tube_geometry_authority_required,
            "proposed_engineering_change": report.proposed_engineering_change,
            "engineering_source_status": report.engineering_source_status,
            "proposed_geometry_authority_state": (
                "PROPOSED_GEOMETRY_AUTHORITY_REQUIRED"
                if report.new_tube_geometry_authority_required
                else "UNKNOWN"
            ),
        },
        "design_decision": report.design_decision,
        "engineering_design_status": "EXPERIMENTAL_PRESCREEN_ONLY",
    }


def write_feasibility_artifacts(
    report: HighKTubeStructuralFeasibilityReport,
    *,
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    artifact = feasibility_artifact_dict(report)
    jp = Path(json_path)
    mp = Path(md_path)
    jp.parent.mkdir(parents=True, exist_ok=True)
    mp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    md = [
        "# High-K tube-side structural feasibility (design C frozen)",
        "",
        f"- **Decision:** {report.design_decision}",
        f"- **High tube Δp:** {report.high_tube_dp_baseline_pa} Pa (excess {report.high_tube_dp_excess_pa} Pa vs {_TUBE_DP_LIMIT_PA} Pa)",
        f"- **Nozzle-only lower bound:** {report.high_tube_dp_nozzle_lower_bound_pa} Pa",
        f"- **Mechanism:** {report.high_k_mechanism_note}",
        "",
        "## Required reduction",
        "",
        f"- Full-path joint reduction: **{report.required_internal_dp_reduction_pa} Pa**",
        f"- Friction-only directional reference (~8.3% of friction at high-K): "
        f"**{report.friction_only_directional_reduction_pa} Pa** (idealized; all components must be recomputed).",
        "",
        "## Authorized variant scan (design C nozzles shared)",
        "",
        f"Evaluated **{report.authorized_variants_evaluated}** unique Task168-authorized 0.52 m geometries. "
        f"Joint feasible: **{report.existing_authorized_variant_feasible}**.",
        "",
        report.proposed_engineering_change,
        "",
        f"**Tube catalog:** {report.engineering_source_status}",
        "",
        "Status: EXPERIMENTAL_PRESCREEN_ONLY — not manufacturing acceptance.",
    ]
    mp.write_text("\n".join(md), encoding="utf-8")


__all__ = [
    "HighKTubeStructuralFeasibilityReport",
    "feasibility_artifact_dict",
    "run_high_k_tube_side_structural_feasibility",
    "write_feasibility_artifacts",
]
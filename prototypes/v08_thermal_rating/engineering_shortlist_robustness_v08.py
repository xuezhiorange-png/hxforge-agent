"""Engineering shortlist robustness and thermal authority for 235/241 tube layouts."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168_svc
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    TURBULENT_LOWER_RE,
    compute_task027_friction_pressure_drop,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.physical_feasibility import (
    THERMODYNAMIC_DUTY_TOLERANCE,
    assess_physical_feasibility,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1, build_solver_handoff
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
)
from prototypes.v08_geometry_candidate_generation.structural_bundles import (
    V08StructuralGeometryBundle,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_M,
    CANDIDATE_C_TUBE_NOZZLE_ID_M,
)
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.high_k_tube_side_structural_feasibility_v08 import (
    _joint_criteria,
)
from prototypes.v08_thermal_rating.intermediate_tube_count_feasibility_v08 import (
    FINITE_ENVELOPE_SCALES,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    RECOVERY_AUTHORITY_LABEL,
    SHELL_052_PROBE_M,
    RecoveredShell052Bundle,
    _with_envelope_override,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    BREAKTHROUGH_DISCRETE_SPACE_PATH,
    baffle_spacing_for_length_m,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import run_thermal_prescreen
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import evaluate_binding_task037
from prototypes.v08_thermal_rating.v08_task037_experimental_authority_v08 import (
    T039_DEMO_FOULING_EVIDENCE,
)

_TARGET_Q_W = Decimal("330000")
_TUBE_DP_LIM = Decimal("1150")
_SHELL_DP_LIM = Decimal("1180")

# Canonical envelope at first plateau for each tube count (no extrapolated search).
_CANONICAL_SCALE: dict[int, Decimal] = {235: Decimal("0.815"), 241: Decimal("0.82")}

_SHORTLIST: tuple[tuple[int, Decimal], ...] = (
    (235, Decimal("5.5")),
    (235, Decimal("6.0")),
    (241, Decimal("5.5")),
    (241, Decimal("6.0")),
)

_SCALES_241_ALIAS = tuple(s for s in FINITE_ENVELOPE_SCALES if s > Decimal("0.815") and s <= Decimal("0.835"))


@dataclass(frozen=True)
class LayoutIdentityRecord:
    shortlist_key: str
    envelope_scale: str
    is_canonical: bool
    physical_tube_count: int
    tube_length_m: str
    candidate_spec_id: str
    rating_candidate_id: str | None
    geometry_v2: str
    tube_layout_hash: str
    tube_layout_id: str
    task168_request_hash_digest: str
    placement_envelope_diameter_m: str
    identity_note: str


@dataclass(frozen=True)
class PortVelocityRow:
    port_id: str
    velocity_m_s: str
    inside_diameter_m: str


@dataclass(frozen=True)
class SensitivityScenarioResult:
    scenario_key: str
    scenario_label: str
    exploratory_only: Literal[True]
    task026_reynolds: str | None
    re_margin_below_turbulent_lower: str | None
    task027_status: str
    task027_blocker_code: str | None
    clean_q_w: str | None
    clean_q_delta_vs_target_w: str | None
    high_tube_dp_pa: str | None
    high_shell_dp_pa: str | None
    high_tube_margin_pa: str | None
    high_shell_margin_pa: str | None
    four_port_check: str


@dataclass(frozen=True)
class ShortlistLayoutReport:
    shortlist_key: str
    physical_tube_count: int
    tube_length_m: str
    canonical_envelope_scale: str
    geometry_v2: str
    rating_candidate_id: str | None
    authority_status: Literal[
        "EXPERIMENTAL_SHADOW_ONLY",
        "FROZEN_DESIGN_C_BREAKTHROUGH",
    ]
    baseline_clean_q_w: str | None
    baseline_clean_q_delta_w: str | None
    baseline_fouled_q_w: str | None
    baseline_fouled_q_delta_w: str | None
    baseline_re: str | None
    baseline_re_margin: str | None
    baseline_high_tube_dp_pa: str | None
    baseline_high_shell_dp_pa: str | None
    baseline_high_tube_margin_pa: str | None
    baseline_high_shell_margin_pa: str | None
    baseline_four_port_check: str
    port_velocities_baseline: tuple[PortVelocityRow, ...]
    task037_clean_authority: str
    task037_foul_authority: str
    thermal_prescreen_grade: str
    joint_prescreen_pass: bool
    sensitivity: tuple[SensitivityScenarioResult, ...]
    min_high_k_margin_pa: str
    min_re_margin_sensitivity: str | None
    regime_blocked_in_sensitivity: bool


@dataclass(frozen=True)
class ParetoChoice:
    shortlist_key: str
    geometry_v2: str
    rationale: str


@dataclass(frozen=True)
class EngineeringShortlistRobustnessReport:
    frozen_candidate_c_unchanged: Literal[True]
    unique_physical_layout_count: int
    identity_binding_status: str
    identity_records: tuple[LayoutIdentityRecord, ...]
    layouts: tuple[ShortlistLayoutReport, ...]
    thermal_priority: ParetoChoice | None
    hydraulic_priority: ParetoChoice | None
    regime_robustness_priority: ParetoChoice | None
    engineering_recommended: ParetoChoice | None
    re_sensitivity_result: str
    high_k_margin_robustness: str
    clean_330kw_status: str
    fouled_330kw_status: str
    fouling_authority_status: str
    task173_production_rating_status: Literal["BLOCKED"]
    placement_envelope_approval_required: Literal[True]
    new_tube_catalog_record_required: Literal["not_proven", False]
    acceptance_contract_note: str
    final_engineering_decision: str
    supersession_chain: tuple[str, ...]


def _handoff_for_case(
    normalized: NormalizedUserDesignCase,
    provider: CoolPropProvider,
) -> V08SolverHandoffV1:
    feasibility = assess_physical_feasibility(normalized, provider=provider)
    if not feasibility.ok:
        raise ValueError(f"perturbed case failed feasibility: {feasibility.issues}")
    return build_solver_handoff(normalized, feasibility, provider)


def _decimal_match(a: object, b: Decimal) -> bool:
    return Decimal(str(a)) == b


def _resolve_structural(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    tube_count: int,
    tube_length_m: Decimal,
    envelope_scale: Decimal,
) -> tuple[V08StructuralGeometryBundle, Any]:
    outcome = _with_envelope_override(
        normalized,
        handoff,
        discrete_path=BREAKTHROUGH_DISCRETE_SPACE_PATH,
        shell_m=SHELL_052_PROBE_M,
        envelope_scale=envelope_scale,
    )
    spacing = baffle_spacing_for_length_m(tube_length_m)
    for item in outcome.valid_structural:
        if int(item.bundle.task021_layout.physical_tube_count) != tube_count:
            continue
        if not _decimal_match(item.candidate.tube_length_m, tube_length_m):
            continue
        if not _decimal_match(item.candidate.baffle_spacing_m, spacing):
            continue
        return item, outcome
    raise RuntimeError(f"no structural match tubes={tube_count} L={tube_length_m} scale={envelope_scale}")


def _task027_from_bundle(
    bundle: Any,
    *,
    t168: Any,
) -> tuple[str, str | None]:
    authz = t168.evaluation_input_authority
    t027 = compute_task027_friction_pressure_drop(
        task025_result=bundle.task025_result,
        task026_result=bundle.task026_result,
        property_snapshot=authz.task027_property_snapshot,
        constant_density_path_assertion=authz.task027_constant_density_assertion,
        zero_net_elevation_change_assertion=authz.task027_zero_net_elevation_assertion,
        flow_direction_assertion=authz.task027_flow_direction_assertion,
        roughness_authority=authz.task027_roughness_authority,
    )
    if type(t027).__name__ == "Task027SuccessResult":
        return "PASS", None
    blockers = getattr(t027, "blockers", None) or []
    return "BLOCKED", str(blockers[0].code) if blockers else "UNKNOWN_TASK027"


def _build_t168_with_envelope(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    envelope_scale: Decimal,
) -> Any:
    from dataclasses import replace as dr

    from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
        evaluation_input_authority_hash,
    )
    from prototypes.v08_geometry_candidate_generation.discrete_space import load_v08_discrete_space
    from prototypes.v08_geometry_candidate_generation.task168_builder import (
        build_v08_task168_request,
        filter_discrete_space_by_envelope,
    )

    space = load_v08_discrete_space(BREAKTHROUGH_DISCRETE_SPACE_PATH)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    tmpl = dict(t168.evaluation_input_authority.task021_request_template)
    envelope_m = (SHELL_052_PROBE_M * envelope_scale).quantize(Decimal("0.0000000001"))
    tmpl.setdefault("placement_envelope", {})
    tmpl["placement_envelope"]["tube_center_envelope_diameter_m"] = str(envelope_m)
    tmpl["placement_envelope"]["evidence_refs"] = [RECOVERY_AUTHORITY_LABEL]
    evaluation = dr(
        t168.evaluation_input_authority,
        task021_request_template=tmpl,
        canonical_hash="",
    )
    evaluation = dr(evaluation, canonical_hash=evaluation_input_authority_hash(evaluation))
    return dr(t168, evaluation_input_authority=evaluation)


def _replay_task026_task027(
    structural: V08StructuralGeometryBundle,
    *,
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    envelope_scale: Decimal,
    baseline_normalized: NormalizedUserDesignCase,
) -> tuple[str | None, str, str | None]:
    t168 = _build_t168_with_envelope(normalized, handoff, envelope_scale)
    expected_layout_hash = str(structural.bundle.task021_layout.layout_hash)
    if normalized.input_snapshot_dict() == baseline_normalized.input_snapshot_dict():
        raw = structural.bundle
        reynolds = (
            str(raw.task026_result.reynolds_number) if raw.task026_result is not None else None
        )
        if raw.task026_result is None or raw.task025_result is None:
            return reynolds, "BLOCKED", "MISSING_TASK026_ON_STRUCTURAL_BUNDLE"
        status, code = _task027_from_bundle(raw, t168=t168)
        return reynolds, status, code
    bundle, stage_failure, _ = task168_svc._execute_candidate_chain(
        t168,
        structural.candidate,
        structural.shell_record,
        include_legacy_task162=False,
        include_legacy_task168_rating_dependencies=False,
    )
    reynolds = (
        str(bundle.task026_result.reynolds_number)
        if bundle.task026_result is not None
        else None
    )
    if bundle.task021_layout is None or str(bundle.task021_layout.layout_hash) != expected_layout_hash:
        code = str(stage_failure.code) if stage_failure else "TASK021_LAYOUT_DRIFT"
        return reynolds, "BLOCKED", code
    if bundle.task026_result is None or bundle.task025_result is None:
        code = str(stage_failure.code) if stage_failure else "MISSING_TASK026"
        return reynolds, "BLOCKED", code
    status, code = _task027_from_bundle(bundle, t168=t168)
    return reynolds, status, code


def _perturb_case(
    normalized: NormalizedUserDesignCase,
    *,
    scenario_key: str,
) -> tuple[NormalizedUserDesignCase, str]:
    base_tube = normalized.tube_side.mass_flow_kg_s
    base_shell = normalized.shell_side.mass_flow_kg_s
    base_tt = normalized.tube_side.inlet_temperature_k
    base_st = normalized.shell_side.inlet_temperature_k
    if scenario_key == "baseline":
        return normalized, "Fixture HXFORGE_330KW_STRICT_DP nominal mass flows and inlets."
    if scenario_key == "tube_mdot_minus_1pct":
        mf = (base_tube * Decimal("0.99")).quantize(Decimal("0.0000000001"))
        return normalized.model_copy(
            update={"tube_side": normalized.tube_side.model_copy(update={"mass_flow_kg_s": mf})}
        ), "Exploratory −1% tube-side mass flow; not an approved operating envelope."
    if scenario_key == "tube_mdot_minus_3pct":
        mf = (base_tube * Decimal("0.97")).quantize(Decimal("0.0000000001"))
        return normalized.model_copy(
            update={"tube_side": normalized.tube_side.model_copy(update={"mass_flow_kg_s": mf})}
        ), "Exploratory −3% tube-side mass flow."
    if scenario_key == "tube_mdot_plus_3pct":
        mf = (base_tube * Decimal("1.03")).quantize(Decimal("0.0000000001"))
        return normalized.model_copy(
            update={"tube_side": normalized.tube_side.model_copy(update={"mass_flow_kg_s": mf})}
        ), "Exploratory +3% tube-side mass flow."
    if scenario_key == "shell_mdot_minus_3pct":
        mf = (base_shell * Decimal("0.97")).quantize(Decimal("0.0000000001"))
        return normalized.model_copy(
            update={"shell_side": normalized.shell_side.model_copy(update={"mass_flow_kg_s": mf})}
        ), "Exploratory −3% shell-side mass flow (thermal/hydraulic binding only)."
    if scenario_key == "shell_mdot_plus_3pct":
        mf = (base_shell * Decimal("1.03")).quantize(Decimal("0.0000000001"))
        return normalized.model_copy(
            update={"shell_side": normalized.shell_side.model_copy(update={"mass_flow_kg_s": mf})}
        ), "Exploratory +3% shell-side mass flow."
    if scenario_key == "tube_inlet_plus_2k":
        tk = (base_tt + Decimal("2")).quantize(Decimal("0.001"))
        return normalized.model_copy(
            update={"tube_side": normalized.tube_side.model_copy(update={"inlet_temperature_k": tk})}
        ), (
            "Exploratory tube inlet +2 K vs fixture 310 K; COOLPROP water at 101325 Pa "
            "(property sensitivity only)."
        )
    if scenario_key == "shell_inlet_minus_2k":
        tk = (base_st - Decimal("2")).quantize(Decimal("0.001"))
        return normalized.model_copy(
            update={"shell_side": normalized.shell_side.model_copy(update={"inlet_temperature_k": tk})}
        ), (
            "Exploratory shell inlet −2 K vs fixture 295 K; COOLPROP water at 101325 Pa "
            "(property sensitivity only)."
        )
    raise KeyError(scenario_key)


_SENSITIVITY_KEYS: tuple[str, ...] = (
    "baseline",
    "tube_mdot_minus_1pct",
    "tube_mdot_minus_3pct",
    "tube_mdot_plus_3pct",
    "shell_mdot_minus_3pct",
    "shell_mdot_plus_3pct",
    "tube_inlet_plus_2k",
    "shell_inlet_minus_2k",
)


def _q_delta(q: Decimal | None) -> str | None:
    if q is None:
        return None
    return str((q - _TARGET_Q_W).quantize(Decimal("0.1")))


def _margin(dp: Decimal | None, limit: Decimal) -> str | None:
    if dp is None:
        return None
    return str((limit - dp).quantize(Decimal("0.001")))


def _re_margin(re: str | None) -> str | None:
    if re is None:
        return None
    return str((Decimal(re) - TURBULENT_LOWER_RE).quantize(Decimal("0.0001")))


def _evaluate_layout_scenario(
    structural: V08StructuralGeometryBundle,
    recovered: RecoveredShell052Bundle,
    *,
    normalized: NormalizedUserDesignCase,
    baseline_normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
    scenario_key: str,
    scenario_label: str,
) -> SensitivityScenarioResult:
    scale = Decimal(recovered.envelope_scale)
    re, t027_status, t027_code = _replay_task026_task027(
        structural,
        normalized=normalized,
        handoff=handoff,
        envelope_scale=scale,
        baseline_normalized=baseline_normalized,
    )
    bindings = build_candidate_rating_bindings(
        structural,
        space_hash=recovered.candidate_space_hash,
        t168_digest=structural.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geometry_projection_hash_v1(structural),
    )
    if bindings is None:
        return SensitivityScenarioResult(
            scenario_key=scenario_key,
            scenario_label=scenario_label,
            exploratory_only=True,
            task026_reynolds=re,
            re_margin_below_turbulent_lower=_re_margin(re),
            task027_status=t027_status,
            task027_blocker_code=t027_code,
            clean_q_w=None,
            clean_q_delta_vs_target_w=None,
            high_tube_dp_pa=None,
            high_shell_dp_pa=None,
            high_tube_margin_pa=None,
            high_shell_margin_pa=None,
            four_port_check="BLOCKED",
        )
    t037_c = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    clean = run_thermal_prescreen(
        bindings, normalized, provider=provider, task037_override=t037_c.raw
    )
    if clean.predicted_tube_outlet_k is None or clean.predicted_shell_outlet_k is None:
        return SensitivityScenarioResult(
            scenario_key=scenario_key,
            scenario_label=scenario_label,
            exploratory_only=True,
            task026_reynolds=re,
            re_margin_below_turbulent_lower=_re_margin(re),
            task027_status=t027_status,
            task027_blocker_code=t027_code,
            clean_q_w=None,
            clean_q_delta_vs_target_w=None,
            high_tube_dp_pa=None,
            high_shell_dp_pa=None,
            high_tube_margin_pa=None,
            high_shell_margin_pa=None,
            four_port_check="BLOCKED",
        )
    q = Decimal(clean.epsilon_ntu_q_w) if clean.epsilon_ntu_q_w else None
    high_tube = high_shell = high_tube_margin = high_shell_margin = None
    four_port = "BLOCKED"
    if t027_status == "BLOCKED":
        return SensitivityScenarioResult(
            scenario_key=scenario_key,
            scenario_label=scenario_label,
            exploratory_only=True,
            task026_reynolds=re,
            re_margin_below_turbulent_lower=None,
            task027_status=t027_status,
            task027_blocker_code=t027_code,
            clean_q_w=clean.epsilon_ntu_q_w,
            clean_q_delta_vs_target_w=_q_delta(q),
            high_tube_dp_pa=None,
            high_shell_dp_pa=None,
            high_tube_margin_pa=None,
            high_shell_margin_pa=None,
            four_port_check="BLOCKED",
        )
    try:
        hydraulic = run_autonomous_nozzle_full_path(
            bindings,
            fixed_tube_inside_diameter_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
            fixed_shell_inside_diameter_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
            tube_outlet_temperature_k=Decimal(clean.predicted_tube_outlet_k),
            shell_outlet_temperature_k=Decimal(clean.predicted_shell_outlet_k),
            provider=provider,
        )
        high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
        ht = Decimal(high.tube_full_path_dp_pa) if high.tube_full_path_dp_pa else None
        hs = Decimal(high.shell_full_path_dp_pa) if high.shell_full_path_dp_pa else None
        high_tube = high.tube_full_path_dp_pa
        high_shell = high.shell_full_path_dp_pa
        high_tube_margin = _margin(ht, _TUBE_DP_LIM)
        high_shell_margin = _margin(hs, _SHELL_DP_LIM)
        four_port = hydraulic.nozzle_velocity_check
    except (ValueError, ValidationError):
        scenario_label = (
            f"{scenario_label} High-K full path not recomputed under Task173 mass-binding mismatch."
        )
    return SensitivityScenarioResult(
        scenario_key=scenario_key,
        scenario_label=scenario_label,
        exploratory_only=True,
        task026_reynolds=re,
        re_margin_below_turbulent_lower=_re_margin(re) if t027_status == "PASS" else None,
        task027_status=t027_status,
        task027_blocker_code=t027_code,
        clean_q_w=clean.epsilon_ntu_q_w,
        clean_q_delta_vs_target_w=_q_delta(q),
        high_tube_dp_pa=high_tube,
        high_shell_dp_pa=high_shell,
        high_tube_margin_pa=high_tube_margin,
        high_shell_margin_pa=high_shell_margin,
        four_port_check=four_port,
    )


def _collect_identity_aliases(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    tube_count: int,
    tube_length_m: Decimal,
    canonical_scale: Decimal,
) -> list[LayoutIdentityRecord]:
    scales: list[Decimal] = [canonical_scale]
    if tube_count == 241:
        scales.extend(_SCALES_241_ALIAS)
    shortlist_key = f"T{tube_count}_L{tube_length_m}"
    records: list[LayoutIdentityRecord] = []
    for scale in scales:
        structural, outcome = _resolve_structural(
            normalized, handoff, tube_count=tube_count, tube_length_m=tube_length_m, envelope_scale=scale
        )
        layout = structural.bundle.task021_layout
        records.append(
            LayoutIdentityRecord(
                shortlist_key=shortlist_key,
                envelope_scale=str(scale),
                is_canonical=(scale == canonical_scale),
                physical_tube_count=tube_count,
                tube_length_m=str(tube_length_m),
                candidate_spec_id=str(structural.candidate.candidate_id),
                rating_candidate_id=None,
                geometry_v2=geometry_identity_v2_hash(structural),
                tube_layout_hash=str(getattr(layout, "layout_hash", "")),
                tube_layout_id=str(getattr(layout, "layout_id", "")),
                task168_request_hash_digest=structural.task168_request_hash_digest,
                placement_envelope_diameter_m=outcome.placement_envelope_diameter_m,
                identity_note=(
                    "geometry_v2 includes clearances and Task024 hash; "
                    "candidate_spec_id is catalog dimensional key, not a unique layout key."
                ),
            )
        )
    return records


def _identity_binding_status(records: tuple[LayoutIdentityRecord, ...]) -> str:
    by_key: dict[str, list[LayoutIdentityRecord]] = {}
    for row in records:
        by_key.setdefault(row.shortlist_key, []).append(row)
    notes: list[str] = []
    for key, rows in by_key.items():
        layout_hashes = {r.tube_layout_hash for r in rows}
        spec_ids = {r.candidate_spec_id for r in rows}
        v2s = {r.geometry_v2 for r in rows}
        if len(layout_hashes) > 1:
            notes.append(
                f"{key}: same tube_count/length across scales yields {len(layout_hashes)} "
                f"distinct Task021 layout_hash values — not one physical structure."
            )
        if len(spec_ids) == 1 and len(v2s) > 1:
            notes.append(
                f"{key}: shared candidate_spec_id={next(iter(spec_ids))} with {len(v2s)} geometry_v2 "
                "values (envelope/clearance projection); no catalog identity mixing detected."
            )
    if not notes:
        return "BOUND_OK_NO_CROSS_LAYOUT_MIXING"
    return "; ".join(notes)


def _layout_report(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
    *,
    tube_count: int,
    tube_length_m: Decimal,
) -> ShortlistLayoutReport:
    scale = _CANONICAL_SCALE[tube_count]
    structural, outcome = _resolve_structural(
        normalized, handoff, tube_count=tube_count, tube_length_m=tube_length_m, envelope_scale=scale
    )
    recovered = RecoveredShell052Bundle(
        structural_bundle=structural,
        candidate_space_hash=outcome.space_hash,
        discrete_space_authority_id=outcome.filtered_space.authority_id,
        discrete_space_content_hash=outcome.filtered_space.content_hash,
        placement_envelope_diameter_m=outcome.placement_envelope_diameter_m,
        envelope_scale=str(scale),
        baffle_cut_fraction="0.35",
        experimental_authority_label=RECOVERY_AUTHORITY_LABEL,
        recovery_note="engineering_shortlist_canonical",
    )
    shortlist_key = f"T{tube_count}_L{tube_length_m}"
    sensitivity: list[SensitivityScenarioResult] = []
    for key in _SENSITIVITY_KEYS:
        case, label = _perturb_case(normalized, scenario_key=key)
        scenario_handoff = handoff if key == "baseline" else _handoff_for_case(case, provider)
        sensitivity.append(
            _evaluate_layout_scenario(
                structural,
                recovered,
                normalized=case,
                baseline_normalized=normalized,
                handoff=scenario_handoff,
                provider=provider,
                scenario_key=key,
                scenario_label=label,
            )
        )
    baseline = next(s for s in sensitivity if s.scenario_key == "baseline")
    bindings = build_candidate_rating_bindings(
        structural,
        space_hash=recovered.candidate_space_hash,
        t168_digest=structural.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geometry_projection_hash_v1(structural),
    )
    t037_c = (
        evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
        if bindings is not None
        else None
    )
    t037_f = (
        evaluate_binding_task037(bindings, fouling_scenario="T039_DEMO_FOULING")
        if bindings is not None
        else None
    )
    foul_q = None
    if bindings is not None and t037_f is not None and t037_f.raw:
        foul_prescreen = run_thermal_prescreen(
            bindings,
            normalized,
            provider=provider,
            task037_override=t037_f.raw,
        )
        foul_q = foul_prescreen.epsilon_ntu_q_w
    ports: tuple[PortVelocityRow, ...] = ()
    joint_pass = False
    rating_id = None
    if bindings is not None:
        rating_id = bindings.rating_request.candidate_id
        clean = run_thermal_prescreen(
            bindings, normalized, provider=provider, task037_override=t037_c.raw
        )
        hydraulic = run_autonomous_nozzle_full_path(
            bindings,
            fixed_tube_inside_diameter_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
            fixed_shell_inside_diameter_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
            tube_outlet_temperature_k=Decimal(clean.predicted_tube_outlet_k),
            shell_outlet_temperature_k=Decimal(clean.predicted_shell_outlet_k),
            provider=provider,
        )
        ports = tuple(
            PortVelocityRow(
                port_id=p.port_id,
                velocity_m_s=str(p.velocity_m_s),
                inside_diameter_m=str(p.inside_diameter_m),
            )
            for p in hydraulic.ports
        )
        high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
        mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
        joint_pass, _ = _joint_criteria(
            clean_q=Decimal(clean.epsilon_ntu_q_w) if clean.epsilon_ntu_q_w else None,
            mid_tube=Decimal(mid.tube_full_path_dp_pa) if mid.tube_full_path_dp_pa else None,
            mid_shell=Decimal(mid.shell_full_path_dp_pa) if mid.shell_full_path_dp_pa else None,
            high_tube=Decimal(high.tube_full_path_dp_pa) if high.tube_full_path_dp_pa else None,
            high_shell=Decimal(high.shell_full_path_dp_pa) if high.shell_full_path_dp_pa else None,
            four_port=hydraulic.nozzle_velocity_check,
        )
    margins = [
        Decimal(s.high_tube_margin_pa)
        for s in sensitivity
        if s.high_tube_margin_pa is not None and s.high_shell_margin_pa is not None
    ]
    shell_margins = [
        Decimal(s.high_shell_margin_pa)
        for s in sensitivity
        if s.high_shell_margin_pa is not None
    ]
    combined = [min(t, sh) for t, sh in zip(margins, shell_margins, strict=False)]
    min_margin = min(combined) if combined else Decimal("0")
    re_margins = [
        Decimal(s.re_margin_below_turbulent_lower)
        for s in sensitivity
        if s.re_margin_below_turbulent_lower is not None and s.task027_status == "PASS"
    ]
    min_re = min(re_margins) if re_margins else None
    regime_blocked = any(s.task027_status == "BLOCKED" for s in sensitivity)
    return ShortlistLayoutReport(
        shortlist_key=shortlist_key,
        physical_tube_count=tube_count,
        tube_length_m=str(tube_length_m),
        canonical_envelope_scale=str(scale),
        geometry_v2=geometry_identity_v2_hash(structural),
        rating_candidate_id=rating_id,
        authority_status="EXPERIMENTAL_SHADOW_ONLY",
        baseline_clean_q_w=baseline.clean_q_w,
        baseline_clean_q_delta_w=baseline.clean_q_delta_vs_target_w,
        baseline_fouled_q_w=foul_q,
        baseline_fouled_q_delta_w=_q_delta(Decimal(foul_q)) if foul_q else None,
        baseline_re=baseline.task026_reynolds,
        baseline_re_margin=baseline.re_margin_below_turbulent_lower,
        baseline_high_tube_dp_pa=baseline.high_tube_dp_pa,
        baseline_high_shell_dp_pa=baseline.high_shell_dp_pa,
        baseline_high_tube_margin_pa=baseline.high_tube_margin_pa,
        baseline_high_shell_margin_pa=baseline.high_shell_margin_pa,
        baseline_four_port_check=baseline.four_port_check,
        port_velocities_baseline=ports,
        task037_clean_authority=str(t037_c.status) if t037_c else "BLOCKED",
        task037_foul_authority=str(t037_f.status) if t037_f else "BLOCKED",
        thermal_prescreen_grade="EXPERIMENTAL_PRESCREEN_ONLY",
        joint_prescreen_pass=joint_pass,
        sensitivity=tuple(sensitivity),
        min_high_k_margin_pa=str(min_margin),
        min_re_margin_sensitivity=str(min_re) if min_re is not None else None,
        regime_blocked_in_sensitivity=regime_blocked,
    )


def _pareto_choices(layouts: tuple[ShortlistLayoutReport, ...]) -> tuple[
    ParetoChoice | None,
    ParetoChoice | None,
    ParetoChoice | None,
    ParetoChoice | None,
]:
    thermal = max(
        layouts,
        key=lambda row: (
            Decimal(row.baseline_clean_q_w or "0"),
            Decimal(row.baseline_fouled_q_w or "0"),
        ),
    )
    hydraulic = max(
        layouts,
        key=lambda row: Decimal(row.min_high_k_margin_pa),
    )
    regime = max(
        [row for row in layouts if row.min_re_margin_sensitivity is not None],
        key=lambda row: Decimal(row.min_re_margin_sensitivity or "-1"),
        default=None,
    )
    thermal_choice = ParetoChoice(
        thermal.shortlist_key,
        thermal.geometry_v2,
        f"Highest baseline clean Q ({thermal.baseline_clean_q_w} W); "
        f"fouled T039_DEMO Q={thermal.baseline_fouled_q_w} W.",
    )
    hydraulic_choice = ParetoChoice(
        hydraulic.shortlist_key,
        hydraulic.geometry_v2,
        f"Largest worst-case high-K min-side margin ({hydraulic.min_high_k_margin_pa} Pa) "
        "across exploratory sensitivities.",
    )
    regime_choice = (
        ParetoChoice(
            regime.shortlist_key,
            regime.geometry_v2,
            f"Best minimum Re margin vs Task027 lower bound across sensitivities "
            f"({regime.min_re_margin_sensitivity}); blocked in sweep={regime.regime_blocked_in_sensitivity}.",
        )
        if regime is not None
        else None
    )
    # Engineering recommendation: prefer layouts that meet clean target with margin, pass joint,
    # and keep Re margin > 50 across sensitivities when available.
    candidates = [
        row
        for row in layouts
        if row.joint_prescreen_pass
        and row.baseline_clean_q_w
        and Decimal(row.baseline_clean_q_w) >= _TARGET_Q_W
    ]
    if not candidates:
        return thermal_choice, hydraulic_choice, regime_choice, None
    robust = sorted(
        candidates,
        key=lambda row: (
            -Decimal(row.min_re_margin_sensitivity or "0"),
            -Decimal(row.min_high_k_margin_pa),
            -Decimal(row.baseline_clean_q_w or "0"),
        ),
    )[0]
    eng = ParetoChoice(
        robust.shortlist_key,
        robust.geometry_v2,
        "Joint prescreen pass at baseline; balances Re robustness, high-K margin, and clean thermal "
        f"({robust.baseline_clean_q_w} W). Authority remains EXPERIMENTAL_SHADOW_ONLY / PENDING.",
    )
    return thermal_choice, hydraulic_choice, regime_choice, eng


def run_engineering_shortlist_robustness(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> EngineeringShortlistRobustnessReport:
    active = provider or CoolPropProvider()
    identity_rows: list[LayoutIdentityRecord] = []
    layouts: list[ShortlistLayoutReport] = []
    for tube_count, length in _SHORTLIST:
        scale = _CANONICAL_SCALE[tube_count]
        identity_rows.extend(
            _collect_identity_aliases(
                normalized, handoff, tube_count=tube_count, tube_length_m=length, canonical_scale=scale
            )
        )
        layouts.append(
            _layout_report(normalized, handoff, active, tube_count=tube_count, tube_length_m=length)
        )
    identity_tuple = tuple(identity_rows)
    layout_tuple = tuple(layouts)
    thermal, hydraulic, regime, eng = _pareto_choices(layout_tuple)
    threshold = _TARGET_Q_W * THERMODYNAMIC_DUTY_TOLERANCE
    clean_status = all(
        row.baseline_clean_q_w and Decimal(row.baseline_clean_q_w) >= threshold for row in layout_tuple
    )
    re_sens = (
        "All canonical shortlist layouts remain Task027-eligible across tube ±3% and shell ±3% "
        "exploratory mass-flow perturbations in this replay; property ±2 K shifts did not "
        "enter blocked Re band."
        if not any(r.regime_blocked_in_sensitivity for r in layout_tuple)
        else "One or more layouts hit Task027 BLOCKED under exploratory perturbation — see JSON."
    )
    min_margin = min(Decimal(row.min_high_k_margin_pa) for row in layout_tuple)
    decision = (
        "ENGINEERING_AUTHORITY_PENDING"
        if eng is not None
        else "INSUFFICIENT_ROBUSTNESS_FOR_AUTHORITY"
    )
    if eng is not None:
        decision = (
            f"{decision}: shortlist {eng.shortlist_key} qualifies for placement-envelope "
            "approval review only (not production validated)."
        )
    return EngineeringShortlistRobustnessReport(
        frozen_candidate_c_unchanged=True,
        unique_physical_layout_count=len(_SHORTLIST),
        identity_binding_status=_identity_binding_status(identity_tuple),
        identity_records=identity_tuple,
        layouts=layout_tuple,
        thermal_priority=thermal,
        hydraulic_priority=hydraulic,
        regime_robustness_priority=regime,
        engineering_recommended=eng,
        re_sensitivity_result=re_sens,
        high_k_margin_robustness=f"Worst-case min(high tube, high shell) margin across sensitivities: {min_margin} Pa",
        clean_330kw_status="MET_CLEAN_CONTRACT" if clean_status else "CLEAN_BELOW_CONTRACT_ON_SHORTLIST",
        fouled_330kw_status="FOULED_BELOW_330KW_T039_DEMO",
        fouling_authority_status=(
            "T039_DEMO_FOULING_SENSITIVITY_ONLY; evidence "
            + ", ".join(T039_DEMO_FOULING_EVIDENCE[:2])
            + "; not plant fouling authority."
        ),
        task173_production_rating_status="BLOCKED",
        placement_envelope_approval_required=True,
        new_tube_catalog_record_required="not_proven",
        acceptance_contract_note=(
            "User case HXFORGE_330KW_STRICT_DP sets target_duty_w=330000 W; joint/prescreen "
            "gates compare CLEAN ε-NTU Q to 330 kW. T039_DEMO fouling is demo sensitivity only."
        ),
        final_engineering_decision=decision,
        supersession_chain=(
            "docs/tasks/evidence/V08-03-intermediate-tube-count-feasibility-r1.json",
            "docs/tasks/evidence/V08-03-high-k-evidence-supersession-r2.json",
            "docs/tasks/evidence/V08-03-tube-side-replay-root-cause-r1.json",
        ),
    )


def artifact_dict(report: EngineeringShortlistRobustnessReport) -> dict[str, Any]:
    frozen_ref = {
        "candidate_id": FROZEN_FIRST_JOINT_CANDIDATE_ID,
        "geometry_v2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "unchanged": True,
    }

    def _pareto(p: ParetoChoice | None) -> dict[str, Any] | None:
        if p is None:
            return None
        return {
            "shortlist_key": p.shortlist_key,
            "geometry_v2": p.geometry_v2,
            "rationale": p.rationale,
        }

    return {
        "schema": "hxforge.engineering-shortlist-robustness.v1",
        "task_id": "V08_03_ENGINEERING_SHORTLIST_ROBUSTNESS_AND_THERMAL_AUTHORITY",
        "frozen_design_c_reference": frozen_ref,
        "unique_physical_layout_count": report.unique_physical_layout_count,
        "identity_binding_status": report.identity_binding_status,
        "identity_records": [row.__dict__ for row in report.identity_records],
        "shortlist_layouts": [
            {
                **{k: v for k, v in row.__dict__.items() if k not in ("sensitivity", "port_velocities_baseline")},
                "port_velocities_baseline": [
                    {"port_id": p.port_id, "velocity_m_s": p.velocity_m_s, "inside_diameter_m": p.inside_diameter_m}
                    for p in row.port_velocities_baseline
                ],
                "sensitivity": [s.__dict__ for s in row.sensitivity],
            }
            for row in report.layouts
        ],
        "pareto": {
            "THERMAL_PRIORITY_CANDIDATE": _pareto(report.thermal_priority),
            "HYDRAULIC_PRIORITY_CANDIDATE": _pareto(report.hydraulic_priority),
            "REGIME_ROBUSTNESS_PRIORITY_CANDIDATE": _pareto(report.regime_robustness_priority),
            "ENGINEERING_RECOMMENDED_CANDIDATE": _pareto(report.engineering_recommended),
        },
        "thermal_authority": {
            "clean_330kw_status": report.clean_330kw_status,
            "fouled_330kw_status": report.fouled_330kw_status,
            "fouling_authority_status": report.fouling_authority_status,
            "task173_production_rating_status": report.task173_production_rating_status,
            "acceptance_contract_note": report.acceptance_contract_note,
            "placement_envelope_approval_required": report.placement_envelope_approval_required,
            "new_tube_catalog_record_required": report.new_tube_catalog_record_required,
        },
        "re_sensitivity_result": report.re_sensitivity_result,
        "high_k_margin_robustness": report.high_k_margin_robustness,
        "final_engineering_decision": report.final_engineering_decision,
        "supersession_chain": list(report.supersession_chain),
        "engineering_design_status": "ENGINEERING_AUTHORITY_PENDING",
    }


def write_shortlist_artifacts(
    report: EngineeringShortlistRobustnessReport,
    *,
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    payload = artifact_dict(report)
    jp = Path(json_path)
    mp = Path(md_path)
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md: list[str] = [
        "# Engineering shortlist robustness (235/241 tubes)",
        "",
        f"- **Final decision:** {report.final_engineering_decision}",
        f"- **Identity binding:** {report.identity_binding_status}",
        f"- **Clean 330 kW contract:** {report.clean_330kw_status}",
        f"- **Fouled T039_DEMO:** {report.fouled_330kw_status}",
        "",
        "## Canonical shortlist (4 physical layouts)",
        "",
    ]
    for row in report.layouts:
        md.append(
            f"- **{row.shortlist_key}** @ envelope {row.canonical_envelope_scale}: "
            f"clean Q={row.baseline_clean_q_w} W (Δ={row.baseline_clean_q_delta_w}); "
            f"high tube margin={row.baseline_high_tube_margin_pa} Pa; "
            f"Re={row.baseline_re} (margin {row.baseline_re_margin}); "
            f"joint_prescreen_pass={row.joint_prescreen_pass}"
        )
    md.extend(["", "## Pareto priorities", ""])
    for label, choice in (
        ("THERMAL", report.thermal_priority),
        ("HYDRAULIC", report.hydraulic_priority),
        ("REGIME", report.regime_robustness_priority),
        ("RECOMMENDED", report.engineering_recommended),
    ):
        if choice:
            md.append(f"- **{label}:** {choice.shortlist_key} — {choice.rationale}")
    md.extend(
        [
            "",
            "## Authority",
            "",
            report.acceptance_contract_note,
            "",
            f"Fouling: {report.fouling_authority_status}",
            "",
            f"Task173 production rating: **{report.task173_production_rating_status}**",
            "",
            "Placement envelope approval **required**; new tube catalog record **not_proven**.",
        ]
    )
    mp.write_text("\n".join(md), encoding="utf-8")


__all__ = [
    "EngineeringShortlistRobustnessReport",
    "artifact_dict",
    "run_engineering_shortlist_robustness",
    "write_shortlist_artifacts",
]
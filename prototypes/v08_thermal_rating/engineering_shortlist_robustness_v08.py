"""Engineering shortlist robustness and thermal authority for 235/241 tube layouts."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168_svc
from hexagent.exchangers.shell_tube.manufacturable_candidates.service import (
    build_raw_tube_side_request_envelope,
)
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    TURBULENT_LOWER_RE,
    compute_task027_friction_pressure_drop,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    compute_tube_side_heat_transfer_coefficient,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.request import TubeSideThermalRequest
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
from prototypes.v08_thermal_rating.task173_mass_binding_boundary_v08 import (
    task173_mass_binding_boundary_report,
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

_SCALES_241_ALIAS = tuple(
    s for s in FINITE_ENVELOPE_SCALES if s > Decimal("0.815") and s <= Decimal("0.835")
)


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


RobustnessEvidenceStatus = Literal[
    "VERIFIED_ROBUST",
    "REPLAY_TASK026_TASK027_VERIFIED",
    "VERIFIED_NOT_ROBUST",
    "REPLAY_BINDING_BLOCKED",
    "PHYSICAL_MODEL_APPLICABILITY_BLOCKED",
    "HYDRAULIC_SENSITIVITY_NOT_VERIFIED",
    "INSUFFICIENT_EVIDENCE",
]

LayoutEngineeringStatus = Literal[
    "BASELINE_PRESCREEN_PASS",
    "OPERATING_RANGE_THERMAL_FAIL",
    "PHYSICAL_MODEL_APPLICABILITY_BLOCKED",
    "HYDRAULIC_SENSITIVITY_NOT_VERIFIED",
    "ROBUST_CANDIDATE_PROVEN",
    "NO_ROBUST_CANDIDATE_PROVEN",
]


@dataclass(frozen=True)
class SensitivityBindingAudit:
    normalized_input_hash: str
    handoff_normalized_input_hash: str
    tube_mass_flow_kg_s: str
    shell_mass_flow_kg_s: str
    tube_inlet_temperature_k: str
    shell_inlet_temperature_k: str
    evaluation_input_authority_hash: str
    candidate_spec_id: str
    task021_layout_hash_expected: str
    task021_layout_hash_observed: str
    task021_physical_tube_count: int
    task025_result_id: str | None
    task026_result_id: str | None
    task026_reynolds_number: str | None
    task027_raw_blocker_code: str | None
    task168_stage_failure_code: str | None
    task168_stage_failure_field_path: str | None
    task173_binding_state: str
    replay_mode: str
    re_scaling_diagnostic: str | None


@dataclass(frozen=True)
class SensitivityScenarioResult:
    scenario_key: str
    scenario_label: str
    exploratory_only: Literal[True]
    robustness_evidence_status: RobustnessEvidenceStatus
    task026_reynolds: str | None
    re_margin_below_turbulent_lower: str | None
    task027_status: str
    task027_blocker_code: str | None
    task027_raw_blocker_code: str | None
    task168_wrapper_code: str | None
    clean_q_w: str | None
    clean_q_delta_vs_target_w: str | None
    high_tube_dp_pa: str | None
    high_shell_dp_pa: str | None
    high_tube_margin_pa: str | None
    high_shell_margin_pa: str | None
    high_k_dp_computed: bool
    four_port_check: str
    binding_audit: SensitivityBindingAudit


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
    min_verified_clean_q_w: str | None
    mass_flow_high_k_computed_count: int
    thermal_operating_range_status: str
    engineering_layout_status: LayoutEngineeringStatus


@dataclass(frozen=True)
class ParetoChoice:
    shortlist_key: str
    geometry_v2: str
    rationale: str


@dataclass(frozen=True)
class EngineeringShortlistRobustnessReport:
    frozen_candidate_c_unchanged: Literal[True]
    canonical_shortlist_size: int
    distinct_audited_layout_hash_count: int
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
    sensitivity_binding_root_cause: str
    layout_identity_drift_confirmed: bool
    replay_binding_defect_confirmed: Literal[True]
    robustness_evidence_valid: bool
    nonbaseline_scenarios_valid: int
    nonbaseline_scenarios_blocked: int
    nonbaseline_high_k_dp_computed: int
    layout_status_by_key: dict[str, str]
    layout_engineering_status_by_key: dict[str, LayoutEngineeringStatus]
    engineering_acceptance_status: str
    robust_candidate_proven: bool
    thermal_sensitivity_status: str
    task173_mass_binding_root_cause: str
    task173_experimental_replay_feasible: bool
    nonbaseline_mass_flow_high_k_coverage: str


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
    raise RuntimeError(
        f"no structural match tubes={tube_count} L={tube_length_m} scale={envelope_scale}"
    )


def _task027_raw(
    *,
    task025_result: Any,
    task026_result: Any,
    t168: Any,
) -> tuple[str, str | None]:
    authz = t168.evaluation_input_authority
    t027 = compute_task027_friction_pressure_drop(
        task025_result=task025_result,
        task026_result=task026_result,
        property_snapshot=authz.task027_property_snapshot,
        constant_density_path_assertion=authz.task027_constant_density_assertion,
        zero_net_elevation_change_assertion=authz.task027_zero_net_elevation_assertion,
        flow_direction_assertion=authz.task027_flow_direction_assertion,
        roughness_authority=authz.task027_roughness_authority,
    )
    if type(t027).__name__ == "Task027SuccessResult":
        return "PASS", None
    blockers = getattr(t027, "blockers", None) or []
    raw = str(blockers[0].code) if blockers else "UNKNOWN_TASK027"
    return "BLOCKED", raw


def _tube_side_flow_or_property_perturbed(scenario_key: str) -> bool:
    return scenario_key in (
        "tube_mdot_minus_1pct",
        "tube_mdot_minus_3pct",
        "tube_mdot_plus_3pct",
        "tube_inlet_plus_2k",
        "shell_inlet_minus_2k",
    )


def _resolve_task026_request(t168: Any) -> TubeSideThermalRequest:
    raw = t168.evaluation_input_authority.task026_request
    if isinstance(raw, TubeSideThermalRequest):
        return raw
    built = build_raw_tube_side_request_envelope(task168_svc._public_value(raw))
    if not isinstance(built, TubeSideThermalRequest):
        raise ValueError("task026_request could not be materialized")
    return built


def _re_scaling_diagnostic(baseline_re: str | None, scenario_key: str) -> str | None:
    if baseline_re is None or scenario_key == "baseline":
        return None
    base = Decimal(baseline_re)
    factors = {
        "tube_mdot_minus_1pct": Decimal("0.99"),
        "tube_mdot_minus_3pct": Decimal("0.97"),
        "tube_mdot_plus_3pct": Decimal("1.03"),
    }
    factor = factors.get(scenario_key)
    if factor is None:
        return "No mass-flow scaling diagnostic for this scenario (shell-only or property shift)."
    expected = (base * factor).quantize(Decimal("0.0001"))
    return (
        f"Constant-property diagnostic Re≈{expected} at "
        f"{factor * 100:.2f}% tube mass flow; not a substitute for Task026."
    )


def _fixed_layout_tube_side_replay(
    structural: V08StructuralGeometryBundle,
    *,
    t168: Any,
    scenario_key: str,
    baseline_re: str | None,
) -> tuple[Any | None, Any | None, str | None, str, str | None]:
    """Rerun Task026/027 only; Task021 layout is frozen from canonical enumeration."""
    raw = structural.bundle
    layout_hash = str(raw.task021_layout.layout_hash)
    t025 = raw.task025_result
    if t025 is None:
        return None, None, None, "BLOCKED", "MISSING_TASK025_ON_STRUCTURAL_BUNDLE"
    if _tube_side_flow_or_property_perturbed(scenario_key):
        task026_request = _resolve_task026_request(t168)
        t026 = compute_tube_side_heat_transfer_coefficient(task026_request, t025)
    else:
        t026 = raw.task026_result
    if t026 is None:
        return t025, None, None, "BLOCKED", "MISSING_TASK026"
    reynolds = str(getattr(t026, "reynolds_number", "")) or None
    status, raw_code = _task027_raw(task025_result=t025, task026_result=t026, t168=t168)
    if (
        scenario_key.startswith("shell_mdot")
        and baseline_re is not None
        and reynolds != baseline_re
    ):
        return (
            t025,
            t026,
            reynolds,
            "BLOCKED",
            "REPLAY_BINDING_TUBE_RE_DRIFT_UNDER_SHELL_ONLY_PERTURBATION",
        )
    # observed layout is frozen
    _ = layout_hash
    return t025, t026, reynolds, status, raw_code


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


def _build_binding_audit(
    *,
    structural: V08StructuralGeometryBundle,
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    t168: Any,
    scenario_key: str,
    baseline_re: str | None,
    t025: Any | None,
    t026: Any | None,
    reynolds: str | None,
    t027_status: str,
    t027_raw: str | None,
    task173_state: str,
) -> SensitivityBindingAudit:
    raw = structural.bundle
    layout = raw.task021_layout
    return SensitivityBindingAudit(
        normalized_input_hash=canonical_sha256(normalized.input_snapshot_dict()),
        handoff_normalized_input_hash=handoff.normalized_input_hash,
        tube_mass_flow_kg_s=str(normalized.tube_side.mass_flow_kg_s),
        shell_mass_flow_kg_s=str(normalized.shell_side.mass_flow_kg_s),
        tube_inlet_temperature_k=str(normalized.tube_side.inlet_temperature_k),
        shell_inlet_temperature_k=str(normalized.shell_side.inlet_temperature_k),
        evaluation_input_authority_hash=str(t168.evaluation_input_authority.canonical_hash),
        candidate_spec_id=str(structural.candidate.candidate_id),
        task021_layout_hash_expected=str(layout.layout_hash),
        task021_layout_hash_observed=str(layout.layout_hash),
        task021_physical_tube_count=int(layout.physical_tube_count),
        task025_result_id=getattr(t025, "result_id", None) if t025 is not None else None,
        task026_result_id=getattr(t026, "result_id", None) if t026 is not None else None,
        task026_reynolds_number=reynolds,
        task027_raw_blocker_code=t027_raw,
        task168_stage_failure_code=None,
        task168_stage_failure_field_path=None,
        task173_binding_state=task173_state,
        replay_mode="FIXED_TASK021_LAYOUT_TASK026_RERUN",
        re_scaling_diagnostic=_re_scaling_diagnostic(baseline_re, scenario_key),
    )


def _robustness_status(
    *,
    scenario_key: str,
    t027_status: str,
    t027_raw: str | None,
    high_k_computed: bool,
    bindings_ok: bool,
) -> RobustnessEvidenceStatus:
    if t027_raw == "REPLAY_BINDING_TUBE_RE_DRIFT_UNDER_SHELL_ONLY_PERTURBATION":
        return "REPLAY_BINDING_BLOCKED"
    if t027_status == "BLOCKED" and t027_raw == "BL_T027_UNSUPPORTED_REYNOLDS_REGIME":
        return "PHYSICAL_MODEL_APPLICABILITY_BLOCKED"
    if t027_status == "BLOCKED":
        return "INSUFFICIENT_EVIDENCE"
    if not bindings_ok:
        return "REPLAY_BINDING_BLOCKED"
    if t027_status == "PASS":
        if high_k_computed:
            return "VERIFIED_ROBUST"
        if scenario_key.startswith(("tube_mdot_", "shell_mdot_")):
            return "HYDRAULIC_SENSITIVITY_NOT_VERIFIED"
        if scenario_key == "baseline":
            return "VERIFIED_ROBUST" if high_k_computed else "INSUFFICIENT_EVIDENCE"
        return "REPLAY_TASK026_TASK027_VERIFIED"
    return "VERIFIED_NOT_ROBUST"


_MASS_FLOW_SCENARIOS = frozenset(
    {
        "tube_mdot_minus_1pct",
        "tube_mdot_minus_3pct",
        "tube_mdot_plus_3pct",
        "shell_mdot_minus_3pct",
        "shell_mdot_plus_3pct",
    }
)


def _layout_engineering_status(
    row: ShortlistLayoutReport,
    *,
    target_q_w: Decimal,
) -> LayoutEngineeringStatus:
    if row.regime_blocked_in_sensitivity:
        return "PHYSICAL_MODEL_APPLICABILITY_BLOCKED"
    if not row.joint_prescreen_pass:
        return "NO_ROBUST_CANDIDATE_PROVEN"
    sweeping_q = [
        s
        for s in row.sensitivity
        if s.scenario_key in _MASS_FLOW_SCENARIOS and s.clean_q_w is not None
    ]
    below = [
        s for s in sweeping_q if Decimal(s.clean_q_w) * THERMODYNAMIC_DUTY_TOLERANCE < target_q_w
    ]
    if below:
        return "OPERATING_RANGE_THERMAL_FAIL"
    if row.mass_flow_high_k_computed_count == 0:
        return "HYDRAULIC_SENSITIVITY_NOT_VERIFIED"
    return "BASELINE_PRESCREEN_PASS"


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
            update={
                "tube_side": normalized.tube_side.model_copy(update={"inlet_temperature_k": tk})
            }
        ), (
            "Exploratory tube inlet +2 K vs fixture 310 K; COOLPROP water at 101325 Pa "
            "(property sensitivity only)."
        )
    if scenario_key == "shell_inlet_minus_2k":
        tk = (base_st - Decimal("2")).quantize(Decimal("0.001"))
        return normalized.model_copy(
            update={
                "shell_side": normalized.shell_side.model_copy(update={"inlet_temperature_k": tk})
            }
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
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
    scenario_key: str,
    scenario_label: str,
    baseline_re: str | None,
) -> SensitivityScenarioResult:
    scale = Decimal(recovered.envelope_scale)
    t168 = _build_t168_with_envelope(normalized, handoff, scale)
    _, t026, re, t027_status, t027_raw = _fixed_layout_tube_side_replay(
        structural,
        t168=t168,
        scenario_key=scenario_key,
        baseline_re=baseline_re,
    )
    t025 = structural.bundle.task025_result
    task173_state = "NOT_ATTEMPTED"
    bindings = build_candidate_rating_bindings(
        structural,
        space_hash=recovered.candidate_space_hash,
        t168_digest=structural.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geometry_projection_hash_v1(structural),
    )
    bindings_ok = bindings is not None
    if not bindings_ok:
        task173_state = "BINDINGS_BLOCKED"
        audit = _build_binding_audit(
            structural=structural,
            normalized=normalized,
            handoff=handoff,
            t168=t168,
            scenario_key=scenario_key,
            baseline_re=baseline_re,
            t025=t025,
            t026=t026,
            reynolds=re,
            t027_status=t027_status,
            t027_raw=t027_raw,
            task173_state=task173_state,
        )
        status = _robustness_status(
            scenario_key=scenario_key,
            t027_status=t027_status,
            t027_raw=t027_raw,
            high_k_computed=False,
            bindings_ok=False,
        )
        wrapper = "TUBE_SIDE_REPLAY_FAILED" if t027_raw else None
        return SensitivityScenarioResult(
            scenario_key=scenario_key,
            scenario_label=scenario_label,
            exploratory_only=True,
            robustness_evidence_status=status,
            task026_reynolds=re,
            re_margin_below_turbulent_lower=_re_margin(re) if t027_status == "PASS" else None,
            task027_status=t027_status,
            task027_blocker_code=t027_raw,
            task027_raw_blocker_code=t027_raw,
            task168_wrapper_code=wrapper,
            clean_q_w=None,
            clean_q_delta_vs_target_w=None,
            high_tube_dp_pa=None,
            high_shell_dp_pa=None,
            high_tube_margin_pa=None,
            high_shell_margin_pa=None,
            high_k_dp_computed=False,
            four_port_check="BLOCKED",
            binding_audit=audit,
        )
    t037_c = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    clean = run_thermal_prescreen(
        bindings, normalized, provider=provider, task037_override=t037_c.raw
    )
    q = Decimal(clean.epsilon_ntu_q_w) if clean.epsilon_ntu_q_w else None
    high_tube = high_shell = high_tube_margin = high_shell_margin = None
    four_port = "BLOCKED"
    high_k_computed = False
    task173_state = "BINDINGS_OK"
    if clean.predicted_tube_outlet_k is not None and clean.predicted_shell_outlet_k is not None:
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
            high_k_computed = high_tube is not None and high_shell is not None
            task173_state = "FULL_PATH_COMPUTED"
        except (ValueError, ValidationError):
            task173_state = "TASK173_MASS_BINDING_REJECTED"
            scenario_label = f"{scenario_label} High-K full path not available (Task173 case binding holds baseline mass)."
    audit = _build_binding_audit(
        structural=structural,
        normalized=normalized,
        handoff=handoff,
        t168=t168,
        scenario_key=scenario_key,
        baseline_re=baseline_re,
        t025=t025,
        t026=t026,
        reynolds=re,
        t027_status=t027_status,
        t027_raw=t027_raw,
        task173_state=task173_state,
    )
    evidence = _robustness_status(
        scenario_key=scenario_key,
        t027_status=t027_status,
        t027_raw=t027_raw,
        high_k_computed=high_k_computed,
        bindings_ok=True,
    )
    return SensitivityScenarioResult(
        scenario_key=scenario_key,
        scenario_label=scenario_label,
        exploratory_only=True,
        robustness_evidence_status=evidence,
        task026_reynolds=re,
        re_margin_below_turbulent_lower=_re_margin(re) if t027_status == "PASS" else None,
        task027_status=t027_status,
        task027_blocker_code=t027_raw,
        task027_raw_blocker_code=t027_raw,
        task168_wrapper_code=None,
        clean_q_w=clean.epsilon_ntu_q_w,
        clean_q_delta_vs_target_w=_q_delta(q),
        high_tube_dp_pa=high_tube,
        high_shell_dp_pa=high_shell,
        high_tube_margin_pa=high_tube_margin,
        high_shell_margin_pa=high_shell_margin,
        high_k_dp_computed=high_k_computed,
        four_port_check=four_port,
        binding_audit=audit,
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
            normalized,
            handoff,
            tube_count=tube_count,
            tube_length_m=tube_length_m,
            envelope_scale=scale,
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
        normalized,
        handoff,
        tube_count=tube_count,
        tube_length_m=tube_length_m,
        envelope_scale=scale,
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
    baseline_re = (
        str(structural.bundle.task026_result.reynolds_number)
        if structural.bundle.task026_result is not None
        else None
    )
    sensitivity: list[SensitivityScenarioResult] = []
    for key in _SENSITIVITY_KEYS:
        case, label = _perturb_case(normalized, scenario_key=key)
        scenario_handoff = handoff if key == "baseline" else _handoff_for_case(case, provider)
        sensitivity.append(
            _evaluate_layout_scenario(
                structural,
                recovered,
                normalized=case,
                handoff=scenario_handoff,
                provider=provider,
                scenario_key=key,
                scenario_label=label,
                baseline_re=baseline_re,
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
    verified_dp = [
        s
        for s in sensitivity
        if s.robustness_evidence_status == "VERIFIED_ROBUST"
        and s.high_k_dp_computed
        and s.high_tube_margin_pa is not None
        and s.high_shell_margin_pa is not None
    ]
    combined = [
        min(Decimal(s.high_tube_margin_pa), Decimal(s.high_shell_margin_pa)) for s in verified_dp
    ]
    min_margin = min(combined) if combined else Decimal("0")
    re_margins = [
        Decimal(s.re_margin_below_turbulent_lower)
        for s in sensitivity
        if s.re_margin_below_turbulent_lower is not None
        and s.robustness_evidence_status
        in ("VERIFIED_ROBUST", "VERIFIED_NOT_ROBUST", "PHYSICAL_MODEL_APPLICABILITY_BLOCKED")
    ]
    min_re = min(re_margins) if re_margins else None
    regime_blocked = any(
        s.robustness_evidence_status == "PHYSICAL_MODEL_APPLICABILITY_BLOCKED"
        for s in sensitivity
        if s.scenario_key != "baseline"
    )
    verified_q = [
        Decimal(s.clean_q_w)
        for s in sensitivity
        if s.clean_q_w is not None
        and s.robustness_evidence_status
        in (
            "VERIFIED_ROBUST",
            "REPLAY_TASK026_TASK027_VERIFIED",
            "HYDRAULIC_SENSITIVITY_NOT_VERIFIED",
        )
    ]
    min_q = min(verified_q) if verified_q else None
    mass_hk = sum(
        1
        for s in sensitivity
        if s.scenario_key in _MASS_FLOW_SCENARIOS
        and s.robustness_evidence_status == "VERIFIED_ROBUST"
    )
    tube_sweeps = [
        s for s in sensitivity if s.scenario_key in _MASS_FLOW_SCENARIOS and s.clean_q_w is not None
    ]
    below_330 = any(
        Decimal(s.clean_q_w) * THERMODYNAMIC_DUTY_TOLERANCE < _TARGET_Q_W for s in tube_sweeps
    )
    thermal_range = (
        "TUBE_OR_SHELL_MDOT_SWEEP_BELOW_330KW"
        if below_330
        else "TUBE_OR_SHELL_MDOT_SWEEP_AT_OR_ABOVE_330KW"
    )
    draft_row = ShortlistLayoutReport(
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
        min_verified_clean_q_w=str(min_q) if min_q is not None else None,
        mass_flow_high_k_computed_count=mass_hk,
        thermal_operating_range_status=thermal_range,
        engineering_layout_status="NO_ROBUST_CANDIDATE_PROVEN",
    )
    eng_st = _layout_engineering_status(draft_row, target_q_w=_TARGET_Q_W)
    return ShortlistLayoutReport(**{**draft_row.__dict__, "engineering_layout_status": eng_st})


def _pareto_choices(
    layouts: tuple[ShortlistLayoutReport, ...],
) -> tuple[
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
        key=lambda row: min(
            Decimal(row.baseline_high_tube_margin_pa or "0"),
            Decimal(row.baseline_high_shell_margin_pa or "0"),
        ),
    )
    regime_pool = [
        row
        for row in layouts
        if not row.regime_blocked_in_sensitivity and row.min_re_margin_sensitivity is not None
    ]
    regime = (
        max(
            regime_pool,
            key=lambda row: Decimal(row.min_re_margin_sensitivity or "-1"),
        )
        if regime_pool
        else None
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
        (
            f"Largest baseline high-K min-side margin "
            f"({hydraulic.baseline_high_tube_margin_pa} Pa tube); "
            "mass-flow high-K sweeps unverified (Task173 template binding)."
        ),
    )
    regime_choice = (
        ParetoChoice(
            regime.shortlist_key,
            regime.geometry_v2,
            f"Best minimum Re margin among layouts without Task027 physical blocker "
            f"({regime.min_re_margin_sensitivity}); 241 layouts excluded.",
        )
        if regime is not None
        else ParetoChoice(
            "NONE",
            "",
            "All 241 layouts blocked by Task027 on tube mass-flow sweeps; "
            "no regime-robustness ranking assigned.",
        )
    )
    return thermal_choice, hydraulic_choice, regime_choice, None


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
                normalized,
                handoff,
                tube_count=tube_count,
                tube_length_m=length,
                canonical_scale=scale,
            )
        )
        layouts.append(
            _layout_report(normalized, handoff, active, tube_count=tube_count, tube_length_m=length)
        )
    identity_tuple = tuple(identity_rows)
    layout_tuple = tuple(layouts)
    distinct_layout_hashes = {r.tube_layout_hash for r in identity_tuple}
    thermal, hydraulic, regime, eng = _pareto_choices(layout_tuple)
    threshold = _TARGET_Q_W * THERMODYNAMIC_DUTY_TOLERANCE
    clean_status = all(
        row.baseline_clean_q_w and Decimal(row.baseline_clean_q_w) >= threshold
        for row in layout_tuple
    )
    nonbaseline = [
        s for row in layout_tuple for s in row.sensitivity if s.scenario_key != "baseline"
    ]
    nb_valid = sum(1 for s in nonbaseline if s.task027_status == "PASS")
    nb_blocked = sum(
        1
        for s in nonbaseline
        if s.robustness_evidence_status
        in ("PHYSICAL_MODEL_APPLICABILITY_BLOCKED", "REPLAY_BINDING_BLOCKED")
    )
    nb_hk = sum(1 for s in nonbaseline if s.high_k_dp_computed)
    root_cause = (
        "Prior pass re-ran full Task168 candidate_chain on catalog candidate_spec_id, "
        "re-solving Task021 and drifting to foreign layouts (Re≈3427/3393). Corrected path "
        "freezes enumeration Task021/Task025 and reruns Task026 only under rebuilt handoff/t168."
    )
    re_sens = (
        f"Fixed-layout replay: {nb_valid} non-baseline scenarios with verified Task026/027; "
        f"{nb_blocked} blocked (physical or binding); "
        f"{nb_hk} non-baseline scenarios with Task173 high-K dp (temperature cases only; "
        "mass-flow sweeps blocked by Task173 case binding)."
    )
    baseline_margins = [
        min(
            Decimal(row.baseline_high_tube_margin_pa or "0"),
            Decimal(row.baseline_high_shell_margin_pa or "0"),
        )
        for row in layout_tuple
        if row.baseline_high_tube_margin_pa and row.baseline_high_shell_margin_pa
    ]
    min_baseline_margin = min(baseline_margins) if baseline_margins else Decimal("0")
    robustness_valid = nb_valid > 0 and all(
        next(s for s in row.sensitivity if s.scenario_key == "baseline").task027_status == "PASS"
        for row in layout_tuple
    )
    layout_status: dict[str, str] = {}
    layout_engineering_status_by_key: dict[str, LayoutEngineeringStatus] = {}
    for row in layout_tuple:
        st = row.engineering_layout_status
        layout_status[row.shortlist_key] = st
        layout_status[row.shortlist_key.replace(".", "P")] = st
        layout_engineering_status_by_key[row.shortlist_key] = st
        layout_engineering_status_by_key[row.shortlist_key.replace(".", "P")] = st
    t173 = task173_mass_binding_boundary_report()
    mass_hk_total = sum(row.mass_flow_high_k_computed_count for row in layout_tuple)
    mass_hk_cov = (
        f"0/20 mass-flow sensitivity scenarios with verified high-K dp "
        f"(total mass-flow high-K={mass_hk_total}); baseline-only hydraulic evidence."
    )
    any_thermal_fail = any(
        row.engineering_layout_status == "OPERATING_RANGE_THERMAL_FAIL" for row in layout_tuple
    )
    thermal_sens = (
        "TUBE_MDOT_SWEEP_CLEAN_Q_BELOW_330KW_ON_T235"
        if any_thermal_fail
        else "NO_MDOT_SWEEP_THERMAL_FAIL_RECORDED"
    )
    decision = (
        "NO_ROBUST_CANDIDATE_PROVEN: separated Re/thermal/hydraulic axes; "
        "mass-flow high-K not verified; Task173 production rating BLOCKED."
    )
    return EngineeringShortlistRobustnessReport(
        frozen_candidate_c_unchanged=True,
        canonical_shortlist_size=len(_SHORTLIST),
        distinct_audited_layout_hash_count=len(distinct_layout_hashes),
        unique_physical_layout_count=len(_SHORTLIST),
        identity_binding_status=_identity_binding_status(identity_tuple),
        identity_records=identity_tuple,
        layouts=layout_tuple,
        thermal_priority=thermal,
        hydraulic_priority=hydraulic,
        regime_robustness_priority=regime,
        engineering_recommended=eng,
        re_sensitivity_result=re_sens,
        high_k_margin_robustness=(
            f"Baseline min-side high-K margin {min_baseline_margin} Pa across four layouts; "
            f"{nb_hk} non-baseline temperature sweeps computed high-K; "
            "mass-flow perturbations excluded from hydraulic worst-case until Task173 binding extended."
        ),
        clean_330kw_status="MET_CLEAN_CONTRACT"
        if clean_status
        else "CLEAN_BELOW_CONTRACT_ON_SHORTLIST",
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
            "docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r1.json",
            "docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r2.json",
        ),
        sensitivity_binding_root_cause=root_cause,
        layout_identity_drift_confirmed=True,
        replay_binding_defect_confirmed=True,
        robustness_evidence_valid=robustness_valid,
        nonbaseline_scenarios_valid=nb_valid,
        nonbaseline_scenarios_blocked=nb_blocked,
        nonbaseline_high_k_dp_computed=nb_hk,
        layout_status_by_key=layout_status,
        layout_engineering_status_by_key=layout_engineering_status_by_key,
        engineering_acceptance_status="EXPERIMENTAL_PRESCREEN_ONLY",
        robust_candidate_proven=False,
        thermal_sensitivity_status=thermal_sens,
        task173_mass_binding_root_cause=t173.root_cause,
        task173_experimental_replay_feasible=t173.experimental_replay_feasible,
        nonbaseline_mass_flow_high_k_coverage=mass_hk_cov,
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
        "schema": "hxforge.engineering-shortlist-robustness.v3",
        "task_id": "V08_03_R2_GATE_CORRECTION_AND_TASK173_MASS_BINDING_BOUNDARY",
        "supersedes": "docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r2.json",
        "canonical_shortlist_size": report.canonical_shortlist_size,
        "distinct_audited_layout_hash_count": report.distinct_audited_layout_hash_count,
        "frozen_design_c_reference": frozen_ref,
        "unique_physical_layout_count": report.unique_physical_layout_count,
        "identity_binding_status": report.identity_binding_status,
        "identity_records": [row.__dict__ for row in report.identity_records],
        "shortlist_layouts": [
            {
                **{
                    k: v
                    for k, v in row.__dict__.items()
                    if k not in ("sensitivity", "port_velocities_baseline")
                },
                "port_velocities_baseline": [
                    {
                        "port_id": p.port_id,
                        "velocity_m_s": p.velocity_m_s,
                        "inside_diameter_m": p.inside_diameter_m,
                    }
                    for p in row.port_velocities_baseline
                ],
                "sensitivity": [
                    {
                        **{k: v for k, v in s.__dict__.items() if k != "binding_audit"},
                        "binding_audit": s.binding_audit.__dict__,
                    }
                    for s in row.sensitivity
                ],
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
        "sensitivity_integrity": {
            "sensitivity_binding_root_cause": report.sensitivity_binding_root_cause,
            "layout_identity_drift_confirmed": report.layout_identity_drift_confirmed,
            "replay_binding_defect_confirmed": report.replay_binding_defect_confirmed,
            "robustness_evidence_valid": report.robustness_evidence_valid,
            "nonbaseline_scenarios_valid": report.nonbaseline_scenarios_valid,
            "nonbaseline_scenarios_blocked": report.nonbaseline_scenarios_blocked,
            "nonbaseline_high_k_dp_computed": report.nonbaseline_high_k_dp_computed,
        },
        "layout_status_by_key": report.layout_status_by_key,
        "final_engineering_decision": report.final_engineering_decision,
        "engineering_acceptance_status": report.engineering_acceptance_status,
        "supersession_chain": list(report.supersession_chain),
        "engineering_design_status": report.engineering_acceptance_status,
        "robust_candidate_proven": report.robust_candidate_proven,
        "thermal_sensitivity_status": report.thermal_sensitivity_status,
        "task173_mass_binding": {
            "root_cause": report.task173_mass_binding_root_cause,
            "experimental_replay_feasible": report.task173_experimental_replay_feasible,
            "mass_flow_high_k_coverage": report.nonbaseline_mass_flow_high_k_coverage,
        },
        "layout_engineering_status_by_key": report.layout_engineering_status_by_key,
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

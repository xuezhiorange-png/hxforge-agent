"""Experimental one-way hydraulic re-evaluation from live Task173 thermal outlets (R14)."""

# ruff: noqa: E501

from __future__ import annotations

import dataclasses
import itertools
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

from hexagent.exchangers.shell_tube.bell_delaware import validate_request as validate_task166
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import Task168Request
from hexagent.exchangers.shell_tube.shell_side_flow_state import (
    validate_request as validate_task032,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import mass_flow_authority_hash
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import (
    parse_request as parse_task032_request,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    validate_request as validate_task031,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import REFERENCE_PRESSURE_PA
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import DIMENSION_ORDER
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    compute_task027_friction_pressure_drop,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline import compute_task028_local_loss
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import ProducerTask
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_composition_authority_hash,
    compute_member_authority_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline import (
    compute_task029_composition,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.request import (
    build_task029_request,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    PhaseRegion,
    compute_tube_side_heat_transfer_coefficient,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import (
    PropertySnapshot,
    recompute_property_snapshot_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.request import TubeSideThermalRequest
from hexagent.exchangers.shell_tube.tube_side_thermal.stage_pipeline import (
    build_raw_tube_side_request_envelope,
)
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.case_streams import (
    shell_stream_spec,
    tube_stream_spec,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_transitional_tube_hydraulic import (
    APPLICABILITY_STATUS as R20_APPLICABILITY_STATUS,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_transitional_tube_hydraulic import (
    compute_experimental_transitional_tube_hydraulic,
    experimental_transitional_tube_hydraulic_enabled,
)
from prototypes.v07_general_rating_sizing_mvp.live_hydraulic_mass_flow_binding import (
    equipment_shell_mass_flow_kg_s,
    equipment_tube_mass_flow_kg_s,
    live_postpass_binding_document,
)
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)

LIVE_THERMAL_HYDRAULIC_AUTHORITY_ID = "V07-LIVE-THERMAL-STATE-HYDRAULIC-POSTPASS-R14"
HYDRAULIC_STATUS_LIVE_POSTPASS = "EXPERIMENTAL_LIVE_THERMAL_STATE_HYDRAULIC_POSTPASS"
PROPERTY_EVALUATION_RULE_ID = "SIDE_BULK_MEAN_TP_AT_INLET_REFERENCE_PRESSURE_R14"
THERMAL_HYDRAULIC_COUPLING_POSTPASS = "EXPERIMENTAL_HYDRAULIC_POST_PASS_ONE_WAY"

_COOLPROP_MIN_PRESSURE_PA = Decimal("100000")
_COOLPROP_MAX_PRESSURE_PA = Decimal("101325")


@dataclasses.dataclass(frozen=True)
class Task168CandidateBundle:
    candidate_id: str
    candidate_hash: str
    t168_request: Task168Request
    bundle: Any
    authority: Any
    configuration: Any
    layout: Any


def _bulk_mean_k(inlet_k: Decimal, outlet_k: Decimal) -> Decimal:
    return (inlet_k + outlet_k) / Decimal(2)


def _decimal_field(value: object) -> Decimal:
    return Decimal(str(value))


def materialize_task168_bundle(case: EngineeringCase, candidate_id: str) -> Task168CandidateBundle:
    sizing_req = build_task173_sizing_request(case)
    t168 = sizing_req.task168_candidate_request
    authority = t168.evaluation_input_authority
    authorities = task168._authority_map(t168)
    dimensions = tuple(
        task168._sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    for combination in itertools.product(t168.shell_geometry_catalog.records, *dimensions):
        candidate = task168._candidate(t168, authorities, combination[0], tuple(combination[1:]))
        if candidate.candidate_id != candidate_id:
            continue
        if task168._structural_blockers(candidate):
            raise RuntimeError(f"candidate {candidate_id} structurally blocked")
        bundle, stage_failure, _ = task168._execute_candidate_chain(
            t168,
            candidate,
            combination[0],
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
            preserve_baffle_orientation_sequence=False,
        )
        if stage_failure is not None:
            raise RuntimeError(
                f"candidate {candidate_id} chain failed at {stage_failure.stage}: {stage_failure.code}"
            )
        return Task168CandidateBundle(
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            t168_request=t168,
            bundle=bundle,
            authority=authority,
            configuration=bundle.task020_configuration,
            layout=bundle.task021_layout,
        )
    raise RuntimeError(f"candidate {candidate_id} not found in Task168 space")


def _template_source_ids(template: PropertySnapshot | dict[str, object]) -> tuple[str, str]:
    if isinstance(template, PropertySnapshot):
        return template.property_source_id, template.property_source_version
    source_id = template.get("property_source_id", "CoolProp-6.6")
    source_version = template.get("property_source_version", "1.0.0")
    return str(source_id), str(source_version)


def _property_snapshot_from_coolprop_tp(
    provider: CoolPropProvider,
    *,
    temperature_k: Decimal,
    pressure_pa: Decimal,
    template: PropertySnapshot | dict[str, object],
) -> PropertySnapshot:
    state = provider.state_tp(
        FluidIdentifier("Water", "HEOS"),
        float(temperature_k),
        float(pressure_pa),
    )
    phase_name = getattr(state.phase, "value", str(state.phase)).lower()
    if "liquid" not in phase_name:
        raise ValueError(f"CoolProp phase not liquid at T={temperature_k} P={pressure_pa}")
    source_id, source_version = _template_source_ids(template)
    base = PropertySnapshot(
        density_kg_m3=Decimal(str(state.density_kg_m3)),
        dynamic_viscosity_pa_s=Decimal(str(state.viscosity_pa_s)),
        thermal_conductivity_w_m_k=Decimal(str(state.conductivity_w_m_k)),
        specific_heat_capacity_j_kg_k=Decimal(str(state.cp_j_kg_k)),
        bulk_temperature_k=temperature_k,
        bulk_pressure_pa=pressure_pa,
        phase_region=PhaseRegion.SINGLE_PHASE_LIQUID,
        property_source_id=source_id,
        property_source_version=source_version,
        property_snapshot_hash="0" * 64,
    )
    snapshot_hash = recompute_property_snapshot_hash(base)
    return replace(base, property_snapshot_hash=snapshot_hash)


def _task026_request_with_snapshot(
    authority: Any,
    snapshot: PropertySnapshot,
    *,
    mass_flow_rate_kg_s: Decimal | None = None,
) -> TubeSideThermalRequest:
    raw_or_request = authority.task026_request
    if type(raw_or_request) is TubeSideThermalRequest:
        task026_request = raw_or_request
    else:
        projected = task168._public_value(raw_or_request)
        task026_request = build_raw_tube_side_request_envelope(projected)
    if type(task026_request) is not TubeSideThermalRequest:
        raise TypeError("task026 request envelope could not be materialized")
    updates: dict[str, object] = {
        "property_snapshot": snapshot,
        "property_snapshot_hash": snapshot.property_snapshot_hash,
    }
    if mass_flow_rate_kg_s is not None:
        updates["mass_flow_rate_kg_s"] = mass_flow_rate_kg_s
    return replace(task026_request, **updates)


def _is_task027_transition_gap_blocker_only(blockers: list[dict[str, str]]) -> bool:
    if not blockers:
        return False
    return all(blocker.get("code") == "BL_T027_UNSUPPORTED_REYNOLDS_REGIME" for blocker in blockers)


def _run_task028_local_loss_only(
    *,
    bundle: Any,
    authority: Any,
    task026_result: Any,
    tube_property_snapshot: PropertySnapshot,
) -> tuple[Any | None, list[dict[str, str]]]:
    try:
        task028_template_value = task168._public_value(
            authority.task028_request_template, decimal_strings=False
        )
    except (TypeError, ValueError, UnicodeError, ArithmeticError) as exc:
        return None, [
            {
                "code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE",
                "scope": "TASK028",
                "detail": f"template projection failed: {exc}",
            }
        ]
    if type(task028_template_value) is not dict:
        return None, [
            {
                "code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE",
                "scope": "TASK028",
                "detail": "task028 template must project to a mapping",
            }
        ]
    task028_template = cast(dict[str, object], task028_template_value)
    task028_template["task025_valid_result"] = task168._public_value(
        bundle.task025_result, decimal_strings=False
    )
    task028_template["task026_success_result"] = task168._public_value(
        task026_result, decimal_strings=False
    )
    task028_template["property_snapshot"] = task168._public_value(
        tube_property_snapshot, decimal_strings=False
    )
    task028_template["property_snapshot_hash"] = tube_property_snapshot.property_snapshot_hash
    task028_template["constant_density_path_assertion"] = task168._status_text(
        authority.task027_constant_density_assertion
    )
    task028_template["zero_net_elevation_change_assertion"] = task168._status_text(
        authority.task027_zero_net_elevation_assertion
    )
    task028_template["flow_direction_assertion"] = task168._status_text(
        authority.task027_flow_direction_assertion
    )
    result028 = compute_task028_local_loss(
        raw_request=task028_template,
        task025_result=cast(Any, bundle.task025_result),
        task026_result=cast(Any, task026_result),
    )
    if type(result028).__name__ != "Task028SuccessResult":
        return None, [
            {"code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE", "scope": "TASK028", "detail": "blocked"}
        ]
    return result028, []


def _run_task027_through_029(
    *,
    bundle: Any,
    authority: Any,
    task026_result: Any,
    tube_property_snapshot: PropertySnapshot,
) -> tuple[Task029SuccessResult | None, list[dict[str, str]]]:
    result027 = compute_task027_friction_pressure_drop(
        task025_result=cast(Any, bundle.task025_result),
        task026_result=cast(Any, task026_result),
        property_snapshot=tube_property_snapshot,
        constant_density_path_assertion=cast(Any, authority.task027_constant_density_assertion),
        zero_net_elevation_change_assertion=cast(
            Any, authority.task027_zero_net_elevation_assertion
        ),
        flow_direction_assertion=cast(Any, authority.task027_flow_direction_assertion),
        roughness_authority=cast(Any, authority.task027_roughness_authority),
    )
    if type(result027).__name__ != "Task027SuccessResult":
        tube_blockers: list[dict[str, str]] = []
        for entry in getattr(result027, "blockers", ()):
            code = getattr(getattr(entry, "code", None), "value", None) or str(
                getattr(entry, "code", "BLOCKED_TASK027")
            )
            tube_blockers.append(
                {
                    "code": str(code),
                    "scope": "TASK027",
                    "detail": str(getattr(entry, "message_key", "task027 blocked")),
                }
            )
        if not tube_blockers:
            tube_blockers.append({"code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE", "scope": "TASK027"})
        return None, tube_blockers
    try:
        task028_template_value = task168._public_value(
            authority.task028_request_template, decimal_strings=False
        )
    except (TypeError, ValueError, UnicodeError, ArithmeticError) as exc:
        return None, [
            {
                "code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE",
                "scope": "TASK028",
                "detail": f"template projection failed: {exc}",
            }
        ]
    if type(task028_template_value) is not dict:
        return None, [
            {
                "code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE",
                "scope": "TASK028",
                "detail": "task028 template must project to a mapping",
            }
        ]
    task028_template = cast(dict[str, object], task028_template_value)
    task028_template["task025_valid_result"] = task168._public_value(
        bundle.task025_result, decimal_strings=False
    )
    task028_template["task026_success_result"] = task168._public_value(
        task026_result, decimal_strings=False
    )
    task028_template["property_snapshot"] = task168._public_value(
        tube_property_snapshot, decimal_strings=False
    )
    task028_template["property_snapshot_hash"] = tube_property_snapshot.property_snapshot_hash
    task028_template["constant_density_path_assertion"] = task168._status_text(
        authority.task027_constant_density_assertion
    )
    task028_template["zero_net_elevation_change_assertion"] = task168._status_text(
        authority.task027_zero_net_elevation_assertion
    )
    task028_template["flow_direction_assertion"] = task168._status_text(
        authority.task027_flow_direction_assertion
    )
    result028 = compute_task028_local_loss(
        raw_request=task028_template,
        task025_result=cast(Any, bundle.task025_result),
        task026_result=cast(Any, task026_result),
    )
    if type(result028).__name__ != "Task028SuccessResult":
        return None, [
            {"code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE", "scope": "TASK028", "detail": "blocked"}
        ]
    task029_template_any = cast(Any, authority.task029_request_template)
    composition = task029_template_any.composition_authority
    template_members = tuple(composition.member_authorities)
    template_components = tuple(
        member for member in template_members if member.producer_task is ProducerTask.TASK_028
    )
    template_friction = tuple(
        member for member in template_members if member.producer_task is ProducerTask.TASK_027
    )
    result027_any = cast(Any, result027)
    result028_any = cast(Any, result028)
    components = tuple(result028_any.component_results)
    if len(template_components) != len(components) or len(template_friction) != 1:
        return None, [
            {
                "code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE",
                "scope": "TASK029",
                "detail": "template member layout mismatch",
            }
        ]
    ordered_template_components = tuple(
        sorted(template_components, key=lambda item: item.global_path_sequence_index)
    )
    members: list[Any] = []
    for index, component in enumerate(components):
        member = ordered_template_components[index]
        updated = replace(
            member,
            global_path_sequence_index=index,
            producer_component_identity=component.component_id,
            expected_producer_component_type=task168._status_text(component.component_type),
            expected_producer_authority_hash=component.authority_hash,
            expected_upstream_reference_plane=component.upstream_reference_plane,
            expected_downstream_reference_plane=component.downstream_reference_plane,
            expected_multiplicity=component.multiplicity,
            member_authority_hash="",
        )
        members.append(
            replace(updated, member_authority_hash=compute_member_authority_hash(updated))
        )
    friction = template_friction[0]
    friction_updated = replace(
        friction,
        global_path_sequence_index=len(members),
        expected_upstream_reference_plane=result027_any.upstream_reference_plane,
        expected_downstream_reference_plane=result027_any.downstream_reference_plane,
        expected_producer_authority_hash="",
        expected_multiplicity=1,
        member_authority_hash="",
    )
    members.append(
        replace(
            friction_updated,
            member_authority_hash=compute_member_authority_hash(friction_updated),
        )
    )
    composition = replace(
        composition,
        member_authorities=tuple(members),
        start_reference_plane=members[0].expected_upstream_reference_plane,
        end_reference_plane=members[-1].expected_downstream_reference_plane,
        composition_authority_hash="",
    )
    composition = replace(
        composition,
        composition_authority_hash=compute_composition_authority_hash(composition),
    )
    task029_request = build_task029_request(
        profile_id=task029_template_any.profile_id,
        task027_success_result=cast(Any, result027),
        task028_success_result=cast(Any, result028),
        composition_authority=composition,
    )
    task029_raw = {
        "schema_version": task029_request.schema_version,
        "profile_id": task029_request.profile_id,
        "composition_authority": task168._public_value(
            task029_request.composition_authority,
            decimal_strings=False,
        ),
        "request_hash": task029_request.request_hash,
    }
    outcome = compute_task029_composition(
        task029_raw,
        task027_success_result=cast(Any, result027),
        task028_success_result=cast(Any, result028),
        input_evidence_refs=authority.evidence_refs,
    )
    if type(outcome) is not Task029SuccessResult:
        return None, [
            {"code": "BLOCKED_TUBE_HYDRAULIC_RECOMPUTE", "scope": "TASK029", "detail": "blocked"}
        ]
    return outcome, []


def _equipment_shell_task032_mass_flow_rate_kg_s(case: EngineeringCase) -> Decimal:
    return equipment_shell_mass_flow_kg_s(case)


def _recompute_shell_bell_delaware(
    *,
    case: EngineeringCase,
    ctx: Task168CandidateBundle,
    shell_property_snapshot: PropertySnapshot,
) -> tuple[Task166Result, Any]:
    bundle = ctx.bundle
    authority = ctx.authority
    request031 = task168._task031_payload(
        authority,
        ctx.configuration,
        ctx.layout,
        bundle.task024_result,
        bundle.task024_geometry,
    )
    result031 = validate_task031(request031)
    request032 = task168._task032_payload(authority, result031, ctx.configuration, ctx.layout)
    request032["property_snapshot"] = task168._public_value(shell_property_snapshot)
    request032["property_snapshot_hash"] = shell_property_snapshot.property_snapshot_hash
    scaled_shell_flow = _equipment_shell_task032_mass_flow_rate_kg_s(case)
    mass_flow = request032.get("mass_flow_authority")
    if type(mass_flow) is dict:
        mass_flow["mass_flow_rate_kg_s"] = str(scaled_shell_flow)
        mass_flow["property_snapshot_hash"] = shell_property_snapshot.property_snapshot_hash
        parsed = parse_task032_request(request032)
        mass_flow["authority_hash"] = mass_flow_authority_hash(parsed.mass_flow_authority)
    result032 = validate_task032(request032)
    if result032.status.value != "VALID":
        raise RuntimeError("task032 blocked in live shell hydraulic post-pass")
    payload166 = task168._task166_payload(
        authority,
        ctx.configuration,
        ctx.layout,
        bundle.task022_geometry,
        bundle.task024_geometry,
        result031,
        result032,
        request032,
    )
    outcome = validate_task166(payload166)
    if outcome.valid is None:
        raise RuntimeError("task166 blocked in live shell hydraulic post-pass")
    return outcome.valid, result032


def _coolprop_outlet_domain_ok(
    provider: CoolPropProvider,
    *,
    temperature_k: Decimal,
    pressure_pa: Decimal,
) -> tuple[bool, str | None]:
    try:
        state = provider.state_tp(
            FluidIdentifier("Water", "HEOS"),
            float(temperature_k),
            float(pressure_pa),
        )
    except Exception as exc:  # CoolProp domain errors are provider-specific
        return False, f"COOLPROP_TP_ERROR:{type(exc).__name__}"
    phase_name = getattr(state.phase, "value", str(state.phase)).lower()
    if "liquid" not in phase_name:
        return False, f"COOLPROP_PHASE_{phase_name}"
    return True, None


def _engineering_inlet_pressure_ok(pressure_pa: Decimal) -> bool:
    return pressure_pa == REFERENCE_PRESSURE_PA


def run_live_thermal_state_hydraulic_postpass(
    case: EngineeringCase,
    *,
    candidate_id: str,
    tube_inlet_temperature_k: Decimal,
    tube_outlet_temperature_k: Decimal,
    shell_inlet_temperature_k: Decimal,
    shell_outlet_temperature_k: Decimal,
    tube_inlet_pressure_pa: Decimal,
    shell_inlet_pressure_pa: Decimal,
    reference_tube_dp_pa: Decimal | None = None,
    reference_shell_dp_pa: Decimal | None = None,
    provider: CoolPropProvider | None = None,
) -> dict[str, Any]:
    """One-way hydraulic post-pass; does not mutate Task174 reference preview semantics."""
    provider = provider or CoolPropProvider()
    tube_inlet_temperature_k = _decimal_field(tube_inlet_temperature_k)
    tube_outlet_temperature_k = _decimal_field(tube_outlet_temperature_k)
    shell_inlet_temperature_k = _decimal_field(shell_inlet_temperature_k)
    shell_outlet_temperature_k = _decimal_field(shell_outlet_temperature_k)
    tube_inlet_pressure_pa = _decimal_field(tube_inlet_pressure_pa)
    shell_inlet_pressure_pa = _decimal_field(shell_inlet_pressure_pa)
    ctx = materialize_task168_bundle(case, candidate_id)
    authority = ctx.authority
    bundle = ctx.bundle
    if reference_tube_dp_pa is None:
        reference_tube_dp_pa = _decimal_field(
            bundle.task029_result.modeled_total_tube_side_pressure_drop_pa
        )
    if reference_shell_dp_pa is None:
        reference_shell_dp_pa = cast(Task166Result, bundle.task166_result).total_shell_pressure_drop

    tube_eval_t = _bulk_mean_k(tube_inlet_temperature_k, tube_outlet_temperature_k)
    shell_eval_t = _bulk_mean_k(shell_inlet_temperature_k, shell_outlet_temperature_k)
    tube_template = authority.task027_property_snapshot
    shell_template = authority.task032_property_snapshot or tube_template

    blockers: list[dict[str, str]] = []
    if not _engineering_inlet_pressure_ok(
        tube_inlet_pressure_pa
    ) or not _engineering_inlet_pressure_ok(shell_inlet_pressure_pa):
        blockers.append(
            {
                "code": "BLOCKED_ENGINEERING_INLET_REFERENCE_PRESSURE",
                "scope": "PROPERTY_EVALUATION",
            }
        )

    try:
        tube_snapshot = _property_snapshot_from_coolprop_tp(
            provider,
            temperature_k=tube_eval_t,
            pressure_pa=tube_inlet_pressure_pa,
            template=tube_template,
        )
        shell_snapshot = _property_snapshot_from_coolprop_tp(
            provider,
            temperature_k=shell_eval_t,
            pressure_pa=shell_inlet_pressure_pa,
            template=shell_template,
        )
    except ValueError as exc:
        return _blocked_postpass_document(
            ctx=ctx,
            case=case,
            blockers=[{"code": "BLOCKED_COOLPROP_PROPERTY_EVALUATION", "detail": str(exc)}],
            tube_inlet_temperature_k=tube_inlet_temperature_k,
            tube_outlet_temperature_k=tube_outlet_temperature_k,
            shell_inlet_temperature_k=shell_inlet_temperature_k,
            shell_outlet_temperature_k=shell_outlet_temperature_k,
            reference_tube_dp_pa=reference_tube_dp_pa,
            reference_shell_dp_pa=reference_shell_dp_pa,
        )

    tube_side = tube_stream_spec(case)
    equipment_tube_flow = equipment_tube_mass_flow_kg_s(case)
    equipment_shell_flow = equipment_shell_mass_flow_kg_s(case)
    historical_task026_template_flow = bundle.task026_result.mass_flow_rate_kg_s
    task026_request = _task026_request_with_snapshot(
        authority,
        tube_snapshot,
        mass_flow_rate_kg_s=equipment_tube_flow,
    )
    task026_result = compute_tube_side_heat_transfer_coefficient(
        task026_request, bundle.task025_result
    )
    task029_outcome, tube_hydraulic_blockers = _run_task027_through_029(
        bundle=bundle,
        authority=authority,
        task026_result=task026_result,
        tube_property_snapshot=tube_snapshot,
    )
    experimental_transitional_tube_hydraulic: dict[str, str] | None = None
    recalc_tube_experimental: Decimal | None = None
    tube_hydraulic_recompute_status = "SUCCESS" if task029_outcome is not None else "BLOCKED"
    if (
        task029_outcome is None
        and experimental_transitional_tube_hydraulic_enabled(case)
        and _is_task027_transition_gap_blocker_only(tube_hydraulic_blockers)
    ):
        result028, task028_blockers = _run_task028_local_loss_only(
            bundle=bundle,
            authority=authority,
            task026_result=task026_result,
            tube_property_snapshot=tube_snapshot,
        )
        if task028_blockers:
            tube_hydraulic_blockers = [*tube_hydraulic_blockers, *task028_blockers]
        elif result028 is not None:
            exp_outcome = compute_experimental_transitional_tube_hydraulic(
                task025_result=bundle.task025_result,
                task026_result=task026_result,
                property_snapshot=tube_snapshot,
                roughness_authority=cast(Any, authority.task027_roughness_authority),
                task028_result=cast(Any, result028),
            )
            if exp_outcome.status == "SUCCESS" and exp_outcome.total_tube_dp_pa is not None:
                tube_hydraulic_recompute_status = "EXPERIMENTAL_TRANSITIONAL_SUCCESS"
                recalc_tube_experimental = exp_outcome.total_tube_dp_pa
                experimental_transitional_tube_hydraulic = exp_outcome.disclosure
                tube_hydraulic_blockers = []
            else:
                tube_hydraulic_blockers = [
                    *tube_hydraulic_blockers,
                    *list(exp_outcome.blockers),
                ]
    blockers.extend(tube_hydraulic_blockers)

    task166_live = None
    task032_live = None
    shell_hydraulic_recompute_status = "NOT_RUN"
    try:
        task166_live, task032_live = _recompute_shell_bell_delaware(
            case=case,
            ctx=ctx,
            shell_property_snapshot=shell_snapshot,
        )
        shell_hydraulic_recompute_status = "SUCCESS"
    except RuntimeError as exc:
        blockers.append({"code": "BLOCKED_SHELL_HYDRAULIC_RECOMPUTE", "detail": str(exc)})
        shell_hydraulic_recompute_status = "BLOCKED"

    mass_flow_binding = live_postpass_binding_document(
        case=case,
        task026_input_mass_flow_kg_s=equipment_tube_flow,
        task032_input_mass_flow_kg_s=equipment_shell_flow,
        task025_total_parallel_flow_area_m2=bundle.task025_result.total_parallel_flow_area_m2,
        historical_task026_template_mass_flow_kg_s=historical_task026_template_flow,
    )

    if task166_live is None:
        return _blocked_postpass_document(
            ctx=ctx,
            case=case,
            blockers=blockers,
            tube_inlet_temperature_k=tube_inlet_temperature_k,
            tube_outlet_temperature_k=tube_outlet_temperature_k,
            shell_inlet_temperature_k=shell_inlet_temperature_k,
            shell_outlet_temperature_k=shell_outlet_temperature_k,
            reference_tube_dp_pa=reference_tube_dp_pa,
            reference_shell_dp_pa=reference_shell_dp_pa,
            recalculated_tube_dp_pa=(
                task029_outcome.modeled_total_tube_side_pressure_drop_pa
                if task029_outcome is not None
                else recalc_tube_experimental
            ),
            property_inputs={
                "tube": _snapshot_public(tube_snapshot),
                "shell": _snapshot_public(shell_snapshot),
            },
            mass_flow_binding=mass_flow_binding,
            tube_reynolds_number=str(task026_result.reynolds_number),
            tube_hydraulic_recompute_status=tube_hydraulic_recompute_status,
            shell_hydraulic_recompute_status=shell_hydraulic_recompute_status,
        )

    recalc_tube = (
        task029_outcome.modeled_total_tube_side_pressure_drop_pa
        if task029_outcome is not None
        else recalc_tube_experimental
    )
    recalc_shell = task166_live.total_shell_pressure_drop
    tube_out_p = tube_inlet_pressure_pa - recalc_tube if recalc_tube is not None else None
    shell_out_p = shell_inlet_pressure_pa - recalc_shell

    coolprop_checks: dict[str, Any] = {}
    outlet_checks: list[tuple[str, Decimal, Decimal | None]] = [
        ("shell", shell_outlet_temperature_k, shell_out_p),
    ]
    if tube_out_p is not None:
        outlet_checks.insert(0, ("tube", tube_outlet_temperature_k, tube_out_p))
    for side, t_out, p_out in outlet_checks:
        if p_out is None:
            continue
        ok, detail = _coolprop_outlet_domain_ok(provider, temperature_k=t_out, pressure_pa=p_out)
        coolprop_checks[side] = {
            "ok": ok,
            "detail": detail,
            "temperature_k": str(t_out),
            "pressure_pa": str(p_out),
        }
        if not ok:
            blockers.append(
                {
                    "code": "BLOCKED_COOLPROP_OUTLET_STATE_DOMAIN",
                    "scope": side,
                    "detail": detail or "",
                }
            )

    task174_style_pressure_ok = (
        _COOLPROP_MIN_PRESSURE_PA <= shell_out_p <= _COOLPROP_MAX_PRESSURE_PA
    )
    if tube_out_p is not None:
        task174_style_pressure_ok = task174_style_pressure_ok and (
            _COOLPROP_MIN_PRESSURE_PA <= tube_out_p <= _COOLPROP_MAX_PRESSURE_PA
        )
    if not task174_style_pressure_ok:
        blockers.append(
            {
                "code": "BLOCKED_TASK174_STYLE_OUTLET_PRESSURE_WINDOW",
                "scope": "OUTLET_PRESSURE",
                "detail": "100000..101325 Pa one-way guard (disclosed separately from user Δp limits)",
            }
        )

    tube_limit_ok = recalc_tube is not None and recalc_tube <= case.max_tube_side_pressure_drop_pa
    shell_limit_ok = recalc_shell <= case.max_shell_side_pressure_drop_pa
    if recalc_tube is None:
        tube_dp_constraint = "BLOCKED"
    elif tube_limit_ok:
        tube_dp_constraint = "SATISFIED"
    else:
        tube_dp_constraint = "NOT_SATISFIED"
    if blockers:
        hydraulic_constraint = "BLOCKED"
    elif tube_limit_ok and shell_limit_ok:
        hydraulic_constraint = "SATISFIED"
    else:
        hydraulic_constraint = "NOT_SATISFIED"

    if tube_hydraulic_recompute_status == "EXPERIMENTAL_TRANSITIONAL_SUCCESS":
        applicability = R20_APPLICABILITY_STATUS
    else:
        applicability = "APPLICABLE"
        if (
            task166_live.applicability is not None
            and task166_live.applicability.status.value != "APPLICABLE"
        ):
            applicability = "BLOCKED_OR_WARN"

    return {
        "schema_version": "hxforge.live-thermal-state-hydraulic-postpass.v1",
        "authority_id": LIVE_THERMAL_HYDRAULIC_AUTHORITY_ID,
        "task174_hydraulic_status": HYDRAULIC_STATUS_LIVE_POSTPASS,
        "thermal_hydraulic_coupling_status": THERMAL_HYDRAULIC_COUPLING_POSTPASS,
        "property_evaluation_rule_id": PROPERTY_EVALUATION_RULE_ID,
        "candidate_id": ctx.candidate_id,
        "candidate_hash": ctx.candidate_hash,
        "physical_tube_count": ctx.layout.physical_tube_count,
        "task025_total_parallel_flow_area_m2": str(
            bundle.task025_result.total_parallel_flow_area_m2
        ),
        "tube_inlet_temperature_k": str(tube_inlet_temperature_k),
        "tube_outlet_temperature_k": str(tube_outlet_temperature_k),
        "shell_inlet_temperature_k": str(shell_inlet_temperature_k),
        "shell_outlet_temperature_k": str(shell_outlet_temperature_k),
        "tube_bulk_evaluation_temperature_k": str(tube_eval_t),
        "shell_bulk_evaluation_temperature_k": str(shell_eval_t),
        "reference_tube_dp_pa": str(reference_tube_dp_pa),
        "reference_shell_dp_pa": str(reference_shell_dp_pa),
        "recalculated_tube_dp_pa": str(recalc_tube) if recalc_tube is not None else None,
        "recalculated_shell_dp_pa": str(recalc_shell),
        "tube_outlet_pressure_pa": str(tube_out_p) if tube_out_p is not None else None,
        "shell_outlet_pressure_pa": str(shell_out_p),
        "max_tube_dp_pa": str(case.max_tube_side_pressure_drop_pa),
        "max_shell_dp_pa": str(case.max_shell_side_pressure_drop_pa),
        "hydraulic_constraint_status": hydraulic_constraint,
        "tube_dp_constraint": tube_dp_constraint,
        "shell_dp_constraint": "SATISFIED" if shell_limit_ok else "NOT_SATISFIED",
        "correlation_applicability_status": applicability,
        "tube_reynolds_number": str(task026_result.reynolds_number),
        "shell_reynolds_number": str(
            getattr(task032_live.flow_state, "shell_side_reynolds_number", "")
        ),
        "shell_side_heat_transfer_coefficient_w_m2_k": str(
            task166_live.corrected_shell_side_heat_transfer_coefficient
        ),
        "tube_mass_flow_kg_s": str(tube_side.mass_flow_kg_s),
        "shell_mass_flow_kg_s": str(shell_stream_spec(case).mass_flow_kg_s),
        "energy_balance_status": "NOT_EVALUATED_IN_POSTPASS",
        "blockers": blockers,
        "property_inputs": {
            "tube": _snapshot_public(tube_snapshot),
            "shell": _snapshot_public(shell_snapshot),
        },
        "shell_dp_components_pa": {
            "central_crossflow": str(task166_live.central_crossflow_contribution),
            "window": str(task166_live.window_contribution),
            "end_zone": str(task166_live.end_zone_pressure_drop),
            "total": str(task166_live.total_shell_pressure_drop),
        },
        "tube_dp_task029_result_hash": (
            task029_outcome.result_hash if task029_outcome is not None else None
        ),
        "mass_flow_binding": mass_flow_binding,
        "tube_hydraulic_recompute_status": tube_hydraulic_recompute_status,
        "shell_hydraulic_recompute_status": shell_hydraulic_recompute_status,
        "task026_input_mass_flow_kg_s": mass_flow_binding["task026_input_mass_flow_kg_s"],
        "task032_input_mass_flow_kg_s": mass_flow_binding["task032_input_mass_flow_kg_s"],
        "shell_dp_task166_result_hash": task166_live.result_hash,
        "coolprop_outlet_domain_checks": coolprop_checks,
        "task174_style_outlet_pressure_window_pass": task174_style_pressure_ok,
        "experimental_transitional_tube_hydraulic": experimental_transitional_tube_hydraulic,
        "hydraulic_model_scope": (
            experimental_transitional_tube_hydraulic.get("hydraulic_model_scope")
            if experimental_transitional_tube_hydraulic
            else None
        ),
    }


def _snapshot_public(snapshot: PropertySnapshot) -> dict[str, str]:
    return {
        "bulk_temperature_k": str(snapshot.bulk_temperature_k),
        "bulk_pressure_pa": str(snapshot.bulk_pressure_pa),
        "density_kg_m3": str(snapshot.density_kg_m3),
        "dynamic_viscosity_pa_s": str(snapshot.dynamic_viscosity_pa_s),
        "property_snapshot_hash": snapshot.property_snapshot_hash,
    }


def _blocked_postpass_document(
    *,
    ctx: Task168CandidateBundle,
    case: EngineeringCase,
    blockers: list[dict[str, str]],
    tube_inlet_temperature_k: Decimal,
    tube_outlet_temperature_k: Decimal,
    shell_inlet_temperature_k: Decimal,
    shell_outlet_temperature_k: Decimal,
    reference_tube_dp_pa: Decimal,
    reference_shell_dp_pa: Decimal,
    recalculated_tube_dp_pa: Decimal | None = None,
    recalculated_shell_dp_pa: Decimal | None = None,
    property_inputs: dict[str, Any] | None = None,
    mass_flow_binding: dict[str, str] | None = None,
    tube_reynolds_number: str | None = None,
    tube_hydraulic_recompute_status: str = "BLOCKED",
    shell_hydraulic_recompute_status: str = "BLOCKED",
) -> dict[str, Any]:
    return {
        "schema_version": "hxforge.live-thermal-state-hydraulic-postpass.v1",
        "authority_id": LIVE_THERMAL_HYDRAULIC_AUTHORITY_ID,
        "task174_hydraulic_status": HYDRAULIC_STATUS_LIVE_POSTPASS,
        "thermal_hydraulic_coupling_status": THERMAL_HYDRAULIC_COUPLING_POSTPASS,
        "property_evaluation_rule_id": PROPERTY_EVALUATION_RULE_ID,
        "candidate_id": ctx.candidate_id,
        "hydraulic_constraint_status": "BLOCKED",
        "blockers": blockers,
        "reference_tube_dp_pa": str(reference_tube_dp_pa),
        "reference_shell_dp_pa": str(reference_shell_dp_pa),
        "recalculated_tube_dp_pa": str(recalculated_tube_dp_pa)
        if recalculated_tube_dp_pa
        else None,
        "recalculated_shell_dp_pa": str(recalculated_shell_dp_pa)
        if recalculated_shell_dp_pa
        else None,
        "tube_inlet_temperature_k": str(tube_inlet_temperature_k),
        "tube_outlet_temperature_k": str(tube_outlet_temperature_k),
        "shell_inlet_temperature_k": str(shell_inlet_temperature_k),
        "shell_outlet_temperature_k": str(shell_outlet_temperature_k),
        "max_tube_dp_pa": str(case.max_tube_side_pressure_drop_pa),
        "max_shell_dp_pa": str(case.max_shell_side_pressure_drop_pa),
        "property_inputs": property_inputs,
        "mass_flow_binding": mass_flow_binding,
        "tube_reynolds_number": tube_reynolds_number,
        "tube_hydraulic_recompute_status": tube_hydraulic_recompute_status,
        "shell_hydraulic_recompute_status": shell_hydraulic_recompute_status,
        "task026_input_mass_flow_kg_s": (
            mass_flow_binding.get("task026_input_mass_flow_kg_s") if mass_flow_binding else None
        ),
        "task032_input_mass_flow_kg_s": (
            mass_flow_binding.get("task032_input_mass_flow_kg_s") if mass_flow_binding else None
        ),
        "tube_dp_constraint": "BLOCKED",
        "shell_dp_constraint": "BLOCKED",
        "correlation_applicability_status": "NOT_EVALUATED",
    }


def postpass_from_mesh_row(
    case: EngineeringCase,
    *,
    candidate_id: str,
    mesh: dict[str, Any],
    native_reference_tube_dp: str | None,
    native_reference_shell_dp: str | None,
) -> dict[str, Any] | None:
    if mesh.get("status") != "NUMERIC_VALID":
        return None
    if (
        mesh.get("tube_outlet_temperature_k") is None
        or mesh.get("shell_outlet_temperature_k") is None
    ):
        return None
    tube_side = tube_stream_spec(case)
    shell_side = shell_stream_spec(case)
    return run_live_thermal_state_hydraulic_postpass(
        case,
        candidate_id=candidate_id,
        tube_inlet_temperature_k=tube_side.inlet_temperature_k,
        tube_outlet_temperature_k=_decimal_field(mesh["tube_outlet_temperature_k"]),
        shell_inlet_temperature_k=shell_side.inlet_temperature_k,
        shell_outlet_temperature_k=_decimal_field(mesh["shell_outlet_temperature_k"]),
        tube_inlet_pressure_pa=tube_side.inlet_pressure_pa,
        shell_inlet_pressure_pa=shell_side.inlet_pressure_pa,
        reference_tube_dp_pa=(
            _decimal_field(native_reference_tube_dp) if native_reference_tube_dp else None
        ),
        reference_shell_dp_pa=(
            _decimal_field(native_reference_shell_dp) if native_reference_shell_dp else None
        ),
    )

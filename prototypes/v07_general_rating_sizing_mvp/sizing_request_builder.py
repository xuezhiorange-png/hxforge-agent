"""Build Task173 sizing requests from general engineering cases (runtime, no tests.*)."""

# ruff: noqa: E501

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.baffle_geometry.models import BaffleOrientation
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    evaluation_input_authority_hash,
    shell_record_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    DiscreteAuthoritySource,
    DiscreteDimensionRole,
    Task168Request,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import (
    SizingRequirementAuthority,
    Task173SizingRequest,
    sizing_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.implementation_validation_request import (
    build_implementation_validation_sizing_request,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1

_MVP_SPACE_ID = "V07-GENERAL-RATING-SIZING-MVP-CANDIDATE-SPACE-R1"
_C3_REFERENCE_SPACE_ID = "V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R3"


def _apply_c3_reference_geometry(
    case: GeneralEngineeringCaseV1, request: Task168Request
) -> Task168Request:
    """Bind Task168 evaluation templates to the C3-qualified reference geometry space."""
    evaluation = request.evaluation_input_authority
    shell_m = case.candidate_constraints.shell_inside_diameter_m
    envelope_m = (shell_m * Decimal("0.9")).quantize(Decimal("0.0000000001"))
    task021_template = cast(dict[str, Any], deepcopy(evaluation.task021_request_template))
    task021_template["placement_envelope"]["tube_center_envelope_diameter_m"] = str(envelope_m)
    task021_template["placement_envelope"]["evidence_refs"] = [
        "V07-GENERAL-RATING-MVP-C3-REFERENCE-PLACEMENT-ENVELOPE"
    ]
    task024_template = evaluation.task024_request_template
    task024_design = replace(
        task024_template.design_authority,
        baffle_thickness_m="0.006",
        orientation_sequence=(BaffleOrientation.BOTTOM,) * case.candidate_constraints.baffle_count,
        shell_to_baffle_diametral_clearance_m="0.003",
        tube_to_baffle_hole_diametral_clearance_m="0.001",
        authority_hash="",
    )
    task024_template = replace(task024_template, design_authority=task024_design)
    evaluation = replace(
        evaluation,
        task021_request_template=task021_template,
        task024_request_template=task024_template,
        canonical_hash="",
    )
    evaluation = replace(evaluation, canonical_hash=evaluation_input_authority_hash(evaluation))
    authorities = list(request.discrete_candidate_set_authorities)
    for index, authority in enumerate(authorities):
        if authority.dimension_role is DiscreteDimensionRole.BAFFLE_CUT:
            changed = replace(
                authority,
                authority_id=f"{_C3_REFERENCE_SPACE_ID}:BAFFLE_CUT",
                authority_version="R3",
                source_class=DiscreteAuthoritySource.OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET,
                source_id=_C3_REFERENCE_SPACE_ID,
                source_revision="FROZEN_BEFORE_PUBLIC_EXECUTION",
                approval_status="APPROVED",
                values=(Decimal("0.30"),),
                evidence_refs=(
                    "OWNER_DIRECTION:C3_DOMAIN_QUALIFIED_IMPLEMENTATION_VALIDATION",
                    "GENERAL_MVP_R3_NOT_PRODUCTION_APPROVED",
                ),
                provenance_refs=(
                    "OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET",
                    "GENERAL_MVP_WORKFLOW_NOT_PRODUCTION_APPROVED",
                ),
                canonical_hash="",
            )
            authorities[index] = replace(changed, canonical_hash=discrete_authority_hash(changed))
    return replace(
        request,
        evaluation_input_authority=evaluation,
        discrete_candidate_set_authorities=tuple(authorities),
    )


def _apply_case_geometry_catalog(
    case: GeneralEngineeringCaseV1, request: Task168Request
) -> Task168Request:
    constraints = case.candidate_constraints
    shell_record = replace(
        request.shell_geometry_catalog.records[0],
        shell_inside_diameter_m=str(constraints.shell_inside_diameter_m),
        record_hash="",
    )
    shell_record = replace(shell_record, record_hash=shell_record_hash(shell_record))
    catalog = replace(
        request.shell_geometry_catalog,
        records=(shell_record,),
        catalog_hash="",
    )
    from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
        shell_catalog_hash,
    )

    catalog = replace(catalog, catalog_hash=shell_catalog_hash(catalog))
    evaluation = request.evaluation_input_authority
    task021_template = cast(dict[str, Any], deepcopy(evaluation.task021_request_template))
    envelope_m = (constraints.shell_inside_diameter_m * Decimal("0.9")).quantize(
        Decimal("0.0000000001")
    )
    task021_template["placement_envelope"]["tube_center_envelope_diameter_m"] = str(envelope_m)
    evaluation = replace(evaluation, task021_request_template=task021_template, canonical_hash="")
    evaluation = replace(evaluation, canonical_hash=evaluation_input_authority_hash(evaluation))
    authorities = list(request.discrete_candidate_set_authorities)
    role_map: dict[DiscreteDimensionRole, Decimal | int] = {
        DiscreteDimensionRole.TUBE_OUTER_DIAMETER: constraints.tube_outer_diameter_m,
        DiscreteDimensionRole.TUBE_WALL_THICKNESS: constraints.tube_wall_thickness_m,
        DiscreteDimensionRole.TUBE_PITCH: constraints.tube_pitch_m,
        DiscreteDimensionRole.BAFFLE_COUNT: constraints.baffle_count,
        DiscreteDimensionRole.TUBE_PASS_COUNT: constraints.tube_pass_count,
    }
    for index, authority in enumerate(authorities):
        if authority.dimension_role in role_map:
            value = role_map[authority.dimension_role]
            changed = replace(authority, values=(value,), canonical_hash="")
            authorities[index] = replace(changed, canonical_hash=discrete_authority_hash(changed))
    return replace(
        request,
        shell_geometry_catalog=catalog,
        evaluation_input_authority=evaluation,
        discrete_candidate_set_authorities=tuple(authorities),
    )


def build_task173_sizing_request(case: GeneralEngineeringCaseV1) -> Task173SizingRequest:
    """Bind general case targets to the reviewed Task173 R2 validation candidate space."""
    constraints = case.candidate_constraints
    max_n = case.solver_budget.max_candidates_to_rate
    lengths = constraints.tube_lengths_m[:max_n]
    spacings = constraints.baffle_spacings_m
    shell_diameter = str(constraints.shell_inside_diameter_m)
    tube_od = str(constraints.tube_outer_diameter_m)
    tube_wall = str(constraints.tube_wall_thickness_m)
    tube_pitch = str(constraints.tube_pitch_m)
    if case.bind_task172_c3_reference_geometry:
        shell_diameter = "0.500"
        tube_od = "0.01905"
        tube_wall = "0.00165"
        tube_pitch = "0.0254"
    base = build_implementation_validation_sizing_request(
        tube_lengths=tuple(lengths),
        baffle_spacings=tuple(spacings),
        tube_pass_counts=(constraints.tube_pass_count,),
        validation_space_r2=True,
        shell_inside_diameter_m=shell_diameter,
        tube_outer_diameter_m=tube_od,
        tube_wall_thickness_m=tube_wall,
        tube_pitch_m=tube_pitch,
        baffle_spacing_m=str(spacings[0]),
        baffle_count=constraints.baffle_count,
    )
    task168 = _apply_case_geometry_catalog(case, base.task168_candidate_request)
    if case.bind_task172_c3_reference_geometry:
        task168 = _apply_c3_reference_geometry(case, task168)
    discrete_bindings = tuple(
        sorted(
            (
                (item.authority_id, discrete_authority_hash(item))
                for item in task168.discrete_candidate_set_authorities
            ),
            key=lambda item: item[0].encode("utf-8"),
        )
    )
    # Task172 constitutive closure remains bound to the implementation-validation
    # thermal templates until project-native thermal authority wiring lands; inlet
    # temperatures are disclosed in request_metadata and engineering reports.
    requirement = base.requirement_authority
    requirement_projection: dict[str, Any] = {
        "requirement_id": requirement.requirement_id,
        "authority_version": requirement.authority_version,
        "source_class": requirement.source_class,
        "source_id": requirement.source_id,
        "source_revision": requirement.source_revision,
        "approval_status": requirement.approval_status,
        "evidence_refs": (
            *requirement.evidence_refs,
            f"GENERAL_MVP_CASE_ID::{case.engineering_case_id}",
            f"GENERAL_MVP_SPACE_ID::{_MVP_SPACE_ID}",
        ),
        "provenance_refs": (
            *requirement.provenance_refs,
            "GENERAL_MVP_WORKFLOW_NOT_PRODUCTION_APPROVED",
        ),
        "required_duty_w": case.target_duty_w,
        "max_tube_dp_pa": case.max_tube_side_pressure_drop_pa,
        "max_shell_dp_pa": case.max_shell_side_pressure_drop_pa,
        "allowed_construction_families": requirement.allowed_construction_families,
        "required_screening_policy_id": requirement.required_screening_policy_id,
        "discrete_candidate_authority_ids_and_hashes": discrete_bindings,
    }
    requirement_hash_projection = {
        **requirement_projection,
        "required_duty_w": str(case.target_duty_w),
        "max_tube_dp_pa": str(case.max_tube_side_pressure_drop_pa),
        "max_shell_dp_pa": str(case.max_shell_side_pressure_drop_pa),
    }
    requirement = SizingRequirementAuthority(
        **requirement_projection,
        canonical_hash=canonical_sha256(requirement_hash_projection),
    )
    metadata = dict(base.request_metadata)
    metadata.update(
        {
            "workflow": "V07_GENERAL_RATING_SIZING_NATIVE_BINDING_R3",
            "kernel_thermal_variant": "TUBE_HOT_SHELL_COLD",
            "bind_task172_c3_reference_geometry": str(
                case.bind_task172_c3_reference_geometry
            ).lower(),
            "engineering_case_id": case.engineering_case_id,
            "experimental_ranking": "true",
            "production_design_approved": "false",
            "golden_reuse": "false",
            "cold_inlet_temperature_k": str(case.cold_side.inlet_temperature_k),
            "hot_inlet_temperature_k": str(case.hot_side.inlet_temperature_k),
            "cold_inlet_pressure_pa": str(case.cold_side.inlet_pressure_pa),
            "hot_inlet_pressure_pa": str(case.hot_side.inlet_pressure_pa),
        }
    )
    return base.model_copy(
        update={
            "requirement_authority": requirement,
            "task168_candidate_request": task168,
            "request_metadata": tuple(sorted(metadata.items(), key=lambda item: item[0])),
        }
    )


def build_task168_request(case: GeneralEngineeringCaseV1) -> Task168Request:
    return build_task173_sizing_request(case).task168_candidate_request


def sizing_request_identity(request: Task173SizingRequest) -> str:
    return sizing_request_hash(request)

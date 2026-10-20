"""Build Task173 sizing requests from general engineering cases (runtime, no tests.*)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    shell_record_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
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
        discrete_candidate_set_authorities=tuple(authorities),
    )


def build_task173_sizing_request(case: GeneralEngineeringCaseV1) -> Task173SizingRequest:
    """Bind general case targets to the reviewed Task173 R2 validation candidate space."""
    constraints = case.candidate_constraints
    max_n = case.solver_budget.max_candidates_to_rate
    lengths = constraints.tube_lengths_m[:max_n]
    spacings = constraints.baffle_spacings_m
    base = build_implementation_validation_sizing_request(
        tube_lengths=tuple(lengths),
        baffle_spacings=tuple(spacings),
        tube_pass_counts=(constraints.tube_pass_count,),
        validation_space_r2=True,
        shell_inside_diameter_m=str(constraints.shell_inside_diameter_m),
        tube_outer_diameter_m=str(constraints.tube_outer_diameter_m),
        tube_wall_thickness_m=str(constraints.tube_wall_thickness_m),
        tube_pitch_m=str(constraints.tube_pitch_m),
        baffle_spacing_m=str(spacings[0]),
        baffle_count=constraints.baffle_count,
    )
    task168 = _apply_case_geometry_catalog(case, base.task168_candidate_request)
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
        "discrete_candidate_authority_ids_and_hashes": (
            requirement.discrete_candidate_authority_ids_and_hashes
        ),
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
            "workflow": "V07_GENERAL_RATING_SIZING_NATIVE_BINDING_R2",
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

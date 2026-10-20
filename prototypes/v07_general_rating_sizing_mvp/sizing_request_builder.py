"""Build Task173 sizing requests from general engineering cases."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from importlib import import_module
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    evaluation_input_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    DiscreteDimensionRole,
    Task168Request,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import (
    SizingRequirementAuthority,
    SizingServiceAuthority,
    Task173SizingRequest,
    sizing_request_hash,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1

_MVP_SPACE_ID = "V07-GENERAL-RATING-SIZING-MVP-CANDIDATE-SPACE-R1"


def _real_request_module():
    return import_module("tests.exchangers.shell_tube.test_task168_manufacturable_candidates")


def build_task168_request(case: GeneralEngineeringCaseV1) -> Task168Request:
    """Materialize a Task168 request via the validated test-owned producer chain."""
    mod = _real_request_module()
    real_request = mod._real_request
    constraints = case.candidate_constraints
    lengths = constraints.tube_lengths_m[: case.solver_budget.max_candidates_to_rate]
    spacings = constraints.baffle_spacings_m
    request = real_request(
        shell_diameter=str(constraints.shell_inside_diameter_m),
        tube_outer_diameter=str(constraints.tube_outer_diameter_m),
        tube_wall_thickness=str(constraints.tube_wall_thickness_m),
        tube_length=str(lengths[0]),
        tube_pitch=str(constraints.tube_pitch_m),
        baffle_spacing=str(spacings[0]),
        baffle_count=constraints.baffle_count,
    )
    task039 = import_module("hexagent.release_demo.v0_4.task039")
    evaluation = request.evaluation_input_authority
    task021_template = deepcopy(evaluation.task021_request_template)
    task021_template["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.72"
    task021_template["placement_envelope"]["evidence_refs"] = ["general-mvp-placement-envelope"]
    evaluation = replace(
        evaluation,
        task021_request_template=task021_template,
        canonical_hash="",
    )
    evaluation = replace(
        evaluation,
        canonical_hash=evaluation_input_authority_hash(evaluation),
    )
    request = replace(
        request,
        task020_configuration=task039._build_actual_chain()["task020_config"],
        evaluation_input_authority=evaluation,
    )
    authorities = list(request.discrete_candidate_set_authorities)
    for index, authority in enumerate(authorities):
        if authority.dimension_role is DiscreteDimensionRole.TUBE_LENGTH:
            changed = replace(authority, values=lengths, canonical_hash="")
            authorities[index] = replace(changed, canonical_hash=discrete_authority_hash(changed))
        elif authority.dimension_role is DiscreteDimensionRole.BAFFLE_SPACING:
            changed = replace(authority, values=spacings, canonical_hash="")
            authorities[index] = replace(changed, canonical_hash=discrete_authority_hash(changed))
        elif authority.dimension_role is DiscreteDimensionRole.TUBE_PASS_COUNT:
            values = (constraints.tube_pass_count,)
            changed = replace(authority, values=values, canonical_hash="")
            authorities[index] = replace(changed, canonical_hash=discrete_authority_hash(changed))
    return replace(request, discrete_candidate_set_authorities=tuple(authorities))


def build_task173_sizing_request(case: GeneralEngineeringCaseV1) -> Task173SizingRequest:
    task168_request = build_task168_request(case)
    authority_bindings = tuple(
        sorted(
            (
                (item.authority_id, discrete_authority_hash(item))
                for item in task168_request.discrete_candidate_set_authorities
            ),
            key=lambda item: item[0].encode("utf-8"),
        )
    )
    requirement_projection: dict[str, Any] = {
        "requirement_id": f"GENERAL-MVP-{case.engineering_case_id}",
        "authority_version": "R1",
        "source_class": "EXPERIMENTAL_GENERAL_ENGINEERING_CASE",
        "source_id": _MVP_SPACE_ID,
        "source_revision": case.engineering_case_id,
        "approval_status": "APPROVED",
        "evidence_refs": (
            f"GENERAL_CASE_ID::{case.engineering_case_id}",
            f"CANDIDATE_SPACE_AUTHORITY::{_MVP_SPACE_ID}",
        ),
        "provenance_refs": (
            "EXPERIMENTAL_MVP_NOT_PRODUCTION_DESIGN_APPROVED",
            "NUMERICAL_AUTHORITY_STATUS=CANDIDATE",
        ),
        "required_duty_w": case.target_duty_w,
        "max_tube_dp_pa": case.max_tube_side_pressure_drop_pa,
        "max_shell_dp_pa": case.max_shell_side_pressure_drop_pa,
        "allowed_construction_families": ("FIXED_TUBESHEET",),
        "required_screening_policy_id": "V07-T173-SIZING-MANDATORY-SCREENING-R1",
        "discrete_candidate_authority_ids_and_hashes": authority_bindings,
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
    service = SizingServiceAuthority(
        authority_id="V07-T173-SIZING-AUTHORITY-PACKAGE-R2",
        authority_hash="750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9",
        construction_family="FIXED_TUBESHEET",
        shell_family="E_SHELL",
        shell_pass_count=1,
        tube_topology="ONE_DECLARED_STRAIGHT_THROUGH_TUBE_PASS",
        countercurrent=True,
        steady_state=True,
        single_phase=True,
        newtonian=True,
        fluid="PURE_ORDINARY_WATER",
        property_profile_id="V07-T172-WATER-PROPERTY-PROFILE-R2",
        clean_surface_only=True,
        tube_mass_flow_kg_s=Decimal("12.000000"),
        shell_mass_flow_kg_s=Decimal("20.000000"),
        minimum_temperature_k=Decimal("298.15"),
        maximum_temperature_k=Decimal("300.00"),
        minimum_pressure_pa=Decimal("100000"),
        maximum_pressure_pa=Decimal("101325"),
        production_mesh_profile_id="V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1",
    )
    return Task173SizingRequest(
        authority_package_id="V07-T173-SIZING-AUTHORITY-PACKAGE-R2",
        authority_package_hash="750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9",
        sizing_scope_projection_hash="7072db59a1f80609b0d502de7dc61a8d047d9cbe302c40b717a39f443440570b",
        service_authority=service,
        requirement_authority=requirement,
        task168_candidate_request=task168_request,
        ranking_policy_id="V07-T173-SIZING-RANKING-POLICY-R1",
        ranking_policy_hash="0d9f6c410414f5a556e92dad15b86fabc4c28c07416513a71645160a0349fba6",
        request_metadata=(
            ("workflow", "V07_GENERAL_RATING_SIZING_END_TO_END_MVP_R1"),
            ("engineering_case_id", case.engineering_case_id),
            ("experimental_ranking", "true"),
            ("production_design_approved", "false"),
            ("golden_reuse", "false"),
        ),
    )


def sizing_request_identity(request: Task173SizingRequest) -> str:
    return sizing_request_hash(request)

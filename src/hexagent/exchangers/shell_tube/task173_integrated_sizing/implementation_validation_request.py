"""Task173 implementation-validation sizing request builder (not production approval)."""

# ruff: noqa: E501

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_space_hash as task168_candidate_space_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    evaluation_input_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.implementation_validation_task168 import (
    build_implementation_validation_task168_reference,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    DiscreteAuthoritySource,
    DiscreteDimensionRole,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import (
    SizingRequirementAuthority,
    SizingServiceAuthority,
    Task173SizingRequest,
)
from hexagent.release_demo.v0_4 import task039

_IMPLEMENTATION_VALIDATION_DUTY_W = Decimal("10000")
_IMPLEMENTATION_VALIDATION_MAX_TUBE_DP_PA = Decimal("1200")
_IMPLEMENTATION_VALIDATION_MAX_SHELL_DP_PA = Decimal("1200")
_VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID = (
    "V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R2"
)
_ATTEMPT_3_CANDIDATE_SPACE_AUTHORITY_ID = (
    "V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R3"
)


def build_implementation_validation_sizing_request(
    *,
    tube_lengths: tuple[Decimal, ...] = (Decimal("4.85"),),
    baffle_spacings: tuple[Decimal, ...] = (Decimal("0.97"),),
    tube_pass_counts: tuple[int, ...] = (1,),
    validation_space_r2: bool = False,
    shell_inside_diameter_m: str = "0.8",
    tube_outer_diameter_m: str = "0.02",
    tube_wall_thickness_m: str = "0.002",
    tube_pitch_m: str = "0.031",
    baffle_spacing_m: str | None = None,
    baffle_count: int = 4,
) -> Task173SizingRequest:
    spacing = baffle_spacing_m if baffle_spacing_m is not None else str(baffle_spacings[0])
    candidate_request = build_implementation_validation_task168_reference(
        shell_diameter=shell_inside_diameter_m,
        tube_outer_diameter=tube_outer_diameter_m,
        tube_wall_thickness=tube_wall_thickness_m,
        tube_length=str(tube_lengths[0]),
        tube_pitch=tube_pitch_m,
        baffle_spacing=spacing,
        baffle_count=baffle_count,
    )
    evaluation = candidate_request.evaluation_input_authority
    task021_template = cast(dict[str, Any], deepcopy(evaluation.task021_request_template))
    task021_template["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.72"
    task021_template["placement_envelope"]["evidence_refs"] = [
        "implementation-validation-only-placement-envelope"
    ]
    evaluation = replace(
        evaluation,
        task021_request_template=task021_template,
        canonical_hash="",
    )
    evaluation = replace(
        evaluation,
        canonical_hash=evaluation_input_authority_hash(evaluation),
    )
    candidate_request = replace(
        candidate_request,
        task020_configuration=task039._build_actual_chain()["task020_config"],
        evaluation_input_authority=evaluation,
    )
    authorities = list(candidate_request.discrete_candidate_set_authorities)
    for index, authority in enumerate(authorities):
        if authority.dimension_role in (
            DiscreteDimensionRole.TUBE_LENGTH,
            DiscreteDimensionRole.BAFFLE_SPACING,
        ):
            values = (
                tube_lengths
                if authority.dimension_role is DiscreteDimensionRole.TUBE_LENGTH
                else baffle_spacings
            )
            if validation_space_r2:
                changed = replace(
                    authority,
                    authority_id=(
                        f"{_VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID}:"
                        f"{authority.dimension_role.value}"
                    ),
                    authority_version="R2",
                    source_class=(
                        DiscreteAuthoritySource.OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET
                    ),
                    source_id=_VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID,
                    source_revision="FROZEN_BEFORE_PUBLIC_EXECUTION",
                    approval_status="APPROVED",
                    values=values,
                    evidence_refs=("OWNER_DIRECTION:IMPLEMENTATION_VALIDATION_CANDIDATE_SPACE_R2",),
                    provenance_refs=(
                        "TASK173_IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_OR_RELEASE",
                    ),
                    canonical_hash="",
                )
            else:
                changed = replace(authority, values=values, canonical_hash="")
            authorities[index] = replace(changed, canonical_hash=discrete_authority_hash(changed))
        elif authority.dimension_role is DiscreteDimensionRole.TUBE_PASS_COUNT:
            changed = replace(authority, values=tube_pass_counts, canonical_hash="")
            authorities[index] = replace(changed, canonical_hash=discrete_authority_hash(changed))
    candidate_request = replace(
        candidate_request,
        discrete_candidate_set_authorities=tuple(authorities),
    )
    authority_bindings = tuple(
        sorted(
            (
                (item.authority_id, discrete_authority_hash(item))
                for item in candidate_request.discrete_candidate_set_authorities
            ),
            key=lambda item: item[0].encode("utf-8"),
        )
    )
    validation_space_hash: str | None = None
    if validation_space_r2:
        validation_space_projection: dict[str, Any] = {
            "authority_id": _VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID,
            "authority_version": "R2",
            "source_class": "OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET",
            "approval_status": "APPROVED",
            "classification": "IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_NOT_RELEASE_AUTHORITY",
            "frozen_dimensions": {
                "TUBE_LENGTH_M": [str(item) for item in tube_lengths],
                "BAFFLE_SPACING_M": [str(item) for item in baffle_spacings],
                "BAFFLE_COUNT": ["4"],
            },
            "expected_structurally_admitted_pairs": [
                ["4.85", "0.97"],
                ["4.90", "0.98"],
            ],
            "expected_structurally_blocked_pairs": [
                ["4.85", "0.98"],
                ["4.90", "0.97"],
            ],
            "all_discrete_authority_hashes": [
                [item.dimension_role.value, discrete_authority_hash(item)]
                for item in sorted(authorities, key=lambda item: item.dimension_role.value)
            ],
            "task168_candidate_space_hash": task168_candidate_space_hash(
                candidate_request, tuple(authorities)
            ),
            "resource_limits": {
                "MAX_VALUES_PER_ROLE": 32,
                "MAX_THEORETICAL_COMBINATIONS": 4096,
                "MAX_MATERIALIZED_CANDIDATES": 4096,
            },
            "candidate_space_changed_after_execution": False,
        }
        validation_space_hash = canonical_sha256(validation_space_projection)
    requirement_projection: dict[str, Any] = {
        "requirement_id": (
            "TASK173-SIZING-IMPLEMENTATION-VALIDATION-R2"
            if validation_space_r2
            else "TASK173-SIZING-IMPLEMENTATION-VALIDATION-R1"
        ),
        "authority_version": "R2" if validation_space_r2 else "R1",
        "source_class": "IMPLEMENTATION_VALIDATION_ONLY",
        "source_id": (
            _VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID
            if validation_space_r2
            else "TASK173-SIZING-IMPLEMENTATION-VALIDATION-FIXTURE-R1"
        ),
        "source_revision": "FROZEN_BEFORE_PUBLIC_EXECUTION"
        if validation_space_r2
        else "FIXED_BEFORE_EXECUTION",
        "approval_status": "APPROVED",
        "evidence_refs": (
            "TASK173-IMPLEMENTATION-VALIDATION-ONLY-NOT-GOLDEN",
            *(
                (f"VALIDATION_CANDIDATE_SPACE_SHA256::{validation_space_hash}",)
                if validation_space_hash is not None
                else ()
            ),
        ),
        "provenance_refs": (
            "TASK173-IMPLEMENTATION-VALIDATION-ONLY-NOT-RELEASE-AUTHORITY",
            *(
                (f"VALIDATION_CANDIDATE_SPACE::{_VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID}",)
                if validation_space_r2
                else ()
            ),
        ),
        "required_duty_w": _IMPLEMENTATION_VALIDATION_DUTY_W,
        "max_tube_dp_pa": _IMPLEMENTATION_VALIDATION_MAX_TUBE_DP_PA,
        "max_shell_dp_pa": _IMPLEMENTATION_VALIDATION_MAX_SHELL_DP_PA,
        "allowed_construction_families": ("FIXED_TUBESHEET",),
        "required_screening_policy_id": "V07-T173-SIZING-MANDATORY-SCREENING-R1",
        "discrete_candidate_authority_ids_and_hashes": authority_bindings,
    }
    requirement_hash_projection = {
        **requirement_projection,
        "required_duty_w": str(_IMPLEMENTATION_VALIDATION_DUTY_W),
        "max_tube_dp_pa": str(_IMPLEMENTATION_VALIDATION_MAX_TUBE_DP_PA),
        "max_shell_dp_pa": str(_IMPLEMENTATION_VALIDATION_MAX_SHELL_DP_PA),
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
        task168_candidate_request=candidate_request,
        ranking_policy_id="V07-T173-SIZING-RANKING-POLICY-R1",
        ranking_policy_hash="0d9f6c410414f5a556e92dad15b86fabc4c28c07416513a71645160a0349fba6",
        request_metadata=(
            ("authority_use", "IMPLEMENTATION_VALIDATION_ONLY"),
            ("golden", "false"),
            ("release_authority", "false"),
            *(
                (
                    (
                        "validation_candidate_space_authority_id",
                        _VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID,
                    ),
                    ("validation_candidate_space_authority_hash", validation_space_hash),
                    ("candidate_space_frozen_before_execution", "true"),
                )
                if validation_space_r2 and validation_space_hash is not None
                else ()
            ),
        ),
    )

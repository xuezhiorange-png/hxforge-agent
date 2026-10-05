"""Contract tests for the separate v0.7 TASK173 Sizing public mode."""

from __future__ import annotations

import itertools
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_space_hash as task168_candidate_space_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    evaluation_input_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    CandidateStage,
    DiscreteAuthoritySource,
    DiscreteDimensionRole,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateShellFlowAuthority,
    CandidateTask172LocalRequest,
    CandidateThermalBinding,
    CandidateTopologyBinding,
    LocalState,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as rating_service
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import (
    SizingRequirementAuthority,
    SizingServiceAuthority,
    Task173SizingRequest,
    Task173SizingSuccessResult,
    recompute_sizing_result_hash,
    sizing_request_hash,
    validate_sizing_request,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing import service as sizing
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    CandidateTask174Request,
    Task174BlockedResult,
    Task174NativeOutputs,
    Task174SuccessResult,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    validate_candidate_request as validate_candidate_task174,
)
from hexagent.release_demo.v0_4 import task039
from tests.exchangers.shell_tube.test_task168_manufacturable_candidates import (
    _real_request as _task168_real_request,
)

_IMPLEMENTATION_VALIDATION_DUTY_W = Decimal("10000")
_IMPLEMENTATION_VALIDATION_MAX_TUBE_DP_PA = Decimal("1200")
_IMPLEMENTATION_VALIDATION_MAX_SHELL_DP_PA = Decimal("1200")
_VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID = (
    "V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R2"
)
_ATTEMPT_3_CANDIDATE_SPACE_AUTHORITY_ID = (
    "V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R3"
)


def _sizing_request(
    *,
    tube_lengths: tuple[Decimal, ...] = (Decimal("4.85"),),
    baffle_spacings: tuple[Decimal, ...] = (Decimal("0.97"),),
    tube_pass_counts: tuple[int, ...] = (1,),
    validation_space_r2: bool = False,
) -> Task173SizingRequest:
    candidate_request = _task168_real_request(
        shell_diameter="0.8",
        tube_outer_diameter="0.02",
        tube_wall_thickness="0.002",
        tube_length=str(tube_lengths[0]),
        tube_pitch="0.031",
        baffle_spacing=str(baffle_spacings[0]),
        baffle_count=4,
    )
    evaluation = candidate_request.evaluation_input_authority
    task021_template = deepcopy(evaluation.task021_request_template)
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


def _attempt_3_sizing_request() -> Task173SizingRequest:
    """Freeze two reference-bound geometries differing only in baffle cut."""
    from hexagent.exchangers.shell_tube.baffle_geometry.models import BaffleOrientation

    candidate_request = _task168_real_request(
        shell_diameter="0.500",
        tube_outer_diameter="0.01905",
        tube_wall_thickness="0.00165",
        tube_length="6.0",
        tube_pitch="0.0254",
        baffle_spacing="1.2",
        baffle_count=4,
    )
    evaluation = candidate_request.evaluation_input_authority
    task021_template = deepcopy(evaluation.task021_request_template)
    task021_template["placement_envelope"]["tube_center_envelope_diameter_m"] = "0.45"
    task021_template["placement_envelope"]["evidence_refs"] = [
        "docs/tasks/TASK-172-v0.7-r118a-project-engineering-native-geometry-input-authority-candidate-r1.md#project-design-inputs",
        "docs/tasks/evidence/TASK-172-r118a-project-engineering-native-geometry-input-authority-candidate-r1.json#/candidate_inputs/TASK021/placement_envelope",
    ]
    task024_template = evaluation.task024_request_template
    task024_design = replace(
        task024_template.design_authority,
        baffle_thickness_m="0.006",
        orientation_sequence=(BaffleOrientation.BOTTOM,) * 4,
        shell_to_baffle_diametral_clearance_m="0.003",
        tube_to_baffle_hole_diametral_clearance_m="0.001",
        authority_hash="",
    )
    task024_template = replace(
        task024_template,
        design_authority=task024_design,
    )
    evaluation = replace(
        evaluation,
        task021_request_template=task021_template,
        task024_request_template=task024_template,
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
        if authority.dimension_role is DiscreteDimensionRole.BAFFLE_CUT:
            changed = replace(
                authority,
                authority_id=(f"{_ATTEMPT_3_CANDIDATE_SPACE_AUTHORITY_ID}:BAFFLE_CUT"),
                authority_version="R3",
                source_class=(DiscreteAuthoritySource.OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET),
                source_id=_ATTEMPT_3_CANDIDATE_SPACE_AUTHORITY_ID,
                source_revision="FROZEN_BEFORE_PUBLIC_EXECUTION",
                approval_status="APPROVED",
                values=(Decimal("0.25"), Decimal("0.30")),
                evidence_refs=(
                    "OWNER_DIRECTION:ATTEMPT_3_C3_DOMAIN_QUALIFIED_IMPLEMENTATION_VALIDATION_RECOVERY",
                    "IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_NOT_RELEASE_AUTHORITY",
                ),
                provenance_refs=(
                    "OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET",
                    "IMPLEMENTATION_VALIDATION_ONLY_NOT_BUSINESS_REQUIREMENT",
                ),
                canonical_hash="",
            )
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
    frozen_dimensions = {
        item.dimension_role.value: [str(value) for value in task168._sort_values(item.values)]
        for item in sorted(
            candidate_request.discrete_candidate_set_authorities,
            key=lambda item: item.dimension_role.value,
        )
    }
    task168_space_hash = task168_candidate_space_hash(
        candidate_request, tuple(candidate_request.discrete_candidate_set_authorities)
    )
    candidate_space_projection: dict[str, Any] = {
        "authority_id": _ATTEMPT_3_CANDIDATE_SPACE_AUTHORITY_ID,
        "authority_version": "R3",
        "source_class": "OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET",
        "approval_status": "APPROVED",
        "classification": "IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_NOT_RELEASE_AUTHORITY",
        "frozen_dimensions": frozen_dimensions,
        "theoretical_candidate_count": 2,
        "task168_candidate_space_hash": task168_space_hash,
        "all_discrete_authority_hashes": [
            [item.dimension_role.value, discrete_authority_hash(item)]
            for item in sorted(
                candidate_request.discrete_candidate_set_authorities,
                key=lambda item: item.dimension_role.value,
            )
        ],
        "resource_limits": {
            "MAX_VALUES_PER_ROLE": 32,
            "MAX_THEORETICAL_COMBINATIONS": 4096,
            "MAX_MATERIALIZED_CANDIDATES": 4096,
        },
        "performance_output_used_to_select_candidates": False,
        "c3_applicability_used_to_select_fixture": True,
        "post_result_performance_tuning": False,
        "candidate_space_changed_after_execution": False,
    }
    candidate_space_hash = canonical_sha256(candidate_space_projection)
    requirement_projection: dict[str, Any] = {
        "requirement_id": "TASK173-SIZING-IMPLEMENTATION-VALIDATION-R3",
        "authority_version": "R3",
        "source_class": "IMPLEMENTATION_VALIDATION_ONLY",
        "source_id": _ATTEMPT_3_CANDIDATE_SPACE_AUTHORITY_ID,
        "source_revision": "FROZEN_BEFORE_PUBLIC_EXECUTION",
        "approval_status": "APPROVED",
        "evidence_refs": (
            "TASK173-IMPLEMENTATION-VALIDATION-ONLY-NOT-GOLDEN",
            f"VALIDATION_CANDIDATE_SPACE_SHA256::{candidate_space_hash}",
        ),
        "provenance_refs": (
            "TASK173-IMPLEMENTATION-VALIDATION-ONLY-NOT-RELEASE-AUTHORITY",
            f"VALIDATION_CANDIDATE_SPACE::{_ATTEMPT_3_CANDIDATE_SPACE_AUTHORITY_ID}",
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
    request = Task173SizingRequest(
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
            ("validation_candidate_space_authority_id", _ATTEMPT_3_CANDIDATE_SPACE_AUTHORITY_ID),
            ("validation_candidate_space_authority_hash", candidate_space_hash),
            ("candidate_space_frozen_before_execution", "true"),
        ),
    )
    return request


def _attempt_3_geometry_and_c3_preflight(
    request: Task173SizingRequest,
) -> tuple[dict[str, Any], ...]:
    """Run only native geometry producers and a service-state C3 check."""
    from hexagent.exchangers.shell_tube.tube_side_thermal import (
        FlowRegime,
        ThermalBoundaryCondition,
        check_pr_envelope,
        compute_single_phase,
    )
    from hexagent.properties.base import FluidIdentifier
    from hexagent.properties.coolprop_provider import CoolPropProvider

    task168_request = request.task168_candidate_request
    authorities = task168._authority_map(task168_request)
    dimensions = tuple(
        task168._sort_values(authorities[role].values)
        for role in task168.DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    provider = CoolPropProvider()
    state = provider.state_tp(FluidIdentifier("Water", "HEOS"), 300.0, 101325.0)
    outcomes: list[dict[str, Any]] = []
    for combination in itertools.product(
        task168_request.shell_geometry_catalog.records, *dimensions
    ):
        shell_record = combination[0]
        candidate = task168._candidate(
            task168_request,
            authorities,
            shell_record,
            tuple(combination[1:]),
        )
        assert task168._structural_blockers(candidate) == ()
        configuration = task168._materialize_candidate_configuration(
            task168_request.task020_configuration, candidate
        )
        layout_outcome = task168.validate_task021(
            task168._task021_payload(
                task168_request.evaluation_input_authority, candidate, configuration
            ),
            software_version="task168-orchestration",
            git_commit="task168-orchestration",
        )
        assert getattr(layout_outcome, "status", None) == "VALID"
        layout = layout_outcome.layout
        shell_outcome = task168.validate_task022(
            task168._task022_payload(
                task168_request.evaluation_input_authority,
                candidate,
                configuration,
                layout,
                shell_record,
            ),
            software_version="task168-orchestration",
            git_commit="task168-orchestration",
        )
        assert getattr(shell_outcome, "status", None) == "VALID"
        shell_geometry = shell_outcome.geometry
        task024_request = task168._task024_payload(
            task168_request.evaluation_input_authority,
            candidate,
            configuration,
            layout,
            shell_geometry,
            preserve_template_orientation_sequence=True,
        )
        task024_outcome = task168.validate_task024(task024_request)
        task025_request = task168._task025_payload(
            task168_request.evaluation_input_authority.task025_request_template,
            candidate,
            configuration,
            layout,
            CandidateStage.TUBE_SIDE,
            "evaluation_input_authority.task025_request_template",
        )
        task025 = task168.evaluate_task025(task025_request)
        assert type(task025).__name__ == "Task025ValidResult"
        tube_output = compute_single_phase(
            Decimal("12.000000"),
            Decimal(str(state.density_kg_m3)),
            Decimal(str(state.viscosity_pa_s)),
            Decimal(str(state.conductivity_w_m_k)),
            Decimal(str(state.cp_j_kg_k)),
            task025.total_parallel_flow_area_m2,
            task025.hydraulic_diameter_m,
            ThermalBoundaryCondition.CWT,
        )
        assert tube_output.flow_regime is FlowRegime.TURBULENT
        assert Decimal("3000") < tube_output.reynolds_number < Decimal("5000000")
        assert check_pr_envelope(tube_output.flow_regime, tube_output.prandtl_number)
        outcomes.append(
            {
                "candidate_id": candidate.candidate_id,
                "candidate_hash": candidate.candidate_hash,
                "selected_baffle_cut_fraction": str(candidate.baffle_cut_fraction),
                "task020_configuration_id": configuration.configuration_id,
                "task020_configuration_hash": configuration.configuration_hash,
                "task021_layout_id": layout.layout_id,
                "task021_layout_hash": layout.layout_hash,
                "task022_geometry_id": shell_geometry.geometry_id,
                "task022_geometry_hash": shell_geometry.geometry_hash,
                "task024_status": getattr(task024_outcome.status, "value", task024_outcome.status),
                "task024_geometry_id": (
                    None
                    if getattr(task024_outcome, "geometry", None) is None
                    else task024_outcome.geometry.geometry_id
                ),
                "task024_geometry_hash": (
                    None
                    if getattr(task024_outcome, "geometry", None) is None
                    else task024_outcome.geometry.geometry_hash
                ),
                "task024_baffle_thickness_m": task024_request["design_authority"][
                    "baffle_thickness_m"
                ],
                "task024_shell_to_baffle_clearance_m": task024_request["design_authority"][
                    "shell_to_baffle_diametral_clearance_m"
                ],
                "task024_orientation_sequence": tuple(
                    getattr(item, "value", item)
                    for item in task024_request["design_authority"]["orientation_sequence"]
                ),
                "task024_blockers": tuple(
                    (item.code, item.field_path, tuple(item.details))
                    for item in getattr(task024_outcome, "blockers", ())
                ),
                "task025_hydraulic_diameter_m": str(task025.hydraulic_diameter_m),
                "task025_total_parallel_flow_area_m2": str(task025.total_parallel_flow_area_m2),
                "physical_tube_count": layout.physical_tube_count,
                "tube_pass_count": layout.tube_pass_count,
                "tube_mass_flow_kg_s": "12.000000",
                "service_state_temperature_k": "300.0",
                "service_state_pressure_pa": "101325.0",
                "reynolds_number": str(tube_output.reynolds_number),
                "prandtl_number": str(tube_output.prandtl_number),
                "flow_regime": tube_output.flow_regime.value,
                "correlation_id": tube_output.correlation_id,
            }
        )
    return tuple(outcomes)


def test_attempt3_reference_bound_baffle_cut_space_and_c3_preflight() -> None:
    request = _attempt_3_sizing_request()
    assert len(request.task168_candidate_request.shell_geometry_catalog.records) == 1
    authorities = task168._authority_map(request.task168_candidate_request)
    assert all(
        len(authorities[role].values) == 1
        for role in task168.DIMENSION_ORDER
        if role not in {"SHELL_GEOMETRY_ID", "BAFFLE_CUT"}
    )
    assert authorities["BAFFLE_CUT"].values == (Decimal("0.25"), Decimal("0.30"))
    outcomes = _attempt_3_geometry_and_c3_preflight(request)
    assert len(outcomes) == 2
    assert [item["selected_baffle_cut_fraction"] for item in outcomes] == ["0.25", "0.30"]
    assert [item["task024_status"] for item in outcomes] == ["BLOCKED", "VALID"]
    assert all(item["task025_hydraulic_diameter_m"] == "0.01575000" for item in outcomes)
    assert all(item["task025_total_parallel_flow_area_m2"] == "0.0492914415" for item in outcomes)
    assert all(item["physical_tube_count"] == 253 for item in outcomes)
    assert all(item["tube_pass_count"] == 1 for item in outcomes)
    assert all(item["task024_baffle_thickness_m"] == "0.006" for item in outcomes)
    assert all(item["task024_shell_to_baffle_clearance_m"] == "0.003" for item in outcomes)
    assert all(item["task024_orientation_sequence"] == ("BOTTOM",) * 4 for item in outcomes)
    assert all(item["flow_regime"] == "TURBULENT" for item in outcomes)


def test_candidate_task174_native_path_accepts_frozen_r2_authority_bindings() -> None:
    request = _sizing_request(
        tube_lengths=(Decimal("4.85"),),
        baffle_spacings=(Decimal("0.97"),),
        validation_space_r2=True,
    )
    task168_request = request.task168_candidate_request
    authorities = task168._authority_map(task168_request)
    selected = {
        role: task168._sort_values(authorities[role].values)[0]
        for role in task168.DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    }
    selected["TUBE_LENGTH"] = Decimal("4.85")
    selected["BAFFLE_SPACING"] = Decimal("0.97")
    shell_record = task168_request.shell_geometry_catalog.records[0]
    candidate = task168._candidate(
        task168_request,
        authorities,
        shell_record,
        tuple(selected[role] for role in task168.DIMENSION_ORDER if role != "SHELL_GEOMETRY_ID"),
    )
    assert task168._structural_blockers(candidate) == ()

    bundle, stage_failure, _ = task168._execute_candidate_chain(
        task168_request,
        candidate,
        shell_record,
        include_legacy_task162=False,
        include_legacy_task168_rating_dependencies=False,
    )
    assert stage_failure is None
    assert bundle.task029_result is not None
    assert bundle.task166_result is not None
    assert bundle.task031_geometry is not None
    shell_authority = CandidateShellFlowAuthority(
        task031_geometry=bundle.task031_geometry,
        task166_result=bundle.task166_result,
    )
    assert shell_authority.task031_geometry is bundle.task031_geometry
    assert shell_authority.task166_result is bundle.task166_result
    topology = materialize_candidate_task171(
        candidate=candidate,
        configuration=bundle.task020_configuration,
        layout=bundle.task021_layout,
        bundle_geometry=bundle.task022_geometry,
        baffle_geometry=bundle.task024_geometry,
        task025_result=bundle.task025_result,
        task024_request=bundle.task024_request,
        task025_request=bundle.task025_request,
    )
    thermal_binding = CandidateThermalBinding(
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        task171_result=topology,
        task025_result=bundle.task025_result,
        task166_result=bundle.task166_result,
    )
    assert thermal_binding.task171_result is topology
    task174_request = sizing._candidate_request_for_task174(candidate, bundle, topology)

    assert type(task174_request) is CandidateTask174Request
    assert task174_request.authority_package_id == "V07-T173-SIZING-AUTHORITY-PACKAGE-R2"
    assert task174_request.authority_package_hash == (
        "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
    )
    assert task174_request.task174_candidate_authority_hash == (
        "4d0f83b8ab1777ba6516dfc607c7accc814ef8a521d26c25c8cf0adc1b264023"
    )
    assert task174_request.task174_project_transfer_authority_hash == (
        "893a6c1644a940b27fbad85ef4d4fc402a7999971dc5e2ed3603fada0398b857"
    )
    assert task174_request.bell_event_transfer_authority_hash == (
        "28c89b6c58fef6050f9a0f5d33b80ce686f875a4ba9350e254d43ff699dccc58"
    )
    assert task174_request.pressure_coupling_authority_hash == (
        "7506d4217d27123cdec1a5d46813445a1a8b500ef24af39e10b7598ba163ce19"
    )
    assert len(task174_request.physical_events) == len(
        task174_request.bell_event_region_allocations
    )
    assert {item.physical_event_id for item in task174_request.physical_events} == {
        item.physical_event_id for item in task174_request.bell_event_region_allocations
    }
    assert all(
        item.task166_result_hash == bundle.task166_result.result_hash
        for item in task174_request.bell_event_region_allocations
    )
    task174 = validate_candidate_task174(
        task174_request,
        Task174NativeOutputs(
            task029=bundle.task029_result,
            task034=None,
            task166=bundle.task166_result,
        ),
    )
    assert type(task174) is Task174SuccessResult, task174.model_dump(mode="json")
    assert task174.status == "VALIDATED"
    assert task174.task029_result_hash == bundle.task029_result.result_hash
    assert task174.task166_result_hash == bundle.task166_result.result_hash
    assert task174.pressure_coupling_authority_id == (
        "V07-T174-CANDIDATE-REFERENCE-PRESSURE-COUPLING-R1"
    )

    native_task166 = bundle.task166_result
    assert type(native_task166) is Task166Result
    for changed_field in ("end_zone_pressure_drop", "total_shell_pressure_drop"):
        changed_value = getattr(native_task166, changed_field) + Decimal("1E-30")
        tampered = replace(native_task166, **{changed_field: changed_value})
        tampered_hash = task166_canonical.result_hash(tampered)
        tampered = replace(
            tampered,
            result_hash=tampered_hash,
            result_id=task166_canonical.result_id(tampered_hash),
        )
        tampered_request = task174_request.model_copy(
            update={
                "task166_result_hash": tampered_hash,
                "bell_event_region_allocations": tuple(
                    item.model_copy(update={"task166_result_hash": tampered_hash})
                    for item in task174_request.bell_event_region_allocations
                ),
            }
        )
        tampered_outcome = validate_candidate_task174(
            tampered_request,
            Task174NativeOutputs(
                task029=bundle.task029_result,
                task034=None,
                task166=tampered,
            ),
        )
        assert type(tampered_outcome) is Task174BlockedResult
        assert any(
            blocker.code == "BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION"
            for blocker in tampered_outcome.blockers
        )

    rating_request = sizing._candidate_rating_request(
        candidate,
        task168_candidate_space_hash(
            task168_request, tuple(task168_request.discrete_candidate_set_authorities)
        ),
        bundle,
        topology,
        task174,
        sizing_request_hash(request),
    )
    assert rating_request.request_metadata
    assert candidate_rating_request_hash(rating_request)
    rating_context = rating_service._candidate_context(rating_request)
    assert rating_context.shell_authority.task031_geometry is bundle.task031_geometry
    assert rating_context.shell_authority.task166_result is bundle.task166_result
    support = rating_service._build_candidate_local_support(rating_context, 0, 1, 0)
    assert support.mesh_level_identity != rating_context.mesh_identity
    candidate_task172_request = CandidateTask172LocalRequest(
        case_id=candidate.candidate_id,
        case_revision_id=candidate.candidate_id,
        topology=CandidateTopologyBinding(
            topology_id=rating_context.topology_id,
            task171_result_hash=rating_context.task171_result_hash,
            mesh_identity=rating_context.mesh_identity,
            physical_ownership_hash=rating_context.physical_ownership_hash,
            definition_projection_hash=canonical_sha256(
                topology.topology_definition.model_dump(mode="json")
            ),
            selected_variant="TUBE_HOT_SHELL_COLD",
            tube_flow_path_id=rating_context.tube_flow_path_id,
            shell_flow_path_id=rating_context.shell_flow_path_id,
        ),
        support=support,
        tube_bulk_state=LocalState(temperature_k=Decimal("299"), pressure_pa=Decimal("101325")),
        shell_bulk_state=LocalState(temperature_k=Decimal("299"), pressure_pa=Decimal("101325")),
        tube_mass_flow_kg_s=Decimal("12.000000"),
        shell_mass_flow_kg_s=Decimal("20.000000"),
        shell_flow_authority=shell_authority,
        candidate_binding=thermal_binding,
    )
    assert candidate_task172_request.topology.mesh_identity == topology.mesh_identity
    assert candidate_task172_request.support.mesh_level_identity == support.mesh_level_identity


def test_candidate_sizing_bell_authority_does_not_depend_on_legacy_task034_cut_domain() -> None:
    """v0.7 Sizing uses native TASK166, not the legacy TASK034 Bell path."""
    from dataclasses import replace as dataclass_replace

    request = _attempt_3_sizing_request()
    task168_request = request.task168_candidate_request
    space_id = "V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R4"
    policy_hash = "2db2372815fbc7295fde129508def1ef794aa55b44a1226c1188312e63e0a887"
    ledger_hash = "aeac45600d17c811b4e873e4d3bf3a3085a1741ad1888837641b993cfa19980c"
    authorities = []
    for authority in task168_request.discrete_candidate_set_authorities:
        if authority.dimension_role is DiscreteDimensionRole.BAFFLE_CUT:
            authority = dataclass_replace(
                authority,
                authority_id=f"{space_id}:BAFFLE_CUT",
                authority_version="R4",
                source_id=space_id,
                source_revision="FROZEN_AFTER_STRUCTURAL_QUALIFICATION_BEFORE_PUBLIC_EXECUTION",
                values=(Decimal("0.215"), Decimal("0.220")),
                evidence_refs=(
                    f"STRUCTURAL_QUALIFICATION_POLICY_HASH::{policy_hash}",
                    f"STRUCTURAL_QUALIFICATION_LEDGER_HASH::{ledger_hash}",
                    "IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_NOT_RELEASE_NOT_BUSINESS_REQUIREMENT",
                ),
                provenance_refs=(
                    "OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET",
                    "FIXTURE_CONSTRUCTION_ONLY_NO_PERFORMANCE_SELECTION",
                ),
                canonical_hash="",
            )
            authority = dataclass_replace(
                authority, canonical_hash=discrete_authority_hash(authority)
            )
        authorities.append(authority)
    task168_request = dataclass_replace(
        task168_request, discrete_candidate_set_authorities=tuple(authorities)
    )

    authority_map = task168._authority_map(task168_request)
    shell_record = task168_request.shell_geometry_catalog.records[0]
    selected = {
        role: task168._sort_values(authority_map[role].values)[0]
        for role in task168.DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    }
    selected["BAFFLE_CUT"] = Decimal("0.215")
    candidate = task168._candidate(
        task168_request,
        authority_map,
        shell_record,
        tuple(selected[role] for role in task168.DIMENSION_ORDER if role != "SHELL_GEOMETRY_ID"),
    )
    assert candidate.candidate_id == "adeab5b1-a339-5eb3-aa66-011ffe49bac0"

    bundle, stage_failure, _ = task168._execute_candidate_chain(
        task168_request,
        candidate,
        shell_record,
        include_legacy_task162=False,
        include_legacy_task168_rating_dependencies=False,
        preserve_baffle_orientation_sequence=True,
    )
    assert stage_failure is None
    assert bundle.task029_result is not None
    assert bundle.task166_result is not None
    assert bundle.task031_geometry is not None
    assert bundle.task034_pressure_drop is None
    assert bundle.task035_result is None
    assert bundle.task037_result is None
    assert bundle.task038_result is None

    topology = materialize_candidate_task171(
        candidate=candidate,
        configuration=bundle.task020_configuration,
        layout=bundle.task021_layout,
        bundle_geometry=bundle.task022_geometry,
        baffle_geometry=bundle.task024_geometry,
        task025_result=bundle.task025_result,
        task024_request=bundle.task024_request,
        task025_request=bundle.task025_request,
    )
    task174_request = sizing._candidate_request_for_task174(candidate, bundle, topology)
    task174 = validate_candidate_task174(
        task174_request,
        Task174NativeOutputs(
            task029=bundle.task029_result,
            task034=None,
            task166=bundle.task166_result,
        ),
    )
    assert type(task174) is Task174SuccessResult, task174.model_dump(mode="json")
    assert task174.status == "VALIDATED"


def test_attempt_two_validation_space_is_frozen_cartesian_closure_set() -> None:
    request = _sizing_request(
        tube_lengths=(Decimal("4.85"), Decimal("4.90")),
        baffle_spacings=(Decimal("0.97"), Decimal("0.98")),
        validation_space_r2=True,
    )
    authorities = task168._authority_map(request.task168_candidate_request)
    length_authority = authorities[DiscreteDimensionRole.TUBE_LENGTH.value]
    spacing_authority = authorities[DiscreteDimensionRole.BAFFLE_SPACING.value]

    assert tuple(length_authority.values) == (Decimal("4.85"), Decimal("4.90"))
    assert tuple(spacing_authority.values) == (Decimal("0.97"), Decimal("0.98"))
    assert length_authority.source_class is (
        DiscreteAuthoritySource.OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET
    )
    assert spacing_authority.source_class is (
        DiscreteAuthoritySource.OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET
    )
    assert discrete_authority_hash(length_authority) == (
        "183f41c1baf8607e29a29cce4bdf2398da32e41f1d7a2cc6f067e2d7c527b649"
    )
    assert discrete_authority_hash(spacing_authority) == (
        "34c36ee0a84d7260908acf55e0c5d68be93a4c49bcd31620aa5f011956fd7f12"
    )
    assert dict(request.request_metadata)["validation_candidate_space_authority_hash"] == (
        "062b8166181a182d1e17ca45cfac708343379d09d8ab109d7a5e475dd0c236c9"
    )
    assert sizing_request_hash(request) == (
        "a49f16a9f4124077996a1fc052387024b9181139d04202b13d98d0f771e8fcdf"
    )
    pair_closure = {
        (length, spacing): length == spacing * Decimal(5)
        for length in length_authority.values
        for spacing in spacing_authority.values
    }
    assert tuple(pair for pair, closes in pair_closure.items() if closes) == (
        (Decimal("4.85"), Decimal("0.97")),
        (Decimal("4.90"), Decimal("0.98")),
    )
    assert tuple(pair for pair, closes in pair_closure.items() if not closes) == (
        (Decimal("4.85"), Decimal("0.98")),
        (Decimal("4.90"), Decimal("0.97")),
    )


def test_sizing_request_is_strict_and_identity_binds_candidate_space() -> None:
    request_a = _sizing_request(tube_lengths=(Decimal("4.85"),))
    request_b = _sizing_request(tube_lengths=(Decimal("4.9"),))

    assert sizing_request_hash(request_a) != sizing_request_hash(request_b)
    with pytest.raises(ValidationError):
        Task173SizingRequest.model_validate(
            {**request_a.model_dump(), "unreviewed_callback": "callable"}, strict=True
        )


def test_sizing_resource_excess_blocks_without_truncation() -> None:
    values = tuple(Decimal(index) for index in range(1, 34))
    request = _sizing_request(tube_lengths=values)

    outcome = validate_sizing_request(request)

    assert outcome.status == "BLOCKED"
    assert outcome.failure_code == "SIZING_RESOURCE_BOUND_EXCEEDED"
    assert "MAX_VALUES_PER_ROLE=32" in outcome.blockers[0]


def test_unsupported_tube_pass_candidate_is_retained_as_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _sizing_request(tube_pass_counts=(1, 2))
    empty_bundle = SimpleNamespace(
        task020_configuration=None,
        task021_layout=None,
        task022_geometry=None,
        task024_geometry=None,
        task025_result=None,
        task031_geometry=None,
        task032_flow_state=None,
        task029_result=None,
        task166_result=None,
    )
    monkeypatch.setattr(
        task168,
        "_execute_candidate_chain",
        lambda *args, **kwargs: (
            empty_bundle,
            SimpleNamespace(stage=CandidateStage.CONFIGURATION, code="TEST_UPSTREAM_BLOCK"),
            None,
        ),
    )

    outcome = validate_sizing_request(request)

    assert type(outcome) is Task173SizingSuccessResult
    assert outcome.candidate_count == 2
    assert outcome.blocked_count == 2
    assert any(
        "UNSUPPORTED_V07_SIZING_TOPOLOGY:TUBE_PASS_COUNT" in item.blockers
        for item in outcome.candidate_records
    )
    assert any("TEST_UPSTREAM_BLOCK" in item.blockers for item in outcome.candidate_records)
    assert outcome.recommendable_count == 0
    assert outcome.selection_status == "NO_RECOMMENDABLE_CANDIDATE"
    assert outcome.result_hash == recompute_sizing_result_hash(outcome)


def test_sizing_result_replays_full_ranking_trace_and_excludes_blocked_candidate() -> None:
    request = _sizing_request()
    entries = []
    for candidate_id, candidate_hash, status, shell_dp, score, blockers in (
        ("pass-b", "b" * 64, "PASS", Decimal("200"), Decimal("2"), ()),
        ("warn-a", "a" * 64, "WARN", Decimal("100"), Decimal("11"), ()),
        ("pass-c", "c" * 64, "PASS", Decimal("200"), Decimal("2"), ()),
        ("blocked-d", "d" * 64, "BLOCKED", Decimal("1"), None, ("DUTY_BELOW_REQUIRED",)),
    ):
        entries.append(
            sizing.CandidateLedgerEntry(
                candidate_id=candidate_id,
                candidate_hash=candidate_hash,
                selected_dimensions=(("TUBE_LENGTH", "4.85"),),
                dimension_authority_hashes=(("TUBE_LENGTH", "e" * 64),),
                disposition="BLOCKED" if status == "BLOCKED" else "EVALUATED",
                stage="CONSTRAINT_EVALUATION" if status == "BLOCKED" else "COMPLETE",
                status=status,
                rated_duty_w=Decimal("10000"),
                tube_dp_pa=Decimal("20"),
                shell_dp_pa=shell_dp,
                duty_constraint="BLOCKED" if status == "BLOCKED" else "PASS",
                tube_dp_constraint="PASS",
                shell_dp_constraint="PASS",
                ranking_score=score,
                warnings=("FIV_NUMERIC_LIMIT_AUTHORITY_MISSING",) if status == "WARN" else (),
                blockers=blockers,
                provenance_hash="f" * 64,
            )
        )

    result = sizing._make_success_result(request, sizing_request_hash(request), "1" * 64, entries)

    assert result.ranked_candidate_ids == ("pass-b", "pass-c", "warn-a")
    assert result.recommended_candidate_id == "pass-b"
    assert result.alternative_candidate_ids == ("pass-c", "warn-a")
    assert tuple(item.rank for item in result.ranking_trace) == (1, 2, 3)
    assert result.ranking_trace[-1].warn_penalty == Decimal("10")
    assert result.ranking_trace[-1].composite_score == Decimal("11")
    assert "blocked-d" not in result.ranked_candidate_ids
    assert result.candidate_count == 4
    assert result.result_hash == recompute_sizing_result_hash(result)
    assert result.result_id == f"urn:hxforge:task173-sizing:{result.result_hash}"

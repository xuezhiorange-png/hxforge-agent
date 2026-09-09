"""Targeted TASK-168 authority, enumeration, and identity tests."""

from __future__ import annotations

from dataclasses import fields, replace
from decimal import Decimal, getcontext, localcontext
from typing import Any

import pytest

from hexagent.exchangers.shell_tube import validate_request as validate_task020
from hexagent.exchangers.shell_tube.manufacturable_candidates import validate_request
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    discrete_authority_hash,
    evaluation_input_authority_hash,
    requirement_authority_hash,
    shell_catalog_hash,
    shell_record_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.errors import BlockerCode
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    TASK168_SCHEMA_VERSION,
    TASK168_SOURCE_DEFINITION_ID,
    TASK168_VERSION,
    CandidateDisposition,
    CandidateStage,
    CandidateStatus,
    DiscreteAuthoritySource,
    DiscreteCandidateSetAuthority,
    DiscreteDimensionRole,
    Task168EvaluationInputAuthority,
    Task168Request,
    Task168RequirementAuthority,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.models import ConstructionFamily, ShellAndTubeConfiguration
from hexagent.shell_geometry_catalogs.models import (
    PROFILE_ID,
    RECORD_SCHEMA_VERSION,
    SOURCE_CLASS_PUBLIC_DOMAIN,
    ShellGeometryCatalog,
    ShellGeometryRecord,
    ShellSourceBinding,
)


def _configuration() -> ShellAndTubeConfiguration:
    raw = {
        "schema_version": "task020.configuration-request.v1",
        "case_authority": {
            "revision_id": "rev-task168",
            "payload_hash": "a" * 64,
            "domain_snapshot_hash": "b" * 64,
            "status": "committed",
        },
        "equipment_family": "SHELL_AND_TUBE",
        "authority_mode": "INTERNAL_GENERIC",
        "construction_family": "FIXED_TUBESHEET",
        "orientation": "HORIZONTAL",
        "shell_pass_count": 1,
        "tube_pass_count": 1,
        "front_head_token": "FRONT",
        "shell_token": "SHELL",
        "rear_head_token": "REAR",
        "standard_system_id": None,
        "requested_rule_pack_identity": None,
        "evidence_refs": ["task168-config"],
    }
    outcome = validate_task020(raw)
    assert outcome.configuration is not None, outcome
    return outcome.configuration


def _shell_catalog() -> ShellGeometryCatalog:
    binding = ShellSourceBinding(
        source_id="task023-test-source",
        source_type=SOURCE_CLASS_PUBLIC_DOMAIN,
        source_revision="v1",
        source_location="test://task023/shell",
        evidence_ref="task023-shell-evidence",
        approved_by="task168-test",
        approved_at="2026-01-01",
    )
    record = ShellGeometryRecord(
        schema_version=RECORD_SCHEMA_VERSION,
        geometry_id="shell-1",
        geometry_type="shell",
        profile_id=PROFILE_ID,
        revision="r1",
        approval_state="approved",
        shell_inside_diameter_m="0.8",
        nominal_label="test-shell",
        source_class=SOURCE_CLASS_PUBLIC_DOMAIN,
        license_evidence={},
        source_binding=binding,
        permission_evidence_refs=("permission-task168",),
        provenance_edge_ids=("edge-task168",),
        evidence_refs=("evidence-task168",),
        record_hash="",
    )
    record = replace(record, record_hash=shell_record_hash(record))
    catalog = ShellGeometryCatalog(
        schema_version="task023.approved-shell-geometry-catalog.v1",
        catalog_id="task023-test-catalog",
        catalog_version="v1",
        profile_id=PROFILE_ID,
        authority="TASK023_TEST_AUTHORITY",
        source_revision="v1",
        records=(record,),
        evidence_bundle_hash="c" * 64,
        catalog_hash="",
        effective_at=None,
    )
    return replace(catalog, catalog_hash=shell_catalog_hash(catalog))


def _authority(role: DiscreteDimensionRole, value: object) -> DiscreteCandidateSetAuthority:
    authority = DiscreteCandidateSetAuthority(
        authority_id=f"task168-{role.value.lower()}",
        authority_version="v1",
        dimension_role=role,
        source_class=DiscreteAuthoritySource.AUTHORIZED_PROJECT_DEFINED_DISCRETE_SET,
        source_id="task168-project-snapshot",
        source_revision="v1",
        approval_status="APPROVED",
        values=(value,),
        evidence_refs=(f"evidence-{role.value.lower()}",),
        provenance_refs=(f"provenance-{role.value.lower()}",),
        canonical_hash="",
    )
    return replace(authority, canonical_hash=discrete_authority_hash(authority))


def _request(**overrides: Any) -> Task168Request:
    requirement = Task168RequirementAuthority(
        requirement_id="task168-requirement",
        authority_version="v1",
        source_class="PROJECT_REQUIREMENT",
        source_id="task168-requirement-source",
        approval_status="APPROVED",
        allowed_construction_families=(ConstructionFamily.FIXED_TUBESHEET,),
        evidence_refs=("requirement-evidence",),
        provenance_refs=("requirement-provenance",),
        canonical_hash="",
    )
    requirement = replace(requirement, canonical_hash=requirement_authority_hash(requirement))
    authorities = (
        _authority(DiscreteDimensionRole.CONSTRUCTION_FAMILY, ConstructionFamily.FIXED_TUBESHEET),
        _authority(DiscreteDimensionRole.TUBE_OUTER_DIAMETER, Decimal("0.019")),
        _authority(DiscreteDimensionRole.TUBE_WALL_THICKNESS, Decimal("0.001")),
        _authority(DiscreteDimensionRole.TUBE_LENGTH, Decimal("3")),
        _authority(DiscreteDimensionRole.TUBE_PITCH, Decimal("0.025")),
        _authority(DiscreteDimensionRole.TUBE_LAYOUT, "LAYOUT_30_DEG"),
        _authority(DiscreteDimensionRole.TUBE_PASS_COUNT, 1),
        _authority(DiscreteDimensionRole.BAFFLE_TYPE, "SINGLE_SEGMENTAL"),
        _authority(DiscreteDimensionRole.BAFFLE_CUT, Decimal("0.25")),
        _authority(DiscreteDimensionRole.BAFFLE_SPACING, Decimal("0.3")),
        _authority(DiscreteDimensionRole.BAFFLE_COUNT, 4),
    )
    evaluation_authority = Task168EvaluationInputAuthority(
        authority_id="task168-evaluation-input",
        authority_version="v1",
        source_class="PROJECT_EVALUATION_INPUT",
        source_id="task168-evaluation-source",
        source_revision="v1",
        approval_status="APPROVED",
        evidence_refs=("evaluation-evidence",),
        provenance_refs=("evaluation-provenance",),
        canonical_hash="",
    )
    evaluation_authority = replace(
        evaluation_authority,
        canonical_hash=evaluation_input_authority_hash(evaluation_authority),
    )
    value = Task168Request(
        schema_version=TASK168_SCHEMA_VERSION,
        task168_version=TASK168_VERSION,
        source_definition_id=TASK168_SOURCE_DEFINITION_ID,
        task020_configuration=_configuration(),
        requirement_authority=requirement,
        shell_geometry_catalog=_shell_catalog(),
        discrete_candidate_set_authorities=authorities,
        evaluation_input_authority=evaluation_authority,
        request_metadata=(("alpha", "1"), ("zeta", "2")),
    )
    return replace(value, **overrides)


def _real_request(
    *,
    shell_diameter: str = "0.12",
    tube_outer_diameter: str = "0.02",
    tube_wall_thickness: str = "0.002",
    tube_length: str = "4.85",
    tube_pitch: str = "0.03",
    baffle_spacing: str = "0.97",
    baffle_count: int = 4,
) -> Task168Request:
    """Build a real candidate-owned producer chain from current authorities."""

    from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
        mass_flow_authority_hash,
    )
    from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import (
        parse_request as parse_task032,
    )
    from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
        AssertionState,
        FlowDirectionAssertion,
    )
    from hexagent.release_demo.v0_4 import task039
    from tests import test_task028_local_loss as task028_tests
    from tests.exchangers.shell_tube import (
        test_task029_upstream as task029_tests,
    )
    from tests.exchangers.shell_tube import (
        test_task162_thermal_performance_closure as task162_tests,
    )
    from tests.exchangers.shell_tube import (
        test_task166_bell_delaware as task166_tests,
    )
    from tests.exchangers.shell_tube import (
        test_task167_engineering_screening as task167_tests,
    )
    from tests.exchangers.shell_tube.baffle_geometry import _builders as task024_builders
    from tests.exchangers.shell_tube.shell_bundle_geometry import _builders as task022_builders
    from tests.exchangers.shell_tube.thermal_stream_state.test_ingress_models import (
        make_r607_raw,
    )
    from tests.exchangers.shell_tube.tube_side import (
        test_task027_production_boundary as task027_tests,
    )

    chain = task039._build_actual_chain()
    request032 = task039._build_task032_request(
        chain["task031_result"], chain["property_snapshot"], chain["mass_flow_authority"]
    )
    request033 = task039._build_task033_request(request032, chain["task032_result"])
    request034 = task039._build_task034_request(
        chain["task031_request"],
        chain["task031_result"],
        request032,
        chain["task032_result"],
        request033,
        chain["task033_result"],
    )
    task021 = task039._build_task021_request(chain["task020_config"], pattern_family="TRIANGULAR")
    task025 = task039._build_task025_request(chain["task021_layout"], chain["task020_config"])
    task022 = task022_builders.make_request(shell_diameter="0.8", minimum_clearance="0")
    task024 = task024_builders.make_request()
    roughness = task027_tests._make_smooth_roughness_authority()
    task028 = task028_tests._build_pipeline_raw_request(
        component_authorities=[
            task028_tests._minimal_component_dict(
                upstream_reference_plane="TUBE_LOCAL_LOSS_START_PLANE",
                downstream_reference_plane="TUBE_INTERNAL_FLOW_START_PLANE",
            )
        ]
    )
    task029 = task029_tests.build_production_fixtures()["request"]
    task037 = task039._build_task037_request()
    task166 = task166_tests._request()
    task167 = task167_tests._request()

    task160_template = make_r607_raw()
    task160_streams = list(task160_template["stream_records"])
    shell_stream = dict(task160_streams[1])
    shell_stream["fluid_or_service_identity"] = "SHELL-WATER-001"
    task160_streams[1] = shell_stream
    task160_template["stream_records"] = task160_streams
    task161_template = {
        "schema_version": "task161.schema.v1",
        "task161_version": "task161.v1",
        "source_definition_id": "TASK161-SOURCE-DEFINITION-R8-ISSUE-225",
        "task160_result": None,
        "request_metadata": [],
    }

    mass = dict(chain["mass_flow_authority"])
    mass["mass_flow_rate_kg_s"] = "20.0000000"
    check032 = dict(request032)
    check032["mass_flow_authority"] = mass
    mass["authority_hash"] = mass_flow_authority_hash(parse_task032(check032).mass_flow_authority)
    base = _request()
    evaluation_authority = replace(
        base.evaluation_input_authority,
        task021_request_template=task021,
        task022_request_template=task022,
        task024_request_template=task024,
        task025_request_template=task025,
        task026_request=chain["task026_request"],
        task027_property_snapshot=chain["task026_request"].property_snapshot,
        task027_roughness_authority=roughness,
        task027_constant_density_assertion=AssertionState.TRUE,
        task027_zero_net_elevation_assertion=AssertionState.TRUE,
        task027_flow_direction_assertion=FlowDirectionAssertion.START_TO_END,
        task028_request_template=task028,
        task029_request_template=task029,
        task031_request_template=chain["task031_request"],
        task032_request_template=request032,
        task032_property_snapshot=chain["property_snapshot"],
        task032_mass_flow_authority=mass,
        task033_request_template=request033,
        task034_request_template=request034,
        task035_request_template=chain["task035_request"],
        task037_request=task037,
        task038_service_binding_authority=chain["service_binding"],
        task166_request_template=task166,
        task160_request_template=task160_template,
        task161_request_template=task161_template,
        task162_case_authority=task162_tests._case(),
        task162_binding_authority=task162_tests._binding(),
        task167_screening_requirements=task167.screening_requirements,
        task167_screening_property_snapshot=task167.screening_property_snapshot,
    )
    evaluation_authority = replace(
        evaluation_authority,
        canonical_hash=evaluation_input_authority_hash(evaluation_authority),
    )

    shell_record = replace(
        base.shell_geometry_catalog.records[0],
        shell_inside_diameter_m=shell_diameter,
        record_hash="",
    )
    shell_record = replace(shell_record, record_hash=shell_record_hash(shell_record))
    shell_catalog = replace(
        base.shell_geometry_catalog,
        records=(shell_record,),
        catalog_hash="",
    )
    shell_catalog = replace(shell_catalog, catalog_hash=shell_catalog_hash(shell_catalog))

    authorities: list[DiscreteCandidateSetAuthority] = []
    for authority in base.discrete_candidate_set_authorities:
        value: object | None = None
        if authority.dimension_role is DiscreteDimensionRole.TUBE_OUTER_DIAMETER:
            value = Decimal(tube_outer_diameter)
        elif authority.dimension_role is DiscreteDimensionRole.TUBE_WALL_THICKNESS:
            value = Decimal(tube_wall_thickness)
        elif authority.dimension_role is DiscreteDimensionRole.TUBE_LENGTH:
            value = Decimal(tube_length)
        elif authority.dimension_role is DiscreteDimensionRole.TUBE_PITCH:
            value = Decimal(tube_pitch)
        elif authority.dimension_role is DiscreteDimensionRole.BAFFLE_SPACING:
            value = Decimal(baffle_spacing)
        elif authority.dimension_role is DiscreteDimensionRole.BAFFLE_COUNT:
            value = baffle_count
        if value is not None:
            authority = replace(authority, values=(value,), canonical_hash="")
            authority = replace(authority, canonical_hash=discrete_authority_hash(authority))
        authorities.append(authority)
    return replace(
        base,
        shell_geometry_catalog=shell_catalog,
        discrete_candidate_set_authorities=tuple(authorities),
        evaluation_input_authority=evaluation_authority,
    )


def _codes(outcome: object) -> set[str]:
    branch = getattr(outcome, "typed_blocked", None) or getattr(
        outcome, "raw_boundary_blocked", None
    )
    return set() if branch is None else {item.code for item in branch.blockers}


def test_exact_discrete_enumeration_retains_missing_evaluation_as_audited_block() -> None:
    outcome = validate_request(_request())
    assert outcome.status is ValidationStatus.VALID
    assert outcome.valid is not None
    assert outcome.valid.total_theoretical_combinations == 1
    assert outcome.valid.total_enumerated_candidates == 1
    assert outcome.valid.blocked_count == 1
    assert outcome.valid.candidate_records[0].status is CandidateStatus.BLOCKED
    assert outcome.valid.candidate_records[0].disposition.value == "BLOCKED"
    assert any(
        blocker.code == BlockerCode.EVALUATION_AUTHORITY_REQUIRED.value
        for blocker in outcome.valid.candidate_records[0].blockers
    )
    assert outcome.valid.provenance.cycle_count == 0
    assert outcome.valid.provenance.self_edge_count == 0


def test_same_semantic_request_replays_exact_identity_under_ambient_decimal_context() -> None:
    first = validate_request(_request())
    assert first.valid is not None
    original_precision = getcontext().prec
    try:
        with localcontext() as context:
            context.prec = 7
            second = validate_request(_request())
        assert second.valid is not None
        assert first.valid.result_hash == second.valid.result_hash
        assert first.valid.result_id == second.valid.result_id
        assert [item.candidate_id for item in first.valid.candidate_records] == [
            item.candidate_id for item in second.valid.candidate_records
        ]
    finally:
        getcontext().prec = original_precision


def test_tampered_discrete_authority_hash_blocks_before_enumeration() -> None:
    request = _request()
    tampered = replace(
        request.discrete_candidate_set_authorities[0],
        canonical_hash="0" * 64,
    )
    outcome = validate_request(
        replace(
            request,
            discrete_candidate_set_authorities=(
                tampered,
                *request.discrete_candidate_set_authorities[1:],
            ),
        )
    )
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.DISCRETE_AUTHORITY_HASH_MISMATCH.value in _codes(outcome)


def test_unsupported_raw_object_never_invokes_repr_or_str() -> None:
    class Explosive:
        def __repr__(self) -> str:
            raise AssertionError("repr must not run")

        def __str__(self) -> str:
            raise AssertionError("str must not run")

    outcome = validate_request(Explosive())
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.UNSUPPORTED_RAW_VALUE.value in _codes(outcome)


def test_raw_unicode_surrogate_is_fail_closed() -> None:
    outcome = validate_request({"bad": "\ud800"})
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.RAW_UNICODE_ENCODING_FAILURE.value in _codes(outcome)


def test_no_psi_n_or_ranking_surface_is_exposed() -> None:
    import hexagent.exchangers.shell_tube.manufacturable_candidates as package

    assert package.__all__ == ("validate_request",)
    assert not hasattr(package, "candidate_score")
    assert not hasattr(package, "recommended_candidate_id")


def test_task168_request_has_base_inputs_not_candidate_result_contexts() -> None:
    names = tuple(item.name for item in fields(Task168Request))
    assert "evaluation_input_authority" in names
    assert "candidate_evaluations" not in names
    evaluation_fields = {item.name for item in fields(Task168EvaluationInputAuthority)}
    assert "task160_request_template" in evaluation_fields
    assert "task161_request_template" in evaluation_fields


def test_real_candidate_orchestrates_the_complete_producer_chain() -> None:
    outcome = validate_request(_real_request())
    assert outcome.status is ValidationStatus.VALID
    assert outcome.valid is not None
    assert outcome.valid.total_enumerated_candidates == 1
    assert outcome.valid.pass_count == 0
    assert outcome.valid.warn_count == 1
    assert outcome.valid.blocked_count == 0
    record = outcome.valid.candidate_records[0]
    assert record.disposition is CandidateDisposition.EVALUATED
    assert record.status is CandidateStatus.WARN
    assert record.stage is CandidateStage.COMPLETE
    assert record.last_successful_stage is CandidateStage.COMPLETE
    assert dict(record.tube_layout_evidence)["layout_id"]
    assert dict(record.tube_dp_evidence)["tube_dp_hash"]
    assert dict(record.bell_evidence)["bell_hash"]
    assert dict(record.thermal_closure_evidence)["task162_hash"]
    assert dict(record.screening_evidence)["task167_hash"]
    assert outcome.valid.provenance.cycle_count == 0
    assert outcome.valid.provenance.self_edge_count == 0


def test_real_candidate_replays_batch_identity_exactly() -> None:
    first = validate_request(_real_request())
    second = validate_request(_real_request())
    assert first.valid is not None
    assert second.valid is not None
    assert first.valid.result_hash == second.valid.result_hash
    assert first.valid.result_id == second.valid.result_id
    assert [item.candidate_id for item in first.valid.candidate_records] == [
        item.candidate_id for item in second.valid.candidate_records
    ]


def test_real_candidate_preserves_warn_as_evaluated_and_retains_blocked_member() -> None:
    request = _real_request()
    authorities = list(request.discrete_candidate_set_authorities)
    for index, authority in enumerate(authorities):
        if authority.dimension_role is DiscreteDimensionRole.TUBE_WALL_THICKNESS:
            changed = replace(authority, values=(Decimal("0.002"), Decimal("0.010")))
            authorities[index] = replace(
                changed,
                canonical_hash=discrete_authority_hash(changed),
            )
    outcome = validate_request(
        replace(request, discrete_candidate_set_authorities=tuple(authorities))
    )
    assert outcome.valid is not None
    assert outcome.valid.total_enumerated_candidates == 2
    assert outcome.valid.warn_count == 1
    assert outcome.valid.blocked_count == 1
    assert [item.disposition for item in outcome.valid.candidate_records] == [
        CandidateDisposition.EVALUATED,
        CandidateDisposition.BLOCKED,
    ]
    blocked = outcome.valid.candidate_records[1]
    assert blocked.stage is CandidateStage.CANDIDATE_AUTHORITY
    assert blocked.last_successful_stage is None
    assert blocked.blockers


def test_reversed_discrete_authority_values_are_identity_invariant() -> None:
    request = _request()
    authorities = list(request.discrete_candidate_set_authorities)
    for index, authority in enumerate(authorities):
        if authority.dimension_role is DiscreteDimensionRole.TUBE_WALL_THICKNESS:
            changed = replace(authority, values=(Decimal("0.001"), Decimal("0.0005")))
            changed = replace(changed, canonical_hash=discrete_authority_hash(changed))
            authorities[index] = changed
    forward = replace(request, discrete_candidate_set_authorities=tuple(authorities))
    reverse_authorities = list(authorities)
    for index, authority in enumerate(reverse_authorities):
        if authority.dimension_role is DiscreteDimensionRole.TUBE_WALL_THICKNESS:
            changed = replace(authority, values=tuple(reversed(authority.values)))
            reverse_authorities[index] = replace(
                changed,
                canonical_hash=discrete_authority_hash(changed),
            )
    reverse = replace(request, discrete_candidate_set_authorities=tuple(reverse_authorities))
    first = validate_request(forward)
    second = validate_request(reverse)
    assert first.valid is not None
    assert second.valid is not None
    assert first.valid.request_hash == second.valid.request_hash
    assert first.valid.result_hash == second.valid.result_hash
    assert [item.candidate_id for item in first.valid.candidate_records] == [
        item.candidate_id for item in second.valid.candidate_records
    ]


def test_structural_candidate_block_does_not_invoke_downstream_chain() -> None:
    request = _real_request(tube_pitch="0.02")
    outcome = validate_request(request)
    assert outcome.valid is not None
    record = outcome.valid.candidate_records[0]
    assert record.status is CandidateStatus.BLOCKED
    assert record.disposition is CandidateDisposition.BLOCKED
    assert record.stage is CandidateStage.CANDIDATE_AUTHORITY
    assert record.last_successful_stage is None
    assert record.tube_layout_evidence == ()
    assert record.bell_evidence == ()
    assert record.thermal_closure_evidence == ()


def test_resource_combination_bound_blocks_without_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hexagent.exchangers.shell_tube.manufacturable_candidates.service as service

    monkeypatch.setattr(service, "MAX_RAW_COMBINATION_COUNT", 0)
    outcome = validate_request(_request())
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.RESOURCE_BOUND_EXCEEDED.value in _codes(outcome)


def test_shell_record_hash_tamper_is_rejected_before_generation() -> None:
    request = _request()
    record = replace(request.shell_geometry_catalog.records[0], record_hash="0" * 64)
    catalog = replace(
        request.shell_geometry_catalog,
        records=(record,),
        catalog_hash="",
    )
    outcome = validate_request(replace(request, shell_geometry_catalog=catalog))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.SHELL_CATALOG_INVALID.value in _codes(outcome)


def test_unapproved_discrete_authority_is_closed() -> None:
    request = _request()
    authority = request.discrete_candidate_set_authorities[0]
    changed = replace(authority, approval_status="PENDING")
    changed = replace(changed, canonical_hash=discrete_authority_hash(changed))
    outcome = validate_request(
        replace(
            request,
            discrete_candidate_set_authorities=(
                changed,
                *request.discrete_candidate_set_authorities[1:],
            ),
        )
    )
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.DISCRETE_AUTHORITY_UNAPPROVED.value in _codes(outcome)


def test_requirement_authority_tamper_is_typed_blocked() -> None:
    request = _request()
    changed = replace(request.requirement_authority, canonical_hash="0" * 64)
    outcome = validate_request(replace(request, requirement_authority=changed))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.REQUIREMENT_AUTHORITY_INVALID.value in _codes(outcome)


def test_real_chain_hard_constraints_accept_exact_authoritative_limits() -> None:
    request = _real_request()
    baseline = validate_request(request)
    assert baseline.valid is not None
    record = baseline.valid.candidate_records[0]
    metrics = dict(record.metrics)
    requirement = replace(
        request.requirement_authority,
        required_duty_w=Decimal(metrics["q_method_w"]),
        max_tube_dp_pa=Decimal(metrics["tube_dp_pa"]),
        max_shell_dp_pa=Decimal(metrics["shell_dp_pa"]),
        canonical_hash="",
    )
    requirement = replace(
        requirement,
        canonical_hash=requirement_authority_hash(requirement),
    )
    outcome = validate_request(replace(request, requirement_authority=requirement))
    assert outcome.valid is not None
    candidate = outcome.valid.candidate_records[0]
    assert candidate.disposition is CandidateDisposition.EVALUATED
    assert candidate.status is CandidateStatus.WARN
    assert dict(candidate.constraint_evaluations) == {
        "required_duty_w": "PASS",
        "max_tube_dp_pa": "PASS",
        "max_shell_dp_pa": "PASS",
    }


def test_real_chain_hard_constraint_just_over_limit_blocks_candidate() -> None:
    request = _real_request()
    baseline = validate_request(request)
    assert baseline.valid is not None
    q_method = Decimal(dict(baseline.valid.candidate_records[0].metrics)["q_method_w"])
    requirement = replace(
        request.requirement_authority,
        required_duty_w=q_method + Decimal("1"),
        canonical_hash="",
    )
    requirement = replace(
        requirement,
        canonical_hash=requirement_authority_hash(requirement),
    )
    outcome = validate_request(replace(request, requirement_authority=requirement))
    assert outcome.valid is not None
    candidate = outcome.valid.candidate_records[0]
    assert candidate.disposition is CandidateDisposition.BLOCKED
    assert candidate.status is CandidateStatus.BLOCKED
    assert candidate.stage is CandidateStage.CONSTRAINT_EVALUATION
    assert candidate.last_successful_stage is CandidateStage.ENGINEERING_SCREENING
    assert any(
        blocker.code == BlockerCode.HARD_CONSTRAINT_UNSATISFIED.value
        for blocker in candidate.blockers
    )


def test_request_metadata_requires_the_frozen_canonical_order() -> None:
    outcome = validate_request(_request(request_metadata=(("zeta", "2"), ("alpha", "1"))))
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.INVALID_REQUEST_SCHEMA.value in _codes(outcome)


def test_duplicate_semantic_decimal_members_are_rejected() -> None:
    request = _request()
    authorities = list(request.discrete_candidate_set_authorities)
    for index, authority in enumerate(authorities):
        if authority.dimension_role is DiscreteDimensionRole.TUBE_PITCH:
            changed = replace(
                authority,
                values=(Decimal("0.025"), Decimal("0.0250")),
            )
            authorities[index] = replace(
                changed,
                canonical_hash=discrete_authority_hash(changed),
            )
    outcome = validate_request(
        replace(request, discrete_candidate_set_authorities=tuple(authorities))
    )
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.DUPLICATE_DISCRETE_MEMBER.value in _codes(outcome)


def test_raw_depth_limit_is_bounded_and_total() -> None:
    raw: object = "leaf"
    for _ in range(18):
        raw = {"nested": raw}
    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.RAW_DEPTH_LIMIT_EXCEEDED.value in _codes(outcome)

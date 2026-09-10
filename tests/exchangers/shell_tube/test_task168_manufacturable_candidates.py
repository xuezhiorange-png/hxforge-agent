"""Targeted TASK-168 authority, enumeration, and identity tests."""

from __future__ import annotations

from dataclasses import fields, replace
from decimal import Decimal, getcontext, localcontext
from types import SimpleNamespace
from typing import Any

import pytest

from hexagent.exchangers.shell_tube import validate_request as validate_task020
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168_service
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
    REQUIRED_DISCRETE_ROLES,
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


def _with_authority_values(
    request: Task168Request,
    role: DiscreteDimensionRole,
    values: tuple[object, ...],
) -> Task168Request:
    authorities = list(request.discrete_candidate_set_authorities)
    for index, authority in enumerate(authorities):
        if authority.dimension_role is role:
            changed = replace(authority, values=values, canonical_hash="")
            authorities[index] = replace(
                changed,
                canonical_hash=discrete_authority_hash(changed),
            )
    return replace(request, discrete_candidate_set_authorities=tuple(authorities))


def test_candidate_specific_task020_configuration_materializes_each_family() -> None:
    request = _request()
    families = (
        ConstructionFamily.FIXED_TUBESHEET,
        ConstructionFamily.U_TUBE,
        ConstructionFamily.FLOATING_HEAD,
    )
    requirement = replace(
        request.requirement_authority,
        allowed_construction_families=families,
        canonical_hash="",
    )
    requirement = replace(requirement, canonical_hash=requirement_authority_hash(requirement))
    request = replace(
        _with_authority_values(
            replace(request, requirement_authority=requirement),
            DiscreteDimensionRole.CONSTRUCTION_FAMILY,
            families,
        ),
        task020_configuration=_configuration(),
    )

    outcome = validate_request(request)

    assert outcome.status is ValidationStatus.VALID
    assert outcome.valid is not None
    records = outcome.valid.candidate_records
    assert tuple(record.candidate.construction_family for record in records) == (
        ConstructionFamily.FIXED_TUBESHEET,
        ConstructionFamily.FLOATING_HEAD,
        ConstructionFamily.U_TUBE,
    )
    configuration_ids = []
    for record in records:
        evidence = dict(record.configuration_evidence)
        configuration_ids.append(evidence["configuration_id"])
        assert evidence["construction_family"] == record.candidate.construction_family.value
        assert record.last_successful_stage is CandidateStage.CONFIGURATION
        assert record.stage is CandidateStage.TUBE_LAYOUT
        assert all(
            blocker.code != BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH.value
            for blocker in record.blockers
        )
    assert len(set(configuration_ids)) == len(families)


def test_candidate_specific_task020_configuration_materializes_each_tube_pass_count() -> None:
    request = _with_authority_values(
        _request(),
        DiscreteDimensionRole.TUBE_PASS_COUNT,
        (1, 2),
    )

    outcome = validate_request(request)

    assert outcome.status is ValidationStatus.VALID
    assert outcome.valid is not None
    records = outcome.valid.candidate_records
    assert [record.candidate.tube_pass_count for record in records] == [1, 2]
    configuration_ids = []
    for record in records:
        evidence = dict(record.configuration_evidence)
        configuration_ids.append(evidence["configuration_id"])
        assert int(evidence["tube_pass_count"]) == record.candidate.tube_pass_count
        assert record.last_successful_stage is CandidateStage.CONFIGURATION
    assert len(set(configuration_ids)) == 2


def test_candidate_task020_configuration_identity_replays_and_tracks_selected_authority() -> None:
    base = _request()
    requirement = replace(
        base.requirement_authority,
        allowed_construction_families=(
            ConstructionFamily.FIXED_TUBESHEET,
            ConstructionFamily.U_TUBE,
        ),
        canonical_hash="",
    )
    request = _with_authority_values(
        replace(
            base,
            requirement_authority=replace(
                requirement,
                canonical_hash=requirement_authority_hash(requirement),
            ),
        ),
        DiscreteDimensionRole.CONSTRUCTION_FAMILY,
        (ConstructionFamily.FIXED_TUBESHEET, ConstructionFamily.U_TUBE),
    )
    first = validate_request(request)
    second = validate_request(request)

    assert first.valid is not None
    assert second.valid is not None
    assert first.valid.result_hash == second.valid.result_hash
    first_evidence = [
        dict(record.configuration_evidence) for record in first.valid.candidate_records
    ]
    second_evidence = [
        dict(record.configuration_evidence) for record in second.valid.candidate_records
    ]
    assert first_evidence == second_evidence
    assert first_evidence[0]["configuration_id"] != first_evidence[1]["configuration_id"]
    assert first_evidence[0]["case_authority_id"] == "rev-task168"


def test_real_candidate_exposes_candidate_task020_identity_for_downstream_chain() -> None:
    outcome = validate_request(_real_request())

    assert outcome.valid is not None
    record = outcome.valid.candidate_records[0]
    configuration = dict(record.configuration_evidence)
    assert configuration["configuration_id"]
    assert configuration["configuration_hash"]
    assert configuration["construction_family"] == "FIXED_TUBESHEET"
    assert configuration["tube_pass_count"] == "1"
    assert configuration["case_authority_id"] == record.candidate.case_authority_id
    request_configuration_id = configuration["configuration_id"]
    assert request_configuration_id
    assert dict(record.tube_layout_evidence)["layout_id"]
    assert dict(record.geometry_evidence)["geometry_id"]
    assert outcome.valid.provenance.cycle_count == 0


def test_task160_envelope_is_candidate_bound_and_does_not_retain_fixed_template() -> None:
    """A non-fixed candidate must reach TASK-160 with its own envelope values."""

    from hexagent.exchangers.shell_tube.thermal_stream_state import (
        validate_request as validate_task160,
    )

    base = _real_request()
    requirement = replace(
        base.requirement_authority,
        allowed_construction_families=(ConstructionFamily.U_TUBE,),
        canonical_hash="",
    )
    requirement = replace(requirement, canonical_hash=requirement_authority_hash(requirement))
    request = _with_authority_values(
        replace(base, requirement_authority=requirement),
        DiscreteDimensionRole.CONSTRUCTION_FAMILY,
        (ConstructionFamily.U_TUBE,),
    )

    outcome = validate_request(request)
    assert outcome.valid is not None
    candidate = outcome.valid.candidate_records[0].candidate
    configuration = task168_service._materialize_candidate_configuration(
        request.task020_configuration,
        candidate,
    )
    payload = task168_service._task160_payload(
        request.evaluation_input_authority,
        configuration,
        candidate,
        SimpleNamespace(result_id="task026-result", property_snapshot_hash="a" * 64),
    )

    envelope = payload["envelope_authority"]
    assert isinstance(envelope, dict)
    assert envelope["construction_family"] == "U_TUBE"
    assert envelope["tube_pass_count"] == candidate.tube_pass_count
    assert envelope["authority_source_identity"] == "TASK169-V06-THERMAL-CLOSURE-AUTHORITY"
    assert envelope["authority_source_version"] == "v0.6"
    assert envelope["authority_identity"].startswith("A06_V06_SHELL_TUBE_THERMAL_ENVELOPE::")
    assert "TASK169-THERMAL-CLOSURE-AUTHORITY-V06" in envelope["evidence_refs"]
    assert any(
        ref.startswith("TASK168_TASK020_CONFIGURATION::") for ref in envelope["evidence_refs"]
    )

    task160_outcome = validate_task160(payload)
    assert task160_outcome.status.value == "RAW_BOUNDARY_BLOCKED"
    assert task160_outcome.raw_boundary_blocked is not None
    assert any(blocker.code == "B022" for blocker in task160_outcome.raw_boundary_blocked.blockers)


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


def test_candidate_retains_complete_selected_discrete_authority_bindings() -> None:
    request = _request()
    outcome = validate_request(request)
    assert outcome.valid is not None
    candidate = outcome.valid.candidate_records[0].candidate
    bindings = {
        binding.dimension_role.value: binding for binding in candidate.dimension_authority_bindings
    }
    authorities = {
        authority.dimension_role.value: authority
        for authority in request.discrete_candidate_set_authorities
    }
    assert tuple(bindings) == REQUIRED_DISCRETE_ROLES
    for role in REQUIRED_DISCRETE_ROLES:
        binding = bindings[role]
        authority = authorities[role]
        assert binding.authority_id == authority.authority_id
        assert binding.authority_version == authority.authority_version
        assert binding.canonical_hash == authority.canonical_hash
        assert binding.source_class is authority.source_class
        assert binding.source_id == authority.source_id
        assert binding.source_revision == authority.source_revision
        assert binding.evidence_refs == authority.evidence_refs
        assert binding.provenance_refs == authority.provenance_refs
        assert binding.selected_member == authority.values[0]
        assert (
            f"TASK168_DISCRETE_AUTHORITY::{role}::{authority.canonical_hash}"
            in task168_service._candidate_dimension_authority_refs(candidate)
        )


def test_discrete_authority_source_swap_changes_candidate_identity() -> None:
    request = _request()
    baseline = validate_request(request)
    assert baseline.valid is not None
    baseline_candidate = baseline.valid.candidate_records[0].candidate
    original = request.discrete_candidate_set_authorities[1]
    changed = replace(
        original,
        source_id="task168-different-project-snapshot",
        canonical_hash="",
    )
    changed = replace(changed, canonical_hash=discrete_authority_hash(changed))
    authorities = list(request.discrete_candidate_set_authorities)
    authorities[1] = changed
    swapped = validate_request(
        replace(request, discrete_candidate_set_authorities=tuple(authorities))
    )
    assert swapped.valid is not None
    swapped_candidate = swapped.valid.candidate_records[0].candidate
    assert swapped_candidate.candidate_id != baseline_candidate.candidate_id
    assert swapped_candidate.candidate_hash != baseline_candidate.candidate_hash
    assert (
        swapped_candidate.dimension_authority_bindings[1].canonical_hash
        != baseline_candidate.dimension_authority_bindings[1].canonical_hash
    )


def test_native_task021_and_task022_identity_and_warnings_survive_task024_admission() -> None:
    request = _real_request()
    initial = validate_request(request)
    assert initial.valid is not None
    candidate = initial.valid.candidate_records[0].candidate
    authority = request.evaluation_input_authority
    configuration = request.task020_configuration
    record = request.shell_geometry_catalog.records[0]

    task021_payload = task168_service._task021_payload(authority, candidate, configuration)
    layout_outcome = task168_service.validate_task021(
        task021_payload,
        software_version=task168_service.TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
        git_commit="task168-orchestration",
    )
    assert layout_outcome.layout is not None
    native_layout = layout_outcome.layout
    tube_geometry_source = task021_payload["tube_geometry"]["source_binding"]
    assert tube_geometry_source["source_type"] == "TASK168_DERIVED_DISCRETE_AUTHORITY"
    assert tube_geometry_source["source_id"].startswith("TASK168-DERIVED-TUBE-GEOMETRY::")
    assert tube_geometry_source["evidence_ref"].startswith("TASK168_TUBE_GEOMETRY_AUTHORITY::")
    assert set(
        task168_service._candidate_dimension_authority_refs(
            candidate, ("TUBE_OUTER_DIAMETER", "TUBE_WALL_THICKNESS")
        )
    ).issubset(set(task021_payload["layout_rule_authority"]["provenance_edge_ids"]))
    geometry_outcome = task168_service.validate_task022(
        task168_service._task022_payload(
            authority, candidate, configuration, native_layout, record
        ),
        software_version=task168_service.TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
        git_commit="task168-orchestration",
    )
    assert geometry_outcome.geometry is not None
    native_geometry = geometry_outcome.geometry
    native_layout_identity = (native_layout.layout_id, native_layout.layout_hash)
    native_geometry_identity = (native_geometry.geometry_id, native_geometry.geometry_hash)
    native_layout_warnings = native_layout.warnings
    native_geometry_warnings = native_geometry.warnings

    task024_payload = task168_service._task024_payload(
        authority,
        candidate,
        configuration,
        native_layout,
        native_geometry,
    )
    bridge_refs = task168_service._candidate_dimension_authority_refs(candidate)
    assert set(bridge_refs).issubset(set(task021_payload["evidence_refs"]))
    assert set(bridge_refs).issubset(set(task024_payload["evidence_refs"]))
    assert set(
        task168_service._candidate_dimension_authority_refs(
            candidate, ("TUBE_LENGTH", "BAFFLE_SPACING", "BAFFLE_COUNT")
        )
    ).issubset(set(task024_payload["axial_span"]["evidence_refs"]))
    assert set(
        task168_service._candidate_dimension_authority_refs(
            candidate, ("BAFFLE_TYPE", "BAFFLE_CUT", "BAFFLE_SPACING", "BAFFLE_COUNT")
        )
    ).issubset(set(task024_payload["design_authority"]["evidence_refs"]))
    assert task024_payload["tube_layout"] is native_layout
    assert task024_payload["shell_bundle_geometry"] is native_geometry
    assert (native_layout.layout_id, native_layout.layout_hash) == native_layout_identity
    assert (native_geometry.geometry_id, native_geometry.geometry_hash) == native_geometry_identity
    assert native_layout.warnings == native_layout_warnings
    assert native_geometry.warnings == native_geometry_warnings

    task024_outcome = task168_service.validate_task024(task024_payload)
    assert task024_outcome.geometry is not None
    assert task024_outcome.geometry.task021_layout_id == native_layout.layout_id
    assert task024_outcome.geometry.task022_geometry_id == native_geometry.geometry_id
    assert task024_outcome.geometry.task021_layout_hash == native_layout.layout_hash
    assert task024_outcome.geometry.task022_geometry_hash == native_geometry.geometry_hash

    task031_payload = task168_service._task031_payload(
        authority,
        configuration,
        native_layout,
        task024_outcome,
        task024_outcome.geometry,
    )
    assert task031_payload["baffle_geometry_result"] == task168_service._public_value(
        task024_outcome
    )


def test_provenance_contains_discrete_authority_and_materialization_edges() -> None:
    outcome = validate_request(_request())
    assert outcome.valid is not None
    record = outcome.valid.candidate_records[0]
    candidate_node = f"TASK168_CANDIDATE::{record.candidate_id}"
    configuration_node = f"TASK020::{dict(record.configuration_evidence)['result_id']}"
    edge_set = {
        (edge.source_node_id, edge.relation, edge.target_node_id)
        for edge in outcome.valid.provenance.edges
    }
    for binding in record.candidate.dimension_authority_bindings:
        role = binding.dimension_role.value
        authority_node = f"TASK168_DISCRETE_AUTHORITY::{role}::{binding.canonical_hash}"
        materialized_node = f"TASK168_MATERIALIZED_AUTHORITY::{record.candidate_id}::{role}"
        assert (authority_node, "AUTHORIZES", candidate_node) in edge_set
        assert (authority_node, "SUPPLIES", materialized_node) in edge_set
        assert (materialized_node, "SUPPLIES", candidate_node) in edge_set
        assert (authority_node, "AUTHORIZES", configuration_node) in edge_set
    assert (configuration_node, "SUPPLIES", candidate_node) in edge_set
    assert outcome.valid.provenance.self_edge_count == 0
    assert outcome.valid.provenance.cycle_count == 0

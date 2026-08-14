"""TASK-029 authority contract tests (I17): 16 frozen TEST_ID proofs."""

from __future__ import annotations

from dataclasses import replace

from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    Task028ComponentFlowDirectionAssertion,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    sort_evidence_refs,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.completeness import (
    validate_exclusion_partition_and_completeness,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ProducerTask,
    Task029BlockerCode,
    Task029FlowDirectionAssertion,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_composition_authority_hash,
    compute_exclusion_authority_hash,
    compute_member_authority_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.path_binding import (
    bind_members_to_producers,
    evaluate_path_topology,
    validate_global_index_domain,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.upstream_replay import (
    replay_task028_success,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.validation import (
    T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES,
    T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS,
    T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    EXCLUSION_AUTHORITY_FIXTURES,
    M000_MEMBER_AUTHORITY_FIXTURE,
    M001_MEMBER_AUTHORITY_FIXTURE,
    VECTOR_01_M000_HASH,
    VECTOR_02_M001_HASH,
    VECTOR_03_CALLER_MEMBER_ORDER_PERMUTATION_HASH,
    VECTOR_03_COMPOSITION_HASH,
)
from tests.exchangers.shell_tube.test_task029_upstream import (
    build_production_fixtures,
    clone_with_field,
    exclusion_from_fixture,
    member_from_fixture,
    rebuild_task028,
    recompute_composition,
)


def test_T029_AUTH_001_MEMBER_M000_HASH_VECTOR() -> None:
    member = member_from_fixture(M000_MEMBER_AUTHORITY_FIXTURE)
    actual = compute_member_authority_hash(member)
    assert actual == VECTOR_01_M000_HASH


def test_T029_AUTH_002_MEMBER_M001_HASH_VECTOR() -> None:
    member = member_from_fixture(M001_MEMBER_AUTHORITY_FIXTURE)
    actual = compute_member_authority_hash(member)
    assert actual == VECTOR_02_M001_HASH


def test_T029_AUTH_003_EXCLUSION_HASH_VECTORS() -> None:
    for fixture in EXCLUSION_AUTHORITY_FIXTURES:
        exclusion = exclusion_from_fixture(fixture)
        actual = compute_exclusion_authority_hash(exclusion)
        assert actual == fixture["exclusion_authority_hash"]


def test_T029_AUTH_004_COMPOSITION_HASH_VECTOR() -> None:
    fixtures = build_production_fixtures()
    actual = compute_composition_authority_hash(fixtures["composition"])
    assert actual == VECTOR_03_COMPOSITION_HASH


def test_T029_AUTH_005_CALLER_MEMBER_ORDER_PERMUTATION() -> None:
    fixtures = build_production_fixtures()
    composition = fixtures["composition"]
    permuted = replace(
        composition,
        member_authorities=(composition.member_authorities[1], composition.member_authorities[0]),
    )
    actual = compute_composition_authority_hash(permuted)
    assert actual == VECTOR_03_CALLER_MEMBER_ORDER_PERMUTATION_HASH


def test_T029_AUTH_006_GLOBAL_INDEX_CONTIGUOUS() -> None:
    fixtures = build_production_fixtures()
    blockers = validate_global_index_domain(fixtures["composition"].member_authorities)
    assert blockers == ()
    bad = replace(fixtures["m001"], global_path_sequence_index=2)
    bad_composition = replace(
        fixtures["composition"],
        member_authorities=(fixtures["m000"], bad),
    )
    blockers = validate_global_index_domain(bad_composition.member_authorities)
    assert any(b.code == Task029BlockerCode.BL_T029_OUT_OF_ORDER_MEMBER for b in blockers)


def test_T029_AUTH_007_TASK027_MEMBER_EXACTLY_ONE() -> None:
    fixtures = build_production_fixtures()
    t027 = fixtures["t027_replay"]
    t028 = fixtures["t028_replay"]
    assert not isinstance(t027, Task029BlockerEntry)
    assert not isinstance(t028, Task029BlockerEntry)
    binding = bind_members_to_producers(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=t027,
        task028_replay_evidence=t028,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert binding.blockers == ()
    task027_count = sum(
        1
        for m in fixtures["composition"].member_authorities
        if m.producer_task == ProducerTask.TASK_027
    )
    assert task027_count == 1


def test_T029_AUTH_008_TASK028_COMPONENT_ONE_TO_ONE() -> None:
    fixtures = build_production_fixtures()
    duplicate_member = replace(
        fixtures["m000"],
        member_id="M000B",
        global_path_sequence_index=2,
    )
    bad_composition = recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], duplicate_member),
        )
    )
    binding = bind_members_to_producers(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert any(b.code == Task029BlockerCode.BL_T029_DUPLICATE_MEMBER for b in binding.blockers)


def test_T029_AUTH_009_TASK028_COMPONENT_TYPE_BINDING() -> None:
    fixtures = build_production_fixtures()
    bad_m000 = replace(fixtures["m000"], expected_producer_component_type="EXIT")
    bad_composition = recompute_composition(
        replace(fixtures["composition"], member_authorities=(bad_m000, fixtures["m001"]))
    )
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_EXPECTED_MEMBER_MISSING for b in binding.blockers
    )


def test_T029_AUTH_010_TASK028_AUTHORITY_HASH_BINDING() -> None:
    fixtures = build_production_fixtures()
    bad_m000 = replace(fixtures["m000"], expected_producer_authority_hash="0" * 64)
    bad_composition = recompute_composition(
        replace(fixtures["composition"], member_authorities=(bad_m000, fixtures["m001"]))
    )
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_COMPOSITION_MEMBER_AUTHORITY_HASH_MISMATCH
        for b in binding.blockers
    )


def test_T029_AUTH_011_EXPECTED_MULTIPLICITY_BINDING() -> None:
    fixtures = build_production_fixtures()
    high_multiplicity_component = replace(fixtures["component"], multiplicity=3)
    bad_t028 = rebuild_task028(fixtures, high_multiplicity_component)
    bad_t028_replay = replay_task028_success(bad_t028)
    assert not isinstance(bad_t028_replay, Task029BlockerEntry)
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=bad_t028_replay,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    blockers = T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE(
        composition_authority=fixtures["composition"],
        bound_members=binding.bound_members,
    )
    assert any(b.code == Task029BlockerCode.BL_T029_MULTIPLICITY_INCOMPATIBILITY for b in blockers)


def test_T029_AUTH_012_EXACT_MEMBER_PLANES() -> None:
    fixtures = build_production_fixtures()
    bad_m000 = replace(fixtures["m000"], expected_upstream_reference_plane="P9")
    bad_composition = recompute_composition(
        replace(fixtures["composition"], member_authorities=(bad_m000, fixtures["m001"]))
    )
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    topology = evaluate_path_topology(
        composition_authority=bad_composition,
        binding_result=binding,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_REFERENCE_PLANE_DISCONTINUITY
        for b in topology.blockers
    )


def test_T029_AUTH_013_FLOW_DIRECTION_START_TO_END() -> None:
    fixtures = build_production_fixtures()
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    blockers = T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE(
        composition_authority=fixtures["composition"],
        bound_members=binding.bound_members,
    )
    assert blockers == ()
    assert (
        fixtures["composition"].flow_direction_assertion
        == Task029FlowDirectionAssertion.START_TO_END
    )

    bad_component = replace(
        fixtures["component"],
        flow_direction_assertion=Task028ComponentFlowDirectionAssertion.END_TO_START,
    )
    bad_t028 = rebuild_task028(fixtures, bad_component)
    bad_t028_replay = replay_task028_success(bad_t028)
    assert not isinstance(bad_t028_replay, Task029BlockerEntry)
    bad_binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=bad_t028_replay,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    component_blockers = T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE(
        composition_authority=fixtures["composition"],
        bound_members=bad_binding.bound_members,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_FLOW_DIRECTION_MISMATCH
        and b.field_path == "task028_success_result.component_results[].flow_direction_assertion"
        for b in component_blockers
    )
    assert not any(
        b.code == Task029BlockerCode.BL_T029_FLOW_DIRECTION_MISMATCH
        and b.field_path == "composition_authority.flow_direction_assertion"
        for b in component_blockers
    )

    bad_authority = clone_with_field(
        fixtures["composition"],
        flow_direction_assertion="END_TO_START",
    )
    authority_blockers = T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE(
        composition_authority=bad_authority,
        bound_members=binding.bound_members,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_FLOW_DIRECTION_MISMATCH
        and b.field_path == "composition_authority.flow_direction_assertion"
        for b in authority_blockers
    )
    t05_blockers = T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES(
        schema_version=fixtures["request"].schema_version,
        profile_id=fixtures["request"].profile_id,
        request_hash=fixtures["request"].request_hash,
        composition_authority=bad_authority,
        task027_result_hash=fixtures["task027"].result_hash,
        task028_result_hash=bad_t028.result_hash,
        task025_hydraulic_authority_hash=fixtures["task027"].task025_hydraulic_authority_hash,
        task025_result_hash=fixtures["task027"].task025_result_hash,
        task026_result_hash=fixtures["task027"].task026_result_hash,
        property_snapshot_hash=fixtures["task027"].property_snapshot_hash,
    )
    assert not any(
        b.code == Task029BlockerCode.BL_T029_FLOW_DIRECTION_MISMATCH for b in t05_blockers
    )


def test_T029_AUTH_014_NO_HIDDEN_EXCLUSION() -> None:
    fixtures = build_production_fixtures()
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    trimmed = replace(
        fixtures["composition"],
        exclusion_authorities=fixtures["composition"].exclusion_authorities[:-1],
    )
    result = validate_exclusion_partition_and_completeness(
        composition_authority=trimmed,
        binding_result=binding,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_EXCLUSION_EVIDENCE_MISSING for b in result.blockers
    )


def test_T029_AUTH_015_EVIDENCE_REF_CANONICAL_ORDER() -> None:
    refs = ("z-ref", "a-ref", "m-ref")
    sorted_refs = sort_evidence_refs(refs)
    assert sorted_refs == ("a-ref", "m-ref", "z-ref")
    assert sort_evidence_refs(sorted_refs) == sorted_refs


def test_T029_AUTH_016_EXCLUSION_PARTITION_COVERAGE() -> None:
    fixtures = build_production_fixtures()
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    result = validate_exclusion_partition_and_completeness(
        composition_authority=fixtures["composition"],
        binding_result=binding,
    )
    assert result.complete_within_modeled_boundary
    assert result.blockers == ()

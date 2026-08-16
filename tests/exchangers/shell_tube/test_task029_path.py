"""TASK-029 path topology contract tests (I17): 10 frozen TEST_ID proofs."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    Task029BlockerCode,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_success_result_hash,
    derive_result_id,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.path_binding import (
    bind_members_to_producers,
    evaluate_path_topology,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline import (
    compute_task029_composition,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.upstream_replay import (
    replay_task028_success,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.validation import (
    T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS,
    T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY,
    T09_VALIDATE_EXCLUSION_PARTITION_AND_COMPLETENESS,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    INPUT_EVIDENCE_REFS,
    VECTOR_06_MODELED_TOTAL,
    VECTOR_06_SUCCESS_RESULT_HASH,
    VECTOR_06_SUCCESS_RESULT_ID,
)
from tests.exchangers.shell_tube.test_task029_upstream import (
    build_oracle_success_result,
    build_production_fixtures,
    composition_to_raw_dict,
    rebuild_task028,
    recompute_composition,
)


def _binding(fixtures: dict) -> object:
    return T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )


def test_T029_PATH_001_ADJACENT_CONTINUITY() -> None:
    fixtures = build_production_fixtures()
    binding = _binding(fixtures)
    topology = evaluate_path_topology(
        composition_authority=fixtures["composition"],
        binding_result=binding,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert topology.blockers == ()
    ordered = topology.ordered_bound_members
    for index in range(len(ordered) - 1):
        assert (
            ordered[index].downstream_reference_plane == ordered[index + 1].upstream_reference_plane
        )


def test_T029_PATH_002_BOUNDARY_MATCH() -> None:
    fixtures = build_production_fixtures()
    composition = fixtures["composition"]
    binding = _binding(fixtures)
    topology = evaluate_path_topology(
        composition_authority=composition,
        binding_result=binding,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert topology.blockers == ()
    ordered = topology.ordered_bound_members
    assert ordered[0].upstream_reference_plane == composition.start_reference_plane
    assert ordered[-1].downstream_reference_plane == composition.end_reference_plane


def test_T029_PATH_003_SELF_LOOP() -> None:
    fixtures = build_production_fixtures()
    loop_component = replace(
        fixtures["component"],
        upstream_reference_plane="P0",
        downstream_reference_plane="P0",
    )
    bad_t028 = rebuild_task028(fixtures, loop_component)
    bad_t028_replay = replay_task028_success(bad_t028)
    fixtures = {**fixtures, "task028": bad_t028, "t028_replay": bad_t028_replay}
    binding = _binding(fixtures)
    topology = evaluate_path_topology(
        composition_authority=fixtures["composition"],
        binding_result=binding,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_REFERENCE_PLANE_SELF_LOOP for b in topology.blockers
    )


def test_T029_PATH_004_CYCLE() -> None:
    fixtures = build_production_fixtures()
    bad_m001 = replace(
        fixtures["m001"],
        expected_upstream_reference_plane="P1",
        expected_downstream_reference_plane="P0",
    )
    bad_composition = recompute_composition(
        replace(fixtures["composition"], member_authorities=(fixtures["m000"], bad_m001))
    )
    binding = bind_members_to_producers(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane="P1",
        task027_downstream_reference_plane="P0",
    )
    topology = evaluate_path_topology(
        composition_authority=bad_composition,
        binding_result=binding,
        task027_upstream_reference_plane="P1",
        task027_downstream_reference_plane="P0",
    )
    assert any(b.code == Task029BlockerCode.BL_T029_PATH_CYCLE for b in topology.blockers)


def test_T029_PATH_005_FORK() -> None:
    fixtures = build_production_fixtures()
    fork_component = replace(
        fixtures["component"],
        component_id="ENTRANCE-002",
        path_sequence_index=1,
    )
    bad_t028 = rebuild_task028(fixtures, fixtures["component"], fork_component)
    bad_t028_replay = replay_task028_success(bad_t028)
    fork_member = replace(
        fixtures["m000"],
        member_id="M000B",
        global_path_sequence_index=2,
        producer_component_identity="ENTRANCE-002",
    )
    bad_composition = recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], fork_member),
        )
    )
    binding = bind_members_to_producers(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=bad_t028_replay,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    topology = evaluate_path_topology(
        composition_authority=bad_composition,
        binding_result=binding,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert any(b.code == Task029BlockerCode.BL_T029_PATH_FORK for b in topology.blockers)


def test_T029_PATH_006_JOIN() -> None:
    fixtures = build_production_fixtures()
    join_member = replace(
        fixtures["m001"],
        member_id="M001B",
        global_path_sequence_index=2,
        expected_upstream_reference_plane="P2",
        expected_downstream_reference_plane="P2",
    )
    bad_composition = recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], join_member),
        )
    )
    binding = bind_members_to_producers(
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
    assert any(b.code == Task029BlockerCode.BL_T029_PATH_JOIN for b in topology.blockers)


def test_T029_PATH_007_OVERLAPPING_DIRECTED_SEGMENT() -> None:
    fixtures = build_production_fixtures()
    overlap_component = replace(
        fixtures["component"],
        component_id="ENTRANCE-002",
        path_sequence_index=1,
    )
    bad_t028 = rebuild_task028(fixtures, fixtures["component"], overlap_component)
    bad_t028_replay = replay_task028_success(bad_t028)
    overlap_member = replace(
        fixtures["m000"],
        member_id="M000DUP",
        global_path_sequence_index=2,
        producer_component_identity="ENTRANCE-002",
    )
    bad_composition = recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], overlap_member),
        )
    )
    binding = bind_members_to_producers(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=bad_t028_replay,
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
        b.code == Task029BlockerCode.BL_T029_OVERLAPPING_PATH_SEGMENT for b in topology.blockers
    )


def test_T029_PATH_008_EXPECTED_MEMBER_MISSING() -> None:
    fixtures = build_production_fixtures()
    bad_m000 = replace(fixtures["m000"], producer_component_identity="MISSING-COMPONENT")
    bad_composition = recompute_composition(
        replace(fixtures["composition"], member_authorities=(bad_m000, fixtures["m001"]))
    )
    binding = bind_members_to_producers(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_EXPECTED_MEMBER_MISSING for b in binding.blockers
    )


def test_T029_PATH_009_UNEXPECTED_EXTRA_MEMBER() -> None:
    fixtures = build_production_fixtures()
    extra = replace(fixtures["m001"], member_id="M002", global_path_sequence_index=2)
    bad_composition = recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], extra),
        )
    )
    binding = bind_members_to_producers(
        composition_authority=bad_composition,
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_UNEXPECTED_EXTRA_MEMBER for b in binding.blockers
    )


def test_T029_PATH_010_SAME_PHYSICAL_PATH_PROOF() -> None:
    fixtures = build_production_fixtures()
    binding = _binding(fixtures)
    topology = T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY(
        composition_authority=fixtures["composition"],
        binding_result=binding,
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert topology.blockers == ()
    exclusion_blockers = T09_VALIDATE_EXCLUSION_PARTITION_AND_COMPLETENESS(
        composition_authority=fixtures["composition"],
        binding_result=binding,
    )
    assert exclusion_blockers == ()

    pipeline_result = compute_task029_composition(
        composition_to_raw_dict(fixtures),
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    assert isinstance(pipeline_result, Task029SuccessResult)
    assert pipeline_result.modeled_total_tube_side_pressure_drop_pa == VECTOR_06_MODELED_TOTAL
    assert pipeline_result.task027_result_hash == fixtures["task027"].result_hash
    assert pipeline_result.task028_result_hash == fixtures["task028"].result_hash

    oracle_success = build_oracle_success_result()
    oracle_hash = compute_success_result_hash(oracle_success)
    assert oracle_hash == VECTOR_06_SUCCESS_RESULT_HASH
    assert derive_result_id(oracle_hash) == VECTOR_06_SUCCESS_RESULT_ID

    planes = topology.plane_sequence
    assert len(set(planes)) == len(planes)
    for bound in topology.ordered_bound_members:
        assert bound.upstream_reference_plane != bound.downstream_reference_plane
    naive_sum = Decimal("250.000") + Decimal("101.504")
    assert naive_sum == VECTOR_06_MODELED_TOTAL
    assert topology.blockers == ()

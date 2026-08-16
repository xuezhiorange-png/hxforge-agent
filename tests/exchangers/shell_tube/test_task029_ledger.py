"""TASK-029 completeness ledger contract tests (I17): 6 frozen TEST_ID proofs."""

from __future__ import annotations

from dataclasses import fields

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    TASK029_DEFERRED_CAPABILITIES_V1,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.completeness import (
    build_completeness_ledger,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.composition import (
    extract_pressure_contribution,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    CompletenessStatus,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_ledger_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline import (
    compute_task029_composition,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.result import (
    build_exclusion_evidence,
    build_member_evidence,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.validation import (
    T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    INPUT_EVIDENCE_REFS,
    LEDGER_FIXTURE,
    VECTOR_05_LEDGER_HASH,
)
from tests.exchangers.shell_tube.test_task029_upstream import (
    build_oracle_ledger,
    build_production_fixtures,
    composition_to_raw_dict,
)


def test_T029_LED_001_MEMBER_EVIDENCE_SCHEMA() -> None:
    fixtures = build_production_fixtures()
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    member = binding.bound_members[0]
    evidence = build_member_evidence(
        member,
        observed_multiplicity=member.expected_multiplicity,
        pressure_contribution_pa=extract_pressure_contribution(member),
    )
    assert len(fields(evidence)) == 16


def test_T029_LED_002_EXCLUSION_EVIDENCE_SCHEMA() -> None:
    fixtures = build_production_fixtures()
    exclusion = fixtures["composition"].exclusion_authorities[0]
    evidence = build_exclusion_evidence(exclusion)
    assert len(fields(evidence)) == 7


def test_T029_LED_003_COMPLETE_WITHIN_MODELED_BOUNDARY() -> None:
    fixtures = build_production_fixtures()
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    member_evidence = tuple(
        build_member_evidence(
            bound,
            observed_multiplicity=bound.expected_multiplicity,
            pressure_contribution_pa=extract_pressure_contribution(bound),
        )
        for bound in binding.bound_members
    )
    exclusion_evidence = tuple(
        build_exclusion_evidence(exclusion)
        for exclusion in fixtures["composition"].exclusion_authorities
    )
    ledger = build_completeness_ledger(
        composition_authority=fixtures["composition"],
        member_evidence=member_evidence,
        exclusion_evidence=exclusion_evidence,
    )
    assert (
        ledger.completeness_status == CompletenessStatus.COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY
    )


def test_T029_LED_004_EXCLUSION_SELF_DESCRIPTION() -> None:
    fixtures = build_production_fixtures()
    for exclusion in fixtures["composition"].exclusion_authorities:
        evidence = build_exclusion_evidence(exclusion)
        assert evidence.exclusion_id == exclusion.exclusion_id
        assert evidence.excluded_item_identity == exclusion.excluded_item_identity
        assert evidence.exclusion_reason == exclusion.exclusion_reason
        assert evidence.evidence_refs == exclusion.evidence_refs
        assert evidence.exclusion_authority_hash == exclusion.exclusion_authority_hash


def test_T029_LED_005_LEDGER_HASH_VECTOR() -> None:
    ledger = build_oracle_ledger()
    actual = compute_ledger_hash(ledger)
    assert actual == VECTOR_05_LEDGER_HASH
    assert LEDGER_FIXTURE["ledger_hash"] == VECTOR_05_LEDGER_HASH


def test_T029_LED_006_FULL_PHYSICAL_COMPLETENESS_NOT_CLAIMED() -> None:
    result = compute_task029_composition(
        composition_to_raw_dict(build_production_fixtures()),
        task027_success_result=build_production_fixtures()["task027"],
        task028_success_result=build_production_fixtures()["task028"],
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    assert isinstance(result, Task029SuccessResult)
    assert "FULL_PHYSICAL_PRESSURE_DROP_COMPLETENESS_NOT_CLAIMED" in result.deferred_capabilities
    assert result.deferred_capabilities == TASK029_DEFERRED_CAPABILITIES_V1
    assert "FULL_PHYSICAL_PRESSURE_DROP_COMPLETE" not in result.deferred_capabilities

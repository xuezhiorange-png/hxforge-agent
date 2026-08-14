"""TASK-029 composition arithmetic contract tests (I17): 10 frozen TEST_ID proofs."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, localcontext

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.composition import (
    extract_pressure_contribution,
    pressure_contribution_field_path,
    sum_ordered_contributions,
    validate_contribution,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.decimal_identity import (
    TASK029_PRESSURE_QUANTUM_PA,
    task029_decimal_context,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ProducerTask,
    Task029BlockerCode,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockedResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.raw_projection import (
    encode_raw_projection,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.result import (
    build_blocked_result,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.upstream_replay import (
    replay_task028_success,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.validation import (
    T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS,
    T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    VECTOR_06_MODELED_TOTAL,
)
from tests.exchangers.shell_tube.test_task029_upstream import (
    build_production_fixtures,
    rebuild_task028,
)


def _bound_members(fixtures: dict) -> tuple:
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=fixtures["composition"],
        task027_replay_evidence=fixtures["t027_replay"],
        task028_replay_evidence=fixtures["t028_replay"],
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    return binding.bound_members


def test_T029_COMP_001_TASK027_PRESSURE_FIELD_BINDING() -> None:
    fixtures = build_production_fixtures()
    task027_member = next(
        m for m in _bound_members(fixtures) if m.producer_task == ProducerTask.TASK_027
    )
    assert pressure_contribution_field_path(task027_member) == (
        "task027_success_result.straight_tube_friction_pressure_drop_pa"
    )
    contribution = extract_pressure_contribution(task027_member)
    assert contribution == Decimal("250.000")


def test_T029_COMP_002_TASK028_PRESSURE_FIELD_BINDING() -> None:
    fixtures = build_production_fixtures()
    task028_member = next(
        m for m in _bound_members(fixtures) if m.producer_task == ProducerTask.TASK_028
    )
    assert pressure_contribution_field_path(task028_member) == (
        "task028_success_result.component_results[].component_irreversible_pressure_loss_pa"
    )
    contribution = extract_pressure_contribution(task028_member)
    assert contribution == Decimal("101.504")


def test_T029_COMP_003_SINGLE_OCCURRENCE_NOT_ADDED() -> None:
    fixtures = build_production_fixtures()
    divergent_component = replace(
        fixtures["component"],
        single_occurrence_irreversible_pressure_loss_pa=Decimal("999.999"),
        component_irreversible_pressure_loss_pa=Decimal("101.504"),
    )
    bad_t028 = rebuild_task028(fixtures, divergent_component)
    fixtures = {**fixtures, "task028": bad_t028, "t028_replay": fixtures["t028_replay"]}
    task028_member = next(
        m for m in _bound_members(fixtures) if m.producer_task == ProducerTask.TASK_028
    )
    contribution = extract_pressure_contribution(task028_member)
    assert contribution == Decimal("101.504")
    assert contribution != divergent_component.single_occurrence_irreversible_pressure_loss_pa


def test_T029_COMP_004_MULTIPLICITY_NOT_REAPPLIED() -> None:
    fixtures = build_production_fixtures()
    high_multiplicity = replace(fixtures["component"], multiplicity=3)
    bad_t028 = rebuild_task028(fixtures, high_multiplicity)
    bad_t028_replay = replay_task028_success(bad_t028)
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


def test_T029_COMP_005_PRESSURE_FINITE_POSITIVE() -> None:
    blockers = validate_contribution(
        Decimal("0"),
        field_path="task027_success_result.straight_tube_friction_pressure_drop_pa",
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_PRESSURE_CONTRIBUTION_NONPOSITIVE for b in blockers
    )
    good = validate_contribution(
        Decimal("250.000"),
        field_path="task027_success_result.straight_tube_friction_pressure_drop_pa",
    )
    assert good == ()


def test_T029_COMP_006_PRESSURE_QUANTUM_001_PA() -> None:
    with localcontext(task029_decimal_context()):
        unquantized = Decimal("1.0005")
        blockers = validate_contribution(
            unquantized,
            field_path="task027_success_result.straight_tube_friction_pressure_drop_pa",
        )
        assert any(b.code == Task029BlockerCode.BL_T029_PRESSURE_QUANTUM_MISMATCH for b in blockers)
        assert Decimal("0.001") == TASK029_PRESSURE_QUANTUM_PA


def test_T029_COMP_007_GLOBAL_ORDER_DECIMAL_SUM() -> None:
    fixtures = build_production_fixtures()
    contributions = tuple(extract_pressure_contribution(m) for m in _bound_members(fixtures))
    total = sum_ordered_contributions(contributions)
    assert total == VECTOR_06_MODELED_TOTAL


def test_T029_COMP_008_MODELED_TOTAL_351_504() -> None:
    fixtures = build_production_fixtures()
    contributions = tuple(extract_pressure_contribution(m) for m in _bound_members(fixtures))
    actual = sum_ordered_contributions(contributions)
    assert actual == VECTOR_06_MODELED_TOTAL


def test_T029_COMP_009_ACTIVE_TUBE_COUNT_NOT_MULTIPLIER() -> None:
    fixtures = build_production_fixtures()
    contributions = tuple(extract_pressure_contribution(m) for m in _bound_members(fixtures))
    total = sum_ordered_contributions(contributions)
    assert total == Decimal("351.504")
    scaled = sum_ordered_contributions(tuple(c * 10 for c in contributions))
    assert scaled != total


def test_T029_COMP_010_NO_PARTIAL_MODELED_TOTAL() -> None:
    projection = encode_raw_projection("task029.raw-request", {})
    result = build_blocked_result(
        profile_id="profile-001",
        request_hash=None,
        task027_result_hash="0" * 64,
        task028_result_hash="0" * 64,
        task025_hydraulic_authority_hash="0" * 64,
        task025_result_hash="0" * 64,
        task026_result_hash="0" * 64,
        property_snapshot_hash=None,
        composition_authority_hash="0" * 64,
        raw_request_projection=projection,
        raw_upstream_blocked_projection=None,
        blockers=(),
        attempted_modeled_total_tube_side_pressure_drop_pa=VECTOR_06_MODELED_TOTAL,
    )
    assert isinstance(result, Task029BlockedResult)
    assert not hasattr(result, "completeness_ledger")
    assert not hasattr(result, "modeled_total_tube_side_pressure_drop_pa")
    assert any(
        b.code == Task029BlockerCode.BL_T029_PARTIAL_RESULT_FORBIDDEN for b in result.blockers
    )

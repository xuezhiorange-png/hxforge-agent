"""TASK-029 upstream contract tests (I17): 12 frozen TEST_ID proofs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
    Task027SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    compute_result_hash as t027_compute_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    derive_result_id as t027_derive_result_id,
)
from hexagent.exchangers.shell_tube.tube_side.provenance import FrozenProvenance
from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
    TASK028_DEFERRED_CAPABILITIES_V1,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    LossCoefficientConvention,
    Task028ComponentFlowDirectionAssertion,
    Task028ComponentType,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
    TubeSideLocalLossComponentResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    build_success_result as build_t028_success,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    COMPLETENESS_LEDGER_SCHEMA_VERSION,
    COMPOSITION_AUTHORITY_SCHEMA_VERSION,
    MEMBER_AUTHORITY_SCHEMA_VERSION,
    TASK027_ACCEPTED_SCHEMA_VERSION,
    TASK028_ACCEPTED_SCHEMA_VERSION,
    TASK029_DEFERRED_CAPABILITIES_V1,
    TASK029_SUCCESS_RESULT_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    CompletenessStatus,
    ExclusionReason,
    ExclusionStatus,
    IdentityCompatibilityStatus,
    MemberStatus,
    PathContinuityStatus,
    ProducerMemberKind,
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
    Task029Request,
    Task029SuccessResult,
    TubeSidePressurePathCompletenessLedger,
    TubeSidePressurePathCompositionAuthority,
    TubeSidePressurePathExclusionAuthority,
    TubeSidePressurePathLedgerExclusionEvidence,
    TubeSidePressurePathLedgerMemberEvidence,
    TubeSidePressurePathMemberAuthority,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.request import (
    build_task029_request,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.result import (
    build_provenance,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.upstream_replay import (
    Task027ReplayEvidence,
    Task028ReplayEvidence,
    replay_task027_success,
    replay_task028_success,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.validation import (
    T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS,
    T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS,
    T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    EXCLUSION_AUTHORITY_FIXTURES,
    INPUT_EVIDENCE_REFS,
    LEDGER_EXCLUSION_FIXTURES,
    LEDGER_MEMBER_FIXTURES,
    PROFILE_ID,
    PROPERTY_SNAPSHOT_HASH,
    PROPERTY_SNAPSHOT_HASH_MISMATCH,
    TASK025_HYDRAULIC_AUTHORITY_HASH,
    TASK025_RESULT_HASH,
    TASK026_RESULT_HASH,
    TASK027_RESULT_HASH,
    TASK028_COMPONENT_AUTHORITY_HASH,
    TASK028_RESULT_HASH,
    TASK029_REQUEST_SCHEMA_VERSION,
    VECTOR_03_COMPOSITION_HASH,
    VECTOR_04_REQUEST_HASH,
    VECTOR_05_LEDGER_HASH,
    VECTOR_06_MODELED_TOTAL,
)


def member_from_fixture(fixture: Mapping[str, Any]) -> TubeSidePressurePathMemberAuthority:
    """Build a member authority dataclass from a frozen I15 fixture literal."""
    return TubeSidePressurePathMemberAuthority(
        schema_version=fixture["schema_version"],
        member_id=fixture["member_id"],
        global_path_sequence_index=fixture["global_path_sequence_index"],
        producer_task=ProducerTask(fixture["producer_task"]),
        producer_member_kind=ProducerMemberKind(fixture["producer_member_kind"]),
        producer_component_identity=fixture["producer_component_identity"],
        expected_producer_component_type=fixture["expected_producer_component_type"],
        expected_producer_authority_hash=fixture["expected_producer_authority_hash"],
        expected_upstream_reference_plane=fixture["expected_upstream_reference_plane"],
        expected_downstream_reference_plane=fixture["expected_downstream_reference_plane"],
        expected_multiplicity=fixture["expected_multiplicity"],
        geometry_evidence_refs=fixture["geometry_evidence_refs"],
        member_authority_hash=fixture["member_authority_hash"],
    )


def exclusion_from_fixture(fixture: Mapping[str, Any]) -> TubeSidePressurePathExclusionAuthority:
    """Build an exclusion authority dataclass from a frozen I15 fixture literal."""
    return TubeSidePressurePathExclusionAuthority(
        schema_version=fixture["schema_version"],
        exclusion_id=fixture["exclusion_id"],
        excluded_item_identity=fixture["excluded_item_identity"],
        exclusion_reason=ExclusionReason(fixture["exclusion_reason"]),
        evidence_refs=fixture["evidence_refs"],
        exclusion_authority_hash=fixture["exclusion_authority_hash"],
    )


def build_oracle_ledger() -> TubeSidePressurePathCompletenessLedger:
    """Build frozen oracle completeness ledger from I15 literals only."""
    members = tuple(
        TubeSidePressurePathLedgerMemberEvidence(
            schema_version=fixture["schema_version"],
            member_id=fixture["member_id"],
            global_path_sequence_index=fixture["global_path_sequence_index"],
            producer_task=ProducerTask(fixture["producer_task"]),
            producer_result_hash=fixture["producer_result_hash"],
            producer_member_kind=ProducerMemberKind(fixture["producer_member_kind"]),
            producer_component_identity=fixture["producer_component_identity"],
            producer_component_type=fixture["producer_component_type"],
            producer_authority_hash=fixture["producer_authority_hash"],
            upstream_reference_plane=fixture["upstream_reference_plane"],
            downstream_reference_plane=fixture["downstream_reference_plane"],
            expected_multiplicity=fixture["expected_multiplicity"],
            observed_multiplicity=fixture["observed_multiplicity"],
            pressure_contribution_pa=fixture["pressure_contribution_pa"],
            composition_member_authority_hash=fixture["composition_member_authority_hash"],
            member_status=MemberStatus(fixture["member_status"]),
        )
        for fixture in LEDGER_MEMBER_FIXTURES
    )
    exclusions = tuple(
        TubeSidePressurePathLedgerExclusionEvidence(
            schema_version=fixture["schema_version"],
            exclusion_id=fixture["exclusion_id"],
            excluded_item_identity=fixture["excluded_item_identity"],
            exclusion_reason=ExclusionReason(fixture["exclusion_reason"]),
            evidence_refs=fixture["evidence_refs"],
            exclusion_authority_hash=fixture["exclusion_authority_hash"],
            exclusion_status=ExclusionStatus(fixture["exclusion_status"]),
        )
        for fixture in LEDGER_EXCLUSION_FIXTURES
    )
    return TubeSidePressurePathCompletenessLedger(
        schema_version=COMPLETENESS_LEDGER_SCHEMA_VERSION,
        modeled_path_id="tube-side-path-001",
        modeled_start_reference_plane="P0",
        modeled_end_reference_plane="P2",
        expected_member_count=2,
        observed_member_count=2,
        ordered_member_evidence=members,
        ordered_exclusion_evidence=exclusions,
        path_continuity_status=PathContinuityStatus.CONTIGUOUS_EXACT_REFERENCE_PLANE_CHAIN,
        identity_compatibility_status=IdentityCompatibilityStatus.MATCHED,
        completeness_status=CompletenessStatus.COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY,
        ledger_hash=VECTOR_05_LEDGER_HASH,
    )


def build_oracle_success_result() -> Task029SuccessResult:
    """Build frozen oracle success semantic projection from I15 literals only."""
    provenance = build_provenance(
        input_evidence_refs=INPUT_EVIDENCE_REFS,
        task027_result_hash=TASK027_RESULT_HASH,
        task028_result_hash=TASK028_RESULT_HASH,
        task025_hydraulic_authority_hash=TASK025_HYDRAULIC_AUTHORITY_HASH,
        task025_result_hash=TASK025_RESULT_HASH,
        task026_result_hash=TASK026_RESULT_HASH,
        property_snapshot_hash=PROPERTY_SNAPSHOT_HASH,
        composition_authority_hash=VECTOR_03_COMPOSITION_HASH,
    )
    return Task029SuccessResult(
        schema_version=TASK029_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        request_hash=VECTOR_04_REQUEST_HASH,
        result_hash="",
        result_id="",
        task027_result_hash=TASK027_RESULT_HASH,
        task028_result_hash=TASK028_RESULT_HASH,
        task025_hydraulic_authority_hash=TASK025_HYDRAULIC_AUTHORITY_HASH,
        task025_result_hash=TASK025_RESULT_HASH,
        task026_result_hash=TASK026_RESULT_HASH,
        property_snapshot_hash=PROPERTY_SNAPSHOT_HASH,
        composition_authority_hash=VECTOR_03_COMPOSITION_HASH,
        completeness_ledger=build_oracle_ledger(),
        modeled_total_tube_side_pressure_drop_pa=VECTOR_06_MODELED_TOTAL,
        warnings=(),
        blockers=(),
        deferred_capabilities=TASK029_DEFERRED_CAPABILITIES_V1,
        provenance=provenance,
    )


def build_production_fixtures() -> dict[str, Any]:
    """Production-valid Task027/Task028/composition fixtures for I17 contract tests."""
    t027_prov = FrozenProvenance(
        task_id="TASK-027",
        design_contract_path="docs/tasks/TASK-027.md",
        implementation_software_version="0.2.0-dev",
        input_evidence_refs=(),
        upstream_identity_hashes=(),
    )
    t027_fields = dict(
        schema_version=TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        request_hash="0000000000000000000000000000000000000000000000000000000000000001",
        task025_hydraulic_authority_hash=TASK025_HYDRAULIC_AUTHORITY_HASH,
        task025_result_hash=TASK025_RESULT_HASH,
        task026_result_hash=TASK026_RESULT_HASH,
        property_snapshot_hash=PROPERTY_SNAPSHOT_HASH,
        darcy_friction_factor=Decimal("0.02"),
        friction_length_m=Decimal("1.0"),
        upstream_reference_plane="P1",
        downstream_reference_plane="P2",
        straight_tube_friction_pressure_drop_pa=Decimal("250.000"),
    )
    t027_rh = t027_compute_result_hash(
        darcy_friction_factor="0.02",
        friction_length_m="1.0",
        straight_tube_friction_pressure_drop_pa="250.000",
        upstream_reference_plane="P1",
        downstream_reference_plane="P2",
        schema_version=t027_fields["schema_version"],
        profile_id=t027_fields["profile_id"],
        request_hash=t027_fields["request_hash"],
        task025_hydraulic_authority_hash=TASK025_HYDRAULIC_AUTHORITY_HASH,
        task025_result_hash=TASK025_RESULT_HASH,
        task026_result_hash=TASK026_RESULT_HASH,
        property_snapshot_hash=PROPERTY_SNAPSHOT_HASH,
    )
    task027 = Task027SuccessResult(
        **t027_fields,
        result_hash=t027_rh,
        result_id=t027_derive_result_id(t027_rh),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=t027_prov,
    )
    component = TubeSideLocalLossComponentResult(
        component_id="ENTRANCE-001",
        component_type=Task028ComponentType.ENTRANCE,
        path_sequence_index=0,
        upstream_reference_plane="P0",
        downstream_reference_plane="P1",
        flow_direction_assertion=Task028ComponentFlowDirectionAssertion.START_TO_END,
        authority_hash=TASK028_COMPONENT_AUTHORITY_HASH,
        reference_flow_area_m2=Decimal("0.007854"),
        reference_velocity_m_s=Decimal("0.63776775"),
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention=(
            LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
        ),
        multiplicity=1,
        single_occurrence_irreversible_pressure_loss_pa=Decimal("101.504"),
        component_irreversible_pressure_loss_pa=Decimal("101.504"),
    )
    t028_prov = FrozenProvenance(
        task_id="TASK-028",
        design_contract_path="docs/tasks/TASK-028.md",
        implementation_software_version="0.2.0-dev",
        input_evidence_refs=(),
        upstream_identity_hashes=(),
    )
    task028 = build_t028_success(
        profile_id=PROFILE_ID,
        request_hash="0000000000000000000000000000000000000000000000000000000000000002",
        task025_hydraulic_authority_hash=TASK025_HYDRAULIC_AUTHORITY_HASH,
        task025_result_hash=TASK025_RESULT_HASH,
        task026_result_hash=TASK026_RESULT_HASH,
        property_snapshot_hash=PROPERTY_SNAPSHOT_HASH,
        component_results=(component,),
        warnings=(),
        blockers=(),
        deferred_capabilities=TASK028_DEFERRED_CAPABILITIES_V1,
        provenance=t028_prov,
    )
    m000_base = TubeSidePressurePathMemberAuthority(
        schema_version=MEMBER_AUTHORITY_SCHEMA_VERSION,
        member_id="M000",
        global_path_sequence_index=0,
        producer_task=ProducerTask.TASK_028,
        producer_member_kind=ProducerMemberKind.LOCAL_MINOR_LOSS,
        producer_component_identity="ENTRANCE-001",
        expected_producer_component_type="ENTRANCE",
        expected_producer_authority_hash=TASK028_COMPONENT_AUTHORITY_HASH,
        expected_upstream_reference_plane="P0",
        expected_downstream_reference_plane="P1",
        expected_multiplicity=1,
        geometry_evidence_refs=("geom:entrance-001",),
        member_authority_hash="",
    )
    m000 = replace(m000_base, member_authority_hash=compute_member_authority_hash(m000_base))
    m001_base = TubeSidePressurePathMemberAuthority(
        schema_version=MEMBER_AUTHORITY_SCHEMA_VERSION,
        member_id="M001",
        global_path_sequence_index=1,
        producer_task=ProducerTask.TASK_027,
        producer_member_kind=ProducerMemberKind.DISTRIBUTED_FRICTION,
        producer_component_identity="STRAIGHT_TUBE_FRICTION",
        expected_producer_component_type="STRAIGHT_TUBE_FRICTION",
        expected_producer_authority_hash="",
        expected_upstream_reference_plane="P1",
        expected_downstream_reference_plane="P2",
        expected_multiplicity=1,
        geometry_evidence_refs=("geom:straight-tube-001",),
        member_authority_hash="",
    )
    m001 = replace(m001_base, member_authority_hash=compute_member_authority_hash(m001_base))
    exclusions: list[TubeSidePressurePathExclusionAuthority] = []
    for exclusion_fixture in EXCLUSION_AUTHORITY_FIXTURES:
        base = TubeSidePressurePathExclusionAuthority(
            schema_version=exclusion_fixture["schema_version"],
            exclusion_id=exclusion_fixture["exclusion_id"],
            excluded_item_identity=exclusion_fixture["excluded_item_identity"],
            exclusion_reason=ExclusionReason(exclusion_fixture["exclusion_reason"]),
            evidence_refs=exclusion_fixture["evidence_refs"],
            exclusion_authority_hash="",
        )
        exclusions.append(
            replace(base, exclusion_authority_hash=compute_exclusion_authority_hash(base))
        )
    comp_base = TubeSidePressurePathCompositionAuthority(
        schema_version=COMPOSITION_AUTHORITY_SCHEMA_VERSION,
        modeled_path_id="tube-side-path-001",
        flow_direction_assertion=Task029FlowDirectionAssertion.START_TO_END,
        start_reference_plane="P0",
        end_reference_plane="P2",
        member_authorities=(m000, m001),
        exclusion_authorities=tuple(exclusions),
        geometry_evidence_refs=("geom:path-001",),
        composition_authority_hash="",
    )
    composition = replace(
        comp_base, composition_authority_hash=compute_composition_authority_hash(comp_base)
    )
    request = build_task029_request(
        profile_id=PROFILE_ID,
        task027_success_result=task027,
        task028_success_result=task028,
        composition_authority=composition,
    )
    return {
        "composition": composition,
        "m000": m000,
        "m001": m001,
        "component": component,
        "task027": task027,
        "task028": task028,
        "request": request,
        "t027_replay": replay_task027_success(task027),
        "t028_replay": replay_task028_success(task028),
    }


def composition_to_raw_dict(
    fixtures: dict[str, Any],
    composition: TubeSidePressurePathCompositionAuthority | None = None,
) -> dict[str, Any]:
    """Serialize a composition authority into a raw TASK-029 request dict."""
    composition = composition or fixtures["composition"]

    def member_dict(member: TubeSidePressurePathMemberAuthority) -> dict[str, Any]:
        return {
            "schema_version": member.schema_version,
            "member_id": member.member_id,
            "global_path_sequence_index": member.global_path_sequence_index,
            "producer_task": member.producer_task.value,
            "producer_member_kind": member.producer_member_kind.value,
            "producer_component_identity": member.producer_component_identity,
            "expected_producer_component_type": member.expected_producer_component_type,
            "expected_producer_authority_hash": member.expected_producer_authority_hash,
            "expected_upstream_reference_plane": member.expected_upstream_reference_plane,
            "expected_downstream_reference_plane": member.expected_downstream_reference_plane,
            "expected_multiplicity": member.expected_multiplicity,
            "geometry_evidence_refs": member.geometry_evidence_refs,
            "member_authority_hash": member.member_authority_hash,
        }

    def exclusion_dict(exclusion: TubeSidePressurePathExclusionAuthority) -> dict[str, Any]:
        return {
            "schema_version": exclusion.schema_version,
            "exclusion_id": exclusion.exclusion_id,
            "excluded_item_identity": exclusion.excluded_item_identity,
            "exclusion_reason": exclusion.exclusion_reason.value,
            "evidence_refs": exclusion.evidence_refs,
            "exclusion_authority_hash": exclusion.exclusion_authority_hash,
        }

    comp_dict = {
        "schema_version": composition.schema_version,
        "modeled_path_id": composition.modeled_path_id,
        "flow_direction_assertion": composition.flow_direction_assertion.value,
        "start_reference_plane": composition.start_reference_plane,
        "end_reference_plane": composition.end_reference_plane,
        "member_authorities": tuple(member_dict(m) for m in composition.member_authorities),
        "exclusion_authorities": tuple(
            exclusion_dict(e) for e in composition.exclusion_authorities
        ),
        "geometry_evidence_refs": composition.geometry_evidence_refs,
        "composition_authority_hash": composition.composition_authority_hash,
    }
    return {
        "schema_version": TASK029_REQUEST_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "composition_authority": comp_dict,
        "request_hash": VECTOR_04_REQUEST_HASH,
    }


def rebuild_task028(
    fixtures: dict[str, Any],
    *components: TubeSideLocalLossComponentResult,
) -> Task028SuccessResult:
    """Rebuild TASK-028 success with alternate component results."""
    task028 = fixtures["task028"]
    return build_t028_success(
        profile_id=task028.profile_id,
        request_hash=task028.request_hash,
        task025_hydraulic_authority_hash=task028.task025_hydraulic_authority_hash,
        task025_result_hash=task028.task025_result_hash,
        task026_result_hash=task028.task026_result_hash,
        property_snapshot_hash=task028.property_snapshot_hash,
        component_results=tuple(components),
        warnings=task028.warnings,
        blockers=task028.blockers,
        deferred_capabilities=task028.deferred_capabilities,
        provenance=task028.provenance,
    )


def task028_with_property_snapshot(
    fixtures: dict[str, Any],
    property_snapshot_hash: str,
) -> Task028SuccessResult:
    """Return TASK-028 success with an overridden property snapshot hash."""
    task028 = fixtures["task028"]
    return build_t028_success(
        profile_id=task028.profile_id,
        request_hash=task028.request_hash,
        task025_hydraulic_authority_hash=task028.task025_hydraulic_authority_hash,
        task025_result_hash=task028.task025_result_hash,
        task026_result_hash=task028.task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        component_results=task028.component_results,
        warnings=task028.warnings,
        blockers=task028.blockers,
        deferred_capabilities=task028.deferred_capabilities,
        provenance=task028.provenance,
    )


def recompute_composition(
    composition: TubeSidePressurePathCompositionAuthority,
) -> TubeSidePressurePathCompositionAuthority:
    """Recompute member and composition authority hashes."""
    members = tuple(
        replace(member, member_authority_hash=compute_member_authority_hash(member))
        for member in composition.member_authorities
    )
    interim = replace(composition, member_authorities=members, composition_authority_hash="")
    return replace(
        interim,
        composition_authority_hash=compute_composition_authority_hash(interim),
    )


def clone_with_field(instance: Any, **overrides: Any) -> Any:
    """Clone a frozen dataclass instance while bypassing ``__post_init__`` guards."""
    cloned = object.__new__(type(instance))
    for field_name in instance.__dataclass_fields__:
        object.__setattr__(cloned, field_name, getattr(instance, field_name))
    for field_name, value in overrides.items():
        object.__setattr__(cloned, field_name, value)
    return cloned


class _Task027Lookalike:
    """Duck-typed object that must be rejected by exact-type upstream replay."""


class _Task028Lookalike:
    """Duck-typed object that must be rejected by exact-type upstream replay."""


def test_T029_UP_001_TASK027_EXACT_SUCCESS_TYPE() -> None:
    fixtures = build_production_fixtures()
    result = replay_task027_success(fixtures["task027"])
    assert isinstance(result, Task027ReplayEvidence)
    result = replay_task027_success(_Task027Lookalike())
    assert isinstance(result, Task029BlockerEntry)
    assert result.code == Task029BlockerCode.BL_T029_UPSTREAM_TASK027_TYPE_INVALID


def test_T029_UP_002_TASK028_EXACT_SUCCESS_TYPE() -> None:
    fixtures = build_production_fixtures()
    result = replay_task028_success(fixtures["task028"])
    assert isinstance(result, Task028ReplayEvidence)
    result = replay_task028_success(_Task028Lookalike())
    assert isinstance(result, Task029BlockerEntry)
    assert result.code == Task029BlockerCode.BL_T029_UPSTREAM_TASK028_TYPE_INVALID


def test_T029_UP_003_TASK027_SCHEMA_VERSION() -> None:
    fixtures = build_production_fixtures()
    bad_t027 = clone_with_field(fixtures["task027"], schema_version="task027.request.v0")
    blockers = T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS(
        task027_success_result=bad_t027,
        task028_success_result=fixtures["task028"],
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED
        and b.field_path == "task027_success_result.schema_version"
        for b in blockers
    )
    good_blockers = T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS(
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert fixtures["task027"].schema_version == TASK027_ACCEPTED_SCHEMA_VERSION
    assert not any(b.field_path == "task027_success_result.schema_version" for b in good_blockers)


def test_T029_UP_004_TASK028_SCHEMA_VERSION() -> None:
    fixtures = build_production_fixtures()
    bad_t028 = clone_with_field(fixtures["task028"], schema_version="task028.request.v0")
    blockers = T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS(
        task027_success_result=fixtures["task027"],
        task028_success_result=bad_t028,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED
        and b.field_path == "task028_success_result.schema_version"
        for b in blockers
    )
    good_blockers = T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS(
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert fixtures["task028"].schema_version == TASK028_ACCEPTED_SCHEMA_VERSION
    assert not any(b.field_path == "task028_success_result.schema_version" for b in good_blockers)


def test_T029_UP_005_TASK027_RESULT_HASH_REPLAY() -> None:
    fixtures = build_production_fixtures()
    task027 = fixtures["task027"]
    result = replay_task027_success(task027)
    assert isinstance(result, Task027ReplayEvidence)
    assert result.result_hash == task027.result_hash
    assert result.result_hash != TASK027_RESULT_HASH
    assert len(result.result_hash) == 64


def test_T029_UP_006_TASK027_RESULT_ID_REPLAY() -> None:
    fixtures = build_production_fixtures()
    task027 = fixtures["task027"]
    result = replay_task027_success(task027)
    assert isinstance(result, Task027ReplayEvidence)
    assert result.result_id == task027.result_id


def test_T029_UP_007_TASK028_RESULT_HASH_REPLAY() -> None:
    fixtures = build_production_fixtures()
    task028 = fixtures["task028"]
    result = replay_task028_success(task028)
    assert isinstance(result, Task028ReplayEvidence)
    assert result.result_hash == task028.result_hash
    assert result.result_hash != TASK028_RESULT_HASH
    assert len(result.result_hash) == 64


def test_T029_UP_008_TASK028_RESULT_ID_REPLAY() -> None:
    fixtures = build_production_fixtures()
    task028 = fixtures["task028"]
    result = replay_task028_success(task028)
    assert isinstance(result, Task028ReplayEvidence)
    assert result.result_id == task028.result_id


def test_T029_UP_009_SUCCESS_WARNINGS_BLOCKERS_EMPTY() -> None:
    fixtures = build_production_fixtures()
    blockers = T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS(
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
        task027_schema_supported=True,
        task028_schema_supported=True,
    )
    assert blockers == ()
    assert fixtures["task027"].warnings == ()
    assert fixtures["task027"].blockers == ()
    assert fixtures["task028"].warnings == ()
    assert fixtures["task028"].blockers == ()


def test_T029_UP_010_COMMON_IDENTITY_MATCH() -> None:
    fixtures = build_production_fixtures()
    request: Task029Request = fixtures["request"]
    blockers = T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES(
        request_profile_id=request.profile_id,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert blockers == ()
    assert fixtures["task027"].task025_hydraulic_authority_hash == (
        fixtures["task028"].task025_hydraulic_authority_hash
    )
    assert fixtures["task027"].property_snapshot_hash == fixtures["task028"].property_snapshot_hash


def test_T029_UP_011_COMMON_IDENTITY_MISMATCH() -> None:
    fixtures = build_production_fixtures()
    bad_t028 = task028_with_property_snapshot(fixtures, PROPERTY_SNAPSHOT_HASH_MISMATCH)
    blockers = T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES(
        request_profile_id=PROFILE_ID,
        task027_success_result=fixtures["task027"],
        task028_success_result=bad_t028,
    )
    assert any(
        b.code == Task029BlockerCode.BL_T029_UPSTREAM_IDENTITY_MISMATCH
        and b.field_path == "task028_success_result.property_snapshot_hash"
        for b in blockers
    )


def test_T029_UP_012_PROFILE_MATCH() -> None:
    fixtures = build_production_fixtures()
    request: Task029Request = fixtures["request"]
    blockers = T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES(
        request_profile_id=request.profile_id,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert blockers == ()
    assert request.profile_id == fixtures["task027"].profile_id == fixtures["task028"].profile_id

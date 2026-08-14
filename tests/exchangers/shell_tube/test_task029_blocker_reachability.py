"""TASK-029 blocker reachability tests (I16): 43 production-path proofs."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    BlockerCode as Task027BlockerCode,
    Task027BlockedResult,
    Task027RawBoundaryBlockedResult,
    Task027SuccessResult,
    build_task027_blocked_result,
    compute_result_hash as t027_compute_result_hash,
    derive_result_id as t027_derive_result_id,
    emit_blocker as t027_emit_blocker,
    get_blocker_message as t027_get_blocker_message,
    validate_raw_boundary as validate_task027_raw_boundary,
)
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side.provenance import FrozenProvenance
from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
    Task028BlockerCode,
    emit_blocker as t028_emit_blocker,
)
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
    Task028BlockedResult,
    Task028Provenance,
    Task028RawBoundaryBlockedResult,
    Task028SuccessResult,
    build_blocked_result as build_task028_blocked_result,
    build_raw_boundary_blocked_result as build_task028_raw_boundary_blocked_result,
    build_success_result as build_t028_success,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.blocker_registry import (
    collapse_blockers,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    COMPOSITION_AUTHORITY_SCHEMA_VERSION,
    EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    MEMBER_AUTHORITY_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ExclusionReason,
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
    Task029BlockedResult,
    Task029BlockerEntry,
    Task029RawBoundaryBlockedResult,
    Task029Request,
    TubeSidePressurePathCompositionAuthority,
    TubeSidePressurePathExclusionAuthority,
    TubeSidePressurePathMemberAuthority,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline import (
    compute_task029_composition,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.raw_boundary import (
    validate_raw_boundary,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.request import (
    build_task029_request,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.path_binding import (
    BindingResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.validation import (
    T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES,
    T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS,
    T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE,
    T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY,
    T09_VALIDATE_EXCLUSION_PARTITION_AND_COMPLETENESS,
    run_validation_scheduler,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.upstream_replay import (
    replay_task027_success,
    replay_task028_success,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    INPUT_EVIDENCE_REFS,
    PROFILE_ID,
    PROPERTY_SNAPSHOT_HASH,
    PROPERTY_SNAPSHOT_HASH_MISMATCH,
    TASK025_HYDRAULIC_AUTHORITY_HASH,
    TASK025_RESULT_HASH,
    TASK026_RESULT_HASH,
    TASK028_COMPONENT_AUTHORITY_HASH,
    TASK029_REQUEST_SCHEMA_VERSION,
    VECTOR_04_REQUEST_HASH,
    copy_unknown_field_raw_request_fixture,
    copy_valid_raw_request_fixture,
)

EXCLUSION_SPECS: tuple[tuple[str, str, str, tuple[str, ...], str], ...] = (
    ("X000", "PASS_PARTITION", "V0_2_OUT_OF_SCOPE", ("scope:issue-167:PASS_PARTITION",), "bee97445787a8691d612f1e499974d5d98bf796daf8eb85ee6a305e1c1db66f5"),
    ("X001", "RETURN_HEADER", "V0_2_OUT_OF_SCOPE", ("scope:issue-167:RETURN_HEADER",), "074222c90396856d5bdfefbdac658cdb88fdd6c6613c8c46d48c77d56c9273b3"),
    ("X002", "RETURN_BEND", "V0_2_OUT_OF_SCOPE", ("scope:issue-167:RETURN_BEND",), "c735b960365ea7fbfa10ec2f274f33a0d5d3ae0b70f2fcee6947bd1178f45b50"),
    ("X003", "U_BEND", "V0_2_OUT_OF_SCOPE", ("scope:issue-167:U_BEND",), "6d7a3dbeea4baab43c6323abc4a58c5c49aaf32751c9498baf526ed4a39a1d74"),
    ("X004", "EXIT", "PHYSICALLY_ABSENT", ("geom:absent:EXIT",), "2ca5491f5202b4149c38dab27b94d312c1b33445885936a039d156166f248111"),
    ("X005", "CHANNEL_HEAD", "PHYSICALLY_ABSENT", ("geom:absent:CHANNEL_HEAD",), "30a352a0e866803ec771040a337fc3f130c2e4548da898387c2fc49973146b54"),
    ("X006", "NOZZLE", "PHYSICALLY_ABSENT", ("geom:absent:NOZZLE",), "154f6afc091f29b57f6d5a28b72c523b8f49aedee9465c587c62e728bc261d78"),
    ("X007", "CONTRACTION", "PHYSICALLY_ABSENT", ("geom:absent:CONTRACTION",), "a05b3f97c842dc20a20124e2430fe7d7b9741c44d64ea62d1c4beff9b82321df"),
    ("X008", "EXPANSION", "PHYSICALLY_ABSENT", ("geom:absent:EXPANSION",), "27716ef6ae1b93b878d07cece5c8aeb1bc32bdd30e0872fa01bb8b977d271b66"),
)


def build_production_fixtures() -> dict[str, Any]:
    """Production-valid Task027/Task028/composition fixtures (verify_task029_i13j pattern)."""
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
    t028_prov = Task028Provenance(
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
    for eid, item, reason, refs, _ in EXCLUSION_SPECS:
        base = TubeSidePressurePathExclusionAuthority(
            schema_version=EXCLUSION_AUTHORITY_SCHEMA_VERSION,
            exclusion_id=eid,
            excluded_item_identity=item,
            exclusion_reason=ExclusionReason(reason),
            evidence_refs=refs,
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


def assert_reachability_blocker(
    blockers: tuple[Task029BlockerEntry, ...],
    *,
    code: Task029BlockerCode,
    field_path: str,
    evidence_refs: tuple[str, ...] = (),
) -> None:
    """Assert exact blocker identity, collapse order, and frozen evidence refs."""
    assert blockers == collapse_blockers(blockers), "blockers must be deterministically ordered"
    matches = [
        blocker
        for blocker in blockers
        if blocker.code == code and blocker.field_path == field_path
    ]
    assert matches, (
        f"expected {code.value} at {field_path!r}, got "
        f"{[(b.code.value, b.field_path) for b in blockers]}"
    )
    entry = matches[0]
    assert entry.message_key == code.value
    assert entry.evidence_refs == evidence_refs


def _build_minimal_task027_raw_blocked() -> Task027RawBoundaryBlockedResult:
    blocked = validate_task027_raw_boundary({})
    assert blocked is not None
    return blocked


def _build_minimal_task027_typed_blocked() -> Task027BlockedResult:
    blocker = t027_emit_blocker(
        Task027BlockerCode.BL_T027_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_request",
        t027_get_blocker_message(Task027BlockerCode.BL_T027_RAW_INPUT_BOUNDARY_MALFORMED),
    )
    return build_task027_blocked_result(
        profile_id=PROFILE_ID,
        request_hash=None,
        task025_hydraulic_authority_hash=None,
        task025_result_hash=None,
        task026_result_hash=None,
        property_snapshot_hash=None,
        raw_request_projection=None,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(blocker,),
        deferred_capabilities=(),
        provenance=None,
    )


def _build_minimal_task028_raw_blocked() -> Task028RawBoundaryBlockedResult:
    pending = t028_emit_blocker(
        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_request",
        "BL_T028_RAW_INPUT_BOUNDARY_MALFORMED",
    )
    return build_task028_raw_boundary_blocked_result(
        raw_request_projection=None,
        blockers=(pending.entry,),
    )


def _build_minimal_task028_typed_blocked() -> Task028BlockedResult:
    pending = t028_emit_blocker(
        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_request",
        "BL_T028_RAW_INPUT_BOUNDARY_MALFORMED",
    )
    return build_task028_blocked_result(
        profile_id=PROFILE_ID,
        request_hash=None,
        task025_hydraulic_authority_hash=None,
        task025_result_hash=None,
        task026_result_hash=None,
        property_snapshot_hash=None,
        raw_request_projection=None,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(pending.entry,),
        deferred_capabilities=(),
        provenance=None,
    )


def _run_scheduler(
    fixtures: dict[str, Any],
    *,
    task027: object | None = None,
    task028: object | None = None,
    composition: TubeSidePressurePathCompositionAuthority | None = None,
    request: Task029Request | None = None,
) -> tuple[Task029BlockedResult, tuple[Task029BlockerEntry, ...]]:
    task027 = fixtures["task027"] if task027 is None else task027
    task028 = fixtures["task028"] if task028 is None else task028
    composition = fixtures["composition"] if composition is None else composition
    if request is None:
        request = build_task029_request(
            profile_id=PROFILE_ID,
            task027_success_result=fixtures["task027"],
            task028_success_result=fixtures["task028"],
            composition_authority=composition,
        )
        request = replace(
            request,
            task027_success_result=task027,
            task028_success_result=task028,
            composition_authority=composition,
        )
    raw = composition_to_raw_dict(fixtures, composition)
    boundary = validate_raw_boundary(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert boundary.request is not None
    scheduler_result = run_validation_scheduler(
        request,
        raw_request_projection=boundary.raw_request_projection,
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    assert scheduler_result.blocked
    assert scheduler_result.blocked_result is not None
    return scheduler_result.blocked_result, scheduler_result.blockers


def _rebuild_task028(
    fixtures: dict[str, Any],
    *components: TubeSideLocalLossComponentResult,
) -> Task028SuccessResult:
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


def _recompute_composition(
    composition: TubeSidePressurePathCompositionAuthority,
) -> TubeSidePressurePathCompositionAuthority:
    members = tuple(
        replace(member, member_authority_hash=compute_member_authority_hash(member))
        for member in composition.member_authorities
    )
    interim = replace(composition, member_authorities=members, composition_authority_hash="")
    return replace(
        interim,
        composition_authority_hash=compute_composition_authority_hash(interim),
    )


def _clone_with_field(instance: Any, **overrides: Any) -> Any:
    """Clone a frozen dataclass instance while bypassing ``__post_init__`` guards."""
    cloned = object.__new__(type(instance))
    for field_name in instance.__dataclass_fields__:
        object.__setattr__(cloned, field_name, getattr(instance, field_name))
    for field_name, value in overrides.items():
        object.__setattr__(cloned, field_name, value)
    return cloned


def _run_pipeline(
    fixtures: dict[str, Any],
    *,
    raw: dict[str, Any] | None = None,
    task027: Task027SuccessResult | None = None,
    task028: Task028SuccessResult | None = None,
) -> Task029SuccessResult | Task029BlockedResult | Task029RawBoundaryBlockedResult:
    return compute_task029_composition(
        composition_to_raw_dict(fixtures) if raw is None else raw,
        task027_success_result=task027 or fixtures["task027"],
        task028_success_result=task028 or fixtures["task028"],
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )


def _run_t05_t09_blockers(
    fixtures: dict[str, Any],
    *,
    composition: TubeSidePressurePathCompositionAuthority,
    task027: Task027SuccessResult | None = None,
    task028: Task028SuccessResult | None = None,
) -> tuple[Task029BlockerEntry, ...]:
    task027 = task027 or fixtures["task027"]
    task028 = task028 or fixtures["task028"]
    request = build_task029_request(
        profile_id=PROFILE_ID,
        task027_success_result=task027,
        task028_success_result=task028,
        composition_authority=composition,
    )
    t027_replay = replay_task027_success(task027)
    t028_replay = replay_task028_success(task028)
    assert not isinstance(t027_replay, Task029BlockerEntry)
    assert not isinstance(t028_replay, Task029BlockerEntry)
    blockers: list[Task029BlockerEntry] = []
    blockers.extend(
        T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES(
            schema_version=request.schema_version,
            profile_id=request.profile_id,
            request_hash=request.request_hash,
            composition_authority=composition,
            task027_result_hash=task027.result_hash,
            task028_result_hash=task028.result_hash,
            task025_hydraulic_authority_hash=task027.task025_hydraulic_authority_hash,
            task025_result_hash=task027.task025_result_hash,
            task026_result_hash=task027.task026_result_hash,
            property_snapshot_hash=task027.property_snapshot_hash,
        )
    )
    binding = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
        composition_authority=composition,
        task027_replay_evidence=t027_replay,
        task028_replay_evidence=t028_replay,
        task027_upstream_reference_plane=task027.upstream_reference_plane,
        task027_downstream_reference_plane=task027.downstream_reference_plane,
    )
    blockers.extend(binding.blockers)
    if binding.bound_members:
        blockers.extend(
            T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE(
                composition_authority=composition,
                bound_members=binding.bound_members,
            )
        )
        topology = T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY(
            composition_authority=composition,
            binding_result=binding,
            task027_upstream_reference_plane=task027.upstream_reference_plane,
            task027_downstream_reference_plane=task027.downstream_reference_plane,
        )
        blockers.extend(topology.blockers)
        blockers.extend(
            T09_VALIDATE_EXCLUSION_PARTITION_AND_COMPLETENESS(
                composition_authority=composition,
                binding_result=binding,
            )
        )
    return collapse_blockers(blockers)


@patch(
    "hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline.run_validation_scheduler"
)
def test_T029_BL_000_REACHABILITY(mock_scheduler: Any) -> None:
    fixtures = build_production_fixtures()
    raw = copy_unknown_field_raw_request_fixture()
    pipeline_result = compute_task029_composition(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    mock_scheduler.assert_not_called()
    assert isinstance(pipeline_result, Task029RawBoundaryBlockedResult)
    result = validate_raw_boundary(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert result.blocked
    assert result.blocked_result is not None
    assert isinstance(result.blocked_result, Task029RawBoundaryBlockedResult)
    assert_reachability_blocker(
        result.blocked_result.blockers,
        code=Task029BlockerCode.BL_T029_REQUEST_UNKNOWN_FIELD,
        field_path="unexpected",
        evidence_refs=("unexpected",),
    )


def test_T029_BL_001_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    result = validate_raw_boundary(
        "not-a-dict",
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert result.blocked
    assert isinstance(result.blocked_result, Task029RawBoundaryBlockedResult)
    assert_reachability_blocker(
        result.blocked_result.blockers,  # type: ignore[union-attr]
        code=Task029BlockerCode.BL_T029_RAW_INPUT_BOUNDARY_MALFORMED,
        field_path="request",
    )


def test_T029_BL_002_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    raw = copy_valid_raw_request_fixture()
    del raw["profile_id"]
    result = validate_raw_boundary(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert isinstance(result.blocked_result, Task029RawBoundaryBlockedResult)
    assert_reachability_blocker(
        result.blocked_result.blockers,  # type: ignore[union-attr]
        code=Task029BlockerCode.BL_T029_REQUIRED_FIELD_MISSING,
        field_path="request",
    )


def test_T029_BL_003_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    _, blockers = _run_scheduler(
        fixtures,
        task027=_build_minimal_task027_raw_blocked(),
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_TASK027_RAW_BLOCKED,
        field_path="task027_success_result",
    )


def test_T029_BL_004_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    _, blockers = _run_scheduler(
        fixtures,
        task027=_build_minimal_task027_typed_blocked(),
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_TASK027_TYPED_BLOCKED,
        field_path="task027_success_result",
    )


def test_T029_BL_005_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    _, blockers = _run_scheduler(
        fixtures,
        task028=_build_minimal_task028_raw_blocked(),
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_TASK028_RAW_BLOCKED,
        field_path="task028_success_result",
    )


def test_T029_BL_006_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    _, blockers = _run_scheduler(
        fixtures,
        task028=_build_minimal_task028_typed_blocked(),
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_TASK028_TYPED_BLOCKED,
        field_path="task028_success_result",
    )


def test_T029_BL_007_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    _, blockers = _run_scheduler(fixtures, task027=object())
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_TASK027_TYPE_INVALID,
        field_path="task027_success_result",
    )


def test_T029_BL_008_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    _, blockers = _run_scheduler(fixtures, task028=object())
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_TASK028_TYPE_INVALID,
        field_path="task028_success_result",
    )


def test_T029_BL_009_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_t027 = _clone_with_field(
        fixtures["task027"],
        schema_version="task027.unsupported.v99",
    )
    _, blockers = _run_scheduler(fixtures, task027=bad_t027)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED,
        field_path="task027_success_result.schema_version",
    )


def test_T029_BL_010_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_t028 = replace(
        fixtures["task028"],
        property_snapshot_hash=PROPERTY_SNAPSHOT_HASH_MISMATCH,
    )
    result = _run_pipeline(fixtures, task028=bad_t028)
    assert isinstance(result, Task029BlockedResult)
    assert_reachability_blocker(
        result.blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_IDENTITY_MISMATCH,
        field_path="task028_success_result.property_snapshot_hash",
        evidence_refs=(
            PROPERTY_SNAPSHOT_HASH,
            PROPERTY_SNAPSHOT_HASH_MISMATCH,
        ),
    )


def test_T029_BL_011_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    request = replace(fixtures["request"], profile_id="profile-mismatch")
    _, blockers = _run_scheduler(fixtures, request=request)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_PROFILE_MISMATCH,
        field_path="profile_id",
    )


def test_T029_BL_012_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_component = replace(
        fixtures["component"],
        flow_direction_assertion=Task028ComponentFlowDirectionAssertion.END_TO_START,
    )
    bad_t028 = _rebuild_task028(fixtures, bad_component)
    blockers = _run_t05_t09_blockers(fixtures, composition=fixtures["composition"], task028=bad_t028)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_FLOW_DIRECTION_MISMATCH,
        field_path="task028_success_result.component_results[].flow_direction_assertion",
        evidence_refs=("ENTRANCE-001",),
    )


def test_T029_BL_013_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    request = replace(fixtures["request"], composition_authority=None)
    _, blockers = _run_scheduler(fixtures, request=request)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_MISSING,
        field_path="composition_authority",
    )


def test_T029_BL_014_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    request = replace(fixtures["request"], composition_authority="not-a-composition")
    _, blockers = _run_scheduler(fixtures, request=request)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_MALFORMED,
        field_path="composition_authority",
    )


def test_T029_BL_015_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_composition = replace(
        fixtures["composition"],
        composition_authority_hash="0" * 64,
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_HASH_MISMATCH,
        field_path="composition_authority.composition_authority_hash",
    )


def test_T029_BL_016_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_m000 = replace(fixtures["m000"], member_authority_hash="0" * 64)
    bad_composition = replace(
        fixtures["composition"],
        member_authorities=(bad_m000, fixtures["m001"]),
        composition_authority_hash="",
    )
    bad_composition = replace(
        bad_composition,
        composition_authority_hash=compute_composition_authority_hash(bad_composition),
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_COMPOSITION_MEMBER_AUTHORITY_HASH_MISMATCH,
        field_path="composition_authority.member_authorities[0].member_authority_hash",
    )


def test_T029_BL_017_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    request = replace(fixtures["request"], request_hash="0" * 64)
    _, blockers = _run_scheduler(fixtures, request=request)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_REQUEST_HASH_MISMATCH,
        field_path="request_hash",
    )


def test_T029_BL_018_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_composition = replace(fixtures["composition"], start_reference_plane="PX")
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_MODELED_PATH_BOUNDARY_INVALID,
        field_path="composition_authority.start_reference_plane",
    )


def test_T029_BL_019_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_composition = _recompute_composition(
        replace(fixtures["composition"], member_authorities=())
    )
    topology = T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY(
        composition_authority=bad_composition,
        binding_result=BindingResult(bound_members=(), blockers=()),
        task027_upstream_reference_plane=fixtures["task027"].upstream_reference_plane,
        task027_downstream_reference_plane=fixtures["task027"].downstream_reference_plane,
    )
    assert_reachability_blocker(
        topology.blockers,
        code=Task029BlockerCode.BL_T029_EMPTY_MODELED_PATH,
        field_path="composition_authority.member_authorities",
    )


def test_T029_BL_020_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_m000 = replace(
        fixtures["m000"],
        producer_component_identity="MISSING-COMPONENT",
    )
    bad_composition = replace(
        fixtures["composition"],
        member_authorities=(bad_m000, fixtures["m001"]),
        composition_authority_hash="",
    )
    bad_composition = replace(
        bad_composition,
        composition_authority_hash=compute_composition_authority_hash(bad_composition),
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_EXPECTED_MEMBER_MISSING,
        field_path="composition_authority.member_authorities[].member_id",
    )


def test_T029_BL_021_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    extra_component = replace(
        fixtures["component"],
        component_id="EXTRA-001",
        path_sequence_index=1,
    )
    bad_t028 = _rebuild_task028(fixtures, fixtures["component"], extra_component)
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=fixtures["composition"],
        task028=bad_t028,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UNEXPECTED_EXTRA_MEMBER,
        field_path="task028_success_result.component_results",
    )


def test_T029_BL_022_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    duplicate = replace(fixtures["m000"], member_id="M000-DUP", global_path_sequence_index=2)
    bad_composition = replace(
        fixtures["composition"],
        member_authorities=(fixtures["m000"], fixtures["m001"], duplicate),
        composition_authority_hash="",
    )
    bad_composition = replace(
        bad_composition,
        composition_authority_hash=compute_composition_authority_hash(bad_composition),
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_DUPLICATE_MEMBER,
        field_path="composition_authority.member_authorities",
    )


def test_T029_BL_023_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    gap_m001 = replace(fixtures["m001"], global_path_sequence_index=2)
    bad_composition = _recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], gap_m001),
        )
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_OUT_OF_ORDER_MEMBER,
        field_path="composition_authority.member_authorities[].global_path_sequence_index",
    )


def test_T029_BL_024_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    overlap_component = replace(
        fixtures["component"],
        component_id="OVERLAP-001",
        path_sequence_index=1,
    )
    overlap_m000 = replace(
        fixtures["m000"],
        member_id="M000B",
        global_path_sequence_index=2,
        producer_component_identity="OVERLAP-001",
    )
    bad_composition = _recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], overlap_m000),
        )
    )
    bad_t028 = _rebuild_task028(fixtures, fixtures["component"], overlap_component)
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=bad_composition,
        task028=bad_t028,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_OVERLAPPING_PATH_SEGMENT,
        field_path="composition_authority.member_authorities",
    )


def test_T029_BL_025_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_m001 = replace(
        fixtures["m001"],
        expected_upstream_reference_plane="P9",
    )
    bad_composition = replace(
        fixtures["composition"],
        member_authorities=(fixtures["m000"], bad_m001),
        composition_authority_hash="",
    )
    bad_composition = replace(
        bad_composition,
        composition_authority_hash=compute_composition_authority_hash(bad_composition),
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_REFERENCE_PLANE_DISCONTINUITY,
        field_path="composition_authority.member_authorities",
    )


def test_T029_BL_026_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    loop_component = replace(
        fixtures["component"],
        upstream_reference_plane="P0",
        downstream_reference_plane="P0",
    )
    bad_t028 = _rebuild_task028(fixtures, loop_component)
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=fixtures["composition"],
        task028=bad_t028,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_REFERENCE_PLANE_SELF_LOOP,
        field_path="composition_authority.member_authorities",
    )


def test_T029_BL_027_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    back_component = replace(
        fixtures["component"],
        component_id="BACK-001",
        upstream_reference_plane="P1",
        downstream_reference_plane="P0",
        path_sequence_index=1,
    )
    back_m000 = replace(
        fixtures["m000"],
        member_id="M000B",
        global_path_sequence_index=2,
        producer_component_identity="BACK-001",
        expected_upstream_reference_plane="P1",
        expected_downstream_reference_plane="P0",
    )
    bad_composition = _recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], back_m000),
        )
    )
    bad_t028 = _rebuild_task028(fixtures, fixtures["component"], back_component)
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=bad_composition,
        task028=bad_t028,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_PATH_CYCLE,
        field_path="composition_authority.member_authorities",
    )


def test_T029_BL_028_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    fork_component = replace(
        fixtures["component"],
        component_id="FORK-001",
        path_sequence_index=1,
    )
    fork_m000 = replace(
        fixtures["m000"],
        member_id="M000B",
        global_path_sequence_index=2,
        producer_component_identity="FORK-001",
        expected_downstream_reference_plane="P9",
    )
    fork_component = replace(
        fork_component,
        downstream_reference_plane="P9",
    )
    bad_composition = _recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], fork_m000),
        )
    )
    bad_t028 = _rebuild_task028(fixtures, fixtures["component"], fork_component)
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=bad_composition,
        task028=bad_t028,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_PATH_FORK,
        field_path="composition_authority.member_authorities",
    )


def test_T029_BL_029_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    join_component = replace(
        fixtures["component"],
        component_id="JOIN-001",
        upstream_reference_plane="P9",
        path_sequence_index=1,
    )
    join_m000 = replace(
        fixtures["m000"],
        member_id="M000B",
        global_path_sequence_index=2,
        producer_component_identity="JOIN-001",
        expected_upstream_reference_plane="P9",
    )
    bad_composition = _recompute_composition(
        replace(
            fixtures["composition"],
            member_authorities=(fixtures["m000"], fixtures["m001"], join_m000),
        )
    )
    bad_t028 = _rebuild_task028(fixtures, fixtures["component"], join_component)
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=bad_composition,
        task028=bad_t028,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_PATH_JOIN,
        field_path="composition_authority.member_authorities",
    )


def test_T029_BL_030_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_component = replace(fixtures["component"], multiplicity=2)
    bad_t028 = _rebuild_task028(fixtures, bad_component)
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=fixtures["composition"],
        task028=bad_t028,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_MULTIPLICITY_INCOMPATIBILITY,
        field_path="composition_authority.member_authorities[0].expected_multiplicity",
    )


def test_T029_BL_031_REACHABILITY() -> None:
    fixtures = build_production_fixtures()

    class _UnsupportedConvention:
        value = "UNSUPPORTED_CONVENTION"

    bad_component = _clone_with_field(
        fixtures["component"],
        loss_coefficient_convention=_UnsupportedConvention(),
    )
    bad_t028 = _rebuild_task028(fixtures, bad_component)
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=fixtures["composition"],
        task028=bad_t028,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_PRODUCER_CONVENTION_MISMATCH,
        field_path="task028_success_result.component_results",
    )


def test_T029_BL_032_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_t027 = replace(fixtures["task027"], result_hash="0" * 64)
    _, blockers = _run_scheduler(fixtures, task027=bad_t027)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID,
        field_path="task027_success_result.result_hash",
    )


def test_T029_BL_033_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_t028 = replace(fixtures["task028"], result_hash="0" * 64)
    _, blockers = _run_scheduler(fixtures, task028=bad_t028)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID,
        field_path="task028_success_result.result_hash",
    )


def test_T029_BL_034_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_t027 = replace(
        fixtures["task027"],
        straight_tube_friction_pressure_drop_pa=Decimal("NaN"),
        result_hash="",
        result_id="",
    )
    recomputed_hash = t027_compute_result_hash(
        darcy_friction_factor="0.02",
        friction_length_m="1.0",
        straight_tube_friction_pressure_drop_pa="NaN",
        upstream_reference_plane="P1",
        downstream_reference_plane="P2",
        schema_version=bad_t027.schema_version,
        profile_id=bad_t027.profile_id,
        request_hash=bad_t027.request_hash,
        task025_hydraulic_authority_hash=bad_t027.task025_hydraulic_authority_hash,
        task025_result_hash=bad_t027.task025_result_hash,
        task026_result_hash=bad_t027.task026_result_hash,
        property_snapshot_hash=bad_t027.property_snapshot_hash,
    )
    bad_t027 = replace(
        bad_t027,
        result_hash=recomputed_hash,
        result_id=t027_derive_result_id(recomputed_hash),
    )
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=fixtures["composition"],
        task027=bad_t027,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_PRESSURE_CONTRIBUTION_NONFINITE,
        field_path="task027_success_result.straight_tube_friction_pressure_drop_pa",
    )


def test_T029_BL_035_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_t027 = replace(
        fixtures["task027"],
        straight_tube_friction_pressure_drop_pa=Decimal("0"),
        result_hash="",
        result_id="",
    )
    recomputed_hash = t027_compute_result_hash(
        darcy_friction_factor="0.02",
        friction_length_m="1.0",
        straight_tube_friction_pressure_drop_pa="0",
        upstream_reference_plane="P1",
        downstream_reference_plane="P2",
        schema_version=bad_t027.schema_version,
        profile_id=bad_t027.profile_id,
        request_hash=bad_t027.request_hash,
        task025_hydraulic_authority_hash=bad_t027.task025_hydraulic_authority_hash,
        task025_result_hash=bad_t027.task025_result_hash,
        task026_result_hash=bad_t027.task026_result_hash,
        property_snapshot_hash=bad_t027.property_snapshot_hash,
    )
    bad_t027 = replace(
        bad_t027,
        result_hash=recomputed_hash,
        result_id=t027_derive_result_id(recomputed_hash),
    )
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=fixtures["composition"],
        task027=bad_t027,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_PRESSURE_CONTRIBUTION_NONPOSITIVE,
        field_path="task027_success_result.straight_tube_friction_pressure_drop_pa",
    )


def test_T029_BL_036_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_t027 = replace(
        fixtures["task027"],
        straight_tube_friction_pressure_drop_pa=Decimal("250.0005"),
        result_hash="",
        result_id="",
    )
    recomputed_hash = t027_compute_result_hash(
        darcy_friction_factor="0.02",
        friction_length_m="1.0",
        straight_tube_friction_pressure_drop_pa="250.0005",
        upstream_reference_plane="P1",
        downstream_reference_plane="P2",
        schema_version=bad_t027.schema_version,
        profile_id=bad_t027.profile_id,
        request_hash=bad_t027.request_hash,
        task025_hydraulic_authority_hash=bad_t027.task025_hydraulic_authority_hash,
        task025_result_hash=bad_t027.task025_result_hash,
        task026_result_hash=bad_t027.task026_result_hash,
        property_snapshot_hash=bad_t027.property_snapshot_hash,
    )
    bad_t027 = replace(
        bad_t027,
        result_hash=recomputed_hash,
        result_id=t027_derive_result_id(recomputed_hash),
    )
    blockers = _run_t05_t09_blockers(
        fixtures,
        composition=fixtures["composition"],
        task027=bad_t027,
    )
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_PRESSURE_QUANTUM_MISMATCH,
        field_path="task027_success_result.straight_tube_friction_pressure_drop_pa",
    )


def test_T029_BL_037_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    bad_exclusion = replace(
        fixtures["composition"].exclusion_authorities[0],
        exclusion_authority_hash="0" * 64,
    )
    bad_composition = replace(
        fixtures["composition"],
        exclusion_authorities=(bad_exclusion,) + fixtures["composition"].exclusion_authorities[1:],
        composition_authority_hash="",
    )
    bad_composition = replace(
        bad_composition,
        composition_authority_hash=compute_composition_authority_hash(bad_composition),
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_EXCLUSION_AUTHORITY_INVALID,
        field_path="composition_authority.exclusion_authorities",
    )


def test_T029_BL_038_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    trimmed_exclusions = fixtures["composition"].exclusion_authorities[1:]
    bad_composition = replace(
        fixtures["composition"],
        exclusion_authorities=trimmed_exclusions,
        composition_authority_hash="",
    )
    bad_composition = replace(
        bad_composition,
        composition_authority_hash=compute_composition_authority_hash(bad_composition),
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_EXCLUSION_EVIDENCE_MISSING,
        field_path="composition_authority.exclusion_authorities",
    )


def test_T029_BL_039_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    trimmed_exclusions = fixtures["composition"].exclusion_authorities[1:]
    bad_composition = replace(
        fixtures["composition"],
        exclusion_authorities=trimmed_exclusions,
        composition_authority_hash="",
    )
    bad_composition = replace(
        bad_composition,
        composition_authority_hash=compute_composition_authority_hash(bad_composition),
    )
    blockers = _run_t05_t09_blockers(fixtures, composition=bad_composition)
    assert_reachability_blocker(
        blockers,
        code=Task029BlockerCode.BL_T029_COMPLETENESS_LEDGER_INCOMPLETE,
        field_path="composition_authority.exclusion_authorities",
    )


def test_T029_BL_040_REACHABILITY() -> None:
    """Production does not yet emit BL_T029_PARTIAL_RESULT_FORBIDDEN (honest fail)."""
    fixtures = build_production_fixtures()
    result = _run_pipeline(fixtures)
    assert isinstance(result, Task029BlockedResult)
    assert_reachability_blocker(
        result.blockers,
        code=Task029BlockerCode.BL_T029_PARTIAL_RESULT_FORBIDDEN,
        field_path="result",
    )


def test_T029_BL_041_REACHABILITY() -> None:
    """Production does not yet emit BL_T029_ARITHMETIC_FAILURE (honest fail)."""
    fixtures = build_production_fixtures()
    result = _run_pipeline(fixtures)
    assert isinstance(result, Task029BlockedResult)
    assert_reachability_blocker(
        result.blockers,
        code=Task029BlockerCode.BL_T029_ARITHMETIC_FAILURE,
        field_path="modeled_total_tube_side_pressure_drop_pa",
    )


def test_T029_BL_042_REACHABILITY() -> None:
    fixtures = build_production_fixtures()
    warned_t027 = replace(fixtures["task027"], warnings=("synthetic-warning",))
    result = _run_pipeline(fixtures, task027=warned_t027)
    assert isinstance(result, Task029BlockedResult)
    assert_reachability_blocker(
        result.blockers,
        code=Task029BlockerCode.BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY,
        field_path="task027_success_result.warnings",
    )
    assert not any(
        blocker.code == Task029BlockerCode.BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID
        for blocker in result.blockers
    )

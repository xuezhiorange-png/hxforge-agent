"""Focused TASK162 implementation contract tests."""

from __future__ import annotations

from dataclasses import fields, replace
from decimal import Decimal, getcontext, localcontext

import pytest

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.service import (
    validate_request as validate_task161,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    TASK162_DECIMAL_CONTEXT,
    Task162AmbientHeatLossAssumption,
    Task162AxialHeatTransferAssumption,
    Task162BindingStatus,
    Task162BypassAssumption,
    Task162CaseAuthority,
    Task162CompatibilityDimension,
    Task162CompatibilityEvidence,
    Task162CompatibilityStatus,
    Task162CrossProducerBindingAuthority,
    Task162FailureCode,
    Task162FlowOrientation,
    Task162HeatTransferCoefficientAssumption,
    Task162InternalSourceSinkAssumption,
    Task162LeakageAssumption,
    Task162RawProjectionKind,
    Task162ShellSideMixingModel,
    Task162ShellType,
    Task162TubeSideMixing,
    Task162ValidationStatus,
    Task162WallPropertyAssumption,
    interval_divide,
    project_raw_request,
    raw_request_projection_hash,
    table7_relation,
    validate_request,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.service import (
    validate_request as validate_task160,
)

from .overall_heat_transfer_coefficient_ua.task038_frozen_vectors import (
    PROVENANCE_HASH_A,
    REQUEST_HASH_A,
    provenance_fixture,
    result_fixture,
)
from .thermal_stream_state.test_ingress_models import make_r607_raw

TASK161_SOURCE_ID = "TASK161-SOURCE-DEFINITION-R8-ISSUE-225"
TASK162_SOURCE_ID = "TASK162-SOURCE-DEFINITION-R1-ISSUE-229"


def _task160() -> object:
    result = validate_task160(make_r607_raw()).valid
    assert result is not None
    return result


def _task161(task160: object | None = None) -> object:
    result = validate_task161(
        {
            "schema_version": "task161.schema.v1",
            "task161_version": "task161.v1",
            "source_definition_id": TASK161_SOURCE_ID,
            "task160_result": task160 or _task160(),
            "request_metadata": [],
        }
    ).valid
    assert result is not None
    return result


def _task038() -> Task038SuccessResult:
    return result_fixture(
        REQUEST_HASH_A,
        provenance_fixture(REQUEST_HASH_A, PROVENANCE_HASH_A),
    )


def _case(baffle_count: object = 1) -> Task162CaseAuthority:
    return Task162CaseAuthority(
        case_authority_id="case-001",
        shell_type=Task162ShellType.TEMA_E,
        overall_flow_orientation=Task162FlowOrientation.COUNTER_FLOW,
        baffle_count=baffle_count,  # type: ignore[arg-type]
        physical_sthe_tube_side_mixing=Task162TubeSideMixing.UNMIXED,
        physical_sthe_shell_side_mixing_model=Task162ShellSideMixingModel.MODEL_2,
        steady_state=True,
        ambient_heat_loss_assumption=Task162AmbientHeatLossAssumption.NEGLIGIBLE_AMBIENT_HEAT_LOSS,
        internal_source_sink_assumption=Task162InternalSourceSinkAssumption.NO_INTERNAL_THERMAL_SOURCE_SINK,
        constant_wall_material_property=Task162WallPropertyAssumption.CONSTANT_WALL_MATERIAL_PROPERTIES,
        constant_heat_transfer_coefficient=Task162HeatTransferCoefficientAssumption.CONSTANT_HEAT_TRANSFER_COEFFICIENT,
        axial_heat_transfer_assumption=Task162AxialHeatTransferAssumption.NEGLIGIBLE_AXIAL_HEAT_TRANSFER,
        leakage_model_assumption=Task162LeakageAssumption.SOURCE_MODEL_ZERO_LEAKAGE_ASSUMPTION_ADOPTED,
        bypass_model_assumption=Task162BypassAssumption.SOURCE_MODEL_ZERO_BYPASS_ASSUMPTION_ADOPTED,
        evidence_refs=("case-evidence-001",),
    )


def _binding(
    task160: object | None = None, task161: object | None = None
) -> Task162CrossProducerBindingAuthority:
    task160 = task160 or _task160()
    task161 = task161 or _task161(task160)
    task038 = _task038()
    dimensions = tuple(
        Task162CompatibilityEvidence(
            dimension=dimension,
            status=Task162CompatibilityStatus.PROVEN,
            evidence_refs=(f"{dimension.value}-evidence",),
        )
        for dimension in Task162CompatibilityDimension
    )
    return Task162CrossProducerBindingAuthority(
        binding_authority_id="binding-001",
        task160_result_hash=task160.result_hash,
        task160_result_id=str(task160.result_id),
        task161_result_hash=task161.result_hash,
        task161_result_id=str(task161.result_id),
        task038_result_hash=task038.result_hash,
        task038_result_id=task038.result_id,
        physical_exchanger_case_id="case-001",
        binding_status=Task162BindingStatus.MATCHED,
        evidence_refs=("binding-evidence-001",),
        compatibility_evidence=dimensions,
    )


def _raw(case: object | None = None, binding: object | None = None) -> dict[str, object]:
    task160 = _task160()
    task161 = _task161(task160)
    return {
        "schema_version": "task162.schema.v1",
        "task162_version": "task162.v1",
        "source_definition_id": TASK162_SOURCE_ID,
        "task160_result": task160,
        "task161_result": task161,
        "task038_result": _task038(),
        "cross_producer_binding_authority": binding or _binding(task160, task161),
        "case_authority": case or _case(),
        "request_metadata": [],
    }


def test_success_contract_and_forbidden_lmtd_surface() -> None:
    outcome = validate_request(_raw())
    assert outcome.status is Task162ValidationStatus.VALID
    assert outcome.valid is not None
    assert outcome.valid.blockers == ()
    assert outcome.valid.applicability.status == "APPLICABLE"
    assert outcome.valid.completeness.status == "COMPLETE"
    assert outcome.valid.energy_balance_evidence.policy_id == "TASK162_DIRECTED_INTERVAL_CLOSURE_V1"
    names = {field.name.lower() for field in fields(outcome.valid)}
    assert not {"lmtd", "lmt d", "f_factor", "correction_factor"} & names
    assert all(token not in names for token in ("effectiveness_value", "ua_value", "heat_duty"))


@pytest.mark.parametrize("baffle_count", [1, 2, 3, 4, 5])
def test_all_table7_selectors_produce_complete_results(baffle_count: int) -> None:
    result = validate_request(_raw(case=_case(baffle_count))).valid
    assert result is not None
    assert result.selected_baffle_relation == f"P_{baffle_count}"
    assert result.p_source.is_finite()
    assert result.ntu >= 0


def test_all_table7_ast_golden_values_are_stable() -> None:
    ntu = Decimal("0.8876560332864")
    ratio = Decimal("0.4186602870813397129186602870813397")
    expected = (
        "0.5330653588535907557719284543446985512845746810578657378055710003956585762596114559208687782046976625523360772710553830180689071767658763487926134764823863348751",
        "0.5354843866457570177730111695194206931001698974022228125083607025979497615031687581265862315812955083147305828057694731760520946494435119230612944313417776165624",
        "0.5363169959789442661658928806981788781069697676257211902302567250542397446241463737276162202048617748610989422313499807777097544461882198455899733029842004251645",
        "0.4499518142163941483629751568857246307643602949329174745069892123787999634534891100736805946762910820822813574906170732430985604640384949916226597255237715340655",
        "0.5082168271065734140380962055428510365690539317635823138499912627431716681569993817102496422371442469814530045075843094167321376867436653709782060062132484141268",
    )
    actual = tuple(str(table7_relation(ntu, ratio, count)) for count in range(1, 6))
    assert actual == expected


def test_task160_task161_task038_identity_replay_and_tamper_block() -> None:
    valid = validate_request(_raw())
    assert valid.status is Task162ValidationStatus.VALID
    original = _raw()
    tampered160 = replace(original["task160_result"], result_hash="0" * 64)
    assert (
        validate_request({**original, "task160_result": tampered160}).status
        is Task162ValidationStatus.TYPED_BLOCKED
    )
    tampered161 = replace(original["task161_result"], result_hash="0" * 64)
    assert (
        validate_request({**original, "task161_result": tampered161}).status
        is Task162ValidationStatus.TYPED_BLOCKED
    )
    tampered038 = replace(original["task038_result"], result_hash="0" * 64)
    assert (
        validate_request({**original, "task038_result": tampered038}).status
        is Task162ValidationStatus.TYPED_BLOCKED
    )


def test_task161_to_task160_and_binding_identity_mismatch_blocks() -> None:
    original = _raw()
    other161 = _task161(_task160())
    mismatched_binding = replace(
        original["cross_producer_binding_authority"], task161_result_hash="f" * 64
    )
    first = validate_request({**original, "cross_producer_binding_authority": mismatched_binding})
    assert first.status is Task162ValidationStatus.TYPED_BLOCKED
    assert first.typed_blocked is not None
    assert (
        first.typed_blocked.blockers[0].code
        == Task162FailureCode.CROSS_PRODUCER_CASE_MISMATCH.value
    )
    mismatched_task161 = replace(
        other161, task160_evidence=replace(other161.task160_evidence, result_hash="e" * 64)
    )
    second = validate_request({**original, "task161_result": mismatched_task161})
    assert second.status is Task162ValidationStatus.TYPED_BLOCKED


def test_binding_case_identity_must_match_case_authority() -> None:
    original = _raw()
    mismatched_binding = replace(
        original["cross_producer_binding_authority"],
        physical_exchanger_case_id="different-case",
    )
    outcome = validate_request({**original, "cross_producer_binding_authority": mismatched_binding})
    assert outcome.status is Task162ValidationStatus.TYPED_BLOCKED
    assert outcome.typed_blocked is not None
    assert (
        outcome.typed_blocked.blockers[0].code
        == Task162FailureCode.CROSS_PRODUCER_CASE_MISMATCH.value
    )


@pytest.mark.parametrize("value", [0, 6, True, Decimal("1.5"), "2"])
def test_baffle_count_is_exact_integer_one_through_five(value: object) -> None:
    outcome = validate_request(_raw(case=_case(value)))
    assert outcome.status is Task162ValidationStatus.TYPED_BLOCKED
    assert outcome.typed_blocked is not None
    assert outcome.typed_blocked.blockers[0].code in {
        Task162FailureCode.UNSUPPORTED_BAFFLE_COUNT.value,
        Task162FailureCode.CASE_BINDING_VALUE_MISMATCH.value,
    }


def test_case_authority_values_are_required() -> None:
    bad = replace(_case(), shell_type=Task162ShellType.TEMA_E)
    outcome = validate_request(_raw(case=replace(bad, overall_flow_orientation="WRONG")))
    assert outcome.status is Task162ValidationStatus.TYPED_BLOCKED


def test_raw_special_objects_use_dedicated_identity_kinds() -> None:
    projection = project_raw_request(_raw())
    kinds = {child.field_name: child.kind for child in projection.root.children}
    assert kinds["task160_result"] is Task162RawProjectionKind.TASK160_RESULT_IDENTITY
    assert kinds["task161_result"] is Task162RawProjectionKind.TASK161_RESULT_IDENTITY
    assert kinds["task038_result"] is Task162RawProjectionKind.TASK038_RESULT_IDENTITY
    assert (
        kinds["cross_producer_binding_authority"]
        is Task162RawProjectionKind.CROSS_PRODUCER_BINDING_IDENTITY
    )
    assert kinds["case_authority"] is Task162RawProjectionKind.CASE_AUTHORITY_IDENTITY


def test_raw_binding_compatibility_uses_frozen_dimension_order() -> None:
    projection = project_raw_request(_raw())
    binding_node = next(
        child
        for child in projection.root.children
        if child.field_name == "cross_producer_binding_authority"
    )
    compatibility = next(
        child for child in binding_node.children if child.field_name == "compatibility_evidence"
    )
    dimensions = tuple(record.children[0].scalar_payload for record in compatibility.children)
    assert dimensions == tuple(dimension.value for dimension in Task162CompatibilityDimension)


def test_raw_permutation_and_projection_identity_are_deterministic() -> None:
    first = _raw()
    second = {key: first[key] for key in reversed(tuple(first))}
    assert raw_request_projection_hash(project_raw_request(first)) == raw_request_projection_hash(
        project_raw_request(second)
    )
    binding = first["cross_producer_binding_authority"]
    reversed_binding = replace(
        binding,
        evidence_refs=tuple(reversed(binding.evidence_refs)),
        compatibility_evidence=tuple(reversed(binding.compatibility_evidence)),
    )
    assert raw_request_projection_hash(
        project_raw_request({**first, "cross_producer_binding_authority": reversed_binding})
    ) == raw_request_projection_hash(project_raw_request(first))


def _markers(node: object) -> list[object]:
    output = [node] if node.kind is Task162RawProjectionKind.LIMIT_MARKER else []
    for child in node.children:
        output.extend(_markers(child))
    return output


def test_raw_marker_schema_and_resource_boundaries() -> None:
    over = project_raw_request({"value": "x" * 16_385})
    marker = _markers(over.root)[0]
    assert marker.field_name == "__TASK162_LIMIT_MARKER__"
    assert marker.type_identity is None
    assert marker.scalar_payload == "SCALAR_BYTE_LIMIT_EXCEEDED"
    assert marker.children == ()
    assert not _markers(project_raw_request({"value": "x" * 16_384}).root)
    allowed: object = "leaf"
    for _ in range(16):
        allowed = {"x": allowed}
    assert not _markers(project_raw_request(allowed).root)
    blocked = {"x": allowed}
    assert any(
        item.scalar_payload == "DEPTH_LIMIT_EXCEEDED"
        for item in _markers(project_raw_request(blocked).root)
    )
    assert not _markers(project_raw_request({f"k-{index:04d}": index for index in range(511)}).root)
    assert any(
        item.scalar_payload == "NODE_LIMIT_EXCEEDED"
        for item in _markers(
            project_raw_request({f"k-{index:04d}": index for index in range(512)}).root
        )
    )


def test_raw_unicode_and_unsupported_objects_fail_closed_without_repr() -> None:
    class Noisy:
        def __repr__(self) -> str:
            raise AssertionError("repr called")

        def __str__(self) -> str:
            raise AssertionError("str called")

    first = project_raw_request({"value": Noisy()})
    second = project_raw_request({"value": Noisy()})
    assert raw_request_projection_hash(first) == raw_request_projection_hash(second)
    surrogate = project_raw_request({"value": "\ud800"})
    assert _markers(surrogate.root)[0].scalar_payload == "UNICODE_ENCODING_FAILURE"
    outcome = validate_request({"value": Noisy()})
    assert outcome.status is Task162ValidationStatus.RAW_BOUNDARY_BLOCKED


def test_raw_marker_collision_ordering_is_total() -> None:
    first = {"a": "x" * 16_385, "b": "\ud800"}
    second = {"b": "\ud800", "a": "x" * 16_385}
    assert raw_request_projection_hash(project_raw_request(first)) == raw_request_projection_hash(
        project_raw_request(second)
    )
    literal_first = {"z": "x" * 16_385, "__TASK162_LIMIT_MARKER__": "literal"}
    literal_second = {"__TASK162_LIMIT_MARKER__": "literal", "z": "x" * 16_385}
    assert raw_request_projection_hash(
        project_raw_request(literal_first)
    ) == raw_request_projection_hash(project_raw_request(literal_second))


def test_request_schema_and_metadata_boundary_are_typed() -> None:
    raw = _raw()
    assert (
        validate_request({**raw, "unknown": 1}).status
        is Task162ValidationStatus.RAW_BOUNDARY_BLOCKED
    )
    duplicate = {**raw, "request_metadata": [("a", "1"), ("a", "2")]}
    blocked = validate_request(duplicate)
    assert blocked.status is Task162ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert blocked.raw_boundary_blocked is not None
    assert Task162FailureCode.INVALID_REQUEST_SCHEMA.value in {
        item.code for item in blocked.raw_boundary_blocked.blockers
    }


def test_decimal_context_is_explicit_and_interval_division_is_fail_closed() -> None:
    before = getcontext().copy()
    getcontext().prec = 6
    first = table7_relation(Decimal("0.8876560332864"), Decimal("0.4186602870813397"), 1)
    with localcontext(TASK162_DECIMAL_CONTEXT):
        second = table7_relation(Decimal("0.8876560332864"), Decimal("0.4186602870813397"), 1)
    getcontext().prec = before.prec
    assert first == second
    with pytest.raises(ArithmeticError):
        interval_divide(
            type("I", (), {"lower": Decimal("1"), "upper": Decimal("1")})(),
            type("I", (), {"lower": Decimal("-1"), "upper": Decimal("1")})(),
        )


def test_success_hash_uuid_and_provenance_graph_are_deterministic() -> None:
    first = validate_request(_raw()).valid
    second = validate_request(_raw()).valid
    assert first is not None and second is not None
    assert first.result_hash == second.result_hash
    assert first.result_id == second.result_id
    assert first.provenance.provenance_hash == second.provenance.provenance_hash
    assert len(first.provenance.graph.nodes) == 11
    assert len(first.provenance.graph.edges) == 10
    assert all(edge.source_id != edge.target_id for edge in first.provenance.graph.edges)


def test_blocked_results_have_no_provenance() -> None:
    raw = _raw()
    blocked = validate_request({**raw, "source_definition_id": "wrong"})
    assert blocked.status is Task162ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert blocked.raw_boundary_blocked is not None
    assert not hasattr(blocked.raw_boundary_blocked, "provenance")
    typed = validate_request({**raw, "case_authority": replace(_case(), baffle_count=6)})
    assert typed.status is Task162ValidationStatus.TYPED_BLOCKED
    assert typed.typed_blocked is not None
    assert not hasattr(typed.typed_blocked, "provenance")

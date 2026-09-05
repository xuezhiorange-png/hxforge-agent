"""Focused TASK161 implementation contract tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, replace
from decimal import Decimal, localcontext

import pytest

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority import (
    LIMIT_MARKER_FIELD_NAME,
    RAW_BLOCKED_ID_PREFIX,
    TASK161_DECIMAL_CONTEXT,
    TASK161_REQUIRED_CASE_INPUTS,
    TASK161_REQUIRED_RUNTIME_INPUTS,
    Task161FailureCode,
    Task161ValidationStatus,
    project_raw_request,
    raw_request_projection_hash,
    validate_request,
)
from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    RawProjectionKind,
    RawProjectionNode,
    Task161Result,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.service import (
    validate_request as validate_task160,
)

from .thermal_stream_state.test_ingress_models import make_r607_raw

SOURCE_ID = "TASK161-SOURCE-DEFINITION-R8-ISSUE-225"


def task160_result(raw: dict[str, object] | None = None) -> object:
    result = validate_task160(raw or make_r607_raw()).valid
    assert result is not None
    return result


def task161_raw(result: object | None = None, **overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "schema_version": "task161.schema.v1",
        "task161_version": "task161.v1",
        "source_definition_id": SOURCE_ID,
        "task160_result": result if result is not None else task160_result(),
        "request_metadata": [],
    }
    raw.update(overrides)
    return raw


def marker_nodes(node: RawProjectionNode) -> list[RawProjectionNode]:
    result: list[RawProjectionNode] = []
    if node.kind is RawProjectionKind.LIMIT_MARKER:
        result.append(node)
    for child in node.children:
        result.extend(marker_nodes(child))
    return result


def test_catalog_success_is_complete_and_has_no_downstream_numbers() -> None:
    result = validate_request(task161_raw())
    assert result.status is Task161ValidationStatus.VALID
    assert result.valid is not None
    assert isinstance(result.valid, Task161Result)
    assert result.valid.required_case_inputs == TASK161_REQUIRED_CASE_INPUTS
    assert result.valid.required_runtime_inputs == TASK161_REQUIRED_RUNTIME_INPUTS
    assert result.valid.case_binding_state.tema_e_binding.value == "UNBOUND"
    assert result.valid.performance_method_catalog.relation_id.endswith("TABLE_7")
    names = {field.name.lower() for field in fields(result.valid)}
    forbidden = {
        "ua",
        "ntu",
        "p_source",
        "epsilon",
        "effectiveness",
        "heat_duty",
        "outlet_temperatures",
        "lmtd",
    }
    assert names.isdisjoint(forbidden)
    assert not hasattr(result.valid, "ntu_value")
    assert not hasattr(result.valid, "p_source_value")


def test_capacity_foundation_uses_cold_side_as_cmin() -> None:
    result = validate_request(task161_raw()).valid
    assert result is not None
    capacity = result.capacity_foundation
    assert capacity.capacity_side_relation.value == "COLD_SIDE_IS_CMIN"
    assert capacity.c_min == capacity.c_dot_cold
    with localcontext(TASK161_DECIMAL_CONTEXT):
        assert capacity.r_source == capacity.c_dot_cold / capacity.c_dot_hot


def test_capacity_foundation_uses_hot_side_as_cmin() -> None:
    raw = make_r607_raw()
    stream = dict(raw["stream_records"][0])  # type: ignore[index]
    stream["mass_flow_kg_s"] = "0.5"
    raw["stream_records"] = [stream, raw["stream_records"][1]]  # type: ignore[index]
    result = validate_request(task161_raw(task160_result(raw))).valid
    assert result is not None
    capacity = result.capacity_foundation
    assert capacity.capacity_side_relation.value == "HOT_SIDE_IS_CMIN"
    with localcontext(TASK161_DECIMAL_CONTEXT):
        assert capacity.r_source == capacity.c_dot_cold / capacity.c_dot_hot
    assert capacity.r_source != Decimal(1) / capacity.c_r


def test_equal_capacity_is_normalized_to_one() -> None:
    raw = make_r607_raw()
    stream = dict(raw["stream_records"][0])  # type: ignore[index]
    snapshot = dict(stream["property_snapshot"])  # type: ignore[arg-type]
    snapshot["specific_heat_J_kg_K"] = "3500"
    stream["property_snapshot"] = snapshot
    stream["mass_flow_kg_s"] = "1.25"
    raw["stream_records"] = [stream, raw["stream_records"][1]]  # type: ignore[index]
    result = validate_request(task161_raw(task160_result(raw))).valid
    assert result is not None
    capacity = result.capacity_foundation
    assert capacity.capacity_side_relation.value == "EQUAL_CAPACITY"
    assert capacity.c_r == Decimal("1")
    assert capacity.r_source == Decimal("1")


@pytest.mark.parametrize(
    ("raw_value", "code"),
    [
        (None, Task161FailureCode.INVALID_REQUEST_TYPE),
        ("not-a-request", Task161FailureCode.INVALID_REQUEST_TYPE),
    ],
)
def test_raw_boundary_rejects_non_mapping_inputs(
    raw_value: object,
    code: Task161FailureCode,
) -> None:
    result = validate_request(raw_value)
    assert result.status is Task161ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert code.value in tuple(item.code for item in result.blockers)
    assert result.raw_boundary_blocked is not None
    assert result.raw_boundary_blocked.blocked_result_id.version == 5
    assert RAW_BLOCKED_ID_PREFIX


def test_raw_boundary_rejects_unknown_and_missing_fields() -> None:
    raw = task161_raw()
    raw["unknown"] = "x"
    result = validate_request(raw)
    assert result.status is Task161ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert Task161FailureCode.INVALID_REQUEST_SCHEMA.value in tuple(
        item.code for item in result.blockers
    )
    del raw["source_definition_id"]
    result = validate_request(raw)
    assert result.status is Task161ValidationStatus.RAW_BOUNDARY_BLOCKED


def test_request_metadata_is_sorted_and_duplicate_keys_block() -> None:
    first = validate_request(task161_raw(request_metadata=[("b", "2"), ("a", "1")]))
    second = validate_request(task161_raw(request_metadata=[("a", "1"), ("b", "2")]))
    assert first.valid is not None and second.valid is not None
    assert first.valid.result_hash == second.valid.result_hash
    blocked = validate_request(task161_raw(request_metadata=[("a", "1"), ("a", "2")]))
    assert blocked.status is Task161ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert Task161FailureCode.INVALID_REQUEST_SCHEMA.value in tuple(
        item.code for item in blocked.blockers
    )


def test_task160_result_uses_stable_six_field_raw_identity_projection() -> None:
    result = task160_result()
    projection = project_raw_request(task161_raw(result))
    task160_node = next(
        child for child in projection.root.children if child.field_name == "task160_result"
    )
    assert task160_node.kind is RawProjectionKind.TASK160_RESULT_IDENTITY
    assert tuple(child.field_name for child in task160_node.children) == (
        "schema_version",
        "task160_version",
        "request_hash",
        "result_hash",
        "result_id",
        "provenance_hash",
    )


def test_task160_tampering_fails_replay_and_does_not_create_task161_success() -> None:
    original = task160_result()
    tampered = replace(original, result_hash="0" * 64)
    result = validate_request(task161_raw(tampered))
    assert result.status is Task161ValidationStatus.TYPED_BLOCKED
    assert Task161FailureCode.TASK160_IDENTITY_REPLAY_FAILED.value in tuple(
        item.code for item in result.blockers
    )
    assert result.typed_blocked is not None
    assert not hasattr(result.typed_blocked, "provenance")


def test_raw_projection_is_insertion_order_independent_for_marker_collisions() -> None:
    first_raw = {"a": "x" * 16385, "b": "\ud800"}
    second_raw = {"b": "\ud800", "a": "x" * 16385}
    first = project_raw_request(first_raw)
    second = project_raw_request(second_raw)
    assert raw_request_projection_hash(first) == raw_request_projection_hash(second)
    reasons = {node.scalar_payload for node in marker_nodes(first.root)}
    assert reasons == {"SCALAR_BYTE_LIMIT_EXCEEDED", "UNICODE_ENCODING_FAILURE"}

    literal_first = {"z": "x" * 16385, LIMIT_MARKER_FIELD_NAME: "literal"}
    literal_second = {LIMIT_MARKER_FIELD_NAME: "literal", "z": "x" * 16385}
    assert raw_request_projection_hash(
        project_raw_request(literal_first)
    ) == raw_request_projection_hash(project_raw_request(literal_second))


def test_raw_projection_limits_and_marker_schema_are_exact() -> None:
    for value, reason in (
        ("x" * 16385, "SCALAR_BYTE_LIMIT_EXCEEDED"),
        ("\ud800", "UNICODE_ENCODING_FAILURE"),
    ):
        projection = project_raw_request({"value": value})
        markers = marker_nodes(projection.root)
        assert len(markers) == 1
        marker = markers[0]
        assert marker.field_name == LIMIT_MARKER_FIELD_NAME
        assert marker.kind is RawProjectionKind.LIMIT_MARKER
        assert marker.type_identity is None
        assert marker.scalar_payload == reason
        assert marker.children == ()

    allowed = project_raw_request({"value": "x" * 16384})
    assert not marker_nodes(allowed.root)


def test_raw_projection_depth_and_node_limits_are_fail_closed() -> None:
    allowed: object = "leaf"
    for _ in range(16):
        allowed = {"x": allowed}
    assert not marker_nodes(project_raw_request(allowed).root)

    blocked: object = "leaf"
    for _ in range(17):
        blocked = {"x": blocked}
    assert any(
        marker.scalar_payload == "DEPTH_LIMIT_EXCEEDED"
        for marker in marker_nodes(project_raw_request(blocked).root)
    )

    exactly = {f"k-{index:04d}": index for index in range(511)}
    assert not marker_nodes(project_raw_request(exactly).root)
    over = {f"k-{index:04d}": index for index in range(512)}
    assert any(
        marker.scalar_payload == "NODE_LIMIT_EXCEEDED"
        for marker in marker_nodes(project_raw_request(over).root)
    )


def test_unsupported_objects_have_stable_type_identity_without_repr() -> None:
    class Noisy:
        def __repr__(self) -> str:
            raise AssertionError("repr must not be called")

        def __str__(self) -> str:
            raise AssertionError("str must not be called")

    first = project_raw_request({"value": Noisy()})
    second = project_raw_request({"value": Noisy()})
    assert raw_request_projection_hash(first) == raw_request_projection_hash(second)
    node = first.root.children[0]
    assert node.kind is RawProjectionKind.UNSUPPORTED_OBJECT
    assert node.type_identity is not None
    result = validate_request(task161_raw(task160_result(), request_metadata=[], extra=Noisy()))
    assert result.status is Task161ValidationStatus.RAW_BOUNDARY_BLOCKED


def test_custom_metaclass_and_surrogate_metadata_fail_closed() -> None:
    calls: list[str] = []

    class Meta(type):
        def __getattribute__(cls, name: str) -> object:
            calls.append(name)
            if name == "__module__":
                raise AssertionError("metaclass hook must not execute")
            return super().__getattribute__(name)

    class Custom(metaclass=Meta):
        pass

    projection = project_raw_request({"value": Custom()})
    assert projection.root.kind is RawProjectionKind.RECORD
    assert calls == []
    surrogate = project_raw_request({"value": "\ud800"})
    assert marker_nodes(surrogate.root)[0].scalar_payload == "UNICODE_ENCODING_FAILURE"


def test_success_provenance_graph_is_deterministic_and_has_frozen_edges() -> None:
    first = validate_request(task161_raw())
    second = validate_request(task161_raw())
    assert first.valid is not None and second.valid is not None
    assert first.valid.result_hash == second.valid.result_hash
    assert first.valid.result_id == second.valid.result_id
    assert first.valid.provenance.provenance_hash == second.valid.provenance.provenance_hash
    assert {edge.relation for edge in first.valid.provenance.graph.edges} == {
        "AUTHORIZES",
        "SUPPLIES",
        "DEFINES",
        "PRODUCES",
    }


def test_task160_provenance_tampering_is_rejected_and_blocked_paths_have_no_graph() -> None:
    original = task160_result()
    tampered = deepcopy(original)
    object.__setattr__(tampered.provenance, "provenance_hash", "sha256:" + "0" * 64)
    result = validate_request(task161_raw(tampered))
    assert result.status is Task161ValidationStatus.TYPED_BLOCKED
    assert result.typed_blocked is not None
    assert not hasattr(result.typed_blocked, "provenance")
    raw = validate_request(task161_raw(task160_result(), bad=object()))
    assert raw.status is Task161ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert raw.raw_boundary_blocked is not None
    assert not hasattr(raw.raw_boundary_blocked, "provenance")


def test_forbidden_task038_and_numeric_inputs_are_not_admitted() -> None:
    raw = task161_raw()
    raw["UA"] = Decimal("1")
    result = validate_request(raw)
    assert result.status is Task161ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert Task161FailureCode.INVALID_REQUEST_SCHEMA.value in tuple(
        item.code for item in result.blockers
    )


def test_task160_result_identity_is_not_full_serialized() -> None:
    result = task160_result()
    projection = project_raw_request(task161_raw(result))
    payload = repr(projection)
    assert "stream_records" not in payload
    assert result.result_hash in repr(projection)


def test_request_with_invalid_task160_value_is_typed_blocked_not_case_unbound() -> None:
    raw = task161_raw()
    raw["task160_result"] = None
    result = validate_request(raw)
    assert result.status is Task161ValidationStatus.TYPED_BLOCKED
    assert Task161FailureCode.INVALID_TASK160_RESULT.value in tuple(
        item.code for item in result.blockers
    )

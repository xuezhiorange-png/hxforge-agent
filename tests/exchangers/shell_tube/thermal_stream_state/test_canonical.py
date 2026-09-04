"""TASK160 framing, normalization, and identity vectors."""

from __future__ import annotations

from copy import deepcopy

from hexagent.exchangers.shell_tube.thermal_stream_state.canonical import (
    RAW_BLOCKED_ID_PREFIX,
    SUCCESS_ID_PREFIX,
    TYPED_BLOCKED_ID_PREFIX,
    raw_request_projection_hash,
    request_hash_fields,
    success_canonical_bytes,
    to_provenance_payload_hash,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.ingress import (
    build_strict_request,
    project_raw_request,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.service import validate_request

from .test_ingress_models import make_r607_raw


def test_r607_request_and_success_vectors_are_stable() -> None:
    result = validate_request(make_r607_raw())
    assert result.valid is not None
    assert (
        result.valid.request_hash
        == "8305b6f6fcfeed768c16a77fcd1f8c1502d6a11e259439c4ff523dd9aa86d200"
    )
    assert (
        result.valid.result_hash
        == "e9889477b0dc0cb0291b6bda528d0b5afd2e129d0f6232e4691d9b7c6ed46be7"
    )
    assert str(result.valid.result_id) == "2b3810e1-f264-5f36-b6fd-422611a76407"
    assert len(success_canonical_bytes(result.valid)) == 21362


def test_request_hash_field_order_is_explicit() -> None:
    raw = make_r607_raw()
    strict, blockers = build_strict_request(raw)
    assert strict is not None
    assert blockers == ()
    assert tuple(name for name, _, _ in request_hash_fields(strict)) == (
        "schema_version",
        "task160_version",
        "implementation_software_version",
        "stream_records_normalized_by_side",
        "envelope_authority",
        "adapter_evidence_normalized",
        "deferred_capabilities_normalized",
        "provenance_inputs",
        "TASK160_SOURCE_DEFINITION_ID",
    )


def test_raw_projection_is_injective_for_nested_scalar_changes() -> None:
    first = project_raw_request(make_r607_raw())
    changed = make_r607_raw()
    streams = deepcopy(changed["stream_records"])  # type: ignore[arg-type]
    streams[0] = dict(streams[0])
    streams[0]["property_snapshot"] = dict(streams[0]["property_snapshot"])
    streams[0]["property_snapshot"]["specific_heat_J_kg_K"] = "4180.0"  # type: ignore[index]
    changed["stream_records"] = streams
    second = project_raw_request(changed)
    assert raw_request_projection_hash(first) != raw_request_projection_hash(second)


def test_raw_transport_list_and_tuple_are_equivalent_only_for_declared_fields() -> None:
    first = make_r607_raw()
    second = make_r607_raw()
    second["stream_records"] = tuple(second["stream_records"])  # type: ignore[arg-type]
    second["adapter_evidence"] = tuple(second["adapter_evidence"])  # type: ignore[arg-type]
    assert raw_request_projection_hash(project_raw_request(first)) == raw_request_projection_hash(
        project_raw_request(second)
    )


def test_stream_order_is_preserved_in_raw_projection() -> None:
    first = project_raw_request(make_r607_raw())
    changed = make_r607_raw()
    changed["stream_records"] = list(reversed(changed["stream_records"]))  # type: ignore[arg-type]
    second = project_raw_request(changed)
    assert raw_request_projection_hash(first) != raw_request_projection_hash(second)


def test_set_like_deferred_capability_order_is_normalized() -> None:
    first = make_r607_raw()
    second = make_r607_raw()
    second["deferred_capabilities"] = list(reversed(second["deferred_capabilities"]))  # type: ignore[index]
    assert raw_request_projection_hash(project_raw_request(first)) == raw_request_projection_hash(
        project_raw_request(second)
    )


def test_decimal_lexemes_are_not_quantized_or_float_converted() -> None:
    raw = make_r607_raw()
    strict, blockers = build_strict_request(raw)
    assert strict is not None and blockers == ()
    assert str(strict.stream_records[0].inlet_temperature_K) == "390.15"
    assert str(strict.stream_records[0].mass_flow_kg_s) == "2.5"
    assert str(strict.stream_records[1].property_snapshot.specific_heat_J_kg_K) == "3500"


def test_provenance_payload_framing_is_representation_only() -> None:
    bare = "a" * 64
    assert to_provenance_payload_hash(bare) == "sha256:" + bare
    assert len(to_provenance_payload_hash(bare)) == 71


def test_branch_prefixes_are_distinct() -> None:
    assert len({SUCCESS_ID_PREFIX, TYPED_BLOCKED_ID_PREFIX, RAW_BLOCKED_ID_PREFIX}) == 3


def test_success_hash_changes_when_implementation_version_changes() -> None:
    first = validate_request(make_r607_raw())
    second_raw = make_r607_raw(implementation_software_version="task160.local-implementation.v2")
    second = validate_request(second_raw)
    assert first.valid is not None and second.valid is not None
    assert first.valid.request_hash != second.valid.request_hash
    assert first.valid.result_hash != second.valid.result_hash

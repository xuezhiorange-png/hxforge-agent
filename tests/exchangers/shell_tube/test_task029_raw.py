"""TASK-029 raw boundary contract tests (I17): 10 frozen TEST_ID proofs."""

from __future__ import annotations

import hashlib
from collections import UserDict
from collections.abc import Mapping
from decimal import Decimal
from types import MappingProxyType

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    Task029BlockerCode,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_raw_boundary_blocked_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.raw_boundary import (
    validate_raw_boundary,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.raw_projection import (
    RAW_BOOL,
    RAW_DECIMAL,
    RAW_INTEGER,
    RAW_UNSUPPORTED,
    canonicalize_raw_value,
    encode_raw_projection,
)
from tests.exchangers.shell_tube.task029_frozen_vectors import (
    UNKNOWN_RAW_REQUEST_CANONICAL_LEN,
    UNKNOWN_RAW_REQUEST_CANONICAL_SHA256,
    VALID_RAW_REQUEST_CANONICAL_LEN,
    VALID_RAW_REQUEST_CANONICAL_SHA256,
    VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256,
    copy_unknown_field_raw_request_fixture,
    copy_valid_raw_request_fixture,
)
from tests.exchangers.shell_tube.test_task029_upstream import build_production_fixtures


def _canonical_sha256_hex(raw_input: object) -> str:
    projection = encode_raw_projection("task029.raw-request", raw_input)
    return hashlib.sha256(bytes.fromhex(projection.canonical_bytes_hex)).hexdigest()


def _canonical_byte_len(raw_input: object) -> int:
    projection = encode_raw_projection("task029.raw-request", raw_input)
    return len(projection.canonical_bytes_hex) // 2


def test_T029_RAW_001_TOP_LEVEL_NOT_DICT() -> None:
    fixtures = build_production_fixtures()
    for bad_input in ("string", 42, [], (), None):
        result = validate_raw_boundary(
            bad_input,
            task027_success_result=fixtures["task027"],
            task028_success_result=fixtures["task028"],
        )
        assert result.blocked
        assert result.blocked_result is not None
        assert any(
            b.code == Task029BlockerCode.BL_T029_RAW_INPUT_BOUNDARY_MALFORMED
            for b in result.blocked_result.blockers
        )


def test_T029_RAW_002_UNKNOWN_FIELD_ACCUMULATION() -> None:
    fixtures = build_production_fixtures()
    raw = copy_unknown_field_raw_request_fixture()
    result = validate_raw_boundary(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert result.blocked
    assert result.blocked_result is not None
    unknown_blockers = [
        b
        for b in result.blocked_result.blockers
        if b.code == Task029BlockerCode.BL_T029_REQUEST_UNKNOWN_FIELD
    ]
    assert unknown_blockers
    assert unknown_blockers[0].evidence_refs == ("unexpected",)


def test_T029_RAW_003_REQUIRED_FIELD_MISSING() -> None:
    fixtures = build_production_fixtures()
    raw = copy_valid_raw_request_fixture()
    del raw["profile_id"]
    result = validate_raw_boundary(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert result.blocked
    assert result.blocked_result is not None
    assert any(
        b.code == Task029BlockerCode.BL_T029_REQUIRED_FIELD_MISSING
        for b in result.blocked_result.blockers
    )


def test_T029_RAW_004_EXACT_RAW_SCALAR_TYPES() -> None:
    assert RAW_BOOL in canonicalize_raw_value(True)
    assert RAW_INTEGER in canonicalize_raw_value(42)
    assert RAW_DECIMAL in canonicalize_raw_value(Decimal("1.5"))
    assert b"true" in canonicalize_raw_value(True)
    assert b"42" in canonicalize_raw_value(42)


def test_T029_RAW_005_NO_FLOAT_TO_DECIMAL() -> None:
    frame = canonicalize_raw_value(1.5)
    assert RAW_UNSUPPORTED in frame
    assert RAW_DECIMAL not in frame


def test_T029_RAW_006_NO_MAPPING_SEQUENCE_DUCK_TYPING() -> None:
    for duck_typed in (
        UserDict({"a": 1}),
        MappingProxyType({"a": 1}),
        bytearray([1, 2]),
    ):
        frame = canonicalize_raw_value(duck_typed)
        assert RAW_UNSUPPORTED in frame


def test_T029_RAW_007_UNSUPPORTED_VALUE_NO_REPR() -> None:
    class _Opaque:
        pass

    value = _Opaque()
    frame = canonicalize_raw_value(value)
    assert RAW_UNSUPPORTED in frame
    assert repr(value).encode("utf-8") not in frame
    assert b"test_task029_raw" in frame


def test_T029_RAW_008_DICT_INSERTION_ORDER_PRESERVED() -> None:
    first = {"z": 1, "a": 2}
    second = {"z": 1, "a": 2}
    assert canonicalize_raw_value(first) == canonicalize_raw_value(second)
    reversed_order = {"a": 2, "z": 1}
    assert canonicalize_raw_value(first) != canonicalize_raw_value(reversed_order)


def test_T029_RAW_009_VALID_RAW_REQUEST_VECTOR() -> None:
    raw: Mapping[str, object] = copy_valid_raw_request_fixture()
    assert _canonical_byte_len(raw) == VALID_RAW_REQUEST_CANONICAL_LEN
    assert _canonical_sha256_hex(raw) == VALID_RAW_REQUEST_CANONICAL_SHA256


def test_T029_RAW_010_RAW_BOUNDARY_BLOCKED_VECTOR() -> None:
    fixtures = build_production_fixtures()
    raw = copy_unknown_field_raw_request_fixture()
    assert _canonical_byte_len(raw) == UNKNOWN_RAW_REQUEST_CANONICAL_LEN
    assert _canonical_sha256_hex(raw) == UNKNOWN_RAW_REQUEST_CANONICAL_SHA256

    result = validate_raw_boundary(
        raw,
        task027_success_result=fixtures["task027"],
        task028_success_result=fixtures["task028"],
    )
    assert result.blocked
    assert result.blocked_result is not None
    actual_hash = compute_raw_boundary_blocked_hash(result.blocked_result)
    assert actual_hash == VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256
    assert any(
        b.code == Task029BlockerCode.BL_T029_REQUEST_UNKNOWN_FIELD
        for b in result.blocked_result.blockers
    )

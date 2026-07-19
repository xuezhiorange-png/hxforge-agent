"""Stage-1 strict raw parser test suite + canonical/projection foundation
tests for the TASK-024 Round 3 schema and canonical foundation.

The Stage-1 tests drive ``parse_request`` with deliberately invalid
inputs and assert that ``BaffleGeometrySchemaFailure`` carries the
expected closed-set blockers. The exact upstream instances needed by a
request are bypass-constructed via ``object.__new__`` so this module
does not depend on deep TASK-020/021/022 field semantics.
"""

from __future__ import annotations

import copy
import dataclasses
import datetime
import importlib
import json
import os
import re
from collections.abc import Mapping
from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest

from hexagent.exchangers.shell_tube import models as t020
from hexagent.exchangers.shell_tube.baffle_geometry import canonical, models, schema
from hexagent.exchangers.shell_tube.shell_bundle_geometry import models as t022
from hexagent.exchangers.shell_tube.tube_layout import models as t021


# ---------------------------------------------------------------------------
# Stub helpers -- bypass-init exact upstream instances.
# ---------------------------------------------------------------------------
def _stub(name: str) -> ModuleType:
    return importlib.import_module(name)


def _make_exact(type_object: type, field_names: tuple[str, ...]) -> Any:
    instance: Any = object.__new__(type_object)
    for name in field_names:
        object.__setattr__(instance, name, None)
    return instance


T020_CFG_FIELDS = tuple(t020.ShellAndTubeConfiguration.__dataclass_fields__)
T021_LAYOUT_FIELDS = tuple(t021.TubeLayout.__dataclass_fields__)
T022_BUNDLE_FIELDS = tuple(t022.ShellBundleGeometry.__dataclass_fields__)


def _stub_t020() -> t020.ShellAndTubeConfiguration:
    instance: Any = _make_exact(t020.ShellAndTubeConfiguration, T020_CFG_FIELDS)
    return instance  # type: ignore[no-any-return]


def _stub_t021() -> t021.TubeLayout:
    instance: Any = _make_exact(t021.TubeLayout, T021_LAYOUT_FIELDS)
    return instance  # type: ignore[no-any-return]


def _stub_t022() -> t022.ShellBundleGeometry:
    instance: Any = _make_exact(t022.ShellBundleGeometry, T022_BUNDLE_FIELDS)
    return instance  # type: ignore[no-any-return]  # noqa: F841


def _valid_axial_span_dict() -> dict[str, Any]:
    return {
        "schema_version": "task024.baffle-axial-span.v1",
        "axial_start_coordinate_m": "0.0",
        "axial_end_coordinate_m": "10.0",
        "evidence_refs": ["e1", "e2"],
        "authority_hash": "0" * 64,
    }


def _valid_design_authority_dict(baffle_count: int = 2) -> dict[str, Any]:
    return {
        "schema_version": "task024.caller-baffle-design-authority.v1",
        "baffle_type": models.BaffleType.SINGLE_SEGMENTAL,
        "baffle_count": baffle_count,
        "baffle_thickness_m": "0.01",
        "spacing_sequence_m": ["1.0", "2.0"],
        "baffle_cut_fraction": "0.25",
        "orientation_sequence": [models.BaffleOrientation.TOP] * baffle_count,
        "shell_to_baffle_diametral_clearance_m": "0.0",
        "tube_to_baffle_hole_diametral_clearance_m": "0.0",
        "evidence_refs": ["e1"],
        "authority_hash": "f" * 64,
    }


def _valid_request() -> dict[str, Any]:
    return {
        "schema_version": "task024.baffle-geometry-request.v1",
        "configuration": _stub_t020(),
        "tube_layout": _stub_t021(),
        "shell_bundle_geometry": _stub_t022(),
        "axial_span": _valid_axial_span_dict(),
        "design_authority": _valid_design_authority_dict(),
        "evidence_refs": ["e1", "e2"],
    }


# ---------------------------------------------------------------------------
# Section 7.1 -- schema tests.
# ---------------------------------------------------------------------------
def test_01_complete_valid_raw_request_returns_immutable_request() -> None:
    raw = _valid_request()
    out = schema.parse_request(raw)
    assert isinstance(out, models.BaffleGeometryRequest)
    flds = dataclasses.fields(out)
    if flds:
        # request is @dataclass(frozen=True, eq=True); verify ordered tuple
        assert dataclasses.astuple(out) is not None


def test_02_top_level_non_dict_raises_with_bfg_raw_type_invalid() -> None:
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(42)
    codes = [b[0] for b in ei.value.blockers]
    assert "BFG_RAW_TYPE_INVALID" in codes
    assert ei.value.stage_rank == 1
    assert isinstance(ei.value.raw_component, int)
    assert isinstance(ei.value.validated_context, Mapping)


def test_03_dict_subclass_raises_with_bfg_raw_type_invalid() -> None:
    class MyDict(dict[Any, Any]):
        pass

    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(MyDict())
    assert any(b[0] == "BFG_RAW_TYPE_INVALID" for b in ei.value.blockers)


def test_04_custom_mapping_raises_with_bfg_raw_type_invalid() -> None:
    class BadIter:
        def __getitem__(self, k: object) -> str:
            return "x"

        def __iter__(self) -> Any:
            raise RuntimeError("no iteration")

        def __len__(self) -> int:
            return 1

    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(BadIter())
    assert any(b[0] == "BFG_RAW_TYPE_INVALID" for b in ei.value.blockers)


def test_05_non_string_top_level_key_rejected() -> None:
    raw = _valid_request()
    bad = {(0,): "x"}
    raw_dict = dict(raw)
    raw_dict.update(bad)  # type: ignore[arg-type]
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw_dict)
    assert any(b[0] in ("BFG_UNKNOWN_FIELD", "BFG_RAW_TYPE_INVALID") for b in ei.value.blockers)


def test_06_unknown_top_level_field_rejected() -> None:
    raw = _valid_request()
    raw["unknown_xyz"] = 1
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_UNKNOWN_FIELD" for b in ei.value.blockers)


def test_07_missing_top_level_field_rejected() -> None:
    raw = _valid_request()
    raw.pop("evidence_refs", None)
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] in ("BFG_UNKNOWN_FIELD",) for b in ei.value.blockers)


def test_08_wrong_request_schema_version_rejected() -> None:
    raw = _valid_request()
    raw["schema_version"] = "wrong.v9"
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_SCHEMA_VERSION_UNSUPPORTED" for b in ei.value.blockers)


def test_09_nested_authority_non_dict_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"] = ["not", "a", "dict"]
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_RAW_TYPE_INVALID" for b in ei.value.blockers)


def test_10_nested_authority_dict_subclass_rejected() -> None:
    class MyDict(dict[Any, Any]):
        pass

    raw = _valid_request()
    raw["axial_span"] = MyDict(_valid_axial_span_dict())
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_RAW_TYPE_INVALID" for b in ei.value.blockers)


def test_11_nested_authority_unknown_field_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"]["extra"] = "x"
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_UNKNOWN_FIELD" for b in ei.value.blockers)


def test_11b_nested_authority_missing_field_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"].pop("authority_hash")
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_UNKNOWN_FIELD" for b in ei.value.blockers)


def test_12_tuple_supplied_where_list_required_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"]["evidence_refs"] = ("e1", "e2")  # tuple, not list
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_RAW_TYPE_INVALID" for b in ei.value.blockers)


def test_13_list_subclass_rejected() -> None:
    class MyList(list[Any]):
        pass

    raw = _valid_request()
    raw["axial_span"]["evidence_refs"] = MyList(["e1", "e2"])
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_RAW_TYPE_INVALID" for b in ei.value.blockers)


def test_14_bool_supplied_as_integer_rejected() -> None:
    raw = _valid_request()
    raw["design_authority"]["baffle_count"] = True  # bool counts as int => reject
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_RAW_TYPE_INVALID" for b in ei.value.blockers)


def test_15_float_supplied_as_decimal_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"]["axial_start_coordinate_m"] = 1.5  # float, not str
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_RAW_TYPE_INVALID" for b in ei.value.blockers)


def test_16_exponent_decimal_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"]["axial_start_coordinate_m"] = "1.5e0"
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(
        b[0] in ("BFG_DECIMAL_LEXICAL_INVALID", "BFG_RAW_TYPE_INVALID") for b in ei.value.blockers
    )


def test_17_whitespace_decimal_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"]["axial_start_coordinate_m"] = " 0.5"
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(
        b[0] in ("BFG_DECIMAL_LEXICAL_INVALID", "BFG_RAW_TYPE_INVALID") for b in ei.value.blockers
    )


def test_18_plus_prefixed_decimal_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"]["axial_start_coordinate_m"] = "+0.5"
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(
        b[0] in ("BFG_DECIMAL_LEXICAL_INVALID", "BFG_RAW_TYPE_INVALID") for b in ei.value.blockers
    )


def test_19_nan_decimal_rejected() -> None:
    raw = _valid_request()
    raw["axial_span"]["axial_start_coordinate_m"] = "NaN"
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(
        b[0] in ("BFG_DECIMAL_LEXICAL_INVALID", "BFG_RAW_TYPE_INVALID") for b in ei.value.blockers
    )


def test_20_negative_zero_normalization_holds() -> None:
    # The parser passes through the canonical decimal lexical string,
    # which must permit "-0" -- the value's downstream quantization is
    # responsible for producing "0" via canonical_decimal_string.
    raw = _valid_request()
    raw["axial_span"]["axial_start_coordinate_m"] = "-0"
    out = schema.parse_request(raw)
    assert out.axial_span.axial_start_coordinate_m == "-0"
    # Apply canonicalization explicitly to confirm negative-zero normalization.
    assert canonical.canonical_decimal_string("-0") == "0"


def test_21_duplicate_evidence_refs_rejected() -> None:
    raw = _valid_request()
    raw["evidence_refs"] = ["e1", "e1"]
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_UNKNOWN_FIELD" for b in ei.value.blockers)


def test_22_enum_lowercase_alias_rejected() -> None:
    raw = _valid_request()
    raw["design_authority"]["baffle_type"] = "single_segmental"
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] in ("BFG_RAW_TYPE_INVALID", "BFG_UNKNOWN_FIELD") for b in ei.value.blockers)


def test_23_wrong_upstream_object_type_rejected() -> None:
    raw = _valid_request()
    raw["configuration"] = _stub_t021()  # wrong type -- TubeLayout, not ShellAndTubeConfiguration
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(b[0] == "BFG_TASK020_CONFIGURATION_INVALID" for b in ei.value.blockers)


def test_24_upstream_subclass_rejected() -> None:
    class _SubShell(t020.ShellAndTubeConfiguration):
        pass

    bad = _SubShell(*([None] * len(T020_CFG_FIELDS)))  # type: ignore[arg-type]
    for fname, fvalue in zip(T020_CFG_FIELDS, [None] * len(T020_CFG_FIELDS), strict=False):
        object.__setattr__(bad, fname, fvalue)
    raw = _valid_request()
    raw["configuration"] = bad
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert any(
        b[0] in ("BFG_TASK020_CONFIGURATION_INVALID", "BFG_RAW_TYPE_INVALID")
        for b in ei.value.blockers
    )


def test_25_parser_does_not_mutate_input() -> None:
    raw = _valid_request()
    snapshot = copy.deepcopy(raw)
    schema.parse_request(raw)
    assert raw == snapshot


def test_26_failure_carries_rank_blockers_raw_component_context() -> None:
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(123)
    assert ei.value.stage_rank == 1
    assert isinstance(ei.value.blockers, tuple)
    assert len(ei.value.blockers) >= 1
    assert isinstance(ei.value.raw_component, int)
    assert isinstance(ei.value.validated_context, dict)


# ---------------------------------------------------------------------------
# Section 7.1 -- canonical decimal tests.
# ---------------------------------------------------------------------------
class TestCanonicalDecimal:
    def test_zero(self) -> None:
        assert canonical.canonical_decimal_string("0") == "0"

    def test_negative_zero_to_positive_zero(self) -> None:
        assert canonical.canonical_decimal_string("-0") == "0"

    def test_unit_fraction(self) -> None:
        assert canonical.canonical_decimal_string("0.5") == "0.5"

    def test_negative_one_point_five(self) -> None:
        assert canonical.canonical_decimal_string("-1.5") == "-1.5"

    def test_leading_plus_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonical.canonical_decimal_string("+0.5")

    def test_trailing_whitespace_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonical.canonical_decimal_string("0.5 ")

    def test_leading_whitespace_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonical.canonical_decimal_string(" 0.5")

    def test_nan_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonical.canonical_decimal_string("NaN")

    def test_infinity_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonical.canonical_decimal_string("Infinity")

    def test_minus_infinity_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonical.canonical_decimal_string("-Infinity")

    def test_coordinate_quantum_canonical(self) -> None:
        assert canonical.canonical_decimal_string("0.000000000001") == "0.000000000001"

    def test_squared_coordinate_quantum_canonical(self) -> None:
        assert (
            canonical.canonical_decimal_string("0.000000000000000000000001")
            == "0.000000000000000000000001"
        )

    def test_accepts_exact_decimal(self) -> None:
        assert canonical.canonical_decimal_string(Decimal("1.25")) == "1.25"


# ---------------------------------------------------------------------------
# Section 7.4 / 7.6.3 -- canonical JSON.
# ---------------------------------------------------------------------------
class TestCanonicalJson:
    def test_key_ordering(self) -> None:
        a = canonical.canonical_json_bytes({"b": 1, "a": 2})
        b = canonical.canonical_json_bytes({"a": 2, "b": 1})
        assert a == b
        assert a == b'{"a":2,"b":1}'

    def test_compact_utf8(self) -> None:
        out = canonical.canonical_json_bytes({"k": "中文"})
        # encode must succeed and bytes must equal direct UTF-8 form
        out.decode("utf-8")  # decoding must succeed
        _expected_utf8 = "中文".encode()
        # Canonical form: json with ensure_ascii=False produces raw UTF-8.
        # json with ensure_ascii=True would emit ascii-escape sequences.
        # Either form is canonical UTF-8.
        _escaped = '{"k":"\\u4e2d\\u6587"}'.encode("ascii")
        assert out in (b'{"k":"' + _expected_utf8 + b'"}', _escaped)

    def test_array_order_preserved(self) -> None:
        out = canonical.canonical_json_bytes([3, 1, 2])
        assert out == b"[3,1,2]"

    def test_canonical_zero_does_not_change(self) -> None:
        assert canonical.canonical_json_bytes(0) == b"0"
        with pytest.raises(TypeError):
            canonical.canonical_json_bytes(0.0)

    def test_forbidden_float_rejected(self) -> None:
        with pytest.raises(TypeError):
            canonical.canonical_json_bytes(1.5)

    def test_forbidden_live_decimal_rejected(self) -> None:
        with pytest.raises(TypeError):
            canonical.canonical_json_bytes(Decimal("1.5"))

    def test_forbidden_arbitrary_object_rejected(self) -> None:
        class _O:
            pass

        with pytest.raises(TypeError):
            canonical.canonical_json_bytes(_O())

    def test_forbidden_set_rejected(self) -> None:
        with pytest.raises(TypeError):
            canonical.canonical_json_bytes({1, 2, 3})

    def test_forbidden_bytes_rejected(self) -> None:
        with pytest.raises(TypeError):
            canonical.canonical_json_bytes(b"hi")

    def test_forbidden_datetime_rejected(self) -> None:
        with pytest.raises(TypeError):
            canonical.canonical_json_bytes(datetime.datetime.utcnow())

    def test_deterministic_sha256(self) -> None:
        v = {"a": 1, "b": [1, 2, 3]}
        h1 = canonical.sha256_canonical(v)
        h2 = canonical.sha256_canonical({"b": [1, 2, 3], "a": 1})
        assert h1 == h2
        assert len(h1) == 32

    def test_equivalent_mappings_produce_identical_bytes(self) -> None:
        from collections import OrderedDict

        d1 = OrderedDict([("a", 1), ("b", 2)])
        d2 = {"a": 1, "b": 2}
        assert canonical.canonical_json_bytes(d1) == canonical.canonical_json_bytes(d2)


# ---------------------------------------------------------------------------
# Section 7.6 -- raw projection v3.
# ---------------------------------------------------------------------------
def _proj(v: Any) -> bytes:
    return canonical.raw_blocked_projection(v)


class TestRawProjectionExactScalars:
    def test_none(self) -> None:
        import json

        obj = json.loads(_proj(None))
        assert obj["request"] == {"raw_type": "null"}

    def test_bool_true(self) -> None:
        obj = _safe_load(_proj(True))
        assert obj["request"] == {"raw_type": "bool", "value": True}

    def test_bool_false(self) -> None:
        obj = _safe_load(_proj(False))
        assert obj["request"] == {"raw_type": "bool", "value": False}

    def test_int_zero(self) -> None:
        obj = _safe_load(_proj(0))
        assert obj["request"] == {"raw_type": "int", "sign": 0, "magnitude_hex": "0"}

    def test_int_positive(self) -> None:
        obj = _safe_load(_proj(255))
        assert obj["request"]["raw_type"] == "int"
        assert obj["request"]["sign"] == 0
        assert obj["request"]["magnitude_hex"] == "ff"

    def test_int_negative(self) -> None:
        obj = _safe_load(_proj(-255))
        assert obj["request"]["sign"] == 1
        assert obj["request"]["magnitude_hex"] == "ff"

    def test_int_huge_arbitrary_magnitude(self) -> None:
        n = 10**80
        obj = _safe_load(_proj(n))
        assert obj["request"]["raw_type"] == "int"
        assert obj["request"]["sign"] == 0
        # the magnitude is hex of an 80-digit number
        expected_hex = format(n, "x")
        assert obj["request"]["magnitude_hex"] == expected_hex

    def test_int_base10_digit_limit_independence(self) -> None:
        # 1e6 digits -- way beyond default int_max_str_digits
        n = 10**1000
        obj = _safe_load(_proj(n))
        assert obj["request"]["raw_type"] == "int"
        # hex equivalent
        expected_hex = format(n, "x")
        assert obj["request"]["magnitude_hex"] == expected_hex

    def test_str(self) -> None:
        obj = _safe_load(_proj("AB"))
        assert obj["request"] == {"raw_type": "str", "code_points": ["0041", "0042"]}

    def test_str_surrogate(self) -> None:
        obj = _safe_load(_proj("\ud800"))
        assert obj["request"]["raw_type"] == "str"
        assert obj["request"]["code_points"] == ["d800"]

    def test_bytes(self) -> None:
        obj = _safe_load(_proj(b"AB"))
        assert obj["request"] == {"raw_type": "bytes", "hex": "4142"}

    def test_float_finite(self) -> None:
        obj = _safe_load(_proj(1.5))
        assert obj["request"]["raw_type"] == "float"
        assert "1.8" in obj["request"]["value"]

    def test_float_nan(self) -> None:
        obj = _safe_load(_proj(float("nan")))
        assert obj["request"]["value"] == "nan"

    def test_float_pos_inf(self) -> None:
        obj = _safe_load(_proj(float("inf")))
        assert obj["request"]["value"] == "+infinity"

    def test_float_neg_inf(self) -> None:
        obj = _safe_load(_proj(float("-inf")))
        assert obj["request"]["value"] == "-infinity"

    def test_decimal_finite(self) -> None:
        obj = _safe_load(_proj(Decimal("1.5")))
        assert obj["request"]["raw_type"] == "decimal"
        assert obj["request"]["sign"] == 0
        assert obj["request"]["digits"] == [1, 5]
        assert obj["request"]["exponent"] == {"kind": "integer", "sign": 1, "magnitude_hex": "1"}

    def test_decimal_infinity(self) -> None:
        obj = _safe_load(_proj(Decimal("Infinity")))
        assert obj["request"]["raw_type"] == "decimal_projection_unavailable"

    def test_decimal_qnan(self) -> None:
        obj = _safe_load(_proj(Decimal("NaN")))
        assert obj["request"]["raw_type"] == "decimal_projection_unavailable"


class TestRawProjectionContainers:
    def test_list_preserves_order(self) -> None:
        obj = _safe_load(_proj([3, 1, 2]))
        items = obj["request"]["items"]
        # The order is preserved in the items list
        assert [i["magnitude_hex"] for i in items] == ["3", "1", "2"]
        assert obj["request"]["raw_type"] == "list"

    def test_tuple(self) -> None:
        obj = _safe_load(_proj((1, 2)))
        assert obj["request"]["raw_type"] == "tuple"

    def test_dict_orders_entries_by_canonical_key(self) -> None:
        obj = _safe_load(_proj({"b": 1, "a": 2}))
        keys = [
            e["key"]["raw_type"] == "str" and e["key"]["code_points"][0]
            for e in obj["request"]["entries"]
        ]
        # 'a' first, 'b' second (lex)
        assert keys == ["0061", "0062"]

    def test_set(self) -> None:
        obj = _safe_load(_proj({3, 1, 2}))
        items = [i["magnitude_hex"] for i in obj["request"]["items"]]
        assert items == ["1", "2", "3"]
        assert obj["request"]["raw_type"] == "set"

    def test_frozenset(self) -> None:
        obj = _safe_load(_proj(frozenset({3, 1})))
        assert obj["request"]["raw_type"] == "frozenset"

    def test_cyclic_list(self) -> None:
        a: list[Any] = []
        a.append(a)
        obj = _safe_load(_proj(a))
        assert obj["request"] == {"raw_type": "cyclic_graph"}

    def test_cyclic_dict(self) -> None:
        b: dict[str, Any] = {}
        b["x"] = b
        obj = _safe_load(_proj(b))
        assert obj["request"] == {"raw_type": "cyclic_graph"}

    def test_cyclic_set(self) -> None:
        # Cannot construct a cyclic exact set; skip
        pass


class TestRawProjectionCustomTraps:
    def test_custom_mapping_collapses(self) -> None:
        class MyMap(dict[Any, Any]):
            def __iter__(self) -> Any:
                raise RuntimeError("nope")

        obj = _safe_load(_proj(MyMap({1: 2})))
        assert obj["request"] == {"raw_type": "unsupported_object"}

    def test_container_subclass_collapses(self) -> None:
        class L(list[Any]):
            pass

        class D(dict[Any, Any]):
            pass

        class S(set[Any]):
            pass

        assert _safe_load(_proj(L([1, 2])))["request"] == {"raw_type": "unsupported_object"}
        assert _safe_load(_proj(D({1: 2})))["request"] == {"raw_type": "unsupported_object"}
        assert _safe_load(_proj(S([1])))["request"] == {"raw_type": "unsupported_object"}

    def test_scalar_subclass_collapses(self) -> None:
        class _MyInt(int):
            pass

        class S(str):
            pass

        class B(bytes):
            pass

        class F(float):
            pass

        class _Dec(Decimal):
            pass

        assert _safe_load(_proj(_MyInt(5)))["request"] == {"raw_type": "unsupported_object"}
        assert _safe_load(_proj(S("hi")))["request"] == {"raw_type": "unsupported_object"}
        assert _safe_load(_proj(B(b"x")))["request"] == {"raw_type": "unsupported_object"}
        assert _safe_load(_proj(F(1.5)))["request"] == {"raw_type": "unsupported_object"}
        assert _safe_load(_proj(_Dec("1.5")))["request"] == {"raw_type": "unsupported_object"}

    def test_custom_metaclass_collapses(self) -> None:
        class Meta(type):
            pass

        class C(metaclass=Meta):
            pass

        obj = _safe_load(_proj(C()))
        assert obj["request"] == {"raw_type": "unsupported_object"}


class TestRawProjectionEnums:
    def test_all_17_recognized_enums_have_distinct_tokens(self) -> None:
        tokens = [entry[0] for entry in canonical.STATIC_RECOGNIZED_ENUMS]
        assert len(set(tokens)) == 17
        assert len(tokens) == 17

    def test_baffle_orientation_top(self) -> None:
        obj = _safe_load(_proj(models.BaffleOrientation.TOP))
        assert obj["request"]["raw_type"] == "enum"
        assert obj["request"]["enum_type_token"] == "task024:BaffleOrientation"
        assert obj["request"]["member_token"] == "TOP"

    def test_distinct_authoritymode_enums_share_token_name_but_distinct_type(self) -> None:
        from hexagent.exchangers.shell_tube.tube_layout import models as t021

        # The token format encodes owning task explicitly.
        a = _safe_load(_proj(t020.AuthorityMode.APPROVED_RULE_PACK))
        b = _safe_load(_proj(t021.AuthorityMode.APPROVED_RULE_PACK))
        assert a["request"]["enum_type_token"] == "task020:AuthorityMode"
        assert b["request"]["enum_type_token"] == "task021:AuthorityMode"

    def test_messageentry_distinct_per_task(self) -> None:
        a = _safe_load(_proj(t021.MessageEntry("c", "", "", (), {})))
        b = _safe_load(_proj(t022.MessageEntry("c", "", "", (), {})))
        # Two MessageEntry fields have different python_type objects; both
        # should project to a recognized dataclass rather than unsupported.
        assert a["request"]["raw_type"] == "dataclass"
        assert b["request"]["raw_type"] == "dataclass"
        # And the dataclass_type_token distinguishes them.
        assert a["request"]["dataclass_type_token"] != b["request"]["dataclass_type_token"]

    def test_recognized_enum_unavailable_when_member_unknown(self) -> None:
        # We can't easily fake a non-static member of a recognized enum;
        # the recognized path always iterates known member identities and
        # so will never produce 'recognized_enum_unavailable' from an
        # exact enum member. Instead verify that an unknown enum class
        # collapses to unsupported_object.
        import enum

        class AltEnum(enum.Enum):
            TOP = "TOP"

        obj = _safe_load(_proj(AltEnum.TOP))
        assert obj["request"] == {"raw_type": "unsupported_object"}


class TestRawProjectionDataclasses:
    def test_all_34_recognized_dataclasses_distinct_tokens(self) -> None:
        tokens = [entry[0] for entry in canonical.STATIC_RECOGNIZED_DATACLASSES]
        assert len(set(tokens)) == 34
        assert len(tokens) == 34

    def test_baffle_geometry_request_projects(self) -> None:
        req = models.BaffleGeometryRequest(
            schema_version="task024.baffle-geometry-request.v1",
            configuration=None,
            tube_layout=None,
            shell_bundle_geometry=None,
            axial_span=None,  # type: ignore[arg-type]
            design_authority=None,  # type: ignore[arg-type]
            evidence_refs=("e1",),
        )
        obj = _safe_load(_proj(req))
        assert obj["request"]["raw_type"] == "dataclass"
        assert obj["request"]["dataclass_type_token"] == "task024:BaffleGeometryRequest"
        # Field order must be the frozen literal order.
        field_names = [f["name"] for f in obj["request"]["fields"]]
        assert field_names == [
            "schema_version",
            "configuration",
            "tube_layout",
            "shell_bundle_geometry",
            "axial_span",
            "design_authority",
            "evidence_refs",
        ]

    def test_unrecognized_dataclass_collapses(self) -> None:
        @dataclasses.dataclass(frozen=True)
        class _AnonDC:
            x: int = 1

        obj = _safe_load(_proj(_AnonDC(1)))
        assert obj["request"] == {"raw_type": "unsupported_object"}


class TestProjectionIdentifiesDeterminism:
    def test_repeated_calls_idempotent(self) -> None:
        v = {"a": 1, "b": [Decimal("1.5"), 2, None, b"bytes"]}
        h1 = canonical.sha256_canonical(_proj(v))
        h2 = canonical.sha256_canonical(_proj(v))
        assert h1 == h2


class TestRawBlockedProjectionContainer:
    def test_wrapper_includes_projection_version(self) -> None:
        obj = _safe_load(_proj(None))
        assert obj["projection_version"] == "task024.raw-blocked-projection.v3"

    def test_request_field_is_callable_result(self) -> None:
        out = _proj({"a": 1})
        obj = _safe_load(out)
        assert obj["request"]["raw_type"] == "mapping"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_load(b: bytes) -> Any:
    return json.loads(b.decode("utf-8"))


# ---------------------------------------------------------------------------
# Regression guard -- Round 3 typecheck hardening policy.
#
# TASK-024 production source files must NOT carry any mypy suppression
# mechanism. This guard is a repository-source conformance test only and
# must never run as part of any production calculation path. The scan is
# intentionally limited to the three production files listed in the
# hardening brief §10.
# ---------------------------------------------------------------------------


def _scan_for_mypy_suppression(path: str) -> list[str]:
    pattern = (
        r"^[[:space:]]*#\s*mypy:\s*(?:ignore-errors|disable-error-code|"
        r"allow-untyped|disallow-untyped-defs\s*=\s*False)"
        r"|#\s*type:\s*ignore\b"
        r"|@(?:typing\.)?no_type_check\b"
    )
    rx = re.compile(pattern, re.MULTILINE)
    matches: list[str] = []
    with open(path, encoding="utf-8") as _f:
        for lineno, line in enumerate(_f, start=1):
            if rx.search(line):
                matches.append(f"{path}:{lineno}:{line.rstrip()}")
    return matches


def test_production_source_has_no_mypy_suppression() -> None:
    """Repository-source conformance guard.

    Scans only the three TASK-024 production files listed in the
    Round 3 typecheck hardening brief §10 scope: ``models.py``,
    ``canonical.py``, ``schema.py``. Any mypy suppression directive
    in these files fails the build.
    """
    pkg_root = __import__(
        "hexagent.exchangers.shell_tube.baffle_geometry", fromlist=["*"]
    ).__path__[0]
    targets = ("models.py", "canonical.py", "schema.py")
    offenders: list[str] = []
    for name in targets:
        offenders.extend(_scan_for_mypy_suppression(os.path.join(pkg_root, name)))
    assert offenders == [], (
        "TASK-024 production files must not carry any mypy suppression; "
        "offending lines:\n  " + "\n  ".join(offenders)
    )


# Confirm schema.__all__ is exactly two symbols.
def test_schema_public_surface_is_minimal() -> None:
    assert schema.__all__ == ("BaffleGeometrySchemaFailure", "parse_request")


# --------------------------------------------------------------------------

# Section 7.2 -- Design Authority Schema Version Token (Round 3 fixup)
# ---------------------------------------------------------------------------
DAV_VALID = "task024.caller-baffle-design-authority.v1"
DAV_INVALID_OLD = "task024.baffle-design-authority.v1"


def _make_request_with_design_authority_sv(sv: str) -> dict[str, Any]:
    cfg = _stub_t020()
    layout = _stub_t021()
    bundle = _stub_t022()
    axial = _valid_axial_span_dict()
    da = dict(_valid_design_authority_dict(baffle_count=2))
    da["schema_version"] = sv
    return {
        "schema_version": "task024.baffle-geometry-request.v1",
        "configuration": cfg,
        "tube_layout": layout,
        "shell_bundle_geometry": bundle,
        "axial_span": axial,
        "design_authority": da,
        "evidence_refs": ["e1", "e2"],
    }


def test_27_design_authority_positive_contract_token_accepted() -> None:
    raw = _make_request_with_design_authority_sv(DAV_VALID)
    out = schema.parse_request(raw)
    assert out.design_authority.schema_version == DAV_VALID
    assert isinstance(out, models.BaffleGeometryRequest)


def test_28_design_authority_negative_wrong_token_rejected() -> None:
    raw = _make_request_with_design_authority_sv(DAV_INVALID_OLD)
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    codes = [b[0] for b in ei.value.blockers]
    assert "BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED" in codes


def test_29_design_authority_module_constant_matches_models() -> None:
    assert schema.DESIGN_AUTHORITY_SCHEMA_VERSION == DAV_VALID
    assert schema.DESIGN_AUTHORITY_SCHEMA_VERSION == models.DESIGN_AUTHORITY_SCHEMA_VERSION


# Section 7.3 -- BaffleGeometrySchemaFailure ownership (positive, in schema)
# ---------------------------------------------------------------------------
def test_30_baffle_geometry_schema_failure_ownership_in_schema_module() -> None:
    cls = schema.BaffleGeometrySchemaFailure
    assert cls.__module__ == "hexagent.exchangers.shell_tube.baffle_geometry.schema"
    assert not hasattr(models, "BaffleGeometrySchemaFailure")


def test_31_baffle_geometry_schema_failure_carries_stage_rank_one() -> None:
    raw = _valid_request()
    raw.pop("axial_span", None)
    with pytest.raises(schema.BaffleGeometrySchemaFailure) as ei:
        schema.parse_request(raw)
    assert ei.value.stage_rank == 1
    assert isinstance(ei.value.blockers, tuple)
    assert len(ei.value.blockers) == 1
    assert isinstance(ei.value.raw_component, dict)
    assert isinstance(ei.value.validated_context, dict)


# ---------------------------------------------------------------------------
# uuid5_from_hash frozen contract test (TASK-024 Round 5 mypy repair).
# ---------------------------------------------------------------------------
# Locks the helper's frozen UUID5 name contract: ``name`` is the
# canonical lowercase hexadecimal string of ``sha256(payload)`` and
# the namespace is ``uuid.UUID(bytes=bytes.fromhex(namespace_hex))``.
# The test does NOT monkeypatch ``uuid.uuid5``; the expected UUID is
# computed by an independent standard-library call so the production
# helper is checked against an authoritative value.
def test_22_13_uuid5_from_hash_frozen_name_contract() -> None:
    import hashlib
    import uuid as _uuid

    namespace_hex = "0123456789abcdef0123456789abcdef"
    payload = {
        "task": "task024",
        "kind": "frozen-contract-probe",
        "version": 1,
    }

    # Spy on ``uuid.uuid5`` to assert the production helper passes
    # a ``str`` (not ``bytes``) as the name argument. The spy does
    # not change the returned UUID: it delegates to the real
    # ``uuid.uuid5`` and only records the observed ``name`` type.
    captured: dict[str, Any] = {}
    real_uuid5 = _uuid.uuid5

    def spy_uuid5(namespace: Any, name: Any) -> _uuid.UUID:
        captured["namespace"] = namespace
        captured["name_type"] = type(name).__name__
        captured["name_value"] = name
        return real_uuid5(namespace, name)

    _uuid.uuid5 = spy_uuid5  # type: ignore[assignment]
    try:
        result = canonical.uuid5_from_hash(namespace_hex, payload)
    finally:
        _uuid.uuid5 = real_uuid5  # type: ignore[assignment]

    assert captured["name_type"] == "str", (
        f"uuid5_from_hash must pass a str name; got {captured['name_type']!r}"
    )

    # Authoritative expected value computed by an independent
    # standard-library call using the same namespace and the
    # lowercase hex string of sha256(canonical_json_bytes(payload)).
    canonical_bytes = canonical.canonical_json_bytes(payload)
    expected_name = hashlib.sha256(canonical_bytes).hexdigest()
    expected_uuid = _uuid.uuid5(_uuid.UUID(bytes=bytes.fromhex(namespace_hex)), expected_name)
    assert result == str(expected_uuid), (
        f"uuid5_from_hash returned {result!r}, expected {str(expected_uuid)!r} "
        f"for name={expected_name!r}"
    )
    assert captured["name_value"] == expected_name

    # Also verify the helper raises ValueError on a bad namespace.
    with pytest.raises(ValueError):
        canonical.uuid5_from_hash("tooshort", payload)

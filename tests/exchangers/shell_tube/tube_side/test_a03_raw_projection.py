"""§A03 — Raw projection tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a03_atom_none() -> None:
    assert ts.project_raw_value(None) != ts.project_raw_value(True)


def test_a03_atom_bool() -> None:
    assert ts.project_raw_value(True) != ts.project_raw_value(False)


def test_a03_atom_int() -> None:
    assert ts.project_raw_value(0) != ts.project_raw_value("0")
    assert ts.project_raw_value(42) != ts.project_raw_value("42")


def test_a03_atom_str_surrogate_rejected() -> None:
    surrogate = "\ud83d"
    with pytest.raises(ValueError):
        ts.project_raw_value(surrogate)


def test_a03_atom_dict_keys_sorted() -> None:
    out_a = ts.project_raw_dict({"b": 2, "a": 1})
    out_b = ts.project_raw_dict({"a": 1, "b": 2})
    assert out_a == out_b


def test_a03_atom_dict_non_str_key_rejected() -> None:
    with pytest.raises(ValueError):
        ts.project_raw_dict({1: "x"})  # type: ignore[dict-item]


def test_a03_atom_tuple_order_preserved() -> None:
    out = ts.project_raw_value((1, 2, 3))
    assert out == ts.project_raw_value((1, 2, 3))


def test_a03_atom_frozenset_sorted_unique() -> None:
    """§7.3 — frozenset members project to unique bytes sorted lexicographically."""
    out = ts.project_raw_value(frozenset([1, 2, 3]))
    assert out is not None
    assert isinstance(out, bytes)


def test_a03_unsupported_class_rejected() -> None:
    class Weird:  # noqa: D401 — test stub
        pass

    with pytest.raises(ValueError):
        ts.project_raw_value(Weird())


def test_raw_projection_atom_kinds_are_pairwise_distinct() -> None:
    values = (None, True, False, 0, 1, "", "1", b"", b"1", Decimal("0"), Decimal("1"))
    projections = [ts.project_raw_value(value) for value in values]
    assert len(set(projections)) == len(values)


def test_raw_projection_rejects_int_subclass() -> None:
    class IntSubclass(int):
        pass

    with pytest.raises(ValueError):
        ts.project_raw_value(IntSubclass(1))


def test_raw_projection_rejects_str_subclass_without_calling_encode() -> None:
    class StrSubclass(str):
        def encode(self, *args: object, **kwargs: object) -> bytes:
            raise AssertionError("caller encode must not run")

    with pytest.raises(ValueError):
        ts.project_raw_value(StrSubclass("x"))


def test_raw_projection_rejects_bytes_subclass() -> None:
    class BytesSubclass(bytes):
        pass

    with pytest.raises(ValueError):
        ts.project_raw_value(BytesSubclass(b"x"))


def test_raw_projection_rejects_decimal_subclass() -> None:
    class DecimalSubclass(Decimal):
        pass

    with pytest.raises(ValueError):
        ts.project_raw_value(DecimalSubclass("1"))


def test_fake_class_named_tube_layout_is_unsafe() -> None:
    """§P0-1 — unsafe_object_signal must use exact concrete types, not class names."""

    class TubeLayout:
        pass

    assert ts.unsafe_object_signal(TubeLayout()) is True
    assert ts.unsafe_object_signal(object()) is True
    assert ts.unsafe_object_signal("benign") is False
    assert ts.unsafe_object_signal(None) is False

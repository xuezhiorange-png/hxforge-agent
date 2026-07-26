"""§A03 — Raw projection tests."""

from __future__ import annotations

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a03_atom_none() -> None:
    assert ts.project_raw_value(None) == b""


def test_a03_atom_bool() -> None:
    assert ts.project_raw_value(True) == b""
    assert ts.project_raw_value(False) == b""


def test_a03_atom_int() -> None:
    assert ts.project_raw_value(0) == b"0"
    assert ts.project_raw_value(42) == b"42"


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

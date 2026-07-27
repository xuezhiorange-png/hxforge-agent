"""§A01 / §14.3 — Upstream closure and A01 imports."""

from __future__ import annotations

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a01_required_exports() -> None:
    """§14.3 — FrozenJsonArray / FrozenJsonObject / sha256_hex are public."""
    assert callable(ts.FrozenJsonArray)
    assert callable(ts.FrozenJsonObject)
    assert callable(ts.sha256_hex)


def test_a01_frozen_json_array_rejects_unknown_atom() -> None:
    """FrozenJsonArray only accepts canonical atoms or nested containers."""
    with pytest.raises(TypeError):
        ts.FrozenJsonArray([1.5])  # type: ignore[list-item]


def test_a01_frozen_json_object_rejects_non_string_keys() -> None:
    """FrozenJsonObject rejects non-str keys."""
    with pytest.raises(TypeError):
        ts.FrozenJsonObject({1: "x"})  # type: ignore[dict-item]


def test_frozen_json_object_copies_input_mapping() -> None:
    source = {"a": 1}
    frozen = ts.FrozenJsonObject(source)
    source["a"] = 2
    assert frozen["a"] == 1
    with pytest.raises(TypeError):
        frozen.items_mapping["b"] = 3  # type: ignore[index]


def test_frozen_json_array_items_cannot_be_rebound() -> None:
    array = ts.FrozenJsonArray([1, 2, 3])
    with pytest.raises((AttributeError, TypeError)):
        array._items = (4, 5, 6)  # type: ignore[misc]


def test_frozen_json_object_items_cannot_be_rebound() -> None:
    obj = ts.FrozenJsonObject({"a": 1})
    with pytest.raises((AttributeError, TypeError)):
        obj._items = {"b": 2}  # type: ignore[misc]


def test_a01_sha256_hex_lowercase_64() -> None:
    out = ts.sha256_hex(b"")
    assert len(out) == 64
    assert all(c in "0123456789abcdef" for c in out)


def test_a01_no_upstream_repo_external_import() -> None:
    """§14.3 — A01 does not import from /tmp or repo-external."""
    import importlib

    module = importlib.import_module("hexagent.exchangers.shell_tube.tube_side")
    src_module = module.__file__ or ""
    assert "/tmp" not in src_module
    assert "tube_side" in src_module

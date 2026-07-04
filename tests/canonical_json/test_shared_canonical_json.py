"""Unit tests for the shared canonical JSON module.

These tests verify Section 13 of the TASK-012 frozen design contract
(docs/tasks/TASK-012-standards-rule-pack-license-boundary.md, review Head
28b6330f8c5221d75f101f6810157d81a428f446). The shared canonical JSON helper
is consumed by both TASK-011 benchmark cases (via hexagent.benchmark_cases.canonical)
and TASK-012 rule-packs.
"""

from __future__ import annotations

import pytest

from hexagent.canonical_json import (
    EXCLUDED_HASH_FIELDS,
    canonical_json_bytes,
    canonical_sha256,
)


def test_canonical_hash_is_deterministic() -> None:
    """Same input MUST produce same hash across calls."""
    v = {"a": 1, "b": 2}
    assert canonical_sha256(v) == canonical_sha256(v)


def test_canonical_hash_depends_only_on_content() -> None:
    """Equivalent contents in different key insertion order MUST hash equal."""
    a = {"a": 1, "b": 2, "c": 3}
    b = {"c": 3, "b": 2, "a": 1}
    assert canonical_sha256(a) == canonical_sha256(b)


def test_canonical_hash_excludes_canonical_hash_field() -> None:
    """``canonical_hash`` field MUST be excluded from hash input."""
    without = {"x": 1, "y": 2}
    with_ignored = {"x": 1, "y": 2, "canonical_hash": "GARBAGE_VALUE_SHOULD_BE_EXCLUDED"}
    assert canonical_sha256(without) == canonical_sha256(with_ignored)


def test_canonical_hash_excludes_mutable_review_comments_field() -> None:
    """``mutable_review_comments`` MUST be excluded from hash input."""
    without = {"x": 1}
    with_comments = {"x": 1, "mutable_review_comments": ["any text is ignored"]}
    assert canonical_sha256(without) == canonical_sha256(with_comments)


def test_canonical_hash_field_change_changes_hash() -> None:
    """Other field changes MUST change the hash."""
    a = {"x": 1}
    b = {"x": 2}
    assert canonical_sha256(a) != canonical_sha256(b)


def test_excluded_hash_fields_constant() -> None:
    """EXCLUDED_HASH_FIELDS MUST list both fields per Section 13."""
    assert "canonical_hash" in EXCLUDED_HASH_FIELDS
    assert "mutable_review_comments" in EXCLUDED_HASH_FIELDS


def test_canonical_json_bytes_is_utf8() -> None:
    """canonical_json_bytes MUST return UTF-8 encoded bytes."""
    v = {"x": "héllo"}
    out = canonical_json_bytes(v)
    assert isinstance(out, bytes)
    # NFC-normalized text round-trips through UTF-8.
    assert "héllo".encode() in out


def test_canonical_json_bytes_returns_rfc8785_sorted_keys() -> None:
    """Object keys MUST be sorted lexicographically (RFC 8785 §3.2.3)."""
    v = {"b": 1, "a": 2, "c": 3}
    out = canonical_json_bytes(v).decode("utf-8")
    # Keys appear in sorted order: a, b, c
    assert out.index('"a"') < out.index('"b"') < out.index('"c"')


def test_canonical_json_nested_dict_keys_sorted() -> None:
    """Nested dict keys MUST also be sorted recursively."""
    v = {"outer": {"z": 1, "a": 2, "m": 3}}
    out = canonical_json_bytes(v).decode("utf-8")
    assert out.index('"a"') < out.index('"m"') < out.index('"z"')


def test_canonical_json_normalizes_nfc() -> None:
    """Equivalent NFC vs NFD strings MUST produce same canonical bytes."""
    # NFD: 'e' + combining acute
    nfd = "he\u0301llo"
    # NFC: precomposed 'é'
    nfc = "héllo"
    v_nfd = {"k": nfd}
    v_nfc = {"k": nfc}
    assert canonical_json_bytes(v_nfd) == canonical_json_bytes(v_nfc)
    assert canonical_sha256(v_nfd) == canonical_sha256(v_nfc)


def test_canonical_json_integers_have_no_decimal_point() -> None:
    """Integers MUST be serialized without a decimal point (Section 13)."""
    v = {"x": 42}
    out = canonical_json_bytes(v).decode("utf-8")
    assert '"x":42' in out
    assert "42.0" not in out


def test_canonical_json_booleans_lowercase() -> None:
    """Booleans MUST be serialized as ``true`` / ``false`` lowercase."""
    v = {"t": True, "f": False}
    out = canonical_json_bytes(v).decode("utf-8")
    assert '"t":true' in out
    assert '"f":false' in out


def test_canonical_json_rejects_nonfinite_float_nan() -> None:
    """NaN MUST raise at hash time (Section 13 non_finite_floats = FORBIDDEN)."""
    with pytest.raises(ValueError):
        canonical_sha256({"x": float("nan")})


def test_canonical_json_rejects_nonfinite_float_pos_inf() -> None:
    """+Infinity MUST raise at hash time."""
    with pytest.raises(ValueError):
        canonical_sha256({"x": float("inf")})


def test_canonical_json_rejects_nonfinite_float_neg_inf() -> None:
    """-Infinity MUST raise at hash time."""
    with pytest.raises(ValueError):
        canonical_sha256({"x": float("-inf")})


def test_canonical_sha256_returns_64_hex_chars() -> None:
    """SHA-256 hex digest MUST be 64 hex chars (FIPS 180-4)."""
    h = canonical_sha256({"x": 1})
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_canonical_json_bytes_list_order_preserved() -> None:
    """List element order MUST be preserved (not sorted — Section 13 field_ordering)."""
    v = {"x": [3, 1, 2]}
    out = canonical_json_bytes(v).decode("utf-8")
    assert "[3,1,2]" in out


def test_shared_module_is_consistent_with_benchmark_canonical() -> None:
    """The shared module MUST produce identical bytes to benchmark_cases.canonical."""
    # Imported inside the test to assert cross-module equivalence.
    from hexagent.benchmark_cases.canonical import (
        canonical_json_bytes as legacy_bytes,
    )
    from hexagent.benchmark_cases.canonical import (
        canonical_sha256 as legacy_sha,
    )

    v = {"a": 1, "b": [3, 2, 1], "c": {"y": 2, "x": "héllo"}}
    assert canonical_json_bytes(v) == legacy_bytes(v)
    assert canonical_sha256(v) == legacy_sha(v)

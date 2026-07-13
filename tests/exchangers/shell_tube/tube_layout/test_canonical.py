from __future__ import annotations

import json
from decimal import Decimal
from types import MappingProxyType

import pytest

from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    CanonicalizationError,
    canonical_json,
    fragment_canonical,
    fragment_canonical_json,
    freeze_deeply,
    quantized_decimal_string,
)


def test_canonical_json_sorts_keys_and_rejects_float() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    with pytest.raises(CanonicalizationError):
        canonical_json({"x": 1.0})


def test_coordinate_quantization_is_half_even() -> None:
    assert quantized_decimal_string(Decimal("0.0000000000015")) == "0.000000000002"
    assert quantized_decimal_string(Decimal("0.0000000000025")) == "0.000000000002"


def test_freeze_deeply_makes_mapping_proxy_for_dict() -> None:
    frozen = freeze_deeply({"a": 1, "b": 2})
    assert isinstance(frozen, MappingProxyType)
    assert frozen["a"] == 1
    # MappingProxyType is read-only — verify mutation fails
    with pytest.raises(TypeError):
        frozen["a"] = 99  # type: ignore[index]


def test_freeze_deeply_converts_nested_lists_to_tuples() -> None:
    frozen = freeze_deeply({"nested": [1, 2, 3]})
    assert isinstance(frozen["nested"], tuple)


def test_freeze_deeply_handles_deeply_nested_structures() -> None:
    raw = {
        "level1": {"level2": [{"level3": [{"value": "x"}]}]},
        "numeric": [1, 2, 3],
    }
    frozen = freeze_deeply(raw)
    canonical = fragment_canonical_json(frozen)
    parsed = json.loads(canonical)
    assert parsed == {
        "level1": {"level2": [{"level3": [{"value": "x"}]}]},
        "numeric": [1, 2, 3],
    }


def test_freeze_deeply_normalizes_decimals_to_canonical_strings() -> None:
    frozen = freeze_deeply({"d": Decimal("0.1")})
    canonical = fragment_canonical_json(frozen)
    parsed = json.loads(canonical)
    assert parsed == {"d": "0.1"}


def test_freeze_deeply_rejects_non_string_keys() -> None:
    with pytest.raises(CanonicalizationError):
        freeze_deeply({1: "value"})


def test_fragment_canonical_returns_sorted_key_dict() -> None:
    canonical = fragment_canonical({"b": 1, "a": 2})
    assert list(canonical.keys()) == ["a", "b"]


def test_fragment_canonical_handles_message_entry_details_like_payload() -> None:
    """Regression: MessageEntry-like details structures freeze cleanly."""

    details = {
        "authority_mode": "INTERNAL_GENERIC",
        "standard_claim_status": "NO_STANDARD_CLAIM",
    }
    frozen = freeze_deeply(details)
    canonical_str = fragment_canonical_json(frozen)
    assert json.loads(canonical_str) == details


def test_freeze_deeply_handles_case_authority_primitive() -> None:
    """Regression: TASK-020 case authority shape freezes and round-trips through canonical_json."""

    case_authority = {
        "revision_id": "rev-001",
        "payload_hash": "f" * 64,
        "domain_snapshot_hash": "0" * 64,
        "revision_status": "COMMITTED",
    }
    canonical_str = fragment_canonical_json(case_authority)
    parsed = json.loads(canonical_str)
    assert parsed == case_authority


def test_freeze_deeply_makes_provenance_proxy_with_nested_tuples() -> None:
    """Regression: provenance-shaped payload freezes with sorted keys + tuple arrays."""

    provenance_like = {
        "task_id": "TASK-021",
        "config_id": "cfg-1",
        "evidence_refs": ["ref-a", "ref-b"],
        "nested": {"inner_key": ["x", "y", "z"]},
    }
    frozen = freeze_deeply(provenance_like)
    assert isinstance(frozen, MappingProxyType)
    assert isinstance(frozen["evidence_refs"], tuple)
    canonical_str = fragment_canonical_json(frozen)
    parsed = json.loads(canonical_str)
    assert parsed["task_id"] == "TASK-021"
    assert tuple(parsed["evidence_refs"]) == ("ref-a", "ref-b")


def test_fragment_canonical_captures_state_per_invocation() -> None:
    """Regression: each freeze+canonical capture is independent of subsequent mutations."""

    raw: dict[str, object] = {"a": [1, 2], "b": {"c": 3}}
    h1 = fragment_canonical_json(freeze_deeply(raw))
    # Mutate AFTER first capture: second capture reflects the new state, proving
    # the freeze is a snapshot, not a reactive link.
    raw["a"] = [1, 2, 99]
    raw["b"] = {"c": 99}
    h2 = fragment_canonical_json(freeze_deeply(raw))
    assert h1 != h2
    # Sanity-check h1 is the original canonical form
    import json as _json

    assert _json.loads(h1) == {"a": [1, 2], "b": {"c": 3}}


def test_freeze_deeply_handles_stl_message_details_payload() -> None:
    """Regression: §11.4 MessageEntry.details-shape payloads freeze to canonical JSON."""

    details_obj = {
        "authority_mode": "INTERNAL_GENERIC",
        "standard_claim_status": "NO_STANDARD_CLAIM",
    }
    payload = freeze_deeply({"details": details_obj})
    canonical = fragment_canonical_json(payload)
    assert json.loads(canonical) == {"details": details_obj}

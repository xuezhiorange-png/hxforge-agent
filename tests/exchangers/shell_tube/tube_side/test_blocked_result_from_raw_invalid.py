"""§6.3 — Blocked result tests."""

from __future__ import annotations

import hexagent.exchangers.shell_tube.tube_side as ts
from hexagent.exchangers.shell_tube.tube_side.provenance import (
    FrozenProvenance,
)


def test_blocked_result_from_raw_invalid() -> None:
    """Top-level non-dict returns a blocked result with stage_rank=1."""
    result = ts.evaluate_task025("not-a-dict")
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1


def test_blocked_result_warnings_always_empty() -> None:
    result = ts.evaluate_task025(None)
    assert result.warnings == ()


def test_blocked_result_deferred_capabilities_present() -> None:
    result = ts.evaluate_task025(None)
    assert isinstance(result.deferred_capabilities, tuple)
    assert len(result.deferred_capabilities) >= 1


def test_blocked_result_provenance_present() -> None:
    result = ts.evaluate_task025(None)
    assert isinstance(result.provenance, FrozenProvenance)


def test_blocked_result_schema_version_literal() -> None:
    result = ts.evaluate_task025(None)
    assert result.schema_version == "task025.blocked-result.v1"


def test_blocked_result_blockers_are_sorted_unique() -> None:
    """§6.3 / §12 — blockers tuple is sorted, deduplicated."""
    result = ts.evaluate_task025(None)
    codes = [entry.code for entry in result.blockers]
    assert codes == sorted(codes, key=lambda c: c.value)
    assert len(set(codes)) == len(codes)
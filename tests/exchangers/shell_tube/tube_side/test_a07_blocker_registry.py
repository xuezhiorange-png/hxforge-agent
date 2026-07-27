"""§A07 — Blocker registry tests."""

from __future__ import annotations

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a07_blocker_registry_member_count() -> None:
    assert len(ts.BlockerCode) == 30


def test_a07_bl001_name_canonical() -> None:
    assert (
        ts.BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING.value
        == "BL_001_ACTIVE_PARTICIPATION_MISSING"
    )


def test_a07_bl030_name_canonical() -> None:
    assert ts.BlockerCode.BL_030_UNSUPPORTED_VERSION.value == "BL_030_UNSUPPORTED_VERSION"


def test_a07_emit_blocker_known_code() -> None:
    entry = ts.emit_blocker(
        ts.BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
        ("raw_input", "foo"),
        "msg-key",
        ("ref1",),
    )
    assert entry.code is ts.BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING
    assert entry.field_path == ("raw_input", "foo")
    assert entry.message_key == "msg-key"
    assert entry.evidence_refs == ("ref1",)


def test_a07_emit_blocker_unknown_code_collapses_to_27() -> None:
    entry = ts.emit_blocker(
        "BL_999_NOT_A_REAL_CODE",  # type: ignore[arg-type]
        "raw_input.foo",
        "msg-key",
    )
    assert entry.code is ts.BlockerCode.BL_027_UNREGISTERED_BLOCKER_CODE


def test_a07_collapse_unregistered_dedups() -> None:
    e1 = ts.emit_blocker(ts.BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING, "a", "k", ())
    e2 = ts.emit_blocker(ts.BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING, "b", "k", ())
    out = ts.collapse_unregistered_codes([e1, e2])
    assert len(out) == 1


def test_a07_emit_blocker_str_field_path_single_tuple() -> None:
    """§13 — a single-string field_path is wrapped into a 1-tuple."""
    entry = ts.emit_blocker(
        ts.BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
        "raw_input_foo",
        "msg-key",
    )
    assert entry.field_path == ("raw_input_foo",)


def test_a07_emit_blocker_evidence_tuple_preserved() -> None:
    """§13 — evidence_refs tuple order is preserved."""
    entry = ts.emit_blocker(
        ts.BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
        "raw_input",
        "msg",
        ("c", "a", "b"),
    )
    assert entry.evidence_refs == ("c", "a", "b")


# ruff: noqa: E501

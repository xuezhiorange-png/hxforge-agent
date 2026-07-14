"""Tests for the TASK-022 Slice B1 adapter blocker taxonomy.

These tests verify the **closed-set** frozen in Issue #147 Record 4:
* the tuple ``RULE_PACK_ADAPTER_BLOCKER_CODES`` contains exactly the
  twenty tokens recorded by Charles, in the canonical order;
* the matching :class:`RulePackAdapterBlockerCode` enum exposes the
  same tokens;
* the default message-key mapping is complete and the message-keys are
  non-empty strings;
* the default field-path mapping is complete;
* every blocker constructed via :func:`build_message_entry` matches
  the slice-A-standard five-field :class:`MessageEntry` payload;
* details are rejected outside the canonical JSON value domain;
* duplicate evidence_refs are deduplicated and sorted in Unicode order;
* deterministic ordering is stable across runs;
* :class:`AdapterFailure` carries an immutable tuple of blockers and
  does not use the exception's ``str()`` as the authoritative signal.

The tests intentionally do NOT touch the rule_pack_adapter.py file —
they only exercise the blocker taxonomy.
"""

from __future__ import annotations

import inspect

import pytest

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    RULE_PACK_ADAPTER_BLOCKER_CODES,
    AdapterFailure,
    RulePackAdapterBlockerCode,
)
from hexagent.exchangers.shell_tube.shell_bundle_geometry.adapter_blockers import (
    RULE_PACK_ADAPTER_DEFAULT_FIELD_PATH,
    RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY,
    build_message_entry,
    sort_adapter_blockers,
)
from hexagent.exchangers.shell_tube.shell_bundle_geometry.models import MessageEntry

EXPECTED_FROZEN_CODES: tuple[str, ...] = (
    "SBG_RULE_ADAPTER_RAW_TYPE_INVALID",
    "SBG_RULE_ADAPTER_UNKNOWN_FIELD",
    "SBG_RULE_ADAPTER_UPSTREAM_OBJECT_INVALID",
    "SBG_RULE_ADAPTER_MANIFEST_INVALID",
    "SBG_RULE_ADAPTER_MANIFEST_HASH_MISMATCH",
    "SBG_RULE_ADAPTER_RULE_ID_INVALID",
    "SBG_RULE_ADAPTER_RULE_NOT_FOUND",
    "SBG_RULE_ADAPTER_MANIFEST_REFERENCE_INVALID",
    "SBG_RULE_ADAPTER_RULE_INVALID",
    "SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH",
    "SBG_RULE_ADAPTER_RULE_HASH_MISMATCH",
    "SBG_RULE_ADAPTER_RULE_UNAPPROVED",
    "SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN",
    "SBG_RULE_ADAPTER_LICENSE_BLOCKED",
    "SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
    "SBG_RULE_ADAPTER_PROVENANCE_INVALID",
    "SBG_RULE_ADAPTER_PROFILE_UNSUPPORTED",
    "SBG_RULE_ADAPTER_RULE_BODY_INVALID",
    "SBG_RULE_ADAPTER_SNAPSHOT_HASH_MISMATCH",
    "SBG_RULE_ADAPTER_SNAPSHOT_VERIFICATION_FAILED",
)


def test_package_root_does_not_export_internal_helpers() -> None:
    """The public-API contract fixup must keep ``build_message_entry`` and
    ``sort_adapter_blockers`` out of the package root. The two helpers are
    consumed via the ``.adapter_blockers`` submodule only — never via
    ``from hexagent.exchangers.shell_tube.shell_bundle_geometry import ...``.
    """
    import hexagent.exchangers.shell_tube.shell_bundle_geometry as package

    assert not hasattr(package, "build_message_entry")
    assert not hasattr(package, "sort_adapter_blockers")
    # The four-name B1 surface MUST still be present at root.
    assert hasattr(package, "AdapterFailure")
    assert hasattr(package, "RulePackAdapterBlockerCode")
    assert hasattr(package, "RULE_PACK_ADAPTER_BLOCKER_CODES")
    assert hasattr(package, "build_shell_bundle_rule_authority_snapshot")


def test_public_api_signature_is_frozen() -> None:
    """Public surface must expose the closed-set + helper names."""
    import hexagent.exchangers.shell_tube.shell_bundle_geometry.adapter_blockers as ab

    expected_names = {
        "AdapterFailure",
        "RulePackAdapterBlockerCode",
        "RULE_PACK_ADAPTER_BLOCKER_CODES",
        "RULE_PACK_ADAPTER_DEFAULT_FIELD_PATH",
        "RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY",
        "build_message_entry",
        "sort_adapter_blockers",
    }
    module_names = {n for n in dir(ab) if not n.startswith("__")}
    assert expected_names.issubset(module_names), expected_names - module_names


def test_closed_set_size_is_20() -> None:
    assert len(RULE_PACK_ADAPTER_BLOCKER_CODES) == 20
    assert len(RulePackAdapterBlockerCode.__members__) == 20


def test_closed_set_exact_equality_with_record_4() -> None:
    assert RULE_PACK_ADAPTER_BLOCKER_CODES == EXPECTED_FROZEN_CODES


def test_enum_member_set_exact_equality_with_record_4() -> None:
    enum_members = tuple(member.value for member in RulePackAdapterBlockerCode)
    assert enum_members == EXPECTED_FROZEN_CODES


def test_message_key_map_is_complete() -> None:
    assert set(RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY) == set(EXPECTED_FROZEN_CODES)
    for _key, msg_key in RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY.items():
        assert isinstance(msg_key, str) and msg_key


def test_field_path_map_is_complete() -> None:
    assert set(RULE_PACK_ADAPTER_DEFAULT_FIELD_PATH) == set(EXPECTED_FROZEN_CODES)
    for _key, path in RULE_PACK_ADAPTER_DEFAULT_FIELD_PATH.items():
        assert isinstance(path, str) and path


def test_build_message_entry_produces_five_field_payload() -> None:
    entry = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
        field_path="loaded_rule_pack.rules.rule_body",
        message_key="rule_adapter_rule_body_invalid",
        evidence_refs=("ref:b", "ref:a", "ref:b"),
        details={
            "actual_type": "dict",
            "missing_projection_fields": ["profile_id"],
        },
    )
    assert isinstance(entry, MessageEntry)
    assert entry.code == "SBG_RULE_ADAPTER_RULE_BODY_INVALID"
    assert entry.field_path == "loaded_rule_pack.rules.rule_body"
    assert entry.message_key == "rule_adapter_rule_body_invalid"
    # evidence_refs must be deduplicated and sorted Unicode-ascending.
    assert entry.evidence_refs == ("ref:a", "ref:b")
    # details is preserved (but wrapped in a FrozenJsonObject by
    # MessageEntry.__post_init__). The canonical test is to compare
    # the primitive shape via the slice-A canonical helper.
    from hexagent.exchangers.shell_tube.shell_bundle_geometry.canonical import (
        internal_frozen_to_primitive,
    )

    assert internal_frozen_to_primitive(entry.details) == {
        "actual_type": "dict",
        "missing_projection_fields": ["profile_id"],
    }


def test_build_message_entry_rejects_unknown_code() -> None:
    with pytest.raises(ValueError):
        build_message_entry(
            code="NOT_A_FROZEN_CODE",
            field_path="x",
            message_key="some_key",
        )


def test_details_must_be_canonical_json_value() -> None:
    # Binary float forbidden.
    with pytest.raises(ValueError):
        build_message_entry(
            code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
            field_path="x",
            message_key="some_key",
            details={"value": 3.14159},
        )
    # Decimal forbidden.
    from decimal import Decimal

    with pytest.raises(ValueError):
        build_message_entry(
            code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
            field_path="x",
            message_key="some_key",
            details={"value": Decimal("1.0")},
        )
    # set forbidden.
    with pytest.raises(ValueError):
        build_message_entry(
            code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
            field_path="x",
            message_key="some_key",
            details={"items": {"a", "b"}},
        )
    # non-string key forbidden.
    with pytest.raises(ValueError):
        build_message_entry(
            code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
            field_path="x",
            message_key="some_key",
            details={1: "value"},
        )


def test_evidence_refs_default_to_empty_tuple() -> None:
    entry = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
        field_path="x",
        message_key="some_key",
    )
    assert entry.evidence_refs == ()


def test_evidence_refs_must_be_non_empty_strings() -> None:
    with pytest.raises(ValueError):
        build_message_entry(
            code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
            field_path="x",
            message_key="some_key",
            evidence_refs=("",),
        )
    with pytest.raises(TypeError):
        build_message_entry(
            code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
            field_path="x",
            message_key="some_key",
            evidence_refs=(1,),
        )


def test_sort_adapter_blockers_is_deterministic_and_total() -> None:
    # Each entry has a distinct (field_path, message_key) so the
    # composite key's secondary sort kicks in. Composite key
    # ordering: (stage_rank, code, field_path, message_key, ...).
    # So sorted by field_path alphabetically ascending: a, b, z.
    first_path = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
        field_path="b",
        message_key="m",
    )
    second_path = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
        field_path="a",
        message_key="m",
    )
    third_path = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
        field_path="z",
        message_key="m",
    )
    ranks = {
        id(first_path): 14,
        id(second_path): 14,
        id(third_path): 14,
    }
    first = sort_adapter_blockers(
        [third_path, first_path, second_path],
        stage_by_identity=ranks,
    )
    second = sort_adapter_blockers(
        [second_path, third_path, first_path],
        stage_by_identity=ranks,
    )
    # Sorted by composite key (stage_rank, code, field_path, message_key, ...).
    assert first == second
    assert first == (second_path, first_path, third_path)


def test_sort_adapter_blockers_accepts_no_stage_ranks() -> None:
    a = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
        field_path="b",
        message_key="m_b",
    )
    out = sort_adapter_blockers([a])
    assert out == (a,)


def test_sort_adapter_blockers_rejects_non_sequence() -> None:
    with pytest.raises(TypeError):
        sort_adapter_blockers("not a sequence")  # type: ignore[arg-type]


def test_adapter_failure_carries_immutable_blocker_tuple() -> None:
    a = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
        field_path="x",
        message_key="m",
    )
    b = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_ID_INVALID",
        field_path="y",
        message_key="m",
    )
    ranks = {id(a): 6, id(b): 6}
    failure = AdapterFailure([b, a], stage_by_identity=ranks)
    assert isinstance(failure.blockers, tuple)
    # sorted by composite key (stage_rank, code, field_path, message_key, ...)
    assert failure.blockers == (a, b)
    # The ``blockers`` attribute is a tuple, not a list: in-place
    # mutation raises ``TypeError``. The contract is type-level
    # (tuple carries no mutating API), not dataclass-frozen.
    with pytest.raises(TypeError):
        failure.blockers[0] = a  # type: ignore[index]
    assert isinstance(failure.blockers, tuple)
    assert not isinstance(failure.blockers, list)


def test_adapter_failure_uses_no_string_only_authority() -> None:
    """The exception string is descriptive only, not the blocker signal."""
    entry = build_message_entry(
        code="SBG_RULE_ADAPTER_RULE_BODY_INVALID",
        field_path="x",
        message_key="m",
    )
    failure = AdapterFailure([entry])
    # The str is descriptive; the structured signal is ``failure.blockers``.
    assert failure.blockers == (entry,)
    # The string mentions the code for debug logging only.
    assert "SBG_RULE_ADAPTER_RULE_BODY_INVALID" in str(failure)


def test_no_string_parsing_authority() -> None:
    """No helper exposes a 'parse the exception string' API."""
    members = inspect.getmembers(
        AdapterFailure,
        predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x),
    )
    names = [name for name, _ in members]
    assert "parse" not in " ".join(names).lower()

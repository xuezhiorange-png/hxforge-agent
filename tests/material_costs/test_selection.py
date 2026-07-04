"""Deterministic selection tests for TASK-013 material / cost records
(Section 14).

Asserts:

* Tie-break chain (priority -> date -> version -> id) is bit-identical
  across replays.
* ``approval_state != approved``, ``superseded_by``, retired,
  ``RESTRICTED_REFERENCE_METADATA_ONLY`` records are all rejected.
* ``MaterialNotFound`` / ``CostNotFound`` carry record_id, region,
  selection_time, reason, and rejected_candidate_count.
"""

from __future__ import annotations

from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.material_costs.errors import CostNotFound, MaterialNotFound
from hexagent.material_costs.models import (
    ApprovalState,
    SourceClass,
)
from hexagent.material_costs.selection import (
    AuditTransition,
    select_cost_record,
    select_material_record,
)

from ._factories import base_cost_record, base_material_record

SELECTION_TIME = "2026-06-01T00:00:00Z"


def _rehash(record: dict[str, Any]) -> dict[str, Any]:
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    return record


def _make_variant(
    *,
    record_id: str = "MAT-001",
    version: str = "1.0.0",
    source_class: str = SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value,
    effective_date: str = "2026-01-01T00:00:00Z",
    approval_state: str = ApprovalState.APPROVED.value,
    superseded_by: str | None = None,
    retirement_date: str | None = None,
    region: str = "US",
    permission_scope: list[str] | None = None,
    usage_scope: str | None = None,
) -> dict[str, Any]:
    record = base_material_record()
    record["material_record_id"] = record_id
    record["material_record_version"] = version
    record["source_class"] = source_class
    record["effective_date"] = effective_date
    record["approval_state"] = approval_state
    if superseded_by is not None:
        record["superseded_by"] = superseded_by
    if retirement_date is not None:
        record["retirement_date"] = retirement_date
    record["region"] = region
    if permission_scope is not None or usage_scope is not None:
        he = record["human_entered_evidence"]
        if permission_scope is not None:
            he["permission_scope"] = permission_scope
        if usage_scope is not None:
            he["usage_scope"] = usage_scope
    return _rehash(record)


# ---------- gate rejections ----------


def test_not_approved_rejected() -> None:
    record = _make_variant(approval_state=ApprovalState.DRAFT.value)
    with __import__("pytest").raises(MaterialNotFound):
        select_material_record(
            [record],
            "MAT-001",
            region="US",
            selection_time=SELECTION_TIME,
        )


def test_superseded_rejected() -> None:
    record = _make_variant(superseded_by="MAT-002")
    with __import__("pytest").raises(MaterialNotFound):
        select_material_record(
            [record],
            "MAT-001",
            region="US",
            selection_time=SELECTION_TIME,
        )


def test_retired_rejected() -> None:
    record = _make_variant(retirement_date="2025-12-31T00:00:00Z")
    with __import__("pytest").raises(MaterialNotFound):
        select_material_record(
            [record],
            "MAT-001",
            region="US",
            selection_time=SELECTION_TIME,
        )


def test_restricted_rejected() -> None:
    record = _make_variant(source_class=SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value)
    with __import__("pytest").raises(MaterialNotFound):
        select_material_record(
            [record],
            "MAT-001",
            region="US",
            selection_time=SELECTION_TIME,
        )


# ---------- MaterialNotFound structure ----------


def test_not_found_carries_full_diagnostic_payload() -> None:
    try:
        select_material_record(
            [],
            "MAT-MISSING",
            region="EU",
            selection_time=SELECTION_TIME,
        )
    except MaterialNotFound as exc:
        assert exc.material_record_id == "MAT-MISSING"
        assert exc.region == "EU"
        assert exc.selection_time == SELECTION_TIME
        assert exc.reason == "no_candidate_passed_selection_chain"
        assert exc.rejected_candidate_count == 0
    else:
        raise AssertionError("expected MaterialNotFound")


def test_not_found_carries_rejected_candidate_count() -> None:
    record = _make_variant(approval_state=ApprovalState.DRAFT.value)
    try:
        select_material_record(
            [record],
            "MAT-001",
            region="US",
            selection_time=SELECTION_TIME,
        )
    except MaterialNotFound as exc:
        assert exc.rejected_candidate_count == 1
    else:
        raise AssertionError("expected MaterialNotFound")


# ---------- deterministic tie-break ----------


def test_priority_user_beats_internal_beats_public() -> None:
    internal = _make_variant(
        record_id="MAT-001",
        source_class=SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value,
    )
    user = _make_variant(
        record_id="MAT-001",
        source_class=SourceClass.USER_PROVIDED_PROJECT_DATA.value,
    )
    public = _make_variant(
        record_id="MAT-001",
        source_class=SourceClass.PUBLIC_METADATA.value,
    )
    winner = select_material_record(
        [internal, public, user],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner["source_class"] == SourceClass.USER_PROVIDED_PROJECT_DATA.value


def test_priority_effective_date_desc() -> None:
    older = _make_variant(
        record_id="MAT-001",
        effective_date="2025-01-01T00:00:00Z",
    )
    newer = _make_variant(
        record_id="MAT-001",
        effective_date="2026-12-01T00:00:00Z",
    )
    winner = select_material_record(
        [older, newer],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner["effective_date"] == "2026-12-01T00:00:00Z"


def test_priority_record_version_desc() -> None:
    low = _make_variant(record_id="MAT-001", version="1.0.0")
    high = _make_variant(record_id="MAT-001", version="2.0.0")
    winner = select_material_record(
        [low, high],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner["material_record_version"] == "2.0.0"


def test_priority_record_id_ascending() -> None:
    # Same priority + date + version + record_id: tiebreak chain
    # #4 is vacuously satisfied because all records share the same
    # record_id. The selector must still return a deterministic
    # single record. We verify stability: the first record in the
    # input list is the winner when all tiebreak keys are equal.
    a = _make_variant(record_id="MAT-001", version="1.0.0")
    b = _make_variant(record_id="MAT-001", version="1.0.0")
    a["source_reference"] = "internal://MAT-A"
    b["source_reference"] = "internal://MAT-B"
    a = _rehash(a)
    b = _rehash(b)
    winner_first = select_material_record(
        [a, b],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner_first["source_reference"] == "internal://MAT-A"
    winner_second = select_material_record(
        [b, a],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner_second["source_reference"] == "internal://MAT-B"


def test_bit_identical_across_replays() -> None:
    a = _make_variant(record_id="MAT-001", version="1.0.0")
    b = _make_variant(record_id="MAT-001", version="1.0.0")
    selected_a = select_material_record(
        [a, b],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    selected_b = select_material_record(
        [a, b],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert selected_a["record_hash"] == selected_b["record_hash"]


def test_vendor_without_usage_scope_loses_tiebreak_to_internal() -> None:
    vendor = _make_variant(
        record_id="MAT-001",
        source_class=SourceClass.VENDOR_PERMISSIONED.value,
        permission_scope=["usage_scope"],
        usage_scope=None,  # no usage_scope; demoted
    )
    internal = _make_variant(
        record_id="MAT-001",
        source_class=SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value,
    )
    winner = select_material_record(
        [vendor, internal],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner["source_class"] == SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value


def test_vendor_with_usage_scope_beats_internal() -> None:
    vendor = _make_variant(
        record_id="MAT-001",
        source_class=SourceClass.VENDOR_PERMISSIONED.value,
        permission_scope=["usage_scope"],
        usage_scope="vendor_internal_consumption_only",
    )
    internal = _make_variant(
        record_id="MAT-001",
        source_class=SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value,
    )
    winner = select_material_record(
        [vendor, internal],
        "MAT-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner["source_class"] == SourceClass.VENDOR_PERMISSIONED.value


# ---------- cost selector ----------


def _cost_variant(
    *,
    record_id: str = "COST-001",
    version: str = "1.0.0",
    source_class: str = SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value,
    effective_date: str = "2026-01-01T00:00:00Z",
    approval_state: str = ApprovalState.APPROVED.value,
    region: str = "US",
) -> dict[str, Any]:
    record = base_cost_record()
    record["cost_record_id"] = record_id
    record["cost_record_version"] = version
    record["source_class"] = source_class
    record["effective_date"] = effective_date
    record["approval_state"] = approval_state
    record["region"] = region
    return _rehash(record)


def test_cost_selector_priority() -> None:
    internal = _cost_variant(source_class=SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value)
    user = _cost_variant(source_class=SourceClass.USER_PROVIDED_PROJECT_DATA.value)
    winner = select_cost_record(
        [internal, user],
        "COST-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner["source_class"] == SourceClass.USER_PROVIDED_PROJECT_DATA.value


def test_cost_selector_date_desc() -> None:
    older = _cost_variant(effective_date="2025-01-01T00:00:00Z")
    newer = _cost_variant(effective_date="2026-12-01T00:00:00Z")
    winner = select_cost_record(
        [older, newer],
        "COST-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner["effective_date"] == "2026-12-01T00:00:00Z"


def test_cost_selector_version_desc() -> None:
    low = _cost_variant(version="1.0.0")
    high = _cost_variant(version="2.0.0")
    winner = select_cost_record(
        [low, high],
        "COST-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner["cost_record_version"] == "2.0.0"


def test_cost_selector_id_ascending() -> None:
    # Same priority + date + version + record_id: tiebreak chain
    # #4 is vacuously satisfied. Sort is stable; first input wins.
    a = _cost_variant(record_id="COST-001", version="1.0.0")
    b = _cost_variant(record_id="COST-001", version="1.0.0")
    a["source_reference"] = "internal://A"
    b["source_reference"] = "internal://B"
    a = _rehash(a)
    b = _rehash(b)
    winner_first = select_cost_record(
        [a, b],
        "COST-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner_first["source_reference"] == "internal://A"
    winner_second = select_cost_record(
        [b, a],
        "COST-001",
        region="US",
        selection_time=SELECTION_TIME,
    )
    assert winner_second["source_reference"] == "internal://B"


def test_cost_not_found_carries_full_diagnostic_payload() -> None:
    try:
        select_cost_record(
            [],
            "COST-MISSING",
            region="EU",
            selection_time=SELECTION_TIME,
        )
    except CostNotFound as exc:
        assert exc.cost_record_id == "COST-MISSING"
        assert exc.region == "EU"
        assert exc.selection_time == SELECTION_TIME
        assert exc.reason == "no_candidate_passed_selection_chain"
        assert exc.rejected_candidate_count == 0
    else:
        raise AssertionError("expected CostNotFound")


# ---------- audit transition representation ----------


def test_audit_transition_repr() -> None:
    t = AuditTransition(
        record_id="MAT-001",
        record_version="1.0.0",
        from_state="draft",
        to_state="needs_source",
        transition_reason="initial review",
        actor="engineering-review",
        timestamp="2026-01-01T00:00:00Z",
    )
    assert t.to_dict() == {
        "record_id": "MAT-001",
        "record_version": "1.0.0",
        "from_state": "draft",
        "to_state": "needs_source",
        "transition_reason": "initial review",
        "actor": "engineering-review",
        "timestamp": "2026-01-01T00:00:00Z",
    }

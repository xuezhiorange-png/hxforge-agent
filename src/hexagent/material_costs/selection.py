"""Deterministic material / cost record selection (Section 14).

Implements Section 14 of the TASK-013 frozen design contract
(docs/tasks/TASK-013-material-cost-data-governance.md, Frozen
Contract Authority SHA
``ee7aa092bca854316be961b536c7a121490aa385``):

1. Reject any candidate whose ``approval_state != approved``.
2. Reject any candidate whose ``superseded_by`` is populated.
3. Reject any candidate whose ``retirement_date`` (if present) is in
   the past.
4. Reject any candidate whose ``source_class`` is
   ``RESTRICTED_REFERENCE_METADATA_ONLY``.
5. Reject any candidate whose license posture forbids runtime
   consumption (RESTRICTED is the only such posture by Section 13;
   the selector also enforces the source-class rule).
6. Rank remaining candidates by source-authority priority (Section 4):
   USER > VENDOR (with usage_scope) > INTERNAL > PUBLIC.
7. Within the same priority rank, rank by ``effective_date`` DESC.
8. Within the same priority and date, rank by ``record_version``
   DESC.
9. Within the same priority, date, and version, rank by record id
   lexicographic ASC.
10. If zero candidates remain, the selection MUST fail closed with a
    structured :class:`MaterialNotFound` / :class:`CostNotFound` error
    referencing the record id, region, and time.

The selector is BIT-IDENTICAL across replays and machines, provided
the underlying catalog and selectors are bit-identical.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import cmp_to_key
from typing import Any

from hexagent.material_costs.errors import CostNotFound, MaterialNotFound
from hexagent.material_costs.models import (
    ApprovalState,
    SourceClass,
)

# Source-authority priority (Section 4 hierarchy).
# Lower numeric value = higher priority.
SOURCE_AUTHORITY_PRIORITY: dict[str, int] = {
    SourceClass.USER_PROVIDED_PROJECT_DATA.value: 0,
    SourceClass.VENDOR_PERMISSIONED.value: 1,
    SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value: 2,
    SourceClass.PUBLIC_METADATA.value: 3,
}

# A candidate's priority rank in the deterministic tie-break chain.
# RESTRICTED is assigned an infinite-rank sentinel so it always loses
# any tie (and is explicitly rejected upstream of the tie-break).
_RESTRICTED_PRIORITY_SENTINEL = 2**31

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _record_id(record: dict[str, Any], *, kind: str) -> str:
    if kind == "material":
        return str(record.get("material_record_id", ""))
    return str(record.get("cost_record_id", ""))


def _record_version(record: dict[str, Any]) -> str:
    if "material_record_version" in record:
        return str(record.get("material_record_version", ""))
    return str(record.get("cost_record_version", ""))


def _effective_date(record: dict[str, Any]) -> str:
    return str(record.get("effective_date", ""))


def _candidate_region(record: dict[str, Any]) -> str:
    return str(record.get("region", ""))


def _is_retired(record: dict[str, Any], selection_time: str) -> bool:
    retirement = record.get("retirement_date")
    if retirement is None:
        return False
    if not isinstance(retirement, str) or not _DATE_RE.match(retirement):
        return False
    # Lexicographic comparison is valid for ISO-8601 UTC "Z" strings.
    return retirement < selection_time


def _has_usage_scope(record: dict[str, Any]) -> bool:
    he = record.get("human_entered_evidence")
    if not isinstance(he, dict):
        return False
    usage = he.get("usage_scope")
    return isinstance(usage, str) and bool(usage.strip())


def _license_posture_allows_runtime_consumption(record: dict[str, Any]) -> bool:
    """Section 14 gate #5 — license posture forbids runtime consumption.

    * ``RESTRICTED_REFERENCE_METADATA_ONLY`` is metadata-only and is
      NEVER consumable at runtime (Section 9).
    * ``VENDOR_PERMISSIONED`` is consumable at runtime ONLY if it
      records a non-empty ``usage_scope`` in
      ``human_entered_evidence`` (Section 4 / 5.5 rule #2 / 6.4
      rule #2). The presence of ``permission_scope`` alone is NOT
      sufficient — runtime consumption must be explicitly scoped.
    * All other source classes whose source-authority rank is
      defined (USER / INTERNAL / PUBLIC) are consumable at runtime.

    This gate is independent of priority demotion: a vendor without
    ``usage_scope`` MUST be rejected before it can be ranked.
    """
    source_class = str(record.get("source_class", ""))
    if source_class == SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value:
        return False
    if source_class == SourceClass.VENDOR_PERMISSIONED.value:
        return _has_usage_scope(record)
    return source_class in SOURCE_AUTHORITY_PRIORITY


def _vendor_priority(record: dict[str, Any]) -> int:
    """Vendor may only consume at USER priority if it carries usage_scope;
    otherwise it is demoted to RESTRICTED-equivalent (sentinel).

    Note: callers MUST also pass :func:`_candidate_passes_gates`
    (which calls :func:`_license_posture_allows_runtime_consumption`)
    before ranking — the priority demotion alone is not sufficient
    to fail-closed against a sole vendor-without-usage_scope
    candidate (Section 14 gate #5).
    """
    if not _has_usage_scope(record):
        return _RESTRICTED_PRIORITY_SENTINEL
    return SOURCE_AUTHORITY_PRIORITY[SourceClass.VENDOR_PERMISSIONED.value]


def _candidate_priority(record: dict[str, Any]) -> int:
    source_class = str(record.get("source_class", ""))
    if source_class == SourceClass.VENDOR_PERMISSIONED.value:
        return _vendor_priority(record)
    return SOURCE_AUTHORITY_PRIORITY.get(source_class, _RESTRICTED_PRIORITY_SENTINEL)


def _candidate_passes_gates(
    record: dict[str, Any],
    *,
    region: str,
    selection_time: str,
) -> bool:
    """Apply gates #1 - #5 from Section 14."""
    if record.get("approval_state") != ApprovalState.APPROVED.value:
        return False
    if record.get("superseded_by"):
        return False
    if _is_retired(record, selection_time):
        return False
    if record.get("source_class") == SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value:
        return False
    # Section 14 gate #5 — license posture forbids runtime consumption
    # for RESTRICTED_REFERENCE_METADATA_ONLY or for VENDOR_PERMISSIONED
    # without usage_scope. Reject BEFORE ranking so a sole
    # vendor-without-usage_scope candidate cannot be selected.
    if not _license_posture_allows_runtime_consumption(record):
        return False
    # Region must match the requested region.
    return _candidate_region(record) == region


def _build_comparator(*, kind: str) -> Callable[[dict[str, Any], dict[str, Any]], int]:
    """Build a Section-14 comparator for the given record kind.

    Sort order (ascending = "best first"):
    (1) source-authority priority ASC (lower = better)
    (2) effective_date DESC (newer first)
    (3) record_version DESC (newer first)
    (4) record_id ASC (lexicographic)
    """

    def _get_id(rec: dict[str, Any]) -> str:
        return _record_id(rec, kind=kind)

    def compare(a: dict[str, Any], b: dict[str, Any]) -> int:
        # 1. priority ASC
        pa = _candidate_priority(a)
        pb = _candidate_priority(b)
        if pa != pb:
            return -1 if pa < pb else 1

        # 2. effective_date DESC
        da = _effective_date(a)
        db = _effective_date(b)
        if da != db:
            return -1 if da > db else 1

        # 3. record_version DESC
        va = _record_version(a)
        vb = _record_version(b)
        if va != vb:
            return -1 if va > vb else 1

        # 4. record_id ASC
        ia = _get_id(a)
        ib = _get_id(b)
        if ia != ib:
            return -1 if ia < ib else 1
        return 0

    return compare


def select_material_record(
    catalog: list[dict[str, Any]],
    material_record_id: str,
    *,
    region: str,
    selection_time: str,
) -> dict[str, Any]:
    """Deterministically select the best material record from
    ``catalog`` for the given ``material_record_id``, ``region``, and
    ``selection_time``.

    Raises :class:`MaterialNotFound` if no candidate satisfies the
    Section 14 deterministic algorithm.
    """
    if not isinstance(selection_time, str) or not _DATE_RE.match(selection_time):
        raise MaterialNotFound(
            material_record_id,
            region=region,
            selection_time=selection_time,
            reason="invalid_selection_time_format",
        )

    matching = [
        rec
        for rec in catalog
        if isinstance(rec, dict)
        and _record_id(rec, kind="material") == material_record_id
        and _candidate_region(rec) == region
    ]

    rejected_count = len(matching)
    passing = [
        rec
        for rec in matching
        if _candidate_passes_gates(rec, region=region, selection_time=selection_time)
    ]

    if not passing:
        raise MaterialNotFound(
            material_record_id,
            region=region,
            selection_time=selection_time,
            reason="no_candidate_passed_selection_chain",
            rejected_candidate_count=rejected_count,
        )

    ordered = sorted(passing, key=cmp_to_key(_build_comparator(kind="material")))
    return ordered[0]


def select_cost_record(
    catalog: list[dict[str, Any]],
    cost_record_id: str,
    *,
    region: str,
    selection_time: str,
) -> dict[str, Any]:
    """Deterministically select the best cost record from ``catalog``.

    Raises :class:`CostNotFound` if no candidate satisfies the Section
    14 deterministic algorithm.
    """
    if not isinstance(selection_time, str) or not _DATE_RE.match(selection_time):
        raise CostNotFound(
            cost_record_id,
            region=region,
            selection_time=selection_time,
            reason="invalid_selection_time_format",
        )

    matching = [
        rec
        for rec in catalog
        if isinstance(rec, dict)
        and _record_id(rec, kind="cost") == cost_record_id
        and _candidate_region(rec) == region
    ]

    rejected_count = len(matching)
    passing = [
        rec
        for rec in matching
        if _candidate_passes_gates(rec, region=region, selection_time=selection_time)
    ]

    if not passing:
        raise CostNotFound(
            cost_record_id,
            region=region,
            selection_time=selection_time,
            reason="no_candidate_passed_selection_chain",
            rejected_candidate_count=rejected_count,
        )

    ordered = sorted(passing, key=cmp_to_key(_build_comparator(kind="cost")))
    return ordered[0]


# Module-level sentinel for typing of the helper above.
__all__ = [
    "select_cost_record",
    "select_material_record",
]


# ---------------------------------------------------------------------------
# Audit transition representation (Section 17 / Section 6.9 of the task).
# ---------------------------------------------------------------------------


class AuditTransition:
    """In-memory record of a state transition (Section 17).

    No persistence layer is authorized (Section 21 explicit
    non-goal). Callers may collect these into a list for tests /
    in-process audit but MUST NOT persist them via any database.
    """

    __slots__ = (
        "record_id",
        "record_version",
        "from_state",
        "to_state",
        "transition_reason",
        "actor",
        "timestamp",
    )

    def __init__(
        self,
        *,
        record_id: str,
        record_version: str,
        from_state: str,
        to_state: str,
        transition_reason: str,
        actor: str,
        timestamp: str,
    ) -> None:
        self.record_id = record_id
        self.record_version = record_version
        self.from_state = from_state
        self.to_state = to_state
        self.transition_reason = transition_reason
        self.actor = actor
        self.timestamp = timestamp

    def to_dict(self) -> dict[str, str]:
        return {
            "record_id": self.record_id,
            "record_version": self.record_version,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "transition_reason": self.transition_reason,
            "actor": self.actor,
            "timestamp": self.timestamp,
        }

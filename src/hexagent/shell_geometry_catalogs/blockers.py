"""TASK-023 — Approved Shell Geometry Catalog blocker taxonomy.

This module is the single source of truth for the closed 27-code
blocker taxonomy that the TASK-023 framework emits. It is intentionally
separate from ``catalog.py`` so the parser layer cannot introduce
unsanctioned codes.

The blocker codes are frozen at the values specified in the merged
TASK-023 design contract §10, Issue #151, and Issue #152 Comment
``4970130136`` (TASK-023 Design Amendment 001 Option B). The TASK-023
``catalog.parse_shell_geometry_catalog`` performs the validation
pipeline in design-contract occurrence order; this module exposes
the closed 27-code taxonomy, the default ``message_key`` /
``default_field_path`` informational maps per code, the ordered
blocker-entry helpers, and the composite-sort key required by design
contract §6/§11.

## Authority — Option B (Amendment 001)

The taxonomy was amended from 25 codes to exactly 27 codes by
Charles Decision Comment ``4970130136`` on Issue #152. The two new
codes ``SGC_PERMISSION_DUPLICATE_ID`` and ``SGC_PROVENANCE_DUPLICATE_ID``
are inserted after ``SGC_CATALOG_HASH_MISMATCH`` and before
``SGC_RECORD_NOT_FOUND`` / ``SGC_SELECTION_NOT_APPROVED``. No alias,
reserved code, warning variant, generic fallback mapping, or
execution-side inferred substitute is permitted.

## Stage rank authority (Amendment 001 §3)

``stage_rank`` binds each **validation occurrence**, not the blocker
code globally. The same code may be emitted at different validation
occurrences and therefore may carry different stage ranks. Every
blocker construction call MUST explicitly pass the actual
occurrence stage rank. The module therefore refuses to expose a
code-derived stage-rank lookup table, an implicit/default rank, or
any zero-rank fallback.

Forbidden:

* ``SHELL_GEOMETRY_CATALOG_STAGE_RANK_BY_CODE`` (and synonyms)
* any code-derived stage-rank mapping
* implicit / default / zero stage-rank fallback

## Frozen public surface

* ``SHELL_GEOMETRY_CATALOG_BLOCKER_CODES`` — the exact 27-code tuple
* ``ShellGeometryCatalogBlockerCode`` — the exact 27-code enum
* ``SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY`` — informational
* ``SHELL_GEOMETRY_CATALOG_DEFAULT_FIELD_PATH`` — informational
* ``ShellGeometryCatalogBlockerEntry`` — ordered entry dataclass
* ``deep_freeze_details`` — recursive immutability projection
* ``freeze_evidence_refs`` — evidence_refs tuple copy
* ``thaw_for_canonical_json`` — recursive plain-JSON projection
* ``composite_order_key`` / ``sort_blockers`` — design §6 ordering

The module forbids filesystem / network / database / environment /
runtime-now / locale / registry / dynamic-import / executable-
deserialization operations. It only imports stdlib + the canonical
SHA-256 helper.
"""

from __future__ import annotations

import enum
import types as _types  # noqa: I001  -- explicit import for MappingProxyType thaw
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, cast

from hexagent.canonical_json import canonical_sha256

# ---------------------------------------------------------------------------
# Frozen closed-set of exactly 27 TASK-023 shell-geometry-catalog blocker
# codes (Amendment 001 Option B). Order is the canonical token order from
# design contract §10 / Issue #151 with the two new amendment-001 codes
# inserted after ``SGC_CATALOG_HASH_MISMATCH`` and before the two
# selection-only codes. Any extension requires a separate Charles
# authorization — round 4 (Option B) hard-frozen this tuple ordering.
# ---------------------------------------------------------------------------

SHELL_GEOMETRY_CATALOG_BLOCKER_CODES: Final[tuple[str, ...]] = (
    "SGC_RAW_TYPE_INVALID",
    "SGC_UNKNOWN_FIELD",
    "SGC_SCHEMA_VERSION_UNSUPPORTED",
    "SGC_CATALOG_ID_INVALID",
    "SGC_CATALOG_VERSION_INVALID",
    "SGC_PROFILE_UNSUPPORTED",
    "SGC_CATALOG_AUTHORITY_INVALID",
    "SGC_RECORDS_INVALID",
    "SGC_RECORD_ID_INVALID",
    "SGC_RECORD_DUPLICATE_ID",
    "SGC_GEOMETRY_TYPE_INVALID",
    "SGC_REVISION_INVALID",
    "SGC_APPROVAL_STATE_INVALID",
    "SGC_RECORD_UNAPPROVED",
    "SGC_SHELL_INSIDE_DIAMETER_INVALID",
    "SGC_SOURCE_BINDING_INCOMPLETE",
    "SGC_SOURCE_CLASS_INVALID",
    "SGC_LICENSE_BLOCKED",
    "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
    "SGC_PROVENANCE_INCOMPLETE",
    "SGC_EVIDENCE_REFS_INVALID",
    "SGC_RECORD_HASH_MISMATCH",
    "SGC_CATALOG_HASH_MISMATCH",
    "SGC_PERMISSION_DUPLICATE_ID",
    "SGC_PROVENANCE_DUPLICATE_ID",
    "SGC_RECORD_NOT_FOUND",
    "SGC_SELECTION_NOT_APPROVED",
)

assert len(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES) == 27, (
    "SHELL_GEOMETRY_CATALOG_BLOCKER_CODES must contain exactly 27 entries "
    "after Amendment 001 Option B."
)


class ShellGeometryCatalogBlockerCode(enum.StrEnum):
    """Closed set of TASK-023 shell-geometry-catalog blocker codes.

    Each member maps to the exact frozen token recorded in the
    design contract §10 (with Amendment 001 Option B additions
    ``SGC_PERMISSION_DUPLICATE_ID`` and ``SGC_PROVENANCE_DUPLICATE_ID``
    inserted after ``SGC_CATALOG_HASH_MISMATCH``). No reserved alias,
    generic fallback, warning repurposing, or fall-through code is
    permitted. The ``.value`` of each member equals the corresponding
    token in ``SHELL_GEOMETRY_CATALOG_BLOCKER_CODES``.
    """

    SGC_RAW_TYPE_INVALID = "SGC_RAW_TYPE_INVALID"
    SGC_UNKNOWN_FIELD = "SGC_UNKNOWN_FIELD"
    SGC_SCHEMA_VERSION_UNSUPPORTED = "SGC_SCHEMA_VERSION_UNSUPPORTED"
    SGC_CATALOG_ID_INVALID = "SGC_CATALOG_ID_INVALID"
    SGC_CATALOG_VERSION_INVALID = "SGC_CATALOG_VERSION_INVALID"
    SGC_PROFILE_UNSUPPORTED = "SGC_PROFILE_UNSUPPORTED"
    SGC_CATALOG_AUTHORITY_INVALID = "SGC_CATALOG_AUTHORITY_INVALID"
    SGC_RECORDS_INVALID = "SGC_RECORDS_INVALID"
    SGC_RECORD_ID_INVALID = "SGC_RECORD_ID_INVALID"
    SGC_RECORD_DUPLICATE_ID = "SGC_RECORD_DUPLICATE_ID"
    SGC_GEOMETRY_TYPE_INVALID = "SGC_GEOMETRY_TYPE_INVALID"
    SGC_REVISION_INVALID = "SGC_REVISION_INVALID"
    SGC_APPROVAL_STATE_INVALID = "SGC_APPROVAL_STATE_INVALID"
    SGC_RECORD_UNAPPROVED = "SGC_RECORD_UNAPPROVED"
    SGC_SHELL_INSIDE_DIAMETER_INVALID = "SGC_SHELL_INSIDE_DIAMETER_INVALID"
    SGC_SOURCE_BINDING_INCOMPLETE = "SGC_SOURCE_BINDING_INCOMPLETE"
    SGC_SOURCE_CLASS_INVALID = "SGC_SOURCE_CLASS_INVALID"
    SGC_LICENSE_BLOCKED = "SGC_LICENSE_BLOCKED"
    SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE = "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE"
    SGC_PROVENANCE_INCOMPLETE = "SGC_PROVENANCE_INCOMPLETE"
    SGC_EVIDENCE_REFS_INVALID = "SGC_EVIDENCE_REFS_INVALID"
    SGC_RECORD_HASH_MISMATCH = "SGC_RECORD_HASH_MISMATCH"
    SGC_CATALOG_HASH_MISMATCH = "SGC_CATALOG_HASH_MISMATCH"
    SGC_PERMISSION_DUPLICATE_ID = "SGC_PERMISSION_DUPLICATE_ID"
    SGC_PROVENANCE_DUPLICATE_ID = "SGC_PROVENANCE_DUPLICATE_ID"
    SGC_RECORD_NOT_FOUND = "SGC_RECORD_NOT_FOUND"
    SGC_SELECTION_NOT_APPROVED = "SGC_SELECTION_NOT_APPROVED"


def _enum_matches_tuple() -> None:
    """Assert the public enum members enumerate in exactly the same
    order as ``SHELL_GEOMETRY_CATALOG_BLOCKER_CODES``. Both tuple-position
    and tuple-member equality are required by Amendment 001 §2.
    """
    members = list(ShellGeometryCatalogBlockerCode.__members__.values())
    enum_values = tuple(members[i].value for i in range(len(members)))
    assert enum_values == SHELL_GEOMETRY_CATALOG_BLOCKER_CODES, (
        "ShellGeometryCatalogBlockerCode enum values must match "
        "SHELL_GEOMETRY_CATALOG_BLOCKER_CODES tuple position-by-position."
    )


_enum_matches_tuple()


# ---------------------------------------------------------------------------
# Informational defaults (NOT stage-rank authority)
#
# These maps record the design-contract §10 default message_key and
# field_path per closed-set code. They are informational only — they
# carry no stage-rank information, which Amendment 001 forbids from
# being code-derived.
# ---------------------------------------------------------------------------

SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY: Final[Mapping[str, str]] = {
    "SGC_RAW_TYPE_INVALID": "sgc_raw_type_invalid",
    "SGC_UNKNOWN_FIELD": "sgc_unknown_field",
    "SGC_SCHEMA_VERSION_UNSUPPORTED": "sgc_schema_version_unsupported",
    "SGC_CATALOG_ID_INVALID": "sgc_catalog_id_invalid",
    "SGC_CATALOG_VERSION_INVALID": "sgc_catalog_version_invalid",
    "SGC_PROFILE_UNSUPPORTED": "sgc_profile_unsupported",
    "SGC_CATALOG_AUTHORITY_INVALID": "sgc_catalog_authority_invalid",
    "SGC_RECORDS_INVALID": "sgc_records_invalid",
    "SGC_RECORD_ID_INVALID": "sgc_record_id_invalid",
    "SGC_RECORD_DUPLICATE_ID": "sgc_record_duplicate_id",
    "SGC_GEOMETRY_TYPE_INVALID": "sgc_geometry_type_invalid",
    "SGC_REVISION_INVALID": "sgc_revision_invalid",
    "SGC_APPROVAL_STATE_INVALID": "sgc_approval_state_invalid",
    "SGC_RECORD_UNAPPROVED": "sgc_record_unapproved",
    "SGC_SHELL_INSIDE_DIAMETER_INVALID": "sgc_shell_inside_diameter_invalid",
    "SGC_SOURCE_BINDING_INCOMPLETE": "sgc_source_binding_incomplete",
    "SGC_SOURCE_CLASS_INVALID": "sgc_source_class_invalid",
    "SGC_LICENSE_BLOCKED": "sgc_license_blocked",
    "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE": "sgc_vendor_permission_scope_incomplete",
    "SGC_PROVENANCE_INCOMPLETE": "sgc_provenance_incomplete",
    "SGC_EVIDENCE_REFS_INVALID": "sgc_evidence_refs_invalid",
    "SGC_RECORD_HASH_MISMATCH": "sgc_record_hash_mismatch",
    "SGC_CATALOG_HASH_MISMATCH": "sgc_catalog_hash_mismatch",
    "SGC_PERMISSION_DUPLICATE_ID": "sgc_permission_duplicate_id",
    "SGC_PROVENANCE_DUPLICATE_ID": "sgc_provenance_duplicate_id",
    "SGC_RECORD_NOT_FOUND": "sgc_record_not_found",
    "SGC_SELECTION_NOT_APPROVED": "sgc_selection_not_approved",
}

SHELL_GEOMETRY_CATALOG_DEFAULT_FIELD_PATH: Final[Mapping[str, str]] = {
    "SGC_RAW_TYPE_INVALID": "raw_catalog",
    "SGC_UNKNOWN_FIELD": "raw_catalog",
    "SGC_SCHEMA_VERSION_UNSUPPORTED": "raw_catalog.schema_version",
    "SGC_CATALOG_ID_INVALID": "raw_catalog.catalog_id",
    "SGC_CATALOG_VERSION_INVALID": "raw_catalog.catalog_version",
    "SGC_PROFILE_UNSUPPORTED": "raw_catalog.profile_id",
    "SGC_CATALOG_AUTHORITY_INVALID": "raw_catalog.authority",
    "SGC_RECORDS_INVALID": "raw_catalog.records",
    "SGC_RECORD_ID_INVALID": "raw_catalog.records.geometry_id",
    "SGC_RECORD_DUPLICATE_ID": "raw_catalog.records.geometry_id",
    "SGC_GEOMETRY_TYPE_INVALID": "raw_catalog.records.geometry_type",
    "SGC_REVISION_INVALID": "raw_catalog.records.revision",
    "SGC_APPROVAL_STATE_INVALID": "raw_catalog.records.approval_state",
    "SGC_RECORD_UNAPPROVED": "raw_catalog.records.approval_state",
    "SGC_SHELL_INSIDE_DIAMETER_INVALID": "raw_catalog.records.shell_inside_diameter_m",
    "SGC_SOURCE_BINDING_INCOMPLETE": "raw_catalog.records.source_binding",
    "SGC_SOURCE_CLASS_INVALID": "raw_catalog.records.source_class",
    "SGC_LICENSE_BLOCKED": "raw_catalog.records.license_evidence",
    "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE": "raw_catalog.records.permission_evidence_refs",
    "SGC_PROVENANCE_INCOMPLETE": "raw_catalog.records.provenance_edge_ids",
    "SGC_EVIDENCE_REFS_INVALID": "raw_catalog.records.evidence_refs",
    "SGC_RECORD_HASH_MISMATCH": "raw_catalog.records.record_hash",
    "SGC_CATALOG_HASH_MISMATCH": "raw_catalog.catalog_hash",
    "SGC_PERMISSION_DUPLICATE_ID": "evidence_bundle.permission_evidence",
    "SGC_PROVENANCE_DUPLICATE_ID": "evidence_bundle.provenance_edges",
    "SGC_RECORD_NOT_FOUND": "geometry_id",
    "SGC_SELECTION_NOT_APPROVED": "geometry_id",
}


# ---------------------------------------------------------------------------
# Hard upper bound for any parser-pipeline stage rank.
#
# This is NOT a code→rank map. It is a single absolute ceiling used only
# to validate caller-supplied ranks. No constant maps ``code`` to a rank.
# ---------------------------------------------------------------------------
_MAX_STAGE_RANK: Final[int] = 20
_MIN_STAGE_RANK: Final[int] = 1


# ---------------------------------------------------------------------------
# Deep-freeze helpers for blocker payloads
# ---------------------------------------------------------------------------


def _deep_freeze_value(value: Any) -> Any:
    """Recursively freeze a value into immutable primitives.

    * nested mappings are converted to a ``MappingProxyType`` over a
      recursive copy (the surface mapping is read-only via proxy);
    * nested sequences (``list`` / ``tuple``) become a tuple of
      recursively-frozen values;
    * ``None`` is preserved (so ``details is None`` continues to hash
      as JSON ``null``);
    * JSON scalar primitives (``str`` / ``int`` / ``float`` / ``bool``)
      are returned unchanged.

    ``set`` / ``frozenset`` / non-Mapping / non-Sequence custom objects
    (including ``Decimal`` and ``datetime``) are rejected up front via
    :class:`TypeError` — Amendment 001 §7 forbids canonical-JSON
    non-compliance from leaking past blocker construction.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _types.MappingProxyType({str(k): _deep_freeze_value(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze_value(v) for v in value)
    # Reject anything else — set/frozenset/custom objects/Decimal/datetime.
    raise TypeError(
        "blocker details must be built from dict/list/tuple/scalar primitives; "
        f"got {type(value).__name__}"
    )


def deep_freeze_details(
    details: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """Deep-freeze a ``details`` mapping for a blocker entry.

    Returns a new mapping whose nested mutable layers (mappings / lists
    / tuples) are themselves immutable. Tests assert that mutating
    the caller's original dict/list does NOT change this frozen
    snapshot. ``None`` is preserved so ``details None`` continues to
    hash as JSON ``null``. ``set`` / ``frozenset`` / custom objects /
    ``Decimal`` / ``datetime`` / non-string keys raise :class:`TypeError`
    at construction time per Amendment 001 §7.
    """
    if details is None:
        return None
    if not isinstance(details, Mapping):
        raise TypeError("details must be a Mapping or None")
    frozen = _deep_freeze_value(details)
    if not isinstance(frozen, Mapping):
        # _deep_freeze_value always returns MappingProxyType for a Mapping
        # input; the redundant isinstance check guards future drift.
        raise TypeError("details freeze invariant violated")
    return cast(Mapping[str, Any], frozen)


def freeze_evidence_refs(
    evidence_refs: Sequence[str],
) -> tuple[str, ...]:
    """Copy a ``Sequence[str]`` into an immutable tuple.

    The conversion preserves duplicates and ordering but rejects any
    non-string entry. Used by ``ShellGeometryCatalogBlockerEntry`` and
    independently by ``catalog.py`` so the public parser cannot leak a
    mutable list back to callers.
    """
    if not isinstance(evidence_refs, Sequence) or isinstance(evidence_refs, str):
        raise TypeError("evidence_refs must be a Sequence[str], not str")
    out: list[str] = []
    for entry in evidence_refs:
        if not isinstance(entry, str) or not entry:
            raise TypeError("evidence_refs entries must be non-empty strings")
        out.append(entry)
    return tuple(out)


def thaw_for_canonical_json(value: Any) -> Any:
    """Recursively project an immutable snapshot to plain JSON values.

    Required by Amendment 001 §4: canonical SHA-256 hashing must be
    computed on recursively thawed plain JSON values — never on
    ``MappingProxyType``, ``tuple``, ``set``, ``frozenset``, custom
    objects, ``bytes``, or ``Decimal``. The thawed projection must be
    semantically identical to the immutable public snapshot so the
    composite order key is stable across attempts at caller mutation.

    ``None`` is preserved as ``None``; JSON scalars pass through
    unchanged.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): thaw_for_canonical_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [thaw_for_canonical_json(v) for v in value]
    if isinstance(value, tuple):
        return [thaw_for_canonical_json(v) for v in value]
    raise TypeError(
        "thaw_for_canonical_json received a non-JSON-compatible value "
        f"({type(value).__name__}); Amendment 001 §4 forbids raw "
        "MappingProxyType/tuple/set/custom-object/bytes/Decimal from "
        "entering canonical_json"
    )


# ---------------------------------------------------------------------------
# Ordered blocker entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShellGeometryCatalogBlockerEntry:
    """One ordered blocker entry for the TASK-023 shell-geometry catalog.

    ``stage_rank`` is REQUIRED at construction and is NOT a default field.
    It binds the validation occurrence that emitted this entry, not the
    blocker code globally. The dataclass will not infer the rank from
    the code and will reject a rank outside ``[1, 20]`` or below
    ``_MIN_STAGE_RANK``. Amendment 001 §3 forbids code-derived or
    implicit rank fallbacks.
    """

    code: str
    field_path: str
    message_key: str
    stage_rank: int
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise ValueError("code must be non-empty string")
        if self.code not in SHELL_GEOMETRY_CATALOG_BLOCKER_CODES:
            raise ValueError(f"code {self.code!r} is not a frozen TASK-023 blocker code")
        if not isinstance(self.field_path, str) or not self.field_path:
            raise ValueError("field_path must be non-empty string")
        if not isinstance(self.message_key, str) or not self.message_key:
            raise ValueError("message_key must be non-empty string")
        if not isinstance(self.stage_rank, int) or isinstance(self.stage_rank, bool):
            raise ValueError("stage_rank must be a non-bool integer")
        if self.stage_rank < _MIN_STAGE_RANK or self.stage_rank > _MAX_STAGE_RANK:
            raise ValueError(
                f"stage_rank {self.stage_rank} out of valid "
                f"[{_MIN_STAGE_RANK}, {_MAX_STAGE_RANK}] range"
            )
        if not isinstance(self.evidence_refs, tuple):
            raise ValueError("evidence_refs must be tuple")
        for entry in self.evidence_refs:
            if not isinstance(entry, str) or not entry:
                raise ValueError("evidence_refs entries must be non-empty strings")
        # details must already be deep-frozen BEFORE the dataclass
        # construction. ``deep_freeze_details`` enforces the set /
        # frozenset / custom-object / Decimal / datetime rejection
        # required by Amendment 001 §7. Do NOT silently coerce.
        if self.details is not None and not isinstance(self.details, Mapping):
            raise ValueError("details must be a Mapping or None")


# ---------------------------------------------------------------------------
# Deterministic ordering helpers
# ---------------------------------------------------------------------------


def _canonical_details_hash(details: Mapping[str, Any] | None) -> str:
    """Return canonical-JSON hash of ``details``.

    ``details is None`` MUST hash as the JSON literal ``null``
    (4-byte lowercase ``null``). The blocker ordering contract
    requires ``details=None`` and ``details={}`` to sort separately,
    which is only achievable when ``None`` hashes as ``null``. The
    payload is recursively thawed via ``thaw_for_canonical_json``
    before being passed to ``canonical_sha256`` (Amendment 001 §4).
    """
    import hashlib
    import json as _json

    if details is None:
        return hashlib.sha256(_json.dumps(None).encode("utf-8")).hexdigest()
    if not isinstance(details, Mapping):
        raise TypeError("details must be a Mapping or None")
    thawed = thaw_for_canonical_json(details)
    return canonical_sha256(thawed)


def _canonical_evidence_refs_hash(
    evidence_refs: Sequence[str],
) -> str:
    """Return SHA-256 of the canonical JSON of the RAW ``evidence_refs``
    array (not wrapped in ``{"refs": [...]}`).

    Per contract, two blockers with distinct evidence_refs sequences
    MUST sort deterministically and distinct from each other; we hash
    the list-of-strings via RFC 8785 directly.
    """
    import hashlib

    import rfc8785

    payload_bytes = rfc8785.dumps(list(evidence_refs))
    return hashlib.sha256(payload_bytes).hexdigest()


def composite_order_key(
    entry: ShellGeometryCatalogBlockerEntry,
) -> tuple[int, str, str, str, str, str]:
    """Composite ordering key per Amendment 001 §3 / design contract §6.

    The stage_rank is read from the entry's own field; no external
    identity→rank mapping is consulted.
    """
    return (
        entry.stage_rank,
        entry.code,
        entry.field_path,
        entry.message_key,
        _canonical_details_hash(entry.details),
        _canonical_evidence_refs_hash(entry.evidence_refs),
    )


def sort_blockers(
    entries: Sequence[ShellGeometryCatalogBlockerEntry],
) -> tuple[ShellGeometryCatalogBlockerEntry, ...]:
    """Apply design contract §6 composite ordering using each entry's
    internal ``stage_rank``. No external identity→rank mapping is used.
    """
    if not isinstance(entries, Sequence):
        raise TypeError("entries must be a Sequence[ShellGeometryCatalogBlockerEntry]")
    for entry in entries:
        if not isinstance(entry, ShellGeometryCatalogBlockerEntry):
            raise TypeError("every entry must be a ShellGeometryCatalogBlockerEntry")
    return tuple(sorted(entries, key=composite_order_key))

"""TASK-023 — Approved Shell Geometry Catalog blocker taxonomy.

This module is the single source of truth for the closed 25-code
blocker taxonomy that the TASK-023 framework emits. It is intentionally
separate from ``catalog.py`` so the parser layer cannot introduce
unsanctioned codes.

The blocker codes are frozen at the values specified in the merged
TASK-023 design contract §10 and Issue #151. The TASK-023
``catalog.parse_shell_geometry_catalog`` performs the validation
pipeline in design-contract order; this module exposes the
closed 25-code taxonomy, an **authoritative stage rank** for every
code based on design contract §11, plus minimal ordered blocker-entry
helpers and the composite-sort key required by design contract §6/§11.

Every blocker entry MUST carry its real internal ``stage_rank`` —
the parser layer MUST NOT default stage_rank to 0; round-3 fixup
established that ``ShellGeometryCatalogFailure`` reordering must not
silently fall back to a 0-rank bucket.

The module forbids filesystem / network / database / environment /
runtime-now / locale / registry / dynamic-import / executable-
deserialization operations. It only imports stdlib + the canonical
SHA-256 helper. The TASK-023 framework imports the sorted-blocker
helpers defined here to enforce the composite ordering key.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, cast

from hexagent.canonical_json import canonical_sha256

# Frozen closed-set of exactly 25 TASK-023 shell-geometry-catalog
# blocker codes. Order is the canonical token order from the merged
# design contract §10 and Issue #151 and MUST be preserved verbatim —
# any extension requires a separate Charles authorization.
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
    "SGC_RECORD_NOT_FOUND",
    "SGC_SELECTION_NOT_APPROVED",
)

assert len(SHELL_GEOMETRY_CATALOG_BLOCKER_CODES) == 25  # hard invariant


class ShellGeometryCatalogBlockerCode(enum.StrEnum):
    """Closed set of TASK-023 shell-geometry-catalog blocker codes.

    Each member maps to the exact frozen token recorded in the
    design contract §10. No reserved alias, generic fallback, warning
    repurposing or fall-through code is permitted.
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
    SGC_RECORD_NOT_FOUND = "SGC_RECORD_NOT_FOUND"
    SGC_SELECTION_NOT_APPROVED = "SGC_SELECTION_NOT_APPROVED"


# ---------------------------------------------------------------------------
# Authoritative stage rank per design contract §11
# ---------------------------------------------------------------------------
#
# The §11 parser pipeline stages are:
#   1. raw types                            (stage_rank 1)
#   2. exact top fields                     (stage_rank 2)
#   3. schemas/profiles/IDs/versions/authority (stage_rank 3)
#   4. bundle approval / TASK-012 hash / bundle hash (stage_rank 4)
#   5. permission snapshots                 (stage_rank 5)
#   6. provenance snapshots                 (stage_rank 6)
#   7. records array                        (stage_rank 7)
#   8. record fields (identity/duplicates/type/profile/revision) (stage_rank 8)
#   9. approval lexical                     (stage_rank 9)
#  10. non-approved rejection               (stage_rank 10)
#  11. decimal                              (stage_rank 11)
#  12. source binding                       (stage_rank 12)
#  13. source class / license               (stage_rank 13)
#  14. permission / provenance resolution + local usage gate (stage_rank 14)
#  15. evidence arrays                      (stage_rank 15)
#  16. record hashes                        (stage_rank 16)
#  17. record ordering                      (stage_rank 17)
#  18. catalog-bundle binding               (stage_rank 18)
#  19. catalog hash                         (stage_rank 19)
#  20. selection stages                     (stage_rank 20)
#
# Each blocker code below maps to exactly one stage. Selection codes
# (SGC_RECORD_NOT_FOUND, SGC_SELECTION_NOT_APPROVED) are stage 20.
# Round 3 fixup hardened this map — every parser-level _make_entry call
# binds its code to its declared stage; no blocker enters the failure
# pool with a default rank 0.

_STAGE_RANK_RAW_TYPES = 1
_STAGE_RANK_EXACT_FIELDS = 2
_STAGE_RANK_SCHEMAS = 3
_STAGE_RANK_BUNDLE_APPROVAL = 4
_STAGE_RANK_PERMISSION_SNAPSHOT = 5
_STAGE_RANK_PROVENANCE_SNAPSHOT = 6
_STAGE_RANK_RECORDS_ARRAY = 7
_STAGE_RANK_RECORD_FIELDS = 8
_STAGE_RANK_APPROVAL_LEXICAL = 9
_STAGE_RANK_APPROVAL_NONAPPROVED = 10
_STAGE_RANK_DECIMAL = 11
_STAGE_RANK_SOURCE_BINDING = 12
_STAGE_RANK_SOURCE_CLASS_LICENSE = 13
_STAGE_RANK_PERMISSION_RESOLUTION = 14
_STAGE_RANK_EVIDENCE_ARRAYS = 15
_STAGE_RANK_RECORD_HASHES = 16
_STAGE_RANK_RECORD_ORDERING = 17
_STAGE_RANK_CATALOG_BINDING = 18
_STAGE_RANK_CATALOG_HASH = 19
_STAGE_RANK_SELECTION = 20

SHELL_GEOMETRY_CATALOG_STAGE_RANK_BY_CODE: Final[Mapping[str, int]] = {
    # Stage 1 — raw types
    "SGC_RAW_TYPE_INVALID": _STAGE_RANK_RAW_TYPES,
    # Stage 2 — exact top fields
    "SGC_UNKNOWN_FIELD": _STAGE_RANK_EXACT_FIELDS,
    # Stage 3 — schemas / profiles / IDs / versions / authority
    "SGC_SCHEMA_VERSION_UNSUPPORTED": _STAGE_RANK_SCHEMAS,
    "SGC_CATALOG_ID_INVALID": _STAGE_RANK_SCHEMAS,
    "SGC_CATALOG_VERSION_INVALID": _STAGE_RANK_SCHEMAS,
    "SGC_PROFILE_UNSUPPORTED": _STAGE_RANK_SCHEMAS,
    "SGC_CATALOG_AUTHORITY_INVALID": _STAGE_RANK_SCHEMAS,
    # Stage 4 — bundle approval / TASK-012 hash / bundle hash (approval_status)
    "SGC_APPROVAL_STATE_INVALID": _STAGE_RANK_BUNDLE_APPROVAL,
    # Stage 10 — non-approved bundle rejection
    "SGC_RECORD_UNAPPROVED": _STAGE_RANK_APPROVAL_NONAPPROVED,
    # Stage 7 — records array lexical structure
    "SGC_RECORDS_INVALID": _STAGE_RANK_RECORDS_ARRAY,
    # Stage 8 — record fields / identity / duplicates / type / profile / revision
    "SGC_RECORD_ID_INVALID": _STAGE_RANK_RECORD_FIELDS,
    "SGC_RECORD_DUPLICATE_ID": _STAGE_RANK_RECORD_FIELDS,
    "SGC_GEOMETRY_TYPE_INVALID": _STAGE_RANK_RECORD_FIELDS,
    "SGC_REVISION_INVALID": _STAGE_RANK_RECORD_FIELDS,
    # Stage 11 — decimal
    "SGC_SHELL_INSIDE_DIAMETER_INVALID": _STAGE_RANK_DECIMAL,
    # Stage 12 — source binding
    "SGC_SOURCE_BINDING_INCOMPLETE": _STAGE_RANK_SOURCE_BINDING,
    # Stage 13 — source class / license
    "SGC_SOURCE_CLASS_INVALID": _STAGE_RANK_SOURCE_CLASS_LICENSE,
    "SGC_LICENSE_BLOCKED": _STAGE_RANK_SOURCE_CLASS_LICENSE,
    # Stage 14 — permission / provenance resolution + local usage gate
    "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE": _STAGE_RANK_PERMISSION_RESOLUTION,
    "SGC_PROVENANCE_INCOMPLETE": _STAGE_RANK_PERMISSION_RESOLUTION,
    # Stage 15 — evidence arrays
    "SGC_EVIDENCE_REFS_INVALID": _STAGE_RANK_EVIDENCE_ARRAYS,
    # Stage 16 — record hashes
    "SGC_RECORD_HASH_MISMATCH": _STAGE_RANK_RECORD_HASHES,
    # Stage 17 — record ordering
    "SGC_CATALOG_HASH_MISMATCH": _STAGE_RANK_RECORD_ORDERING,
    # Stage 20 — selection
    "SGC_RECORD_NOT_FOUND": _STAGE_RANK_SELECTION,
    "SGC_SELECTION_NOT_APPROVED": _STAGE_RANK_SELECTION,
}

assert set(SHELL_GEOMETRY_CATALOG_STAGE_RANK_BY_CODE) == set(
    SHELL_GEOMETRY_CATALOG_BLOCKER_CODES
), "stage_rank map must cover every closed-set code exactly once"


# Default message_key mapping per design contract §10 / Issue #151.
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
    "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE": ("sgc_vendor_permission_scope_incomplete"),
    "SGC_PROVENANCE_INCOMPLETE": "sgc_provenance_incomplete",
    "SGC_EVIDENCE_REFS_INVALID": "sgc_evidence_refs_invalid",
    "SGC_RECORD_HASH_MISMATCH": "sgc_record_hash_mismatch",
    "SGC_CATALOG_HASH_MISMATCH": "sgc_catalog_hash_mismatch",
    "SGC_RECORD_NOT_FOUND": "sgc_record_not_found",
    "SGC_SELECTION_NOT_APPROVED": "sgc_selection_not_approved",
}

# Default field_path mapping per design contract §10 / Issue #151.
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
    "SGC_SHELL_INSIDE_DIAMETER_INVALID": ("raw_catalog.records.shell_inside_diameter_m"),
    "SGC_SOURCE_BINDING_INCOMPLETE": "raw_catalog.records.source_binding",
    "SGC_SOURCE_CLASS_INVALID": "raw_catalog.records.source_class",
    "SGC_LICENSE_BLOCKED": "raw_catalog.records.license_evidence",
    "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE": ("raw_catalog.records.permission_evidence_refs"),
    "SGC_PROVENANCE_INCOMPLETE": "raw_catalog.records.provenance_edge_ids",
    "SGC_EVIDENCE_REFS_INVALID": "raw_catalog.records.evidence_refs",
    "SGC_RECORD_HASH_MISMATCH": "raw_catalog.records.record_hash",
    "SGC_CATALOG_HASH_MISMATCH": "raw_catalog.catalog_hash",
    "SGC_RECORD_NOT_FOUND": "geometry_id",
    "SGC_SELECTION_NOT_APPROVED": "geometry_id",
}


# ---------------------------------------------------------------------------
# Deep-freeze helpers for blocker payloads (Round 3 §6)
# ---------------------------------------------------------------------------


def _deep_freeze_value(value: Any) -> Any:
    """Recursively freeze a value into immutable primitives.

    Nested mappings are converted to a frozen ``MappingProxyType`` over a
    recursive copy. Nested sequences (list / tuple) become a tuple of
    recursively-frozen values. Scalars are returned unchanged. ``None``
    is preserved as-is so ``details is None`` continues to hash as JSON
    ``null``.
    """
    import types

    if value is None or isinstance(value, (str, bytes, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return types.MappingProxyType({str(k): _deep_freeze_value(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze_value(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze_value(v) for v in value)
    # Anything else (custom objects, etc.) is returned unchanged — the
    # caller is responsible for not placing non-hashable mutables into
    # the blocker payload.
    return value


def deep_freeze_details(
    details: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """Deep-freeze a ``details`` mapping for a blocker entry.

    Returns a new Mapping whose nested mutable layers (mappings / lists /
    tuples) are themselves immutable. Tests assert that mutating the
    caller's original dict/list does NOT change this frozen snapshot.
    ``None`` is preserved so ``details None`` continues to hash as JSON
    ``null``.
    """
    if details is None:
        return None
    if not isinstance(details, Mapping):
        raise TypeError("details must be a Mapping or None")
    return cast(Mapping[str, Any], _deep_freeze_value(details))


def freeze_evidence_refs(
    evidence_refs: Sequence[str],
) -> tuple[str, ...]:
    """Copy a ``Sequence[str]`` into an immutable tuple.

    The convertion preserves duplicates and ordering but rejects any
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


# ---------------------------------------------------------------------------
# Ordered blocker entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShellGeometryCatalogBlockerEntry:
    """One ordered blocker entry for the TASK-023 shell-geometry catalog."""

    code: str
    field_path: str
    message_key: str
    stage_rank: int
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise ValueError("code must be non-empty string")
        if self.code not in SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY:
            raise ValueError(f"code {self.code!r} is not a frozen TASK-023 blocker code")
        if not isinstance(self.field_path, str) or not self.field_path:
            raise ValueError("field_path must be non-empty string")
        if not isinstance(self.message_key, str) or not self.message_key:
            raise ValueError("message_key must be non-empty string")
        if not isinstance(self.stage_rank, int) or isinstance(self.stage_rank, bool):
            raise ValueError("stage_rank must be a non-bool integer")
        if self.stage_rank < 1 or self.stage_rank > _STAGE_RANK_SELECTION:
            raise ValueError(
                f"stage_rank {self.stage_rank} out of valid 1..{_STAGE_RANK_SELECTION} range"
            )
        expected_rank = SHELL_GEOMETRY_CATALOG_STAGE_RANK_BY_CODE[self.code]
        if self.stage_rank != expected_rank:
            raise ValueError(
                f"stage_rank {self.stage_rank} does not match authoritative "
                f"rank {expected_rank} for code {self.code!r}; round 3 fixup "
                "binds every blocker to its §11 stage"
            )
        if not isinstance(self.evidence_refs, tuple):
            raise ValueError("evidence_refs must be tuple")
        for entry in self.evidence_refs:
            if not isinstance(entry, str) or not entry:
                raise ValueError("evidence_refs entries must be non-empty strings")
        # details may be None or a frozen mapping; do not silently coerce dict → tuple.
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
    which is only achievable when ``None`` hashes as ``null``.
    """
    import hashlib
    import json as _json

    if details is None:
        return hashlib.sha256(_json.dumps(None).encode("utf-8")).hexdigest()
    if isinstance(details, Mapping):
        # convert MappingProxyType back to a dict for canonical hashing
        return canonical_sha256(dict(details))
    raise TypeError("details must be a Mapping or None")


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
    """Composite ordering key per design contract §6.

    The stage_rank is read from the entry's internal field; the caller
    no longer provides an identity→rank mapping.
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

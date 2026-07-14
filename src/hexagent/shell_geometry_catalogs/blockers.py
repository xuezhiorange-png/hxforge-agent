"""TASK-023 — Approved Shell Geometry Catalog blocker taxonomy.

This module is the single source of truth for the closed 25-code
blocker taxonomy that the TASK-023 framework emits. It is intentionally
separate from ``catalog.py`` so the parser layer cannot introduce
unsanctioned codes.

The blocker codes are frozen at the values specified in the merged
TASK-023 design contract §10 and Issue #151. The TASK-023
``catalog.parse_shell_geometry_catalog`` performs the 18-stage
validation pipeline in design-contract order; this module exposes the
closed 25-code taxonomy plus minimal ordered blocker-entry helpers
and the composite-sort key required by design contract §6 / §11.

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
from typing import Any, Final

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
# Ordered blocker entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShellGeometryCatalogBlockerEntry:
    """One ordered blocker entry for the TASK-023 shell-geometry catalog."""

    code: str
    field_path: str
    message_key: str
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
        if not isinstance(self.evidence_refs, tuple):
            raise ValueError("evidence_refs must be tuple")
        for entry in self.evidence_refs:
            if not isinstance(entry, str) or not entry:
                raise ValueError("evidence_refs entries must be non-empty strings")
        if self.details is not None and not isinstance(self.details, Mapping):
            raise ValueError("details must be a Mapping or None")


# ---------------------------------------------------------------------------
# Deterministic ordering helpers
# ---------------------------------------------------------------------------


def _canonical_details_hash(details: Mapping[str, Any] | None) -> str:
    """Return canonical-JSON hash of ``details``."""
    if details is None:
        return canonical_sha256({})
    if isinstance(details, Mapping):
        return canonical_sha256(dict(details))
    raise TypeError("details must be a Mapping or None")


def _canonical_evidence_refs_hash(
    evidence_refs: Sequence[str],
) -> str:
    """Return canonical-JSON hash of an evidence_refs sequence."""
    return canonical_sha256({"refs": list(evidence_refs)})


def composite_order_key(
    entry: ShellGeometryCatalogBlockerEntry,
    stage_rank: int,
) -> tuple[int, str, str, str, str, str]:
    """Composite ordering key per design contract §6."""
    return (
        stage_rank,
        entry.code,
        entry.field_path,
        entry.message_key,
        _canonical_details_hash(entry.details),
        _canonical_evidence_refs_hash(entry.evidence_refs),
    )


def sort_blockers(
    entries: Sequence[ShellGeometryCatalogBlockerEntry],
    *,
    stage_by_identity: Mapping[int, int] | None = None,
) -> tuple[ShellGeometryCatalogBlockerEntry, ...]:
    """Apply design contract §6 composite ordering."""
    if not isinstance(entries, Sequence):
        raise TypeError("entries must be a Sequence[ShellGeometryCatalogBlockerEntry]")
    for entry in entries:
        if not isinstance(entry, ShellGeometryCatalogBlockerEntry):
            raise TypeError("every entry must be a ShellGeometryCatalogBlockerEntry")
    ranks: Mapping[int, int] = stage_by_identity or {}

    def key(
        e: ShellGeometryCatalogBlockerEntry,
    ) -> tuple[int, str, str, str, str, str]:
        return composite_order_key(e, ranks.get(id(e), 0))

    return tuple(sorted(entries, key=key))

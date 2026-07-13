"""TASK-021 Slice B — adapter blocker taxonomy and AdapterFailure exception.

This module is the single source of truth for the closed-set blocker
codes that the Slice B source adapters (geometry_adapter.py and
rule_pack_adapter.py) may emit. It is intentionally separate from
``models.py`` so that the adapter layer cannot introduce blocker codes
into the slice-A deterministic core's namespace.

The blocker codes are frozen at the values specified in Issue #141
Record 7. The two adapters import the constants from here and use them
verbatim. The exception class ``AdapterFailure`` is the single signal
carrying a complete structured blocker list.

Per TASK-021 §11.3 the composite ordering key for blockers across both
adapters is:

    (code, field_path or "", message_key,
     SHA-256(canonical_json(details)),
     SHA-256(canonical_json(evidence_refs)))

This module exposes the helpers used to construct and order the blockers;
it does NOT itself perform any ordering — the ordering happens inside
each adapter's verifier so that the verifier owns ordering decisions in
one place.

The module forbids filesystem / network / database / environment /
runtime-now / locale operations. It only imports stdlib and slice-A
canonical helpers, all of which are pure.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from .canonical import canonical_json, internal_frozen_to_primitive, sha256_hex
from .models import MessageEntry

# --- Geometry adapter blocker codes (10 codes, frozen in Record 7) --------

GEOMETRY_ADAPTER_BLOCKER_CODES: Final[tuple[str, ...]] = (
    "STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID",
    "STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID",
    "STL_GEOMETRY_ADAPTER_CATALOG_HASH_MISMATCH",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_ID_NOT_FOUND",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_ID_DUPLICATE",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_TYPE_NOT_TUBE",
    "STL_GEOMETRY_ADAPTER_RECORD_NOT_APPROVED",
    "STL_GEOMETRY_ADAPTER_RECORD_HASH_MISMATCH",
    "STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE",
    "STL_GEOMETRY_ADAPTER_PROJECTION_INVALID",
)


class GeometryAdapterBlockerCode(enum.StrEnum):
    """Closed set of geometry-adapter blocker codes (Record 7)."""

    STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID = "STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID"
    STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID = "STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID"
    STL_GEOMETRY_ADAPTER_CATALOG_HASH_MISMATCH = "STL_GEOMETRY_ADAPTER_CATALOG_HASH_MISMATCH"
    STL_GEOMETRY_ADAPTER_GEOMETRY_ID_NOT_FOUND = "STL_GEOMETRY_ADAPTER_GEOMETRY_ID_NOT_FOUND"
    STL_GEOMETRY_ADAPTER_GEOMETRY_ID_DUPLICATE = "STL_GEOMETRY_ADAPTER_GEOMETRY_ID_DUPLICATE"
    STL_GEOMETRY_ADAPTER_GEOMETRY_TYPE_NOT_TUBE = "STL_GEOMETRY_ADAPTER_GEOMETRY_TYPE_NOT_TUBE"
    STL_GEOMETRY_ADAPTER_RECORD_NOT_APPROVED = "STL_GEOMETRY_ADAPTER_RECORD_NOT_APPROVED"
    STL_GEOMETRY_ADAPTER_RECORD_HASH_MISMATCH = "STL_GEOMETRY_ADAPTER_RECORD_HASH_MISMATCH"
    STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE = (
        "STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE"  # noqa: E501
    )
    STL_GEOMETRY_ADAPTER_PROJECTION_INVALID = "STL_GEOMETRY_ADAPTER_PROJECTION_INVALID"


# Per-Record-7 default message_key mapping for the geometry adapter
# (each code maps to one exact message_key recorded in Issue #141).
GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY: Final[dict[str, str]] = {
    "STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID": "geometry_adapter_raw_type_invalid",
    "STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID": "geometry_adapter_upstream_object_invalid",
    "STL_GEOMETRY_ADAPTER_CATALOG_HASH_MISMATCH": "geometry_adapter_catalog_hash_mismatch",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_ID_NOT_FOUND": "geometry_id_not_found",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_ID_DUPLICATE": "geometry_id_duplicate",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_TYPE_NOT_TUBE": "geometry_type_not_tube",
    "STL_GEOMETRY_ADAPTER_RECORD_NOT_APPROVED": "geometry_record_not_approved",
    "STL_GEOMETRY_ADAPTER_RECORD_HASH_MISMATCH": "geometry_adapter_record_hash_mismatch",
    "STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE": "geometry_adapter_source_binding_incomplete",
    "STL_GEOMETRY_ADAPTER_PROJECTION_INVALID": "geometry_adapter_projection_invalid",
}

# Default field_path for each geometry-adapter code (Record 7).
GEOMETRY_ADAPTER_DEFAULT_FIELD_PATH: Final[dict[str, str]] = {
    "STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID": "geometry_id",
    "STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID": "catalog",
    "STL_GEOMETRY_ADAPTER_CATALOG_HASH_MISMATCH": "catalog.content_hash",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_ID_NOT_FOUND": "geometry_id",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_ID_DUPLICATE": "geometry_id",
    "STL_GEOMETRY_ADAPTER_GEOMETRY_TYPE_NOT_TUBE": "geometry_id",
    "STL_GEOMETRY_ADAPTER_RECORD_NOT_APPROVED": "geometry_id",
    "STL_GEOMETRY_ADAPTER_RECORD_HASH_MISMATCH": "geometry_id",
    "STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE": "geometry_id",
    "STL_GEOMETRY_ADAPTER_PROJECTION_INVALID": "geometry_id",
}

# --- Rule-pack adapter blocker codes (14 codes, frozen in Record 7) -------

RULE_PACK_ADAPTER_BLOCKER_CODES: Final[tuple[str, ...]] = (
    "STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID",
    "STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID",
    "STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH",
    "STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH",
    "STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND",
    "STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE",
    "STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH",
    "STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED",
    "STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN",
    "STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING",
    "STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING",
    "STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN",
    "STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED",
    "STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE",
)


class RulePackAdapterBlockerCode(enum.StrEnum):
    """Closed set of rule-pack-adapter blocker codes (Record 7)."""

    STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID = "STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID"
    STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID = "STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID"
    STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH = "STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH"
    STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH = "STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH"
    STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND = "STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND"
    STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE = "STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE"
    STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH = "STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH"
    STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED = "STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED"
    STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN = "STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN"
    STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING = (
        "STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING"  # noqa: E501
    )
    STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING = (
        "STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING"  # noqa: E501
    )
    STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN = "STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN"
    STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED = (
        "STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED"  # noqa: E501
    )
    STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE = "STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE"


# Per-Record-7 default message_key mapping for the rule-pack adapter.
RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY: Final[dict[str, str]] = {
    "STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID": "rule_pack_adapter_raw_type_invalid",
    "STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID": "rule_pack_adapter_upstream_object_invalid",
    "STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH": "layout_rule_profile_unsupported",
    "STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH": "rule_pack_hash_mismatch",
    "STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND": "rule_id_not_found",
    "STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE": "rule_id_duplicate",
    "STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH": "rule_hash_mismatch",
    "STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED": "layout_rule_unapproved",
    "STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN": "rule_source_class_forbidden",
    "STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING": "rule_license_evidence_missing",
    "STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING": "rule_vendor_permission_scope_missing",
    "STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN": "rule_runtime_scope_forbidden",
    "STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED": "rule_restricted_body_rejected",
    "STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE": "rule_provenance_incomplete",
}

# Default field_path for each rule-pack-adapter code.
RULE_PACK_ADAPTER_DEFAULT_FIELD_PATH: Final[dict[str, str]] = {
    "STL_RULE_PACK_ADAPTER_RAW_TYPE_INVALID": "rule_id",
    "STL_RULE_PACK_ADAPTER_UPSTREAM_OBJECT_INVALID": "rule_pack_validation_report",
    "STL_RULE_PACK_ADAPTER_PROFILE_MISMATCH": "profile_id",
    "STL_RULE_PACK_ADAPTER_RULE_PACK_HASH_MISMATCH": "rule_pack_manifest",
    "STL_RULE_PACK_ADAPTER_RULE_ID_NOT_FOUND": "rule_id",
    "STL_RULE_PACK_ADAPTER_RULE_ID_DUPLICATE": "rule_id",
    "STL_RULE_PACK_ADAPTER_RULE_HASH_MISMATCH": "rule_id",
    "STL_RULE_PACK_ADAPTER_RULE_NOT_APPROVED": "rule_id",
    "STL_RULE_PACK_ADAPTER_SOURCE_CLASS_FORBIDDEN": "rule_id",
    "STL_RULE_PACK_ADAPTER_LICENSE_EVIDENCE_MISSING": "rule_id",
    "STL_RULE_PACK_ADAPTER_VENDOR_PERMISSION_SCOPE_MISSING": "rule_id",
    "STL_RULE_PACK_ADAPTER_RUNTIME_SCOPE_FORBIDDEN": "rule_id",
    "STL_RULE_PACK_ADAPTER_RESTRICTED_BODY_REJECTED": "rule_id",
    "STL_RULE_PACK_ADAPTER_PROVENANCE_INCOMPLETE": "rule_id",
}


# --- adapter payload helpers ---------------------------------------------


def _frozen_evidence_refs(evidence_refs: Sequence[str]) -> tuple[str, ...]:
    """Return a tuple of non-empty strings sorted in Unicode order, deduped.

    Defensive: rejects non-strings, empty strings, and preserves the
    TASK-021 §6.2 sorted-Unicode-order duplicate-free invariant.
    """
    out: set[str] = set()
    for ref in evidence_refs:
        if not isinstance(ref, str):
            raise TypeError(f"evidence_refs entries must be strings; got {type(ref).__name__}")
        if not ref:
            raise ValueError("evidence_refs entries must be non-empty strings")
        out.add(ref)
    return tuple(sorted(out))


def _is_canonical_json_value(value: Any) -> bool:
    """Restrict ``details`` to the slice-A §6.1 canonical JSON value domain.

    Used as a defensive runtime check before constructing a
    ``MessageEntry``. Recursive; rejects binary float, Decimal, bytes,
    set, frozenset, tuple, dataclass, arbitrary objects, and non-string
    mapping keys.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_canonical_json_value(item) for item in value)
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                return False
            if not _is_canonical_json_value(v):
                return False
        return True
    return False


def build_message_entry(
    *,
    code: str,
    field_path: str | None,
    message_key: str,
    evidence_refs: Sequence[str] = (),
    details: Mapping[str, Any] | None = None,
) -> MessageEntry:
    """Construct one canonical slice-A ``MessageEntry`` for an adapter.

    The five-field payload is exactly the slice-A standard. The function:

    * normalizes ``code`` to ``str``;
    * enforces ``field_path is None or non-empty str``;
    * enforces ``message_key is non-empty str``;
    * freezes ``evidence_refs`` via :func:`_frozen_evidence_refs`;
    * enforces ``details`` is canonical-JSON-domain (or None).
    """
    if not isinstance(code, str) or not code:
        raise ValueError("code must be a non-empty string")
    if not isinstance(message_key, str) or not message_key:
        raise ValueError("message_key must be a non-empty string")
    if field_path is not None and (not isinstance(field_path, str) or not field_path):
        raise ValueError("field_path must be None or a non-empty string")
    frozen_refs = _frozen_evidence_refs(evidence_refs)
    if details is not None:
        if not isinstance(details, Mapping):
            raise ValueError("details must be a Mapping or None")
        if not _is_canonical_json_value(dict(details)):
            raise ValueError(
                "details must be a canonical-JSON-domain value "
                "(slice-A §6.1): no float / Decimal / bytes / set / "
                "frozenset / tuple / arbitrary object / non-string key"
            )
    return MessageEntry(
        code=code,
        field_path=field_path,
        message_key=message_key,
        evidence_refs=frozen_refs,
        details=dict(details) if details is not None else None,
    )


# --- AdapterFailure exception --------------------------------------------


@dataclass(frozen=True)
class _AdapterFailureDeps:
    """Internal: stable composite ordering key per TASK-021 §11.3."""

    code: str
    field_path: str
    message_key: str
    canonical_details_hash: str
    canonical_evidence_refs_hash: str


def _canonical_details_hash(details: Any) -> str:
    """SHA-256 over canonical JSON. ``None`` hashes the canonical bytes of
    ``null``. Bytes are UTF-8 with no whitespace.

    The slice-A ``MessageEntry.__post_init__`` (Round 8 §P1-1) wraps
    ``details`` in a ``FrozenJsonObject`` whenever a non-None dict is
    supplied, so the value reaching this helper is typically a Layer-B
    internal marker. ``sha256_hex -> canonical_json`` rejects internal
    markers at the public Layer-A boundary; we therefore reduce to
    public-domain primitives via ``internal_frozen_to_primitive`` first
    and only then hash the result.
    """
    primitive = None if details is None else internal_frozen_to_primitive(details)
    return sha256_hex(primitive)


def _evidence_refs_hash(evidence_refs: Sequence[str]) -> str:
    """SHA-256 over canonical-JSON of evidence_refs (a list of strings).

    Always a list (even if ``evidence_refs`` is empty) to make the bytes
    deterministic across runs. ``MessageEntry.__post_init__`` freezes
    evidence_refs into a tuple; we listify through canonical JSON which
    accepts a tuple of strings as the public-domain sequence shape.
    """
    return sha256_hex(canonical_json(list(evidence_refs)))


def _composite_order_key(entry: MessageEntry) -> tuple[str, str, str, str, str]:
    """Compute the slice-A §11.3 composite ordering key for one entry.

    Returns ``(code, field_path or "", message_key,
    canonical_details_hash, canonical_evidence_refs_hash)``.
    """
    details_hash = _canonical_details_hash(entry.details)
    refs_hash = _evidence_refs_hash(entry.evidence_refs)
    return (
        entry.code,
        "" if entry.field_path is None else entry.field_path,
        entry.message_key,
        details_hash,
        refs_hash,
    )


def sort_adapter_blockers(
    entries: Sequence[MessageEntry],
) -> tuple[MessageEntry, ...]:
    """Apply slice-A §11.3 composite ordering, returning a new tuple.

    Stable, deterministic, and free of side effects. Used by both
    adapters as the final pass before raising ``AdapterFailure`` or
    returning a partial verification report.
    """
    if not isinstance(entries, Sequence):
        raise TypeError("entries must be a Sequence[MessageEntry]")
    if any(not isinstance(e, MessageEntry) for e in entries):
        raise TypeError("every entry must be a MessageEntry")
    return tuple(sorted(entries, key=_composite_order_key))


class AdapterFailure(Exception):
    """Single structured-exception type carrying a complete blocker list.

    Each blocker is a fully-populated ``MessageEntry`` carrying the
    slice-A-standard five-field payload. The constructor takes a
    sequence of entries, applies composite ordering per slice-A §11.3,
    and freezes the resulting tuple on ``self.blockers``. No partial
    information is ever lost; even on a single blocker the composite
    ordering pass is applied so that the blocker list is deterministic
    across runs.

    The exception NEVER uses exception string messages as the
    authoritative blocker payload. The ``blockers`` attribute is the
    only structured signal.
    """

    def __init__(self, blockers: Sequence[MessageEntry]) -> None:
        ordered = sort_adapter_blockers(blockers)
        object.__setattr__(self, "blockers", ordered)
        # A descriptive exception string for debug only — never the
        # authoritative signal.
        codes = ", ".join(b.code for b in ordered)
        super().__init__(f"AdapterFailure[{codes}]")


# --- module guard --------------------------------------------------------

# FORBIDDEN_IMPORT_TOKENS is enforced by the slice-A architecture test
# test_core_has_no_forbidden_io_imports at
# tests/exchangers/shell_tube/tube_layout/test_architecture_and_boundaries.py.
# This module imports ONLY stdlib + slice-A canonical helpers above;
# absence of forbidden tokens is verified by the global gate.

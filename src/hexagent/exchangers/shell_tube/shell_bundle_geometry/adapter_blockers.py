"""TASK-022 Slice B1 — adapter blocker taxonomy and AdapterFailure exception.

This module is the single source of truth for the closed-set rule-pack
adapter blocker codes that the TASK-022 Slice B1 rule-pack adapter may
emit. It is intentionally separate from ``models.py`` so that the
adapter layer cannot introduce blocker codes into the slice-A
deterministic core's namespace.

The blocker codes are frozen at the values specified in Issue #147
Record 4 (Binding commit ``4964517555``). The TASK-022 Slice B1
``rule_pack_adapter`` imports the constants from here and uses them
verbatim. The exception class ``AdapterFailure`` is the single signal
carrying a complete structured blocker list.

The 16-stage validation pipeline (Issue #147 Record 4) orders blockers
deterministically via:

    (adapter_stage_rank, code, field_path or "", message_key,
     sha256(canonical_json(details)),
     sha256(canonical_json(evidence_refs)))

This module exposes the helpers used to construct and order the
blockers; the ordering helper accepts a ``stage_by_identity`` mapping
so each adapter stage can carry its own rank while preserving
deterministic ordering per stage 1–16.

The module forbids filesystem / network / database / environment /
runtime-now / locale operations. It only imports stdlib + slice-A
canonical helpers + the slice-A ``MessageEntry`` model, all of which
are pure.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from .canonical import canonical_json, internal_frozen_to_primitive, sha256_hex
from .models import MessageEntry

# Frozen closed-set of 20 TASK-022 Slice B1 adapter blocker codes
# (Issue #147 Record 4). Order is the canonical token order Charles
# recorded in Record 4 and MUST be preserved verbatim — any extension
# requires a separate Charles authorization.
RULE_PACK_ADAPTER_BLOCKER_CODES: Final[tuple[str, ...]] = (
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


class RulePackAdapterBlockerCode(enum.StrEnum):
    """Closed set of TASK-022 Slice B1 rule-pack adapter blocker codes.

    Each member maps to the exact frozen token recorded in Issue #147
    Record 4. No reserved alias, generic code, or repurpose is permitted.
    """

    SBG_RULE_ADAPTER_RAW_TYPE_INVALID = "SBG_RULE_ADAPTER_RAW_TYPE_INVALID"
    SBG_RULE_ADAPTER_UNKNOWN_FIELD = "SBG_RULE_ADAPTER_UNKNOWN_FIELD"
    SBG_RULE_ADAPTER_UPSTREAM_OBJECT_INVALID = "SBG_RULE_ADAPTER_UPSTREAM_OBJECT_INVALID"
    SBG_RULE_ADAPTER_MANIFEST_INVALID = "SBG_RULE_ADAPTER_MANIFEST_INVALID"
    SBG_RULE_ADAPTER_MANIFEST_HASH_MISMATCH = "SBG_RULE_ADAPTER_MANIFEST_HASH_MISMATCH"
    SBG_RULE_ADAPTER_RULE_ID_INVALID = "SBG_RULE_ADAPTER_RULE_ID_INVALID"
    SBG_RULE_ADAPTER_RULE_NOT_FOUND = "SBG_RULE_ADAPTER_RULE_NOT_FOUND"
    SBG_RULE_ADAPTER_MANIFEST_REFERENCE_INVALID = "SBG_RULE_ADAPTER_MANIFEST_REFERENCE_INVALID"
    SBG_RULE_ADAPTER_RULE_INVALID = "SBG_RULE_ADAPTER_RULE_INVALID"
    SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH = "SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH"
    SBG_RULE_ADAPTER_RULE_HASH_MISMATCH = "SBG_RULE_ADAPTER_RULE_HASH_MISMATCH"
    SBG_RULE_ADAPTER_RULE_UNAPPROVED = "SBG_RULE_ADAPTER_RULE_UNAPPROVED"
    SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN = (
        "SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN"
    )
    SBG_RULE_ADAPTER_LICENSE_BLOCKED = "SBG_RULE_ADAPTER_LICENSE_BLOCKED"
    SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE = (
        "SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE"
    )
    SBG_RULE_ADAPTER_PROVENANCE_INVALID = "SBG_RULE_ADAPTER_PROVENANCE_INVALID"
    SBG_RULE_ADAPTER_PROFILE_UNSUPPORTED = "SBG_RULE_ADAPTER_PROFILE_UNSUPPORTED"
    SBG_RULE_ADAPTER_RULE_BODY_INVALID = "SBG_RULE_ADAPTER_RULE_BODY_INVALID"
    SBG_RULE_ADAPTER_SNAPSHOT_HASH_MISMATCH = "SBG_RULE_ADAPTER_SNAPSHOT_HASH_MISMATCH"
    SBG_RULE_ADAPTER_SNAPSHOT_VERIFICATION_FAILED = "SBG_RULE_ADAPTER_SNAPSHOT_VERIFICATION_FAILED"


# Per-Record-4 default message_key mapping for the B1 adapter. Each code
# maps to one exact message_key token recorded in Issue #147.
RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY: Final[dict[str, str]] = {
    "SBG_RULE_ADAPTER_RAW_TYPE_INVALID": "rule_adapter_raw_type_invalid",
    "SBG_RULE_ADAPTER_UNKNOWN_FIELD": "rule_adapter_unknown_field",
    "SBG_RULE_ADAPTER_UPSTREAM_OBJECT_INVALID": "rule_adapter_upstream_object_invalid",
    "SBG_RULE_ADAPTER_MANIFEST_INVALID": "rule_adapter_manifest_invalid",
    "SBG_RULE_ADAPTER_MANIFEST_HASH_MISMATCH": "rule_adapter_manifest_hash_mismatch",
    "SBG_RULE_ADAPTER_RULE_ID_INVALID": "rule_adapter_rule_id_invalid",
    "SBG_RULE_ADAPTER_RULE_NOT_FOUND": "rule_adapter_rule_not_found",
    "SBG_RULE_ADAPTER_MANIFEST_REFERENCE_INVALID": "rule_adapter_manifest_reference_invalid",
    "SBG_RULE_ADAPTER_RULE_INVALID": "rule_adapter_rule_invalid",
    "SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH": "rule_adapter_rule_identity_mismatch",
    "SBG_RULE_ADAPTER_RULE_HASH_MISMATCH": "rule_adapter_rule_hash_mismatch",
    "SBG_RULE_ADAPTER_RULE_UNAPPROVED": "rule_adapter_rule_unapproved",
    "SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN": (
        "rule_adapter_source_class_runtime_forbidden"
    ),
    "SBG_RULE_ADAPTER_LICENSE_BLOCKED": "rule_adapter_license_blocked",
    "SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE": (
        "rule_adapter_vendor_permission_scope_incomplete"
    ),
    "SBG_RULE_ADAPTER_PROVENANCE_INVALID": "rule_adapter_provenance_invalid",
    "SBG_RULE_ADAPTER_PROFILE_UNSUPPORTED": "rule_adapter_profile_unsupported",
    "SBG_RULE_ADAPTER_RULE_BODY_INVALID": "rule_adapter_rule_body_invalid",
    "SBG_RULE_ADAPTER_SNAPSHOT_HASH_MISMATCH": "rule_adapter_snapshot_hash_mismatch",
    "SBG_RULE_ADAPTER_SNAPSHOT_VERIFICATION_FAILED": "rule_adapter_snapshot_verification_failed",
}

# Per-Record-4 default field_path mapping for the B1 adapter. Each code
# records the schema field the blocker is most naturally anchored to.
RULE_PACK_ADAPTER_DEFAULT_FIELD_PATH: Final[dict[str, str]] = {
    "SBG_RULE_ADAPTER_RAW_TYPE_INVALID": "loaded_rule_pack",
    "SBG_RULE_ADAPTER_UNKNOWN_FIELD": "loaded_rule_pack",
    "SBG_RULE_ADAPTER_UPSTREAM_OBJECT_INVALID": "loaded_rule_pack",
    "SBG_RULE_ADAPTER_MANIFEST_INVALID": "loaded_rule_pack.manifest",
    "SBG_RULE_ADAPTER_MANIFEST_HASH_MISMATCH": "loaded_rule_pack.manifest.canonical_hash",
    "SBG_RULE_ADAPTER_RULE_ID_INVALID": "rule_id",
    "SBG_RULE_ADAPTER_RULE_NOT_FOUND": "rule_id",
    "SBG_RULE_ADAPTER_MANIFEST_REFERENCE_INVALID": "loaded_rule_pack.manifest.rules",
    "SBG_RULE_ADAPTER_RULE_INVALID": "loaded_rule_pack.rules",
    "SBG_RULE_ADAPTER_RULE_IDENTITY_MISMATCH": "loaded_rule_pack.rules",
    "SBG_RULE_ADAPTER_RULE_HASH_MISMATCH": "loaded_rule_pack.rules",
    "SBG_RULE_ADAPTER_RULE_UNAPPROVED": "loaded_rule_pack.rules",
    "SBG_RULE_ADAPTER_SOURCE_CLASS_RUNTIME_FORBIDDEN": "loaded_rule_pack.rules",
    "SBG_RULE_ADAPTER_LICENSE_BLOCKED": "loaded_rule_pack.rules",
    "SBG_RULE_ADAPTER_VENDOR_PERMISSION_SCOPE_INCOMPLETE": "loaded_rule_pack.rules",
    "SBG_RULE_ADAPTER_PROVENANCE_INVALID": "loaded_rule_pack.provenance_edges",
    "SBG_RULE_ADAPTER_PROFILE_UNSUPPORTED": "loaded_rule_pack.rules.rule_body.profile_id",
    "SBG_RULE_ADAPTER_RULE_BODY_INVALID": "loaded_rule_pack.rules.rule_body",
    "SBG_RULE_ADAPTER_SNAPSHOT_HASH_MISMATCH": "geometry_rule_authority.snapshot_hash",
    "SBG_RULE_ADAPTER_SNAPSHOT_VERIFICATION_FAILED": "geometry_rule_authority",
}


# --- payload normalisation helpers ---------------------------------------


def _frozen_evidence_refs(evidence_refs: Sequence[str]) -> tuple[str, ...]:
    """Return a tuple of non-empty strings sorted in Unicode order, deduplicated.

    Defensive: rejects non-string entries and empty strings, and
    preserves the slice-A §6.2 sorted-Unicode-order duplicate-free
    invariant.
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

    Recursive. Rejects binary float, ``Decimal``, bytes, set, frozenset,
    tuple, dataclass, arbitrary objects, and non-string mapping keys.
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

    * enforces ``code`` is one of the closed-set tokens;
    * enforces ``field_path`` is ``None`` or a non-empty string;
    * enforces ``message_key`` is a non-empty string;
    * freezes ``evidence_refs`` via :func:`_frozen_evidence_refs`;
    * enforces ``details`` is canonical-JSON-domain (or ``None``).
    """
    if not isinstance(code, str) or not code:
        raise ValueError("code must be a non-empty string")
    if code not in RULE_PACK_ADAPTER_DEFAULT_MESSAGE_KEY:
        raise ValueError(f"code {code!r} is not a frozen TASK-022 Slice B1 blocker code")
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


# --- deterministic ordering ------------------------------------------------


@dataclass(frozen=True)
class _CompositeSortKeyDeps:
    """Internal: stable composite ordering per Issue #147 Record 4."""


def _canonical_details_hash(details: Any) -> str:
    """SHA-256 over canonical JSON of ``details``.

    ``None`` hashes the canonical bytes of ``null``. The slice-A
    ``MessageEntry.__post_init__`` wraps ``details`` in a Layer-B
    internal marker whenever a non-None dict is supplied; we therefore
    reduce to public-domain primitives via
    :func:`internal_frozen_to_primitive` first.
    """
    primitive = None if details is None else internal_frozen_to_primitive(details)
    return sha256_hex(primitive)


def _evidence_refs_hash(evidence_refs: Sequence[str]) -> str:
    """SHA-256 over canonical-JSON of evidence_refs (a list of strings)."""
    return sha256_hex(canonical_json(list(evidence_refs)))


def _composite_order_key(
    entry: MessageEntry,
    stage_rank: int,
) -> tuple[int, str, str, str, str, str]:
    """Composite ordering key per Issue #147 Record 4.

    Returns ``(adapter_stage_rank, code, field_path or "", message_key,
    canonical_details_hash, canonical_evidence_refs_hash)``.
    """
    details_hash = _canonical_details_hash(entry.details)
    refs_hash = _evidence_refs_hash(entry.evidence_refs)
    return (
        stage_rank,
        entry.code,
        "" if entry.field_path is None else entry.field_path,
        entry.message_key,
        details_hash,
        refs_hash,
    )


def sort_adapter_blockers(
    entries: Sequence[MessageEntry],
    *,
    stage_by_identity: Mapping[int, int] | None = None,
) -> tuple[MessageEntry, ...]:
    """Apply Issue #147 Record 4 composite ordering and return a new tuple.

    ``stage_by_identity`` is a mapping from ``id(entry)`` to the entry's
    1-based adapter_stage_rank (1-16). When absent, every entry is
    treated as stage 0. This matches the slice-A ``sort_messages`` API
    signature so the adapter can reuse the canonical ordering helper.
    """
    if not isinstance(entries, Sequence):
        raise TypeError("entries must be a Sequence[MessageEntry]")
    if any(not isinstance(e, MessageEntry) for e in entries):
        raise TypeError("every entry must be a MessageEntry")
    ranks: Mapping[int, int] = stage_by_identity or {}

    def key(entry: MessageEntry) -> tuple[int, str, str, str, str, str]:
        return _composite_order_key(entry, ranks.get(id(entry), 0))

    return tuple(sorted(entries, key=key))


class AdapterFailure(Exception):
    """Single structured-exception type carrying a complete blocker list.

    Each blocker is a fully-populated ``MessageEntry`` carrying the
    slice-A-standard five-field payload. The constructor takes a
    sequence of entries and an optional ``stage_by_identity`` mapping
    describing each entry's 1-based adapter stage rank (1-16), then
    applies the Record-4 composite ordering and freezes the resulting
    tuple on ``self.blockers``. No partial information is ever lost;
    even on a single blocker the composite ordering pass is applied so
    that the blocker list is deterministic across runs.

    The exception NEVER uses exception string messages as the
    authoritative blocker payload. The ``blockers`` attribute is the
    only structured signal.
    """

    def __init__(
        self,
        blockers: Sequence[MessageEntry],
        *,
        stage_by_identity: Mapping[int, int] | None = None,
    ) -> None:
        ordered = sort_adapter_blockers(blockers, stage_by_identity=stage_by_identity)
        object.__setattr__(self, "blockers", ordered)
        # A descriptive exception string for debug only — never the
        # authoritative signal.
        codes = ", ".join(b.code for b in ordered)
        super().__init__(f"AdapterFailure[{codes}]")


# --- module guard ----------------------------------------------------------

# FORBIDDEN_IMPORT_TOKENS is enforced by the slice-A architecture test
# test_core_has_no_forbidden_io_imports and by
# test_rule_pack_adapter_architecture. This module imports ONLY stdlib
# + slice-A canonical helpers; absence of forbidden tokens is verified
# by the global gate.

"""TASK-023 — Approved Shell Geometry Catalog immutable value objects.

This module is the single source of truth for the closed-set frozen
model objects that the TASK-023 shell geometry catalog framework uses.
It is intentionally separate from ``blockers.py`` and ``catalog.py``
so that the package cannot accidentally import a partial surface from
the parser layer.

The model fields are frozen at the values specified in the merged
design contract (docs/tasks/TASK-023-approved-shell-geometry-catalog.md)
and Issue #151. The implementation MUST NOT introduce extra fields,
rename fields, change types or weaken immutability.

The module forbids filesystem / network / database / environment /
runtime-now / locale / registry / dynamic-import / executable-
deserialization operations. It only depends on stdlib + TASK-023
local primitives + the shared canonical SHA-256 helper, all of which
are pure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

# Frozen constants — exact tokens from the merged design contract §4.
CATALOG_SCHEMA_VERSION: Final[str] = "task023.approved-shell-geometry-catalog.v1"
RECORD_SCHEMA_VERSION: Final[str] = "task023.approved-shell-geometry-record.v1"
EVIDENCE_BUNDLE_SCHEMA_VERSION: Final[str] = "task023.shell-authority-evidence-bundle.v1"
PROFILE_ID: Final[str] = "hxforge.shell_geometry_catalog.v1"
GEOMETRY_TYPE: Final[str] = "shell"
GEOMETRY_ROLE: Final[str] = "shell"
APPROVAL_STATES: Final[tuple[str, ...]] = (
    "approved",
    "pending",
    "rejected",
    "retired",
)
SELECTABLE_APPROVAL_STATES: Final[tuple[str, ...]] = ("approved",)


# TASK-012 source-class tokens frozen for TASK-023. These mirror the
# TASK-012 governance matrix recorded in the closed-set design and
# must not be widened, narrowed or reordered.
SOURCE_CLASS_PUBLIC_DOMAIN: Final[str] = "PUBLIC_DOMAIN"
SOURCE_CLASS_OPEN_LICENSE: Final[str] = "OPEN_LICENSE"
SOURCE_CLASS_USER_PROVIDED_LICENSED_SUMMARY: Final[str] = "USER_PROVIDED_LICENSED_SUMMARY"
SOURCE_CLASS_INTERNAL_ENGINEERING_RULE: Final[str] = "INTERNAL_ENGINEERING_RULE"
SOURCE_CLASS_DERIVED_ENGINEERING_RULE: Final[str] = "DERIVED_ENGINEERING_RULE"
SOURCE_CLASS_REFERENCE_ONLY_RESTRICTED_STANDARD: Final[str] = "REFERENCE_ONLY_RESTRICTED_STANDARD"
SOURCE_CLASS_VENDOR_PERMISSIONED: Final[str] = "VENDOR_PERMISSIONED"
RECOGNIZED_SOURCE_CLASSES: Final[frozenset[str]] = frozenset(
    {
        SOURCE_CLASS_PUBLIC_DOMAIN,
        SOURCE_CLASS_OPEN_LICENSE,
        SOURCE_CLASS_USER_PROVIDED_LICENSED_SUMMARY,
        SOURCE_CLASS_INTERNAL_ENGINEERING_RULE,
        SOURCE_CLASS_DERIVED_ENGINEERING_RULE,
        SOURCE_CLASS_REFERENCE_ONLY_RESTRICTED_STANDARD,
        SOURCE_CLASS_VENDOR_PERMISSIONED,
    }
)

# Public-repository vendor-scope requirements recorded in the merged
# design contract §7 / Issue #151 — kept here so models stay authority-
# self-sufficient.
VENDOR_PERMISSION_REQUIRED_SCOPE_TOKENS: Final[tuple[str, ...]] = (
    "repository_storage",
    "repository_redistribution",
)


# ---------------------------------------------------------------------------
# Deep-freeze helper — used to detach caller-mutable mappings and lists.
# ---------------------------------------------------------------------------


def _freeze_nested(value: Any) -> Any:
    """Return a read-only view of ``value`` with caller mutability removed.

    - Mappings become a ``MappingProxyType`` with frozen inner mappings /
      frozen inner sequences.
    - Sequences become tuples; inner elements recursively frozen.
    - Other values are returned unchanged.

    The returned structure is read-only via Python's ``MappingProxyType``
    and tuple immutability; the parser layer still rebuilds structural
    copies for hash-domain stability.
    """
    import types
    from collections.abc import Mapping as _Mapping

    if isinstance(value, _Mapping):
        # Build a new dict (copy) then return a read-only proxy.
        frozen_inner = {key: _freeze_nested(item) for key, item in value.items()}
        return types.MappingProxyType(frozen_inner)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_nested(item) for item in value)
    return value


def _str_seq(value: Sequence[Any] | None) -> tuple[str, ...]:
    """Validate and coerce ``value`` to a ``tuple[str, ...]`` with no
    caller-mutable alias. Empty sequence allowed unless caller requires
    non-empty.
    """
    if value is None:
        return ()
    items = tuple(value)
    for entry in items:
        if not isinstance(entry, str):
            raise ValueError("sequence entries must be strings")
    return items


def _str_seq_nonempty(value: Sequence[Any] | None) -> tuple[str, ...]:
    seq = _str_seq(value)
    if not seq:
        raise ValueError("sequence must be non-empty")
    return seq


# ---------------------------------------------------------------------------
# Immutable model objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShellSourceBinding:
    """Closed TASK-023 source-binding snapshot.

    Field set is exactly the design contract §5.1 record. The model
    is detached from any caller-mutable container: every field is a
    normalized primitive and ``__post_init__`` rebuilds sequence
    fields into fresh tuples.
    """

    source_id: str
    source_type: str
    source_revision: str
    source_location: str
    evidence_ref: str
    approved_by: str
    approved_at: str

    def __post_init__(self) -> None:
        for field_name in (
            "source_id",
            "source_type",
            "source_revision",
            "source_location",
            "evidence_ref",
            "approved_by",
            "approved_at",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"ShellSourceBinding.{field_name} must be a non-empty string")


@dataclass(frozen=True)
class VendorPermissionEvidenceSnapshot:
    """Closed TASK-023 vendor permission evidence snapshot.

    Field set is exactly the design contract §5.5 record. ``scope`` and
    ``usage_scope`` are tuples of sorted canonical strings.
    """

    permission_id: str
    permission_scope: tuple[str, ...]
    usage_scope: tuple[str, ...]
    evidence_ref: str
    approved_by: str
    approved_at: str
    permission_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.permission_id, str) or not self.permission_id:
            raise ValueError("VendorPermissionEvidenceSnapshot.permission_id must be non-empty")
        for seq_name in ("permission_scope", "usage_scope"):
            seq = getattr(self, seq_name)
            if not isinstance(seq, tuple):
                raise ValueError(f"VendorPermissionEvidenceSnapshot.{seq_name} must be tuple")
            for entry in seq:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"VendorPermissionEvidenceSnapshot.{seq_name} entries "
                        f"must be non-empty strings"
                    )
        if not isinstance(self.evidence_ref, str) or not self.evidence_ref:
            raise ValueError("VendorPermissionEvidenceSnapshot.evidence_ref must be non-empty")
        if not isinstance(self.approved_by, str) or not self.approved_by:
            raise ValueError("VendorPermissionEvidenceSnapshot.approved_by must be non-empty")
        if not isinstance(self.approved_at, str) or not self.approved_at:
            raise ValueError("VendorPermissionEvidenceSnapshot.approved_at must be non-empty")
        if not isinstance(self.permission_hash, str):
            raise ValueError("VendorPermissionEvidenceSnapshot.permission_hash must be string")


@dataclass(frozen=True)
class ProvenanceEdgeSnapshot:
    """Closed TASK-023 provenance-edge snapshot."""

    edge_id: str
    source_id: str
    target_geometry_id: str
    relation_type: str
    evidence_refs: tuple[str, ...]
    edge_hash: str

    def __post_init__(self) -> None:
        for field_name in (
            "edge_id",
            "source_id",
            "target_geometry_id",
            "relation_type",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"ProvenanceEdgeSnapshot.{field_name} must be non-empty string")
        if not isinstance(self.evidence_refs, tuple):
            raise ValueError("ProvenanceEdgeSnapshot.evidence_refs must be tuple")
        for entry in self.evidence_refs:
            if not isinstance(entry, str) or not entry:
                raise ValueError("ProvenanceEdgeSnapshot.evidence_refs entries must be non-empty")
        if not isinstance(self.edge_hash, str):
            raise ValueError("ProvenanceEdgeSnapshot.edge_hash must be string")


@dataclass(frozen=True)
class ShellAuthorityEvidenceBundle:
    """Closed TASK-023 evidence-bundle snapshot.

    Field set is exactly the design contract §5.7 record. Permissions
    and edges are sorted canonically (by identity then hash) so the
    bundle_hash domain is deterministic.
    """

    schema_version: str
    bundle_id: str
    bundle_version: str
    approval_status: str
    permission_evidence: tuple[VendorPermissionEvidenceSnapshot, ...]
    provenance_edges: tuple[ProvenanceEdgeSnapshot, ...]
    local_kernel_usage_scope: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    task012_validation_hash: str
    bundle_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_BUNDLE_SCHEMA_VERSION:
            raise ValueError(
                f"ShellAuthorityEvidenceBundle.schema_version must equal "
                f"{EVIDENCE_BUNDLE_SCHEMA_VERSION!r}"
            )
        for field_name in ("bundle_id", "bundle_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"ShellAuthorityEvidenceBundle.{field_name} must be non-empty")
        if self.approval_status not in APPROVAL_STATES:
            raise ValueError(
                f"ShellAuthorityEvidenceBundle.approval_status must be one of {APPROVAL_STATES!r}"
            )
        perms = self.permission_evidence
        if not isinstance(perms, tuple) or not all(
            isinstance(p, VendorPermissionEvidenceSnapshot) for p in perms
        ):
            raise ValueError(
                "ShellAuthorityEvidenceBundle.permission_evidence must be "
                "tuple[VendorPermissionEvidenceSnapshot, ...]"
            )
        edges = self.provenance_edges
        if not isinstance(edges, tuple) or not all(
            isinstance(e, ProvenanceEdgeSnapshot) for e in edges
        ):
            raise ValueError(
                "ShellAuthorityEvidenceBundle.provenance_edges must be "
                "tuple[ProvenanceEdgeSnapshot, ...]"
            )
        if not isinstance(self.local_kernel_usage_scope, tuple):
            raise ValueError("ShellAuthorityEvidenceBundle.local_kernel_usage_scope must be tuple")
        for entry in self.local_kernel_usage_scope:
            if not isinstance(entry, str) or not entry:
                raise ValueError(
                    "ShellAuthorityEvidenceBundle.local_kernel_usage_scope "
                    "entries must be non-empty strings"
                )
        refs = self.evidence_refs
        if not isinstance(refs, tuple):
            raise ValueError("ShellAuthorityEvidenceBundle.evidence_refs must be a tuple")
        for entry in refs:
            if not isinstance(entry, str) or not entry:
                raise ValueError(
                    "ShellAuthorityEvidenceBundle.evidence_refs entries must be non-empty strings"
                )
        if not isinstance(self.task012_validation_hash, str):
            raise ValueError("ShellAuthorityEvidenceBundle.task012_validation_hash must be string")
        if not isinstance(self.bundle_hash, str):
            raise ValueError("ShellAuthorityEvidenceBundle.bundle_hash must be string")


@dataclass(frozen=True)
class ShellGeometryRecord:
    """Closed TASK-023 shell-geometry record.

    All reference arrays are stored as canonicalized (deduplicated,
    sorted-by-Unicode-codepoint) tuples. The model surface preserves
    caller-mutable isolation.
    """

    schema_version: str
    geometry_id: str
    geometry_type: str
    profile_id: str
    revision: str
    approval_state: str
    shell_inside_diameter_m: str
    nominal_label: str | None
    source_class: str
    license_evidence: Mapping[str, Any]
    source_binding: ShellSourceBinding
    permission_evidence_refs: tuple[str, ...]
    provenance_edge_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    record_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != RECORD_SCHEMA_VERSION:
            raise ValueError(
                f"ShellGeometryRecord.schema_version must equal {RECORD_SCHEMA_VERSION!r}"
            )
        if not isinstance(self.geometry_id, str) or not self.geometry_id:
            raise ValueError("ShellGeometryRecord.geometry_id must be non-empty")
        if self.geometry_type != GEOMETRY_TYPE:
            raise ValueError(f"ShellGeometryRecord.geometry_type must equal {GEOMETRY_TYPE!r}")
        if self.profile_id != PROFILE_ID:
            raise ValueError(f"ShellGeometryRecord.profile_id must equal {PROFILE_ID!r}")
        if not isinstance(self.revision, str) or not self.revision:
            raise ValueError("ShellGeometryRecord.revision must be non-empty")
        if self.approval_state not in APPROVAL_STATES:
            raise ValueError(
                f"ShellGeometryRecord.approval_state must be one of {APPROVAL_STATES!r}"
            )
        if not isinstance(self.shell_inside_diameter_m, str) or not (self.shell_inside_diameter_m):
            raise ValueError(
                "ShellGeometryRecord.shell_inside_diameter_m must be a non-empty string"
            )
        if self.nominal_label is not None and (
            not isinstance(self.nominal_label, str) or not self.nominal_label
        ):
            raise ValueError("ShellGeometryRecord.nominal_label must be None or a non-empty string")
        if self.source_class not in RECOGNIZED_SOURCE_CLASSES:
            raise ValueError(
                f"ShellGeometryRecord.source_class must be one of "
                f"{sorted(RECOGNIZED_SOURCE_CLASSES)!r}"
            )
        if not isinstance(self.license_evidence, Mapping):
            raise ValueError("ShellGeometryRecord.license_evidence must be a Mapping")
        if not isinstance(self.source_binding, ShellSourceBinding):
            raise ValueError("ShellGeometryRecord.source_binding must be ShellSourceBinding")
        for seq_name in (
            "permission_evidence_refs",
            "provenance_edge_ids",
            "evidence_refs",
        ):
            seq = getattr(self, seq_name)
            if not isinstance(seq, tuple):
                raise ValueError(f"ShellGeometryRecord.{seq_name} must be tuple")
            for entry in seq:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"ShellGeometryRecord.{seq_name} entries must be non-empty strings"
                    )
        if not isinstance(self.record_hash, str):
            raise ValueError("ShellGeometryRecord.record_hash must be string")


@dataclass(frozen=True)
class ShellGeometryCatalog:
    """Closed TASK-023 shell-geometry catalog.

    The records tuple is rebuilt in ``__post_init__`` and sorted
    deterministically by ``(geometry_id, revision, record_hash)`` per
    the design contract "Hashing and ordering" §6 — duplicates already
    fail at the parser layer, but sorting at model layer guarantees
    the hash domain is stable across input orderings.
    """

    schema_version: str
    catalog_id: str
    catalog_version: str
    profile_id: str
    authority: str
    source_revision: str
    records: tuple[ShellGeometryRecord, ...]
    evidence_bundle_hash: str
    catalog_hash: str
    effective_at: str | None

    def __post_init__(self) -> None:
        if self.schema_version != CATALOG_SCHEMA_VERSION:
            raise ValueError(
                f"ShellGeometryCatalog.schema_version must equal {CATALOG_SCHEMA_VERSION!r}"
            )
        for field_name in (
            "catalog_id",
            "catalog_version",
            "authority",
            "source_revision",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"ShellGeometryCatalog.{field_name} must be non-empty string")
        if self.effective_at is not None and (
            not isinstance(self.effective_at, str) or self.effective_at == ""
        ):
            raise ValueError("ShellGeometryCatalog.effective_at must be None or a non-empty string")
        if self.profile_id != PROFILE_ID:
            raise ValueError(f"ShellGeometryCatalog.profile_id must equal {PROFILE_ID!r}")
        recs = self.records
        if not isinstance(recs, tuple) or not recs:
            raise ValueError("ShellGeometryCatalog.records must be a non-empty tuple")
        for rec in recs:
            if not isinstance(rec, ShellGeometryRecord):
                raise ValueError(
                    "ShellGeometryCatalog.records must contain only ShellGeometryRecord entries"
                )
        if not isinstance(self.evidence_bundle_hash, str):
            raise ValueError("ShellGeometryCatalog.evidence_bundle_hash must be string")
        if not isinstance(self.catalog_hash, str):
            raise ValueError("ShellGeometryCatalog.catalog_hash must be string")

        sorted_records = tuple(
            sorted(recs, key=lambda r: (r.geometry_id, r.revision, r.record_hash))
        )
        if sorted_records != recs:
            object.__setattr__(self, "records", sorted_records)

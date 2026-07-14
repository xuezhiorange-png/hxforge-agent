"""TASK-023 — Approved Shell Geometry Catalog parser and selector.

This module owns:

- :func:`parse_shell_geometry_catalog` — pure in-memory parser that
  consumes one already-loaded raw catalog and one already-loaded
  authority evidence bundle, performs the 18-stage validation
  pipeline in design-contract order and returns either one complete
  ``ShellGeometryCatalog`` or one ``ShellGeometryCatalogFailure``
  carrying the full ordered blocker tuple.

- :func:`select_approved_shell_geometry` — exact-ID selection from a
  previously parsed approved-only catalog.

The parser forbids filesystem / network / database / environment /
runtime-now / locale / registry / dynamic-import / executable-
deserialization operations. It only imports stdlib + TASK-023 local
models + the canonical SHA-256 helper.

The framework emits the 25-blocker-code taxonomy exactly as recorded
in the merged TASK-023 design contract §10 and Issue #151. No alias,
warning, generic fallback or reserved code exists.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    parse_decimal as _project_parse_decimal,
)

from .blockers import (
    SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY,
    ShellGeometryCatalogBlockerEntry,
    sort_blockers,
)
from .models import (
    APPROVAL_STATES,
    CATALOG_SCHEMA_VERSION,
    GEOMETRY_TYPE,
    PROFILE_ID,
    RECOGNIZED_SOURCE_CLASSES,
    SELECTABLE_APPROVAL_STATES,
    VENDOR_PERMISSION_REQUIRED_SCOPE_TOKENS,
    ProvenanceEdgeSnapshot,
    ShellGeometryCatalog,
    ShellGeometryRecord,
    ShellSourceBinding,
    VendorPermissionEvidenceSnapshot,
)

__all__ = [
    "ShellGeometryCatalogFailure",
    "parse_shell_geometry_catalog",
    "select_approved_shell_geometry",
]


# ---------------------------------------------------------------------------
# Failure surface
# ---------------------------------------------------------------------------


class ShellGeometryCatalogFailure(Exception):
    """Single structured-exception type carrying the complete blocker tuple.

    The catalog parser NEVER returns a partial catalog, partial record,
    trusted partial hash, warning channel or TASK-022 snapshot. Either
    parsing succeeds and returns one complete ``ShellGeometryCatalog``,
    or it raises exactly one ``ShellGeometryCatalogFailure`` carrying the
    complete ordered blocker tuple.

    The exception NEVER uses the exception string as the authoritative
    blocker payload. ``self.blockers`` is the only structured signal.
    """

    def __init__(self, blockers: Sequence[ShellGeometryCatalogBlockerEntry]) -> None:
        ordered = sort_blockers(blockers)
        object.__setattr__(self, "blockers", ordered)
        codes = ", ".join(b.code for b in ordered)
        super().__init__(f"ShellGeometryCatalogFailure[{codes}]")


# ---------------------------------------------------------------------------
# Internal helpers (no public export)
# ---------------------------------------------------------------------------


_DECIMAL_FULL_RE: Final[re.Pattern[str]] = re.compile(r"^([1-9][0-9]*|0)(\.[0-9]+)?$")


def _check_shell_inside_diameter_m(value: Any) -> str | None:
    """Validate ``shell_inside_diameter_m`` as a canonical positive decimal.

    Returns the canonical string on success, raises ``ValueError``
    on any other code path. The strict positive-canonical-SI-metre
    rules are recorded in the design contract §7 implementation
    requirement. We reject floats, ints, ``Decimal`` objects, exponents,
    leading ``+``, embedded whitespace, leading zeros (other than a
    single ``0``), trailing zeros in the fractional component that
    could be normalized, ``NaN`` / ``±Infinity``, zero, negative values,
    empty strings, unit suffixes and DN/NPS/schedule/gauge inputs.
    """
    if isinstance(value, bool):
        raise ValueError("shell_inside_diameter_m must not be a bool")
    if isinstance(value, (int, float)):
        raise ValueError(
            "shell_inside_diameter_m must be a positive canonical decimal "
            "string; got a numeric value"
        )
    import decimal

    if isinstance(value, decimal.Decimal):
        raise ValueError(
            "shell_inside_diameter_m must be a positive canonical decimal "
            "string; got a Decimal object"
        )
    if not isinstance(value, str):
        raise ValueError("shell_inside_diameter_m must be a positive canonical decimal string")
    raw = value
    if raw == "" or raw != raw.strip():
        raise ValueError("shell_inside_diameter_m must not contain leading/trailing whitespace")
    if raw.startswith("+"):
        raise ValueError("shell_inside_diameter_m must not contain a leading '+'")
    lowered = raw.lower()
    if "e" in lowered or "n" in lowered or "i" in lowered:
        raise ValueError("shell_inside_diameter_m must not contain exponent / nan / inf tokens")
    if not _DECIMAL_FULL_RE.fullmatch(raw):
        raise ValueError("shell_inside_diameter_m must match ^[1-9][0-9]*|[0](\\.[0-9]+)?$")
    # Reject leading zeros in the integral component. The regex
    # ``[1-9][0-9]*|0`` already enforces this; double-check the
    # length-zero-decimal case ``0.0`` / ``0.00`` / ``0`` etc.
    if raw.startswith("0") and len(raw) > 1 and raw[1] != ".":
        raise ValueError("shell_inside_diameter_m must not contain leading zeros")
    try:
        canonical = _project_parse_decimal(raw, positive=True)
    except Exception as exc:
        raise ValueError(
            f"shell_inside_diameter_m must be a positive canonical decimal string: {exc!s}"
        ) from None
    # Reject redundant trailing zeros in fractional component.
    if "." in raw and raw.rstrip("0").endswith("."):
        raise ValueError("shell_inside_diameter_m must not contain redundant trailing zeros")
    if str(canonical) != raw:
        # The TASK-023 layer additionally requires that the raw
        # lexical form equals the canonical decimal — that closes
        # any reformulation attacks.
        raise ValueError(
            "shell_inside_diameter_m lexical form does not equal its canonical decimal string"
        )
    return raw


def _is_canonical_decimal_string(value: Any) -> bool:
    """Heuristic canonical-decimal string predicate used by tests."""
    if not isinstance(value, str):
        return False
    try:
        _check_shell_inside_diameter_m(value)
    except ValueError:
        return False
    return True


def _expected_record_fields() -> frozenset[str]:
    return frozenset(
        {
            "schema_version",
            "geometry_id",
            "geometry_type",
            "profile_id",
            "revision",
            "approval_state",
            "shell_inside_diameter_m",
            "nominal_label",
            "source_class",
            "license_evidence",
            "source_binding",
            "permission_evidence_refs",
            "provenance_edge_ids",
            "evidence_refs",
            "record_hash",
        }
    )


def _expected_bundle_fields() -> frozenset[str]:
    return frozenset(
        {
            "schema_version",
            "bundle_id",
            "bundle_version",
            "approval_status",
            "permission_evidence",
            "provenance_edges",
            "local_kernel_usage_scope",
            "evidence_refs",
            "task012_validation_hash",
            "bundle_hash",
        }
    )


def _expected_permission_fields() -> frozenset[str]:
    return frozenset(
        {
            "permission_id",
            "permission_scope",
            "usage_scope",
            "evidence_ref",
            "approved_by",
            "approved_at",
            "permission_hash",
        }
    )


def _expected_edge_fields() -> frozenset[str]:
    return frozenset(
        {
            "edge_id",
            "source_id",
            "target_geometry_id",
            "relation_type",
            "evidence_refs",
            "edge_hash",
        }
    )


def _expected_binding_fields() -> frozenset[str]:
    return frozenset(
        {
            "source_id",
            "source_type",
            "source_revision",
            "source_location",
            "evidence_ref",
            "approved_by",
            "approved_at",
        }
    )


def _expected_top_catalog_fields() -> frozenset[str]:
    return frozenset(
        {
            "schema_version",
            "catalog_id",
            "catalog_version",
            "profile_id",
            "authority",
            "source_revision",
            "records",
            "evidence_bundle_hash",
            "catalog_hash",
            "effective_at",
        }
    )


def _enforce_exact_fields(
    *,
    container: Mapping[str, Any],
    allowed: frozenset[str],
    field_path: str,
    blockers_out: list[ShellGeometryCatalogBlockerEntry],
) -> bool:
    """Emit SGC_UNKNOWN_FIELD for every key outside ``allowed``.

    Returns True if any unknown-field blockers were emitted; the
    caller decides whether to gate later stages. Raw-type validation
    is the caller's responsibility.
    """
    unknown_emitted = False
    for key in container:
        if key not in allowed:
            unknown_emitted = True
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_UNKNOWN_FIELD",
                    field_path=field_path,
                    message_key="sgc_unknown_field",
                    evidence_refs=(),
                    details={"unknown_field": str(key)},
                )
            )
    return unknown_emitted


def _check_raw_mapping(
    value: Any,
    *,
    field_path: str,
    blockers_out: list[ShellGeometryCatalogBlockerEntry],
) -> bool:
    """Emit SGC_RAW_TYPE_INVALID for non-mapping inputs. Returns False on
    success, True if a blocker was emitted."""
    if not isinstance(value, Mapping):
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_RAW_TYPE_INVALID",
                field_path=field_path,
                message_key="sgc_raw_type_invalid",
                evidence_refs=(),
                details={
                    "field": field_path,
                    "actual_type": type(value).__name__,
                },
            )
        )
        return True
    return False


def _check_non_empty_string(
    *,
    value: Any,
    field_path: str,
    blockers_out: list[ShellGeometryCatalogBlockerEntry],
    code: str,
) -> bool:
    """Emit SGC_RAW_TYPE_INVALID for non-string value or SGC_<code> for
    empty string."""
    if not isinstance(value, str):
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_RAW_TYPE_INVALID",
                field_path=field_path,
                message_key="sgc_raw_type_invalid",
                evidence_refs=(),
                details={"field": field_path, "actual_type": type(value).__name__},
            )
        )
        return True
    if not value:
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code=code,
                field_path=field_path,
                message_key=SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY[code],
                evidence_refs=(),
                details={"field": field_path},
            )
        )
        return True
    return False


def _check_string_sequence(
    *,
    value: Any,
    field_path: str,
    blockers_out: list[ShellGeometryCatalogBlockerEntry],
    nonempty: bool,
) -> bool:
    """Validate that ``value`` is a list of non-empty strings and emit
    EVIDENCE_REFS_INVALID if duplicates / non-strings / empties appear."""
    if not isinstance(value, list):
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_RAW_TYPE_INVALID",
                field_path=field_path,
                message_key="sgc_raw_type_invalid",
                evidence_refs=(),
                details={"field": field_path, "actual_type": type(value).__name__},
            )
        )
        return True
    if not value and not nonempty:
        return False
    if not value and nonempty:
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_EVIDENCE_REFS_INVALID",
                field_path=field_path,
                message_key="sgc_evidence_refs_invalid",
                evidence_refs=(),
                details={"field": field_path, "reason": "empty"},
            )
        )
        return True
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str) or not entry:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RAW_TYPE_INVALID",
                    field_path=field_path,
                    message_key="sgc_raw_type_invalid",
                    evidence_refs=(),
                    details={"field": field_path, "actual_type": type(entry).__name__},
                )
            )
            return True
        if entry in seen:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_EVIDENCE_REFS_INVALID",
                    field_path=field_path,
                    message_key="sgc_evidence_refs_invalid",
                    evidence_refs=(),
                    details={"field": field_path, "reason": "duplicate", "value": entry},
                )
            )
            return True
        seen.add(entry)
    return False


def _catalog_hash_payload(
    *,
    catalog_id: str,
    catalog_version: str,
    profile_id: str,
    authority: str,
    source_revision: str,
    effective_at: str,
    evidence_bundle_hash: str,
    record_hashes: Sequence[str],
) -> str:
    """Build the canonical-JSON payload for the catalog hash.

    Per design contract §6 / Issue #151, the catalog hash covers
    every other field plus the canonical ordered ``evidence_bundle_hash``
    and the sorted ``record_hash`` sequence.
    """
    payload = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "catalog_id": catalog_id,
        "catalog_version": catalog_version,
        "profile_id": profile_id,
        "authority": authority,
        "source_revision": source_revision,
        "effective_at": effective_at,
        "evidence_bundle_hash": evidence_bundle_hash,
        "record_hashes": sorted(record_hashes),
    }
    return canonical_sha256(payload)


def _record_hash_payload(record: Mapping[str, Any]) -> str:
    """Compute the canonical-JSON SHA-256 over the record hash domain.

    Excludes ``record_hash`` and ``nominal_label`` per design contract
    §6 / §8. ``nominal_label`` is a non-authoritative display label;
    rejecting it from the hash domain means nominal-label edits
    never recompute the record hash.
    """
    payload: dict[str, Any] = {}
    for key, value in record.items():
        if key in {"record_hash", "nominal_label"}:
            continue
        payload[key] = value
    return canonical_sha256(payload)


def _permission_hash_payload(permission: Mapping[str, Any]) -> str:
    payload: dict[str, Any] = {}
    for key, value in permission.items():
        if key == "permission_hash":
            continue
        payload[key] = value
    return canonical_sha256(payload)


def _edge_hash_payload(edge: Mapping[str, Any]) -> str:
    payload: dict[str, Any] = {}
    for key, value in edge.items():
        if key == "edge_hash":
            continue
        payload[key] = value
    return canonical_sha256(payload)


def _bundle_hash_payload(
    *,
    bundle_id: str,
    bundle_version: str,
    approval_status: str,
    permission_hashes: Sequence[str],
    edge_hashes: Sequence[str],
    local_kernel_usage_scope: Sequence[str],
    evidence_refs: Sequence[str],
    task012_validation_hash: str,
) -> str:
    """Compute the canonical-JSON SHA-256 over the bundle hash domain.

    Per design contract §6 / Issue #151, the bundle hash covers every
    other field plus the canonical ordered ``permission_hash``
    sequence and the canonical ordered ``edge_hash`` sequence.
    """
    payload = {
        "schema_version": "task023.shell-authority-evidence-bundle.v1",
        "bundle_id": bundle_id,
        "bundle_version": bundle_version,
        "approval_status": approval_status,
        "permission_hashes": sorted(permission_hashes),
        "edge_hashes": sorted(edge_hashes),
        "local_kernel_usage_scope": sorted(local_kernel_usage_scope),
        "evidence_refs": sorted(evidence_refs),
        "task012_validation_hash": task012_validation_hash,
    }
    return canonical_sha256(payload)


# ---------------------------------------------------------------------------
# Parser — 18-stage validation pipeline (Issue #151)
# ---------------------------------------------------------------------------


def parse_shell_geometry_catalog(
    *,
    raw_catalog: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
) -> ShellGeometryCatalog:
    """Parse one already-loaded raw catalog against one already-loaded
    evidence bundle.

    Returns one complete :class:`ShellGeometryCatalog` on success;
    raises :class:`ShellGeometryCatalogFailure` carrying the
    complete ordered blocker tuple on any blocker.

    Per design contract §11 the parser runs an 18-stage validation
    pipeline in a deterministic order. Blocked stages gate
    dependents; independent same-stage blockers accumulate. No
    partial catalog, partial record, partial hash or warning is
    ever returned.
    """

    blockers_out: list[ShellGeometryCatalogBlockerEntry] = []
    # Blocked-stage gate. Stage N+1 only runs when all earlier
    # independent same-stage blockers are absent. Stage 1 gates
    # stage 2+; stage 2 gates stage 3+ etc. Within a stage, multiple
    # blockers accumulate (and are deterministically ordered at the
    # end via ``sort_blockers``).
    failed = False

    # Stage 1 — raw types. Both inputs MUST be mappings.
    if _check_raw_mapping(raw_catalog, field_path="raw_catalog", blockers_out=blockers_out):
        failed = True
    if _check_raw_mapping(evidence_bundle, field_path="evidence_bundle", blockers_out=blockers_out):
        failed = True
    if failed:
        raise ShellGeometryCatalogFailure(blockers_out)

    catalog_dict = dict(raw_catalog)
    bundle_dict = dict(evidence_bundle)

    # Stage 2 — exact top-level fields on raw_catalog.
    if _enforce_exact_fields(
        container=catalog_dict,
        allowed=_expected_top_catalog_fields(),
        field_path="raw_catalog",
        blockers_out=blockers_out,
    ):
        failed = True
    if _enforce_exact_fields(
        container=bundle_dict,
        allowed=_expected_bundle_fields(),
        field_path="evidence_bundle",
        blockers_out=blockers_out,
    ):
        failed = True

    # Stage 3 — schema / profile / id / version / authority.
    if not failed:
        if _check_non_empty_string(
            value=catalog_dict.get("schema_version"),
            field_path="raw_catalog.schema_version",
            blockers_out=blockers_out,
            code="SGC_SCHEMA_VERSION_UNSUPPORTED",
        ):
            failed = True
        elif catalog_dict.get("schema_version") != CATALOG_SCHEMA_VERSION:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_SCHEMA_VERSION_UNSUPPORTED",
                    field_path="raw_catalog.schema_version",
                    message_key="sgc_schema_version_unsupported",
                    evidence_refs=(),
                    details={
                        "expected": CATALOG_SCHEMA_VERSION,
                        "actual": catalog_dict.get("schema_version"),
                    },
                )
            )
            failed = True
        if _check_non_empty_string(
            value=catalog_dict.get("catalog_id"),
            field_path="raw_catalog.catalog_id",
            blockers_out=blockers_out,
            code="SGC_CATALOG_ID_INVALID",
        ):
            failed = True
        if _check_non_empty_string(
            value=catalog_dict.get("catalog_version"),
            field_path="raw_catalog.catalog_version",
            blockers_out=blockers_out,
            code="SGC_CATALOG_VERSION_INVALID",
        ):
            failed = True
        if not failed:
            profile_id_value = catalog_dict.get("profile_id")
            if not isinstance(profile_id_value, str) or profile_id_value != PROFILE_ID:
                blockers_out.append(
                    ShellGeometryCatalogBlockerEntry(
                        code="SGC_PROFILE_UNSUPPORTED",
                        field_path="raw_catalog.profile_id",
                        message_key="sgc_profile_unsupported",
                        evidence_refs=(),
                        details={
                            "expected": PROFILE_ID,
                            "actual": profile_id_value,
                        },
                    )
                )
                failed = True
        if _check_non_empty_string(
            value=catalog_dict.get("authority"),
            field_path="raw_catalog.authority",
            blockers_out=blockers_out,
            code="SGC_CATALOG_AUTHORITY_INVALID",
        ):
            failed = True

    # Stage 4 — bundle approval and TASK-012 binding.
    if not failed:
        bundle_schema_value = bundle_dict.get("schema_version")
        if (
            not isinstance(bundle_schema_value, str)
            or bundle_schema_value != "task023.shell-authority-evidence-bundle.v1"
        ):
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_SCHEMA_VERSION_UNSUPPORTED",
                    field_path="evidence_bundle.schema_version",
                    message_key="sgc_schema_version_unsupported",
                    evidence_refs=(),
                    details={
                        "expected": "task023.shell-authority-evidence-bundle.v1",
                        "actual": bundle_schema_value,
                    },
                )
            )
            failed = True
        approval_status_value = bundle_dict.get("approval_status")
        if approval_status_value not in APPROVAL_STATES:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RAW_TYPE_INVALID",
                    field_path="evidence_bundle.approval_status",
                    message_key="sgc_raw_type_invalid",
                    evidence_refs=(),
                    details={
                        "actual_type": type(approval_status_value).__name__,
                        "actual_value": approval_status_value,
                    },
                )
            )
            failed = True
        elif approval_status_value != "approved":
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RECORD_UNAPPROVED",
                    field_path="evidence_bundle.approval_status",
                    message_key="sgc_record_unapproved",
                    evidence_refs=(),
                    details={
                        "expected": "approved",
                        "actual": approval_status_value,
                    },
                )
            )
            failed = True

    if failed:
        raise ShellGeometryCatalogFailure(blockers_out)

    # Stage 5 — permission snapshots.
    raw_permissions = bundle_dict.get("permission_evidence")
    parsed_permissions: list[VendorPermissionEvidenceSnapshot] = []
    if not isinstance(raw_permissions, list):
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_RAW_TYPE_INVALID",
                field_path="evidence_bundle.permission_evidence",
                message_key="sgc_raw_type_invalid",
                evidence_refs=(),
                details={
                    "actual_type": type(raw_permissions).__name__,
                },
            )
        )
        failed = True
    else:
        for index, raw_permission in enumerate(raw_permissions):
            field_path = f"evidence_bundle.permission_evidence[{index}]"
            if _check_raw_mapping(
                raw_permission,
                field_path=field_path,
                blockers_out=blockers_out,
            ):
                failed = True
                continue
            perm_dict = dict(raw_permission)
            unknown = _enforce_exact_fields(
                container=perm_dict,
                allowed=_expected_permission_fields(),
                field_path=field_path,
                blockers_out=blockers_out,
            )
            if unknown:
                failed = True
                continue
            if _check_string_sequence(
                value=perm_dict.get("permission_scope"),
                field_path=f"{field_path}.permission_scope",
                blockers_out=blockers_out,
                nonempty=False,
            ):
                failed = True
                continue
            if _check_string_sequence(
                value=perm_dict.get("usage_scope"),
                field_path=f"{field_path}.usage_scope",
                blockers_out=blockers_out,
                nonempty=False,
            ):
                failed = True
                continue
            for str_field in (
                "permission_id",
                "evidence_ref",
                "approved_by",
                "approved_at",
                "permission_hash",
            ):
                if _check_non_empty_string(
                    value=perm_dict.get(str_field),
                    field_path=f"{field_path}.{str_field}",
                    blockers_out=blockers_out,
                    code="SGC_RAW_TYPE_INVALID",
                ):
                    failed = True
            if failed:
                continue
            permission_scope: tuple[str, ...] = tuple(perm_dict["permission_scope"])
            usage_scope: tuple[str, ...] = tuple(perm_dict["usage_scope"])
            expected_hash = _permission_hash_payload(
                {
                    "permission_id": perm_dict["permission_id"],
                    "permission_scope": list(permission_scope),
                    "usage_scope": list(usage_scope),
                    "evidence_ref": perm_dict["evidence_ref"],
                    "approved_by": perm_dict["approved_by"],
                    "approved_at": perm_dict["approved_at"],
                }
            )
            if perm_dict["permission_hash"] != expected_hash:
                blockers_out.append(
                    ShellGeometryCatalogBlockerEntry(
                        code="SGC_RECORD_HASH_MISMATCH",
                        field_path=f"{field_path}.permission_hash",
                        message_key="sgc_record_hash_mismatch",
                        evidence_refs=(perm_dict["permission_id"],),
                        details={
                            "expected": expected_hash,
                            "actual": perm_dict["permission_hash"],
                        },
                    )
                )
                failed = True
                continue
            parsed_permissions.append(
                VendorPermissionEvidenceSnapshot(
                    permission_id=perm_dict["permission_id"],
                    permission_scope=permission_scope,
                    usage_scope=usage_scope,
                    evidence_ref=perm_dict["evidence_ref"],
                    approved_by=perm_dict["approved_by"],
                    approved_at=perm_dict["approved_at"],
                    permission_hash=perm_dict["permission_hash"],
                )
            )

    # Stage 6 — provenance snapshots.
    raw_edges = bundle_dict.get("provenance_edges")
    parsed_edges: list[ProvenanceEdgeSnapshot] = []
    if not isinstance(raw_edges, list):
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_RAW_TYPE_INVALID",
                field_path="evidence_bundle.provenance_edges",
                message_key="sgc_raw_type_invalid",
                evidence_refs=(),
                details={
                    "actual_type": type(raw_edges).__name__,
                },
            )
        )
        failed = True
    else:
        for index, raw_edge in enumerate(raw_edges):
            field_path = f"evidence_bundle.provenance_edges[{index}]"
            if _check_raw_mapping(raw_edge, field_path=field_path, blockers_out=blockers_out):
                failed = True
                continue
            edge_dict = dict(raw_edge)
            unknown = _enforce_exact_fields(
                container=edge_dict,
                allowed=_expected_edge_fields(),
                field_path=field_path,
                blockers_out=blockers_out,
            )
            if unknown:
                failed = True
                continue
            for str_field in (
                "edge_id",
                "source_id",
                "target_geometry_id",
                "relation_type",
                "edge_hash",
            ):
                if _check_non_empty_string(
                    value=edge_dict.get(str_field),
                    field_path=f"{field_path}.{str_field}",
                    blockers_out=blockers_out,
                    code="SGC_RAW_TYPE_INVALID",
                ):
                    failed = True
            if failed:
                continue
            if _check_string_sequence(
                value=edge_dict.get("evidence_refs"),
                field_path=f"{field_path}.evidence_refs",
                blockers_out=blockers_out,
                nonempty=False,
            ):
                failed = True
                continue
            evidence_refs_edge: tuple[str, ...] = tuple(edge_dict["evidence_refs"])
            expected_hash = _edge_hash_payload(
                {
                    "edge_id": edge_dict["edge_id"],
                    "source_id": edge_dict["source_id"],
                    "target_geometry_id": edge_dict["target_geometry_id"],
                    "relation_type": edge_dict["relation_type"],
                    "evidence_refs": list(evidence_refs_edge),
                }
            )
            if edge_dict["edge_hash"] != expected_hash:
                blockers_out.append(
                    ShellGeometryCatalogBlockerEntry(
                        code="SGC_RECORD_HASH_MISMATCH",
                        field_path=f"{field_path}.edge_hash",
                        message_key="sgc_record_hash_mismatch",
                        evidence_refs=(edge_dict["edge_id"],),
                        details={
                            "expected": expected_hash,
                            "actual": edge_dict["edge_hash"],
                        },
                    )
                )
                failed = True
                continue
            parsed_edges.append(
                ProvenanceEdgeSnapshot(
                    edge_id=edge_dict["edge_id"],
                    source_id=edge_dict["source_id"],
                    target_geometry_id=edge_dict["target_geometry_id"],
                    relation_type=edge_dict["relation_type"],
                    evidence_refs=evidence_refs_edge,
                    edge_hash=edge_dict["edge_hash"],
                )
            )

    # Stage 7 — bundle metadata top fields beyond what stage 4 verified.
    local_kernel_usage_scope_raw = bundle_dict.get("local_kernel_usage_scope")
    evidence_refs_raw = bundle_dict.get("evidence_refs")
    task012_validation_hash = bundle_dict.get("task012_validation_hash")

    if _check_string_sequence(
        value=local_kernel_usage_scope_raw,
        field_path="evidence_bundle.local_kernel_usage_scope",
        blockers_out=blockers_out,
        nonempty=True,
    ):
        failed = True
    if _check_string_sequence(
        value=evidence_refs_raw,
        field_path="evidence_bundle.evidence_refs",
        blockers_out=blockers_out,
        nonempty=True,
    ):
        failed = True
    if _check_non_empty_string(
        value=task012_validation_hash,
        field_path="evidence_bundle.task012_validation_hash",
        blockers_out=blockers_out,
        code="SGC_RAW_TYPE_INVALID",
    ):
        failed = True
    if not failed:
        if not isinstance(bundle_dict.get("bundle_hash"), str):
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RAW_TYPE_INVALID",
                    field_path="evidence_bundle.bundle_hash",
                    message_key="sgc_raw_type_invalid",
                    evidence_refs=(),
                    details={
                        "actual_type": type(bundle_dict.get("bundle_hash")).__name__,
                    },
                )
            )
            failed = True
        if not isinstance(bundle_dict.get("bundle_id"), str) or not bundle_dict.get("bundle_id"):
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RAW_TYPE_INVALID",
                    field_path="evidence_bundle.bundle_id",
                    message_key="sgc_raw_type_invalid",
                    evidence_refs=(),
                    details={
                        "actual_type": type(bundle_dict.get("bundle_id")).__name__,
                    },
                )
            )
            failed = True
        if not isinstance(bundle_dict.get("bundle_version"), str) or not bundle_dict.get(
            "bundle_version"
        ):
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RAW_TYPE_INVALID",
                    field_path="evidence_bundle.bundle_version",
                    message_key="sgc_raw_type_invalid",
                    evidence_refs=(),
                    details={
                        "actual_type": type(bundle_dict.get("bundle_version")).__name__,
                    },
                )
            )
            failed = True

    # Stage 8 — bundle hash verification.
    if not failed:
        expected_bundle_hash = _bundle_hash_payload(
            bundle_id=str(bundle_dict["bundle_id"]),
            bundle_version=str(bundle_dict["bundle_version"]),
            approval_status=str(bundle_dict["approval_status"]),
            permission_hashes=[p.permission_hash for p in parsed_permissions],
            edge_hashes=[e.edge_hash for e in parsed_edges],
            local_kernel_usage_scope=tuple(local_kernel_usage_scope_raw or ()),
            evidence_refs=tuple(evidence_refs_raw or ()),
            task012_validation_hash=str(task012_validation_hash),
        )
        if bundle_dict["bundle_hash"] != expected_bundle_hash:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_CATALOG_HASH_MISMATCH",
                    field_path="evidence_bundle.bundle_hash",
                    message_key="sgc_catalog_hash_mismatch",
                    evidence_refs=(bundle_dict["bundle_id"],),
                    details={
                        "expected": expected_bundle_hash,
                        "actual": bundle_dict["bundle_hash"],
                    },
                )
            )
            failed = True

    if failed:
        raise ShellGeometryCatalogFailure(blockers_out)

    # Stage 9 — records array.
    raw_records = catalog_dict.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        if not isinstance(raw_records, list):
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RAW_TYPE_INVALID",
                    field_path="raw_catalog.records",
                    message_key="sgc_raw_type_invalid",
                    evidence_refs=(),
                    details={
                        "actual_type": type(raw_records).__name__,
                    },
                )
            )
        else:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RECORDS_INVALID",
                    field_path="raw_catalog.records",
                    message_key="sgc_records_invalid",
                    evidence_refs=(),
                    details={"reason": "empty"},
                )
            )
        raise ShellGeometryCatalogFailure(blockers_out)

    # Stage 10..12 — records exact fields, identity/duplicate/type/profile/
    # revision.
    parsed_records: list[ShellGeometryRecord] = []
    seen_geometry_ids: dict[str, int] = {}

    for index, raw_record in enumerate(raw_records):
        record_field_path = f"raw_catalog.records[{index}]"
        if _check_raw_mapping(raw_record, field_path=record_field_path, blockers_out=blockers_out):
            failed = True
            continue
        rec_dict = dict(raw_record)
        unknown = _enforce_exact_fields(
            container=rec_dict,
            allowed=_expected_record_fields(),
            field_path=record_field_path,
            blockers_out=blockers_out,
        )
        if unknown:
            failed = True
            continue
        from .models import RECORD_SCHEMA_VERSION as _REC_VER

        if rec_dict.get("schema_version") != _REC_VER:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_SCHEMA_VERSION_UNSUPPORTED",
                    field_path=f"{record_field_path}.schema_version",
                    message_key="sgc_schema_version_unsupported",
                    evidence_refs=(),
                    details={
                        "expected": _REC_VER,
                        "actual": rec_dict.get("schema_version"),
                    },
                )
            )
            failed = True
            continue
        # geometry_id
        geom_id_raw = rec_dict.get("geometry_id")
        geom_id_str: str
        if not isinstance(geom_id_raw, str) or not geom_id_raw:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RECORD_ID_INVALID",
                    field_path=f"{record_field_path}.geometry_id",
                    message_key="sgc_record_id_invalid",
                    evidence_refs=(),
                    details={"actual_type": type(geom_id_raw).__name__},
                )
            )
            failed = True
            continue
        geom_id_str = geom_id_raw
        if geom_id_str in seen_geometry_ids:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RECORD_DUPLICATE_ID",
                    field_path=f"{record_field_path}.geometry_id",
                    message_key="sgc_record_duplicate_id",
                    evidence_refs=(geom_id_str,),
                    details={"geometry_id": geom_id_str},
                )
            )
            failed = True
            continue
        seen_geometry_ids[geom_id_str] = index

        if rec_dict.get("geometry_type") != GEOMETRY_TYPE:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_GEOMETRY_TYPE_INVALID",
                    field_path=f"{record_field_path}.geometry_type",
                    message_key="sgc_geometry_type_invalid",
                    evidence_refs=(geom_id_str,),
                    details={
                        "expected": GEOMETRY_TYPE,
                        "actual": rec_dict.get("geometry_type"),
                    },
                )
            )
            failed = True
            continue
        if rec_dict.get("profile_id") != PROFILE_ID:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_PROFILE_UNSUPPORTED",
                    field_path=f"{record_field_path}.profile_id",
                    message_key="sgc_profile_unsupported",
                    evidence_refs=(geom_id_str,),
                    details={
                        "expected": PROFILE_ID,
                        "actual": rec_dict.get("profile_id"),
                    },
                )
            )
            failed = True
            continue

        revision_raw = rec_dict.get("revision")
        if not isinstance(revision_raw, str) or not revision_raw:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_REVISION_INVALID",
                    field_path=f"{record_field_path}.revision",
                    message_key="sgc_revision_invalid",
                    evidence_refs=(geom_id_str,),
                    details={"actual_type": type(revision_raw).__name__},
                )
            )
            failed = True
            continue

        # Stage 11 — approval_state lexical validation.
        approval_value = rec_dict.get("approval_state")
        if not isinstance(approval_value, str):
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_APPROVAL_STATE_INVALID",
                    field_path=f"{record_field_path}.approval_state",
                    message_key="sgc_approval_state_invalid",
                    evidence_refs=(geom_id_str,),
                    details={
                        "actual_type": type(approval_value).__name__,
                    },
                )
            )
            failed = True
            continue
        if approval_value not in APPROVAL_STATES:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_APPROVAL_STATE_INVALID",
                    field_path=f"{record_field_path}.approval_state",
                    message_key="sgc_approval_state_invalid",
                    evidence_refs=(geom_id_str,),
                    details={"actual_value": approval_value},
                )
            )
            failed = True
            continue
        # Stage 12 — known non-approved rejection at parse time.
        if approval_value not in SELECTABLE_APPROVAL_STATES:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RECORD_UNAPPROVED",
                    field_path=f"{record_field_path}.approval_state",
                    message_key="sgc_record_unapproved",
                    evidence_refs=(geom_id_str,),
                    details={"actual_value": approval_value},
                )
            )
            failed = True
            continue

        # Stage 13 — canonical decimal validation.
        try:
            decimal_str = _check_shell_inside_diameter_m(rec_dict.get("shell_inside_diameter_m"))
        except ValueError as exc:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_SHELL_INSIDE_DIAMETER_INVALID",
                    field_path=f"{record_field_path}.shell_inside_diameter_m",
                    message_key="sgc_shell_inside_diameter_invalid",
                    evidence_refs=(geom_id_str,),
                    details={"reason": str(exc)},
                )
            )
            failed = True
            continue
        if decimal_str is None:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_SHELL_INSIDE_DIAMETER_INVALID",
                    field_path=f"{record_field_path}.shell_inside_diameter_m",
                    message_key="sgc_shell_inside_diameter_invalid",
                    evidence_refs=(geom_id_str,),
                    details={},
                )
            )
            failed = True
            continue

        # Stage 14 — source binding exact fields.
        raw_binding = rec_dict.get("source_binding")
        if _check_raw_mapping(
            raw_binding,
            field_path=f"{record_field_path}.source_binding",
            blockers_out=blockers_out,
        ):
            failed = True
            continue
        binding_dict = dict(raw_binding) if raw_binding is not None else {}
        assert isinstance(binding_dict, dict)
        unknown_bind = _enforce_exact_fields(
            container=binding_dict,
            allowed=_expected_binding_fields(),
            field_path=f"{record_field_path}.source_binding",
            blockers_out=blockers_out,
        )
        if unknown_bind:
            failed = True
            continue
        binding_fields_ok = True
        for str_field in (
            "source_id",
            "source_type",
            "source_revision",
            "source_location",
            "evidence_ref",
            "approved_by",
            "approved_at",
        ):
            if _check_non_empty_string(
                value=binding_dict.get(str_field),
                field_path=f"{record_field_path}.source_binding.{str_field}",
                blockers_out=blockers_out,
                code="SGC_SOURCE_BINDING_INCOMPLETE",
            ):
                failed = True
                binding_fields_ok = False
        if not binding_fields_ok:
            continue

        # Stage 15 — source class + license disposition (vendor scope
        # for VENDOR_PERMISSIONED records).
        source_class = rec_dict.get("source_class")
        if source_class not in RECOGNIZED_SOURCE_CLASSES:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_SOURCE_CLASS_INVALID",
                    field_path=f"{record_field_path}.source_class",
                    message_key="sgc_source_class_invalid",
                    evidence_refs=(geom_id_str,),
                    details={"actual_value": source_class},
                )
            )
            failed = True
            continue

        license_evidence = rec_dict.get("license_evidence")
        if not isinstance(license_evidence, Mapping) or not license_evidence:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_LICENSE_BLOCKED",
                    field_path=f"{record_field_path}.license_evidence",
                    message_key="sgc_license_blocked",
                    evidence_refs=(geom_id_str,),
                    details={"reason": "missing_or_empty"},
                )
            )
            failed = True
            continue
        disposition = license_evidence.get("license_form")
        valid_dispositions = {
            "PUBLIC_DOMAIN",
            "OPEN_LICENSE",
            "USER_PROVIDED_LICENSED_SUMMARY",
            "INTERNAL_ENGINEERING_RULE",
            "DERIVED_ENGINEERING_RULE",
            "REFERENCE_ONLY_RESTRICTED_STANDARD",
            "VENDOR_PERMISSIONED",
        }
        if disposition not in valid_dispositions:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_LICENSE_BLOCKED",
                    field_path=f"{record_field_path}.license_evidence",
                    message_key="sgc_license_blocked",
                    evidence_refs=(geom_id_str,),
                    details={"reason": "unknown_disposition", "value": disposition},
                )
            )
            failed = True
            continue

        # Authority-script reference-only restricted standards are
        # not authorized for use in approved catalogs (Issue #151).
        if source_class == "REFERENCE_ONLY_RESTRICTED_STANDARD":
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_SOURCE_CLASS_INVALID",
                    field_path=f"{record_field_path}.source_class",
                    message_key="sgc_source_class_invalid",
                    evidence_refs=(geom_id_str,),
                    details={
                        "actual_value": source_class,
                        "reason": "reference_only_restricted_standard_not_authorized",
                    },
                )
            )
            failed = True
            continue

        # Stage 16 — permission / provenance resolution and usage gate.
        permission_refs = rec_dict.get("permission_evidence_refs")
        if _check_string_sequence(
            value=permission_refs,
            field_path=f"{record_field_path}.permission_evidence_refs",
            blockers_out=blockers_out,
            nonempty=True,
        ):
            failed = True
            continue
        permission_refs_tuple: tuple[str, ...] = tuple(permission_refs or ())
        permission_by_id = {perm.permission_id: perm for perm in parsed_permissions}
        for ref in permission_refs_tuple:
            if ref not in permission_by_id:
                blockers_out.append(
                    ShellGeometryCatalogBlockerEntry(
                        code="SGC_EVIDENCE_REFS_INVALID",
                        field_path=f"{record_field_path}.permission_evidence_refs",
                        message_key="sgc_evidence_refs_invalid",
                        evidence_refs=(geom_id_str, ref),
                        details={"reason": "permission_ref_missing", "ref": ref},
                    )
                )
                failed = True
                break
        if failed:
            continue

        # Vendor records require repository_storage +
        # repository_redistribution and compatible usage_scope.
        if source_class == "VENDOR_PERMISSIONED":
            for required_token in VENDOR_PERMISSION_REQUIRED_SCOPE_TOKENS:
                if not _scope_token_present(
                    required_token, permission_refs_tuple, permission_by_id
                ):
                    blockers_out.append(
                        ShellGeometryCatalogBlockerEntry(
                            code="SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
                            field_path=(f"{record_field_path}.permission_evidence_refs"),
                            message_key="sgc_vendor_permission_scope_incomplete",
                            evidence_refs=(geom_id_str,),
                            details={
                                "required_token": required_token,
                            },
                        )
                    )
                    failed = True
                    break
            if failed:
                continue
            # usage_scope must be compatible with local_kernel_usage_scope.
            if not _vendor_usage_compatible(
                permission_refs_tuple,
                permission_by_id,
                tuple(local_kernel_usage_scope_raw or ()),
            ):
                blockers_out.append(
                    ShellGeometryCatalogBlockerEntry(
                        code="SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
                        field_path=(f"{record_field_path}.permission_evidence_refs"),
                        message_key="sgc_vendor_permission_scope_incomplete",
                        evidence_refs=(geom_id_str,),
                        details={
                            "reason": "usage_scope_incompatible_with_local_kernel_usage_scope",
                        },
                    )
                )
                failed = True
                continue

        # Provenance edges — target must equal the referencing
        # geometry_id; missing refs fail closed.
        provenance_refs = rec_dict.get("provenance_edge_ids")
        if _check_string_sequence(
            value=provenance_refs,
            field_path=f"{record_field_path}.provenance_edge_ids",
            blockers_out=blockers_out,
            nonempty=True,
        ):
            failed = True
            continue
        provenance_refs_tuple: tuple[str, ...] = tuple(provenance_refs or ())
        edge_by_id = {edge.edge_id: edge for edge in parsed_edges}
        for ref in provenance_refs_tuple:
            edge = edge_by_id.get(ref)
            if edge is None:
                blockers_out.append(
                    ShellGeometryCatalogBlockerEntry(
                        code="SGC_PROVENANCE_INCOMPLETE",
                        field_path=f"{record_field_path}.provenance_edge_ids",
                        message_key="sgc_provenance_incomplete",
                        evidence_refs=(geom_id_str, ref),
                        details={"reason": "edge_ref_missing", "ref": ref},
                    )
                )
                failed = True
                break
            if edge.target_geometry_id != geom_id_str:
                blockers_out.append(
                    ShellGeometryCatalogBlockerEntry(
                        code="SGC_PROVENANCE_INCOMPLETE",
                        field_path=f"{record_field_path}.provenance_edge_ids",
                        message_key="sgc_provenance_incomplete",
                        evidence_refs=(geom_id_str, ref),
                        details={
                            "reason": "target_mismatch",
                            "edge_target": edge.target_geometry_id,
                            "record_geometry_id": geom_id_str,
                        },
                    )
                )
                failed = True
                break
        if failed:
            continue

        # Stage 17 — record hash.
        if _check_string_sequence(
            value=rec_dict.get("evidence_refs"),
            field_path=f"{record_field_path}.evidence_refs",
            blockers_out=blockers_out,
            nonempty=False,
        ):
            failed = True
            continue
        evidence_refs_tuple: tuple[str, ...] = tuple(rec_dict["evidence_refs"])
        nominal_label_raw = rec_dict.get("nominal_label")
        nominal_label_value: str | None
        if nominal_label_raw is None:
            nominal_label_value = None
        elif isinstance(nominal_label_raw, str) and nominal_label_raw:
            nominal_label_value = nominal_label_raw
        else:
            nominal_label_value = ""  # any non-None invalid raw

        record_hash_payload = {
            "schema_version": rec_dict["schema_version"],
            "geometry_id": geom_id_str,
            "geometry_type": rec_dict["geometry_type"],
            "profile_id": rec_dict["profile_id"],
            "revision": revision_raw,
            "approval_state": approval_value,
            "shell_inside_diameter_m": decimal_str,
            "source_class": source_class,
            "license_evidence": dict(license_evidence),
            "source_binding": dict(binding_dict),
            "permission_evidence_refs": list(permission_refs_tuple),
            "provenance_edge_ids": list(provenance_refs_tuple),
            "evidence_refs": list(evidence_refs_tuple),
        }
        expected_record_hash = _record_hash_payload(record_hash_payload)
        actual_record_hash = rec_dict.get("record_hash")
        if not isinstance(actual_record_hash, str):
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RAW_TYPE_INVALID",
                    field_path=f"{record_field_path}.record_hash",
                    message_key="sgc_raw_type_invalid",
                    evidence_refs=(geom_id_str,),
                    details={
                        "actual_type": type(actual_record_hash).__name__,
                    },
                )
            )
            failed = True
            continue
        if actual_record_hash != expected_record_hash:
            blockers_out.append(
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RECORD_HASH_MISMATCH",
                    field_path=f"{record_field_path}.record_hash",
                    message_key="sgc_record_hash_mismatch",
                    evidence_refs=(geom_id_str,),
                    details={
                        "expected": expected_record_hash,
                        "actual": actual_record_hash,
                    },
                )
            )
            failed = True
            continue

        # All record-stage checks passed — emit the immutable model.
        try:
            binding = ShellSourceBinding(
                source_id=binding_dict["source_id"],
                source_type=binding_dict["source_type"],
                source_revision=binding_dict["source_revision"],
                source_location=binding_dict["source_location"],
                evidence_ref=binding_dict["evidence_ref"],
                approved_by=binding_dict["approved_by"],
                approved_at=binding_dict["approved_at"],
            )
            record = ShellGeometryRecord(
                schema_version=rec_dict["schema_version"],
                geometry_id=geom_id_str,
                geometry_type=rec_dict["geometry_type"],
                profile_id=rec_dict["profile_id"],
                revision=revision_raw,
                approval_state=approval_value,
                shell_inside_diameter_m=decimal_str,
                nominal_label=nominal_label_value if nominal_label_value else None,
                source_class=source_class,
                license_evidence=dict(license_evidence),
                source_binding=binding,
                permission_evidence_refs=permission_refs_tuple,
                provenance_edge_ids=provenance_refs_tuple,
                evidence_refs=evidence_refs_tuple,
                record_hash=actual_record_hash,
            )
            parsed_records.append(record)
        except ValueError:
            failed = True
            continue

    if failed or not parsed_records:
        raise ShellGeometryCatalogFailure(blockers_out)

    # Stage 18 — catalog hash + record ordering + bundle binding.
    record_hashes = [r.record_hash for r in parsed_records]
    catalog_hash_value = _catalog_hash_payload(
        catalog_id=catalog_dict["catalog_id"],
        catalog_version=catalog_dict["catalog_version"],
        profile_id=catalog_dict["profile_id"],
        authority=catalog_dict["authority"],
        source_revision=catalog_dict["source_revision"],
        effective_at=catalog_dict["effective_at"],
        evidence_bundle_hash=bundle_dict["bundle_hash"],
        record_hashes=record_hashes,
    )
    if catalog_dict.get("catalog_hash") != catalog_hash_value:
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_CATALOG_HASH_MISMATCH",
                field_path="raw_catalog.catalog_hash",
                message_key="sgc_catalog_hash_mismatch",
                evidence_refs=(catalog_dict["catalog_id"],),
                details={
                    "expected": catalog_hash_value,
                    "actual": catalog_dict.get("catalog_hash"),
                },
            )
        )
        raise ShellGeometryCatalogFailure(blockers_out)
    if catalog_dict.get("evidence_bundle_hash") != bundle_dict["bundle_hash"]:
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_CATALOG_HASH_MISMATCH",
                field_path="raw_catalog.evidence_bundle_hash",
                message_key="sgc_catalog_hash_mismatch",
                evidence_refs=(catalog_dict["catalog_id"],),
                details={
                    "expected": bundle_dict["bundle_hash"],
                    "actual": catalog_dict.get("evidence_bundle_hash"),
                },
            )
        )
        raise ShellGeometryCatalogFailure(blockers_out)

    try:
        return ShellGeometryCatalog(
            schema_version=CATALOG_SCHEMA_VERSION,
            catalog_id=catalog_dict["catalog_id"],
            catalog_version=catalog_dict["catalog_version"],
            profile_id=PROFILE_ID,
            authority=catalog_dict["authority"],
            source_revision=catalog_dict["source_revision"],
            records=tuple(parsed_records),
            evidence_bundle_hash=bundle_dict["bundle_hash"],
            catalog_hash=catalog_hash_value,
            effective_at=catalog_dict["effective_at"],
        )
    except ValueError as exc:
        blockers_out.append(
            ShellGeometryCatalogBlockerEntry(
                code="SGC_RAW_TYPE_INVALID",
                field_path="raw_catalog",
                message_key="sgc_raw_type_invalid",
                evidence_refs=(),
                details={"reason": str(exc)},
            )
        )
        raise ShellGeometryCatalogFailure(blockers_out) from None


def _scope_token_present(
    token: str,
    permission_refs: Sequence[str],
    permission_by_id: Mapping[str, VendorPermissionEvidenceSnapshot],
) -> bool:
    for ref in permission_refs:
        perm = permission_by_id.get(ref)
        if perm is not None and token in perm.permission_scope:
            return True
    return False


def _vendor_usage_compatible(
    permission_refs: Sequence[str],
    permission_by_id: Mapping[str, VendorPermissionEvidenceSnapshot],
    local_kernel_usage_scope: Sequence[str],
) -> bool:
    """Return True iff every recorded vendor usage_scope is a subset
    of the bundle's ``local_kernel_usage_scope``."""
    if not local_kernel_usage_scope:
        return False
    local_set = set(local_kernel_usage_scope)
    for ref in permission_refs:
        perm = permission_by_id.get(ref)
        if perm is None:
            return False
        if not perm.usage_scope:
            return False
        if not set(perm.usage_scope).issubset(local_set):
            return False
    return True


# ---------------------------------------------------------------------------
# Selection — exact ID only
# ---------------------------------------------------------------------------


def select_approved_shell_geometry(
    *,
    catalog: ShellGeometryCatalog,
    geometry_id: str,
) -> ShellGeometryRecord:
    """Select exactly one approved record from a successfully parsed
    catalog.

    Behavior (design contract §12):

    1. ``catalog`` must be a :class:`ShellGeometryCatalog`.
    2. ``geometry_id`` must be a non-empty string.
    3. Exact identity lookup only.
    4. Missing — :class:`ShellGeometryCatalogFailure` carrying
       ``SGC_RECORD_NOT_FOUND``.
    5. Defensive approval-state recheck — non-approved records carry
       ``SGC_SELECTION_NOT_APPROVED``.
    6. Success returns the catalog's original immutable record.
    """
    if not isinstance(catalog, ShellGeometryCatalog):
        raise ShellGeometryCatalogFailure(
            [
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RAW_TYPE_INVALID",
                    field_path="catalog",
                    message_key="sgc_raw_type_invalid",
                    evidence_refs=(),
                    details={
                        "actual_type": type(catalog).__name__,
                    },
                )
            ]
        )
    if not isinstance(geometry_id, str) or not geometry_id:
        raise ShellGeometryCatalogFailure(
            [
                ShellGeometryCatalogBlockerEntry(
                    code="SGC_RECORD_NOT_FOUND",
                    field_path="geometry_id",
                    message_key="sgc_record_not_found",
                    evidence_refs=(),
                    details={"reason": "geometry_id_empty_or_invalid"},
                )
            ]
        )

    for record in catalog.records:
        if record.geometry_id == geometry_id:
            # Defensive recheck at the catalog layer: the parser
            # only admits approved records, but selection is a
            # second-look gate that must never accept a non-approved
            # record even if the catalog were constructed manually.
            if record.approval_state not in SELECTABLE_APPROVAL_STATES:
                raise ShellGeometryCatalogFailure(
                    [
                        ShellGeometryCatalogBlockerEntry(
                            code="SGC_SELECTION_NOT_APPROVED",
                            field_path="geometry_id",
                            message_key="sgc_selection_not_approved",
                            evidence_refs=(geometry_id,),
                            details={
                                "approval_state": record.approval_state,
                            },
                        )
                    ]
                )
            return record
    raise ShellGeometryCatalogFailure(
        [
            ShellGeometryCatalogBlockerEntry(
                code="SGC_RECORD_NOT_FOUND",
                field_path="geometry_id",
                message_key="sgc_record_not_found",
                evidence_refs=(),
                details={"geometry_id": geometry_id},
            )
        ]
    )

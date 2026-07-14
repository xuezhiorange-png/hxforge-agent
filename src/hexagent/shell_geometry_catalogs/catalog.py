"""TASK-023 — Approved Shell Geometry Catalog parser and selector.

This module owns:

- :func:`parse_shell_geometry_catalog` — pure in-memory parser that
  consumes one already-loaded raw catalog and one already-loaded
  authority evidence bundle, performs the multi-stage validation
  pipeline in design-contract order and returns either one complete
  ``ShellGeometryCatalog`` or one ``ShellGeometryCatalogFailure``
  carrying the full ordered blocker tuple.

- :func:`select_approved_shell_geometry` — exact-ID selection from a
  previously parsed approved-only catalog.

The parser forbids filesystem / network / database / environment /
runtime-now / locale / registry / dynamic-import / executable-
deserialization operations. It only imports stdlib + TASK-023 local
models + the shared canonical SHA-256 helper + ``hexagent.canonical_json``.

Failure model
-------------

* Either parsing succeeds and returns one complete ``ShellGeometryCatalog``.
* Or it raises one ``ShellGeometryCatalogFailure`` whose ``blockers``
  attribute is the COMPLETE ordered blocker tuple (no partial
  catalog, no warnings, no partial hash, no first-only error).

Every blocker carries a real ``stage_rank``. Same-stage failures
accumulate; later-stage gates are enforced only AFTER the current
stage has completed.

Hashing and ordering
--------------------

Permission hashes are sorted by ``(permission_id, permission_hash)``;
edge hashes by ``(edge_id, edge_hash)``; record hashes by
``(geometry_id, revision, record_hash)``. The catalog hash covers
catalog fields including the canonical ordered record_hash sequence
and the bundle hash; the bundle hash covers bundle fields including
permission_hashes sequence bound by permission_id ordering.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final, NoReturn, TypeGuard, cast

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    parse_decimal as _project_parse_decimal,
)
from hexagent.rule_packs.models import (
    LicenseEvidenceForm,
)

from .blockers import (
    SHELL_GEOMETRY_CATALOG_DEFAULT_FIELD_PATH,
    SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY,
    ShellGeometryCatalogBlockerEntry,
    deep_freeze_details,
    freeze_evidence_refs,
    sort_blockers,
)
from .models import (
    APPROVAL_STATES,
    CATALOG_SCHEMA_VERSION,
    GEOMETRY_ROLE,
    GEOMETRY_TYPE,
    PROFILE_ID,
    RECOGNIZED_SOURCE_CLASSES,
    SELECTABLE_APPROVAL_STATES,
    VENDOR_PERMISSION_REQUIRED_SCOPE_TOKENS,
    ProvenanceEdgeSnapshot,
    ShellAuthorityEvidenceBundle,
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

    The parser NEVER returns a partial catalog, partial record,
    trusted partial hash, warning channel or TASK-022 snapshot.
    """

    def __init__(self, blockers: Sequence[ShellGeometryCatalogBlockerEntry]) -> None:
        ordered = sort_blockers(blockers)
        object.__setattr__(self, "blockers", ordered)
        codes = ", ".join(b.code for b in ordered)
        super().__init__(f"ShellGeometryCatalogFailure[{codes}]")


# ---------------------------------------------------------------------------
# Stage ranks (design contract §11 / §18 pipeline).
# ---------------------------------------------------------------------------


_STAGE_RAW_TYPES = 1
_STAGE_TOP_FIELDS = 2
_STAGE_CATALOG_HEADER = 3
_STAGE_BUNDLE_HEADER = 4
_STAGE_PERMISSION_FIELDS = 5
_STAGE_EDGE_FIELDS = 6
_STAGE_RECORDS_LIST = 7
_STAGE_RECORD_FIELDS = 8
_STAGE_DUPLICATE_IDS = 9
_STAGE_APPROVAL_LEXICAL = 10
_STAGE_APPROVAL_STATE = 11
_STAGE_DIAMETER_DECIMAL = 12
_STAGE_SOURCE_CLASS = 13
_STAGE_LICENSE_DISPOSITION = 14
_STAGE_SOURCE_BINDING = 15
_STAGE_REF_RESOLUTION = 16
_STAGE_HASHES = 17
_STAGE_SELECTION = 20  # Amendment 001 §3: select_approved_shell_geometry occurrences


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_DECIMAL_FULL_RE: Final[re.Pattern[str]] = re.compile(r"^([1-9][0-9]*|0)(\.[0-9]+)?$")


def _check_shell_inside_diameter_m(value: Any) -> str:
    """Return the canonical positive SI metre decimal string.

    Rejects: bool / int / float / Decimal / exponents / leading ``+`` /
    embedded whitespace / leading zeros in integral component /
    redundant trailing zeros in fractional component / ``NaN`` /
    ``±Infinity`` / zero / negative values / empty string / unit
    suffixes / DN/NPS inputs.
    """
    if isinstance(value, bool):
        raise ValueError("shell_inside_diameter_m must not be a bool")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        raise ValueError("shell_inside_diameter_m must be a positive canonical decimal string")
    import decimal

    if isinstance(value, decimal.Decimal):
        raise ValueError("shell_inside_diameter_m must be a positive canonical decimal string")
    if not isinstance(value, str):
        raise ValueError("shell_inside_diameter_m must be a positive canonical decimal string")
    raw = value
    if raw == "" or raw != raw.strip():
        raise ValueError("shell_inside_diameter_m must not contain whitespace")
    if raw.startswith("+"):
        raise ValueError("shell_inside_diameter_m must not contain a leading '+'")
    lowered = raw.lower()
    if "e" in lowered or "n" in lowered or "i" in lowered:
        raise ValueError("shell_inside_diameter_m must not contain exponent / nan / inf tokens")
    if not _DECIMAL_FULL_RE.fullmatch(raw):
        raise ValueError("shell_inside_diameter_m must match ^([1-9][0-9]*|0)(\\.[0-9]+)?$")
    if raw.startswith("0") and len(raw) > 1 and raw[1] != ".":
        raise ValueError("shell_inside_diameter_m must not contain leading zeros")
    try:
        canonical = _project_parse_decimal(raw, positive=True)
    except Exception as exc:
        raise ValueError(str(exc)) from None
    if "." in raw and raw.rstrip("0").endswith("."):
        raise ValueError("shell_inside_diameter_m must not contain redundant trailing zeros")
    if str(canonical) != raw:
        raise ValueError(
            "shell_inside_diameter_m lexical form does not equal its canonical decimal string"
        )
    return raw


def _make_entry(
    code: str,
    *,
    stage_rank: int,
    field_path: str | None = None,
    evidence_refs: Sequence[str] | tuple[str, ...] = (),
    details: Mapping[str, Any] | None = None,
) -> ShellGeometryCatalogBlockerEntry:
    """Construct a TASK-023 blocker entry with an explicit stage rank.

    Amendment 001 §3 (Issue #152 Comment 4970130136): ``stage_rank``
    binds the validation **occurrence** that emitted this entry. There
    is no code-derived lookup table and no default rank. Every parser
    call site MUST pass the actual occurrence rank (typically one of
    the ``_STAGE_RAW_TYPES`` … ``_STAGE_HASHES`` constants in this
    module). The dataclass ``__post_init__`` rejects any entry whose
    rank is outside ``[1, 20]``.

    ``details`` is deep-frozen through ``deep_freeze_details`` and
    ``evidence_refs`` is normalized through ``freeze_evidence_refs`` so
    the caller cannot mutate the blocker entry post-construction.
    """
    frozen_details = deep_freeze_details(details)
    frozen_refs = freeze_evidence_refs(evidence_refs)
    return ShellGeometryCatalogBlockerEntry(
        code=code,
        field_path=field_path or SHELL_GEOMETRY_CATALOG_DEFAULT_FIELD_PATH[code],
        message_key=SHELL_GEOMETRY_CATALOG_DEFAULT_MESSAGE_KEY[code],
        stage_rank=stage_rank,
        evidence_refs=frozen_refs,
        details=frozen_details,
    )


def _expect_str(
    value: Any,
    *,
    path: str,
    failures: list[ShellGeometryCatalogBlockerEntry],
    code: str,
    stage_rank: int,
) -> str | None:
    """Strict raw-type string validator: any non-string OR empty string fails.

    Returns the validated string (mypy-narrowed) on success; returns
    ``None`` on failure (after appending a blocker). The caller MUST
    pass the actual occurrence ``stage_rank`` (Amendment 001 §3).
    """
    if not isinstance(value, str) or not value:
        failures.append(_make_entry(code, stage_rank=stage_rank, field_path=path))
        return None
    return value


def _expect_nonempty_str_or_none(
    value: Any,
    *,
    path: str,
    failures: list[ShellGeometryCatalogBlockerEntry],
    code: str,
    stage_rank: int,
) -> str | None | bool:
    """Returns (a) value if str, (b) None sentinel if value is exactly None,
    (c) None-if-error.

    The sentinel ``None`` (Python None) is the allowed "absent" marker for
    ``effective_at``. We distinguish it from "fail" using a separate boolean.
    The caller MUST pass the actual occurrence ``stage_rank``
    (Amendment 001 §3).
    """
    if value is None:
        return True  # allowed-None marker
    if not isinstance(value, str) or not value:
        failures.append(_make_entry(code, stage_rank=stage_rank, field_path=path))
        return False
    return value


def _expect_mapping(
    value: Any,
    *,
    path: str,
    failures: list[ShellGeometryCatalogBlockerEntry],
    code: str,
    stage_rank: int,
) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        failures.append(_make_entry(code, stage_rank=stage_rank, field_path=path))
        return None
    return value


def _expect_sequence(
    value: Any,
    *,
    path: str,
    failures: list[ShellGeometryCatalogBlockerEntry],
    code: str,
    stage_rank: int,
) -> Sequence[Any] | None:
    if not isinstance(value, (list, tuple)) or isinstance(value, str):
        failures.append(_make_entry(code, stage_rank=stage_rank, field_path=path))
        return None
    return value


def _expect_exact_fields(
    raw: Mapping[str, Any],
    expected: frozenset[str],
    *,
    failures: list[ShellGeometryCatalogBlockerEntry],
    code_for_extra: str,
    base_field_path: str,
    stage_rank: int,
) -> None:
    """Reject any extra or missing fields. Caller MUST pass the actual
    occurrence ``stage_rank`` (Amendment 001 §3).
    """
    actual = frozenset(raw)
    extras = actual - expected
    missing = expected - actual
    for extra in sorted(extras):
        failures.append(
            _make_entry(
                code_for_extra,
                stage_rank=stage_rank,
                field_path=f"{base_field_path}.{extra}",
            )
        )
    for m in sorted(missing):
        failures.append(
            _make_entry(
                code_for_extra,
                stage_rank=stage_rank,
                field_path=f"{base_field_path}.{m}",
            )
        )


def _strict_str_seq(
    raw: Sequence[Any],
    *,
    path: str,
    required_nonempty: bool,
    failures: list[ShellGeometryCatalogBlockerEntry],
    code: str,
    stage_rank: int,
    unique: bool = True,
) -> tuple[str, ...] | None:
    """Validate that every entry is a non-empty string; reject duplicates.

    Returns the canonical sorted-tuple (Unicode code-point order) on
    success; returns None on failure (with blockers appended).
    The output tuple is the canonical sequence used by hash domains.
    The caller MUST pass the actual occurrence ``stage_rank``
    (Amendment 001 §3).
    """
    items = list(raw)
    for i, entry in enumerate(items):
        if not isinstance(entry, str) or not entry:
            failures.append(_make_entry(code, stage_rank=stage_rank, field_path=f"{path}[{i}]"))
            return None
    if unique:
        seen: dict[str, int] = {}
        for entry in items:
            if entry in seen:
                failures.append(
                    _make_entry(code, stage_rank=stage_rank, field_path=f"{path}[{entry!r}]")
                )
                return None
            seen[entry] = 1
    canonical = tuple(sorted(items))
    if required_nonempty and not canonical:
        failures.append(_make_entry(code, stage_rank=stage_rank, field_path=path))
        return None
    return canonical


def _stable_geometry_id(
    *,
    catalog_id: str,
    record_key: str,
    revision: str,
) -> str:
    """Compute the stable, design-frozen geometry identity.

    The identity is ``<catalog_id>/shell/<record_key>/<revision>`` — four
    segments, no extras, no normalization, no case folding. Both
    ``record_key`` and ``revision`` MUST NOT contain the ``/`` separator
    because the identity form strictly disallows nested slashes past the
    three structural separators.
    """
    if "/" in record_key:
        raise ValueError(
            "record_key must not contain '/' separator "
            "(four-part stable identity is exactly four segments)"
        )
    if "/" in revision:
        raise ValueError(
            "revision must not contain '/' separator "
            "(four-part stable identity is exactly four segments)"
        )
    return f"{catalog_id}/{GEOMETRY_ROLE}/{record_key}/{revision}"


def _verify_stable_geometry_identity(
    *,
    catalog_id: str,
    raw_id: str,
    failures: list[ShellGeometryCatalogBlockerEntry],
    stage_rank: int,
) -> tuple[str, str] | None:
    """Reject any deviation from the design-frozen identity format.

    Round 3 fixup §2 enforces the **exact four-part** form
    ``<catalog_id>/shell/<record_key>/<revision>``:

    * The raw id MUST contain EXACTLY THREE ``/`` separators (four
      segments).  Forms such as ``catalog/shell/a/b/1`` (four segments),
      ``catalog/shell//1`` (empty record_key), ``catalog/SHELL/a/1``
      (wrong role case), and ``catalog/shell/a/1/extra`` (extra
      revision segment) all reject with ``SGC_RECORD_ID_INVALID``.
    * ``record_key`` MUST NOT contain ``/`` after the role (separate
      condition; same code).
    * ``revision`` MUST equal the record's ``revision`` field byte-for-byte.
    * No Unicode normalization or case folding is applied; the caller
      must pass raw ASCII path-literal segment tokens.
    """
    if not isinstance(raw_id, str) or not raw_id:
        failures.append(
            _make_entry(
                "SGC_RECORD_ID_INVALID",
                stage_rank=stage_rank,
                details={
                    "expected_form": "<catalog_id>/shell/<record_key>/<revision>",
                    "actual": repr(raw_id),
                },
            )
        )
        return None
    segments = raw_id.split("/")
    if len(segments) != 4:
        failures.append(
            _make_entry(
                "SGC_RECORD_ID_INVALID",
                stage_rank=stage_rank,
                details={
                    "expected_form": "<catalog_id>/shell/<record_key>/<revision>",
                    "actual": raw_id,
                    "segment_count": len(segments),
                    "expected_segment_count": 4,
                },
            )
        )
        return None
    seg_catalog, seg_role, seg_record_key, seg_revision = segments
    if seg_catalog != catalog_id:
        failures.append(
            _make_entry(
                "SGC_RECORD_ID_INVALID",
                stage_rank=stage_rank,
                details={
                    "expected_form": f"{catalog_id}/shell/<record_key>/<revision>",
                    "actual": raw_id,
                    "mismatch": "catalog_id",
                    "expected_prefix": catalog_id,
                },
            )
        )
        return None
    if seg_role != GEOMETRY_ROLE:
        failures.append(
            _make_entry(
                "SGC_RECORD_ID_INVALID",
                stage_rank=stage_rank,
                details={
                    "expected_form": f"{catalog_id}/shell/<record_key>/<revision>",
                    "actual": raw_id,
                    "mismatch": "geometry_role",
                    "expected_role": GEOMETRY_ROLE,
                    "actual_role": seg_role,
                },
            )
        )
        return None
    if not seg_record_key:
        failures.append(
            _make_entry(
                "SGC_RECORD_ID_INVALID",
                stage_rank=stage_rank,
                details={
                    "expected_form": f"{catalog_id}/shell/<record_key>/<revision>",
                    "actual": raw_id,
                    "mismatch": "record_key_empty",
                },
            )
        )
        return None
    if not seg_revision:
        failures.append(
            _make_entry(
                "SGC_RECORD_ID_INVALID",
                stage_rank=stage_rank,
                details={
                    "expected_form": f"{catalog_id}/shell/<record_key>/<revision>",
                    "actual": raw_id,
                    "mismatch": "revision_empty",
                },
            )
        )
        return None
    if "/" in seg_record_key:
        failures.append(
            _make_entry(
                "SGC_RECORD_ID_INVALID",
                stage_rank=stage_rank,
                details={
                    "expected_form": f"{catalog_id}/shell/<record_key>/<revision>",
                    "actual": raw_id,
                    "mismatch": "record_key_contains_slash",
                },
            )
        )
        return None
    if "/" in seg_revision:
        failures.append(
            _make_entry(
                "SGC_RECORD_ID_INVALID",
                stage_rank=stage_rank,
                details={
                    "expected_form": f"{catalog_id}/shell/<record_key>/<revision>",
                    "actual": raw_id,
                    "mismatch": "revision_contains_slash",
                },
            )
        )
        return None
    return (seg_record_key, seg_revision)


# ---------------------------------------------------------------------------
# License and source-class disposition (TASK-012 compat layer).
# ---------------------------------------------------------------------------


_PUBLIC_DOMAIN_LICENSE = "public_domain"
_INTERNAL_AUTHORITY = "project_internal_authority"
_PERMISSION_POINTER_SCHEME_MARKERS = ("://",)


def _classify_license_form(
    raw: Any,
) -> LicenseEvidenceForm:
    """Classify a TASK-023 license_evidence form via TASK-012 closed rules.

    Rules: SPDX identifier OR ``public_domain`` OR
    ``project_internal_authority`` OR a permission-evidence pointer
    (URI with ``://``).
    """
    from hexagent.rule_packs.license_boundary import (
        classify_license_evidence as _cls,
    )

    if not isinstance(raw, Mapping):
        raise ValueError("license_evidence must be a mapping")
    # TASK-023 license_evidence carries its form under the
    # ``license_form`` key (per design contract §5.4). TASK-012
    # keywords live directly on the value side. We accept both
    # shapes so the synthetic builders and real-world producers
    # share the same gate.
    form_token: Any = raw.get("license_form")
    spdx_token: Any = raw.get("spdx")
    if form_token is None and spdx_token is not None:
        form_token = spdx_token
    if form_token is None:
        # Fallback: derive form from raw pointer string if present.
        pointer = raw.get("pointer")
        if isinstance(pointer, str) and _PERMISSION_POINTER_SCHEME_MARKERS[0] in pointer:
            return LicenseEvidenceForm.PERMISSION_EVIDENCE_POINTER
        raise ValueError(
            "license_evidence must include license_form (spdx / public_domain / "
            "permission_evidence_pointer / project_internal_authority)"
        )
    if not isinstance(form_token, str) or not form_token:
        raise ValueError("license_evidence.license_form must be a non-empty string")
    if form_token == _PUBLIC_DOMAIN_LICENSE:
        return LicenseEvidenceForm.PUBLIC_DOMAIN
    if form_token == _INTERNAL_AUTHORITY:
        return LicenseEvidenceForm.PROJECT_INTERNAL_AUTHORITY
    if "://" in form_token:
        return LicenseEvidenceForm.PERMISSION_EVIDENCE_POINTER
    # SPDX short identifier accepted verbatim by TASK-012
    try:
        return _cls(form_token)
    except Exception as exc:
        # If TASK-012 rejects it, validate it manually as SPDX token.
        if form_token in {
            "MIT",
            "MIT-0",
            "Apache-2.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "ISC",
            "Unlicense",
            "CC0-1.0",
            "GPL-3.0-or-later",
        }:
            return LicenseEvidenceForm.SPDX
        raise ValueError(str(exc)) from None


# TASK-023 license disposition table (TASK-012 compat):
#   INTERNAL_ENGINEERING_RULE / DERIVED_ENGINEERING_RULE
#     -> project_internal_authority (matches TASK-012 §7.2 internal_authority rule)
#   VENDOR_PERMISSIONED
#     -> permission_evidence_pointer, requires explicit
#        (repository_storage + repository_redistribution) scope
#   PUBLIC_DOMAIN
#     -> public_domain (allowed; zero permission references)
#   REFERENCE_ONLY_RESTRICTED_STANDARD
#     -> permission_evidence_pointer required (metadata-only body)
#   USER_PROVIDED_LICENSED_SUMMARY
#     -> permission_evidence_pointer required
#   OPEN_LICENSE
#     -> SPDX / permission_evidence_pointer
# All license forms are ALSO permitted to declare explicit permission
# pointers for auditability; in that case the corresponding gating
# applies.

_INTERNAL_SOURCE_CLASSES = frozenset({"INTERNAL_ENGINEERING_RULE", "DERIVED_ENGINEERING_RULE"})


# ---------------------------------------------------------------------------
# Frozen canonical ordering helpers
# ---------------------------------------------------------------------------


def _canonical_permission_hash_sequence(
    permissions: tuple[VendorPermissionEvidenceSnapshot, ...],
) -> tuple[str, ...]:
    """Return the canonical (permission_id, permission_hash)-sorted
    sequence of permission hashes for the bundle."""
    return tuple(
        sorted(
            (p.permission_hash for p in permissions),
            key=lambda h: (
                next(p.permission_id for p in permissions if p.permission_hash == h),
                h,
            ),
        )
    )


def _canonical_edge_hash_sequence(
    edges: tuple[ProvenanceEdgeSnapshot, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            (e.edge_hash for e in edges),
            key=lambda h: (
                next(e.edge_id for e in edges if e.edge_hash == h),
                h,
            ),
        )
    )


def _compute_bundle_hash(
    *,
    schema_version: str,
    bundle_id: str,
    bundle_version: str,
    bundle_approval: str,
    perm_records_tuple: tuple[VendorPermissionEvidenceSnapshot, ...],
    edge_records_tuple: tuple[ProvenanceEdgeSnapshot, ...],
    local_kernel_usage_canon: tuple[str, ...],
    bundle_evidence_refs_canon: tuple[str, ...],
    task012_validation_hash: str,
) -> str:
    """Return the canonical SHA-256 hash of the evidence bundle.

    Round 2 §1 — the caller MUST pass already-validated full-fidelity
    snapshot tuples. Any caller that intends to compute the bundle
    hash from a partial snapshot set (i.e. after a permission /
    edge stage failure) MUST gate before calling this helper; the
    helper itself does NOT re-validate the snapshots. This isolates
    the canonical-hash domain construction from the upstream stage
    gating.

    The helper is intentionally module-private (leading underscore)
    so the public parser surface cannot accidentally bypass the
    upstream gate. It is registered as a candidate for monkeypatch
    in Round 2 architecture tests to prove the gate fires before
    the hash is computed.
    """
    bundle_hash_payload = {
        "schema_version": schema_version,
        "bundle_id": bundle_id,
        "bundle_version": bundle_version,
        "approval_status": bundle_approval,
        "permission_hashes": _canonical_permission_hash_sequence(perm_records_tuple),
        "edge_hashes": _canonical_edge_hash_sequence(edge_records_tuple),
        "local_kernel_usage_scope": sorted(local_kernel_usage_canon),
        "evidence_refs": sorted(bundle_evidence_refs_canon),
        "task012_validation_hash": task012_validation_hash,
    }
    return canonical_sha256(bundle_hash_payload)


# ---------------------------------------------------------------------------
# Top-level parser
# ---------------------------------------------------------------------------


def parse_shell_geometry_catalog(
    *,
    raw_catalog: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
) -> ShellGeometryCatalog:
    """Parse a raw catalog + evidence bundle into a ShellGeometryCatalog.

    Raises ``ShellGeometryCatalogFailure`` carrying the ordered blocker
    tuple (one entry per independent failure, ordered by the design
    contract §6 composite key) on any structural or content failure.
    """
    failures: list[ShellGeometryCatalogBlockerEntry] = []

    # ------------------------------------------------------------------
    # Stage 1 — raw input type validation
    # ------------------------------------------------------------------
    if not isinstance(raw_catalog, Mapping):
        failures.append(
            _make_entry(
                "SGC_RAW_TYPE_INVALID",
                stage_rank=_STAGE_RAW_TYPES,
                field_path="raw_catalog",
            )
        )
        _raise(failures)
    if not isinstance(evidence_bundle, Mapping):
        failures.append(
            _make_entry(
                "SGC_RAW_TYPE_INVALID",
                stage_rank=_STAGE_RAW_TYPES,
                field_path="evidence_bundle",
            )
        )
        _raise(failures)

    records_raw = raw_catalog.get("records")
    perms_raw = evidence_bundle.get("permission_evidence")
    edges_raw = evidence_bundle.get("provenance_edges")

    records_seq = _expect_sequence(
        records_raw,
        path="raw_catalog.records",
        failures=failures,
        code="SGC_RECORDS_INVALID",
        stage_rank=_STAGE_RAW_TYPES,
    )
    perms_seq = _expect_sequence(
        perms_raw,
        path="evidence_bundle.permission_evidence",
        failures=failures,
        code="SGC_RECORDS_INVALID",
        stage_rank=_STAGE_RAW_TYPES,
    )
    edges_seq = _expect_sequence(
        edges_raw,
        path="evidence_bundle.provenance_edges",
        failures=failures,
        code="SGC_RECORDS_INVALID",
        stage_rank=_STAGE_RAW_TYPES,
    )

    if records_seq is None or perms_seq is None or edges_seq is None:
        _raise(failures)

    # mypy correctly narrows after a NoReturn-raising guard for each
    # variable individually.

    # ------------------------------------------------------------------
    # Stage 2 — exact top-level fields
    # ------------------------------------------------------------------
    raw_catalog_expected = frozenset(
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
    _expect_exact_fields(
        raw_catalog,
        raw_catalog_expected,
        failures=failures,
        code_for_extra="SGC_UNKNOWN_FIELD",
        base_field_path="raw_catalog",
        stage_rank=_STAGE_TOP_FIELDS,
    )

    bundle_expected = frozenset(
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
    _expect_exact_fields(
        evidence_bundle,
        bundle_expected,
        failures=failures,
        code_for_extra="SGC_UNKNOWN_FIELD",
        base_field_path="evidence_bundle",
        stage_rank=_STAGE_TOP_FIELDS,
    )

    if any(f.code == "SGC_UNKNOWN_FIELD" for f in failures):
        _raise(failures)

    # ------------------------------------------------------------------
    # Stage 3 — catalog top-level fields
    # ------------------------------------------------------------------
    schema_version = _expect_str(
        raw_catalog.get("schema_version"),
        path="raw_catalog.schema_version",
        failures=failures,
        code="SGC_SCHEMA_VERSION_UNSUPPORTED",
        stage_rank=_STAGE_CATALOG_HEADER,
    )
    if schema_version != CATALOG_SCHEMA_VERSION:
        failures.append(
            _make_entry("SGC_SCHEMA_VERSION_UNSUPPORTED", stage_rank=_STAGE_CATALOG_HEADER)
        )
        _raise(failures)

    catalog_id = _expect_str(
        raw_catalog.get("catalog_id"),
        path="raw_catalog.catalog_id",
        failures=failures,
        code="SGC_CATALOG_ID_INVALID",
        stage_rank=_STAGE_CATALOG_HEADER,
    )
    catalog_version = _expect_str(
        raw_catalog.get("catalog_version"),
        path="raw_catalog.catalog_version",
        failures=failures,
        code="SGC_CATALOG_VERSION_INVALID",
        stage_rank=_STAGE_CATALOG_HEADER,
    )
    profile_id = _expect_str(
        raw_catalog.get("profile_id"),
        path="raw_catalog.profile_id",
        failures=failures,
        code="SGC_PROFILE_UNSUPPORTED",
        stage_rank=_STAGE_CATALOG_HEADER,
    )
    if profile_id != PROFILE_ID:
        failures.append(_make_entry("SGC_PROFILE_UNSUPPORTED", stage_rank=_STAGE_CATALOG_HEADER))
        _raise(failures)

    authority = _expect_str(
        raw_catalog.get("authority"),
        path="raw_catalog.authority",
        failures=failures,
        code="SGC_CATALOG_AUTHORITY_INVALID",
        stage_rank=_STAGE_CATALOG_HEADER,
    )
    source_revision = _expect_str(
        raw_catalog.get("source_revision"),
        path="raw_catalog.source_revision",
        failures=failures,
        code="SGC_CATALOG_AUTHORITY_INVALID",
        stage_rank=_STAGE_CATALOG_HEADER,
    )
    effective_at_raw = raw_catalog.get("effective_at")
    if not isinstance(effective_at_raw, (str, type(None))) or (
        isinstance(effective_at_raw, str) and not effective_at_raw
    ):
        failures.append(
            _make_entry(
                "SGC_CATALOG_AUTHORITY_INVALID",
                stage_rank=_STAGE_CATALOG_HEADER,
                field_path="raw_catalog.effective_at",
            )
        )
        _raise(failures)
    effective_at: str | None = effective_at_raw

    if not catalog_id or not catalog_version or not authority or not source_revision:
        _raise(failures)

    # ------------------------------------------------------------------
    # Stage 4 — bundle top-level fields + approval + task012_validation_hash
    # ------------------------------------------------------------------
    bundle_schema = _expect_str(
        evidence_bundle.get("schema_version"),
        path="evidence_bundle.schema_version",
        failures=failures,
        code="SGC_SCHEMA_VERSION_UNSUPPORTED",
        stage_rank=_STAGE_BUNDLE_HEADER,
    )
    if bundle_schema is None or bundle_schema != "task023.shell-authority-evidence-bundle.v1":
        failures.append(
            _make_entry(
                "SGC_SCHEMA_VERSION_UNSUPPORTED",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.schema_version",
            )
        )
        _raise(failures)

    bundle_id = _expect_str(
        evidence_bundle.get("bundle_id"),
        path="evidence_bundle.bundle_id",
        failures=failures,
        code="SGC_CATALOG_ID_INVALID",
        stage_rank=_STAGE_BUNDLE_HEADER,
    )
    bundle_version = _expect_str(
        evidence_bundle.get("bundle_version"),
        path="evidence_bundle.bundle_version",
        failures=failures,
        code="SGC_CATALOG_VERSION_INVALID",
        stage_rank=_STAGE_BUNDLE_HEADER,
    )
    bundle_approval = evidence_bundle.get("approval_status")
    if not isinstance(bundle_approval, str) or bundle_approval not in APPROVAL_STATES:
        failures.append(
            _make_entry(
                "SGC_APPROVAL_STATE_INVALID",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.approval_status",
            )
        )
        _raise(failures)
    if bundle_approval not in SELECTABLE_APPROVAL_STATES:
        failures.append(
            _make_entry(
                "SGC_RECORD_UNAPPROVED",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.approval_status",
            )
        )
        _raise(failures)

    task012_validation_hash = _expect_str(
        evidence_bundle.get("task012_validation_hash"),
        path="evidence_bundle.task012_validation_hash",
        failures=failures,
        code="SGC_PROVENANCE_INCOMPLETE",
        stage_rank=_STAGE_BUNDLE_HEADER,
    )
    if task012_validation_hash is None or not re.fullmatch(
        r"[0-9a-f]{64}", task012_validation_hash
    ):
        failures.append(
            _make_entry(
                "SGC_PROVENANCE_INCOMPLETE",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.task012_validation_hash",
            )
        )
        _raise(failures)
    bundle_hash_in = _expect_str(
        evidence_bundle.get("bundle_hash"),
        path="evidence_bundle.bundle_hash",
        failures=failures,
        code="SGC_CATALOG_HASH_MISMATCH",
        stage_rank=_STAGE_BUNDLE_HEADER,
    )

    # ------------------------------------------------------------------
    # Stage 5 — permission snapshots: 2-pass identity + full validation
    # ------------------------------------------------------------------
    perm_expected = frozenset(
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
    perm_records: list[VendorPermissionEvidenceSnapshot] = []
    perm_id_seen_order: list[str] = []
    perm_id_positions: dict[str, list[int]] = {}
    perm_hash_set: dict[str, int] = {}

    # Stage 5 PASS 1 — identity pre-pass (Amendment 001 §5 + Round 2 §2).
    # Collect every non-empty ``permission_id`` from the raw entries
    # REGARDLESS of scope / usage-scope / hash validity. The pre-pass
    # must not short-circuit on other field failures so the duplicate
    # blocker is reachable even when the same entry has independent
    # validation errors. Pre-pass failures (non-string permission_id)
    # continue into Pass 2 so full-validation raw-type blockers still
    # accumulate on the SAME entry alongside the duplicate blocker.
    for i, raw_perm in enumerate(perms_seq):
        if not isinstance(raw_perm, Mapping):
            continue
        pid = raw_perm.get("permission_id")
        if not isinstance(pid, str) or not pid:
            continue
        perm_id_positions.setdefault(pid, []).append(i)
        if pid not in perm_id_seen_order:
            perm_id_seen_order.append(pid)

    # Emit one SGC_PERMISSION_DUPLICATE_ID per duplicate group. The
    # first occurrence participates in ``perm_id_positions`` as a
    # natural index so the failure carries a deterministic
    # ``first_seen`` field path.
    for pid, positions in perm_id_positions.items():
        if len(positions) < 2:
            continue
        for pos in positions:
            failures.append(
                _make_entry(
                    "SGC_PERMISSION_DUPLICATE_ID",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{pos}].permission_id",
                    details={"permission_id": pid, "duplicate_group": pid},
                )
            )

    # Stage 5 PASS 2 — full validation. The same entry is re-validated
    # for ALL independent fields (exact fields / raw types / scope /
    # usage / evidence_ref / approved_by / approved_at / hash) so
    # additional raw-type / hash-mismatch blockers accumulate on the
    # SAME entry alongside the duplicate blocker. Duplicate entries
    # (i.e. entries whose permission_id is in a duplicate group) MUST
    # NOT enter the trusted snapshot tuple.
    duplicate_permission_ids = {pid for pid, pos in perm_id_positions.items() if len(pos) >= 2}
    for i, raw_perm in enumerate(perms_seq):
        if not isinstance(raw_perm, Mapping):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{i}]",
                )
            )
            continue
        actual_keys = frozenset(raw_perm)
        extras = actual_keys - perm_expected
        missing = perm_expected - actual_keys
        if extras or missing:
            for extra in sorted(extras):
                failures.append(
                    _make_entry(
                        "SGC_UNKNOWN_FIELD",
                        stage_rank=_STAGE_PERMISSION_FIELDS,
                        field_path=f"evidence_bundle.permission_evidence[{i}].{extra}",
                    )
                )
            for m in sorted(missing):
                failures.append(
                    _make_entry(
                        "SGC_UNKNOWN_FIELD",
                        stage_rank=_STAGE_PERMISSION_FIELDS,
                        field_path=f"evidence_bundle.permission_evidence[{i}].{m}",
                    )
                )
            continue
        pid = raw_perm.get("permission_id")
        if not isinstance(pid, str) or not pid:
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{i}].permission_id",
                )
            )
            continue
        # Round 2 §2 — duplicate entries MUST NOT enter the trusted
        # snapshot tuple. They still emit their independent
        # validation blockers above (raw-type / hash / scope) so
        # the same-stage accumulation contract holds, but they do
        # not contribute to ``perm_records``.
        if pid in duplicate_permission_ids:
            # Re-run the full per-field validation so a duplicate
            # entry with an invalid scope / usage / hash accumulates
            # an additional SGC_RAW_TYPE_INVALID or
            # SGC_CATALOG_HASH_MISMATCH alongside the
            # SGC_PERMISSION_DUPLICATE_ID emitted in Pass 1.
            perm_scope_raw = raw_perm.get("permission_scope")
            perm_usage_raw = raw_perm.get("usage_scope")
            if not _is_str_seq(perm_scope_raw) or not _is_str_seq(perm_usage_raw):
                failures.append(
                    _make_entry(
                        "SGC_RAW_TYPE_INVALID",
                        stage_rank=_STAGE_PERMISSION_FIELDS,
                        field_path=f"evidence_bundle.permission_evidence[{i}].permission_scope",
                    )
                )
            perm_hash_in = raw_perm.get("permission_hash")
            if not _is_nonempty_str(perm_hash_in) or not re.fullmatch(
                r"[0-9a-f]{64}", perm_hash_in
            ):
                failures.append(
                    _make_entry(
                        "SGC_RAW_TYPE_INVALID",
                        stage_rank=_STAGE_PERMISSION_FIELDS,
                        field_path=f"evidence_bundle.permission_evidence[{i}].permission_hash",
                    )
                )
            continue
        perm_scope_raw = raw_perm.get("permission_scope")
        perm_usage_raw = raw_perm.get("usage_scope")
        if not _is_str_seq(perm_scope_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{i}].permission_scope",
                )
            )
            continue
        if not _is_str_seq(perm_usage_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{i}].usage_scope",
                )
            )
            continue
        scope_tuple_l = _canonicalize_str_seq(perm_scope_raw)
        usage_tuple_l = _canonicalize_str_seq(perm_usage_raw)
        if scope_tuple_l is None or usage_tuple_l is None:
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{i}]",
                )
            )
            continue
        scope_tuple: tuple[str, ...] = scope_tuple_l
        usage_tuple: tuple[str, ...] = usage_tuple_l
        ev_ref = raw_perm.get("evidence_ref")
        approved_by = raw_perm.get("approved_by")
        approved_at = raw_perm.get("approved_at")
        if (
            not _is_nonempty_str(ev_ref)
            or not _is_nonempty_str(approved_by)
            or not _is_nonempty_str(approved_at)
        ):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{i}]",
                )
            )
            continue
        perm_hash_in = raw_perm.get("permission_hash")
        if not _is_nonempty_str(perm_hash_in) or not re.fullmatch(r"[0-9a-f]{64}", perm_hash_in):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{i}].permission_hash",
                )
            )
            continue
        if perm_hash_in in perm_hash_set:
            failures.append(
                _make_entry(
                    "SGC_CATALOG_HASH_MISMATCH",
                    stage_rank=_STAGE_PERMISSION_FIELDS,
                    field_path=f"evidence_bundle.permission_evidence[{perm_hash_set[perm_hash_in]}].permission_hash",
                    details={"permission_hash": perm_hash_in},
                )
            )
            continue
        perm_hash_set[perm_hash_in] = i
        snapshot = VendorPermissionEvidenceSnapshot(
            permission_id=pid,
            permission_scope=scope_tuple,
            usage_scope=usage_tuple,
            evidence_ref=ev_ref,
            approved_by=approved_by,
            approved_at=approved_at,
            permission_hash=perm_hash_in,
        )
        perm_records.append(snapshot)

    # ------------------------------------------------------------------
    # Stage 6 — provenance edges: 2-pass identity + full validation
    # ------------------------------------------------------------------
    edge_expected = frozenset(
        {
            "edge_id",
            "source_id",
            "target_geometry_id",
            "relation_type",
            "evidence_refs",
            "edge_hash",
        }
    )
    edge_records: list[ProvenanceEdgeSnapshot] = []
    edge_id_positions: dict[str, list[int]] = {}
    edge_hash_set: dict[str, int] = {}

    # Stage 6 PASS 1 — identity pre-pass (Amendment 001 §5 + Round 2 §2).
    for i, raw_edge in enumerate(edges_seq):
        if not isinstance(raw_edge, Mapping):
            continue
        eid = raw_edge.get("edge_id")
        if not isinstance(eid, str) or not eid:
            continue
        edge_id_positions.setdefault(eid, []).append(i)

    for eid, positions in edge_id_positions.items():
        if len(positions) < 2:
            continue
        for pos in positions:
            failures.append(
                _make_entry(
                    "SGC_PROVENANCE_DUPLICATE_ID",
                    stage_rank=_STAGE_EDGE_FIELDS,
                    field_path=f"evidence_bundle.provenance_edges[{pos}].edge_id",
                    details={"edge_id": eid, "duplicate_group": eid},
                )
            )

    # Stage 6 PASS 2 — full validation. The same entry is re-validated
    # for ALL independent fields (exact fields / raw types /
    # relation_type / evidence_refs / hash) so additional raw-type
    # blockers accumulate on the SAME entry alongside the duplicate
    # blocker. Duplicate entries MUST NOT enter the trusted snapshot
    # tuple.
    duplicate_edge_ids = {eid for eid, pos in edge_id_positions.items() if len(pos) >= 2}
    for i, raw_edge in enumerate(edges_seq):
        if not isinstance(raw_edge, Mapping):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_EDGE_FIELDS,
                    field_path=f"evidence_bundle.provenance_edges[{i}]",
                )
            )
            continue
        actual_keys = frozenset(raw_edge)
        extras = actual_keys - edge_expected
        missing = edge_expected - actual_keys
        if extras or missing:
            for extra in sorted(extras):
                failures.append(
                    _make_entry(
                        "SGC_UNKNOWN_FIELD",
                        stage_rank=_STAGE_EDGE_FIELDS,
                        field_path=f"evidence_bundle.provenance_edges[{i}].{extra}",
                    )
                )
            for m in sorted(missing):
                failures.append(
                    _make_entry(
                        "SGC_UNKNOWN_FIELD",
                        stage_rank=_STAGE_EDGE_FIELDS,
                        field_path=f"evidence_bundle.provenance_edges[{i}].{m}",
                    )
                )
            continue
        eid = raw_edge.get("edge_id")
        sid = raw_edge.get("source_id")
        tgt = raw_edge.get("target_geometry_id")
        rel = raw_edge.get("relation_type")
        ev_refs_raw = raw_edge.get("evidence_refs")
        edge_hash_in = raw_edge.get("edge_hash")
        if not _is_nonempty_str(eid) or not _is_nonempty_str(sid) or not _is_nonempty_str(tgt):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_EDGE_FIELDS,
                    field_path=f"evidence_bundle.provenance_edges[{i}]",
                )
            )
            continue
        # Round 2 §2 — duplicate entries MUST NOT enter the trusted
        # snapshot tuple. They still emit their independent
        # validation blockers (relation_type / evidence_refs / hash)
        # so the same-stage accumulation contract holds.
        if eid in duplicate_edge_ids:
            if not isinstance(rel, str) or not rel:
                failures.append(
                    _make_entry(
                        "SGC_RAW_TYPE_INVALID",
                        stage_rank=_STAGE_EDGE_FIELDS,
                        field_path=f"evidence_bundle.provenance_edges[{i}].relation_type",
                    )
                )
            if not _is_str_seq(ev_refs_raw):
                failures.append(
                    _make_entry(
                        "SGC_RAW_TYPE_INVALID",
                        stage_rank=_STAGE_EDGE_FIELDS,
                        field_path=f"evidence_bundle.provenance_edges[{i}].evidence_refs",
                    )
                )
            continue
        if not isinstance(rel, str) or not rel:
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_EDGE_FIELDS,
                    field_path=f"evidence_bundle.provenance_edges[{i}].relation_type",
                )
            )
            continue
        if not _is_str_seq(ev_refs_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_EDGE_FIELDS,
                    field_path=f"evidence_bundle.provenance_edges[{i}].evidence_refs",
                )
            )
            continue
        ev_refs_canon = _canonicalize_str_seq(ev_refs_raw, unique=True)
        if ev_refs_canon is None:
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_EDGE_FIELDS,
                    field_path=f"evidence_bundle.provenance_edges[{i}].evidence_refs",
                )
            )
            continue
        if not _is_nonempty_str(edge_hash_in) or not re.fullmatch(r"[0-9a-f]{64}", edge_hash_in):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_EDGE_FIELDS,
                    field_path=f"evidence_bundle.provenance_edges[{i}].edge_hash",
                )
            )
            continue
        if edge_hash_in in edge_hash_set:
            failures.append(
                _make_entry(
                    "SGC_CATALOG_HASH_MISMATCH",
                    stage_rank=_STAGE_EDGE_FIELDS,
                    field_path=f"evidence_bundle.provenance_edges[{edge_hash_set[edge_hash_in]}].edge_hash",
                    details={"edge_hash": edge_hash_in},
                )
            )
            continue
        edge_hash_set[edge_hash_in] = i
        edge_snapshot = ProvenanceEdgeSnapshot(
            edge_id=eid,
            source_id=sid,
            target_geometry_id=tgt,
            relation_type=rel,
            evidence_refs=ev_refs_canon,
            edge_hash=edge_hash_in,
        )
        edge_records.append(edge_snapshot)

    # ------------------------------------------------------------------
    # Stage 4-extension: dependent-stage gating MUST fire BEFORE any
    # partial snapshot tuple construction or bundle-hash computation.
    # ------------------------------------------------------------------
    # Round 2 §1 — the upstream-stage gate fires before
    # (a) building the trusted snapshot tuples,
    # (b) building the bundle-hash payload,
    # (c) calling canonical_sha256,
    # (d) comparing the supplied bundle_hash.
    # If either the permission or the edge stage produced ANY blocker
    # we MUST raise the ordered failure immediately; the partial
    # snapshot set MUST NOT be hashed.
    permission_stage_failed = any(
        f.field_path.startswith("evidence_bundle.permission_evidence") for f in failures
    )
    edge_stage_failed = any(
        f.field_path.startswith("evidence_bundle.provenance_edges") for f in failures
    )
    if permission_stage_failed or edge_stage_failed:
        _raise(failures)

    perm_records_tuple = tuple(cast(Sequence[VendorPermissionEvidenceSnapshot], perm_records))
    edge_records_tuple = tuple(cast(Sequence[ProvenanceEdgeSnapshot], edge_records))

    # Round 3 §3 — raw-before-hash: validate ``local_kernel_usage_scope``
    # and ``evidence_refs`` BEFORE computing the bundle_hash payload.
    # Without this pre-validation an int submitted in place of
    # ``local_kernel_usage_scope`` leaks a ``TypeError`` from
    # ``sorted(...)`` instead of producing a structured
    # ``SGC_RAW_TYPE_INVALID`` blocker.
    # Amendment 001 §7: validate local_kernel_usage_scope + bundle
    # evidence_refs BEFORE computing the bundle hash payload so that
    # an int/list-of-int leaked into the raw bundle becomes a
    # structured SGC_RAW_TYPE_INVALID rather than a TypeError from
    # sorted(...).
    raw_local_kernel_usage_scope = evidence_bundle.get("local_kernel_usage_scope")
    if not _is_str_seq(raw_local_kernel_usage_scope):
        failures.append(
            _make_entry(
                "SGC_RAW_TYPE_INVALID",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.local_kernel_usage_scope",
            )
        )
        _raise(failures)
    local_kernel_usage_canon = _canonicalize_str_seq(raw_local_kernel_usage_scope, unique=True)
    if local_kernel_usage_canon is None or not local_kernel_usage_canon:
        failures.append(
            _make_entry(
                "SGC_RAW_TYPE_INVALID",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.local_kernel_usage_scope",
            )
        )
        _raise(failures)

    raw_evidence_refs = evidence_bundle.get("evidence_refs")
    if not _is_str_seq(raw_evidence_refs) or not raw_evidence_refs:
        failures.append(
            _make_entry(
                "SGC_RAW_TYPE_INVALID",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.evidence_refs",
            )
        )
        _raise(failures)
    bundle_evidence_refs_canon = _canonicalize_str_seq(raw_evidence_refs, unique=True)
    if bundle_evidence_refs_canon is None or not bundle_evidence_refs_canon:
        failures.append(
            _make_entry(
                "SGC_RAW_TYPE_INVALID",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.evidence_refs",
            )
        )
        _raise(failures)

    # Round 2 §1 — ONLY NOW, after the upstream stage gate has fired
    # AND the snapshot tuples are full-fidelity, call the private
    # bundle-hash helper. The helper does NOT re-validate the
    # snapshots; the gate above is the only check.
    expected_bundle_hash = _compute_bundle_hash(
        schema_version="task023.shell-authority-evidence-bundle.v1",
        bundle_id=cast(str, bundle_id),
        bundle_version=cast(str, bundle_version),
        bundle_approval=bundle_approval,
        perm_records_tuple=perm_records_tuple,
        edge_records_tuple=edge_records_tuple,
        local_kernel_usage_canon=local_kernel_usage_canon,
        bundle_evidence_refs_canon=bundle_evidence_refs_canon,
        task012_validation_hash=task012_validation_hash,
    )
    if expected_bundle_hash != bundle_hash_in:
        failures.append(
            _make_entry(
                "SGC_CATALOG_HASH_MISMATCH",
                stage_rank=_STAGE_BUNDLE_HEADER,
                field_path="evidence_bundle.bundle_hash",
                details={
                    "expected": expected_bundle_hash,
                    "actual": bundle_hash_in,
                },
            )
        )
        _raise(failures)

    # ------------------------------------------------------------------
    # Build the model-side bundle for further reference.
    # ------------------------------------------------------------------
    # Constructed only as a transient invariant check on
    # raw-type / reference-array canonicalization. Re-using the frozen
    # model here ensures the parser cannot bypass model layer invariants.
    bundle = ShellAuthorityEvidenceBundle(
        schema_version="task023.shell-authority-evidence-bundle.v1",
        bundle_id=cast(str, bundle_id),
        bundle_version=cast(str, bundle_version),
        approval_status=bundle_approval,
        permission_evidence=perm_records_tuple,
        provenance_edges=edge_records_tuple,
        local_kernel_usage_scope=local_kernel_usage_canon,
        evidence_refs=bundle_evidence_refs_canon,
        task012_validation_hash=task012_validation_hash,
        bundle_hash=expected_bundle_hash,
    )
    assert bundle.bundle_id == bundle_id  # round-trip contract

    # ------------------------------------------------------------------
    # Stage 7 — records list iteration
    # ------------------------------------------------------------------
    if not records_seq:
        failures.append(
            _make_entry(
                "SGC_RECORDS_INVALID",
                stage_rank=_STAGE_RECORDS_LIST,
                field_path="raw_catalog.records",
            )
        )
        _raise(failures)

    # ------------------------------------------------------------------
    # Stage 8 — per-record fields, identity, raw types, stable geometry_id binding
    # ------------------------------------------------------------------
    record_expected = frozenset(
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

    used_stable_ids: dict[str, int] = {}
    raw_records_seen: list[dict[str, Any]] = []  # for later duplicate/full hashing

    for idx, raw_rec in enumerate(records_seq):
        if not isinstance(raw_rec, Mapping):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}]",
                )
            )
            continue

        actual_keys = frozenset(raw_rec)
        extras = actual_keys - record_expected
        missing = record_expected - actual_keys
        for extra in sorted(extras):
            failures.append(
                _make_entry(
                    "SGC_UNKNOWN_FIELD",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].{extra}",
                )
            )
        for m in sorted(missing):
            failures.append(
                _make_entry(
                    "SGC_UNKNOWN_FIELD",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].{m}",
                )
            )

        # Strict raw types — all of these are Stage 8 record-fields.
        rec_schema = raw_rec.get("schema_version")
        if not _is_nonempty_str(rec_schema):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].schema_version",
                )
            )
            continue
        if rec_schema != "task023.approved-shell-geometry-record.v1":
            failures.append(
                _make_entry(
                    "SGC_SCHEMA_VERSION_UNSUPPORTED",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].schema_version",
                )
            )
            continue

        # geometry_id raw-type stage (must be non-empty string). Stable-id
        # binding verified at stage 9 once revision is also validated.
        geom_id_raw = raw_rec.get("geometry_id")
        if not _is_nonempty_str(geom_id_raw):
            failures.append(
                _make_entry(
                    "SGC_RECORD_ID_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].geometry_id",
                )
            )
            continue
        geom_type_raw = raw_rec.get("geometry_type")
        if not _is_nonempty_str(geom_type_raw):
            failures.append(
                _make_entry(
                    "SGC_GEOMETRY_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].geometry_type",
                )
            )
            continue
        if geom_type_raw != GEOMETRY_TYPE:
            failures.append(
                _make_entry(
                    "SGC_GEOMETRY_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].geometry_type",
                )
            )
            continue
        profile_id_raw = raw_rec.get("profile_id")
        if not _is_nonempty_str(profile_id_raw) or profile_id_raw != PROFILE_ID:
            failures.append(
                _make_entry(
                    "SGC_PROFILE_UNSUPPORTED",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].profile_id",
                )
            )
            continue
        revision_raw = raw_rec.get("revision")
        if not _is_nonempty_str(revision_raw):
            failures.append(
                _make_entry(
                    "SGC_REVISION_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].revision",
                )
            )
            continue
        approval_raw = raw_rec.get("approval_state")
        if not _is_nonempty_str(approval_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].approval_state",
                )
            )
            continue
        sid_raw = raw_rec.get("shell_inside_diameter_m")
        if not _is_nonempty_str(sid_raw):
            # Raw-type violation: emit BOTH the general raw-type and
            # the design-frozen SGC_SHELL_INSIDE_DIAMETER_INVALID
            # blocker so callers can detect decimal-specific failures
            # even when the raw type is wrong.
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].shell_inside_diameter_m",
                )
            )
            failures.append(
                _make_entry(
                    "SGC_SHELL_INSIDE_DIAMETER_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].shell_inside_diameter_m",
                )
            )
            continue
        nominal_raw = raw_rec.get("nominal_label")
        if nominal_raw is not None and (not isinstance(nominal_raw, str) or not nominal_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].nominal_label",
                )
            )
            continue
        src_cls_raw = raw_rec.get("source_class")
        if not _is_nonempty_str(src_cls_raw):
            failures.append(
                _make_entry(
                    "SGC_SOURCE_CLASS_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].source_class",
                )
            )
            continue
        if src_cls_raw not in RECOGNIZED_SOURCE_CLASSES:
            failures.append(
                _make_entry(
                    "SGC_SOURCE_CLASS_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].source_class",
                )
            )
            continue

        # License evidence raw type
        license_raw = raw_rec.get("license_evidence")
        if not _is_nonempty_mapping(license_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].license_evidence",
                )
            )
            continue

        # Source binding: raw type, exact fields
        binding_raw = raw_rec.get("source_binding")
        if not _is_nonempty_mapping(binding_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].source_binding",
                )
            )
            continue
        binding_expected = frozenset(
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
        binding_extras = frozenset(binding_raw) - binding_expected
        for extra in sorted(binding_extras):
            failures.append(
                _make_entry(
                    "SGC_SOURCE_BINDING_INCOMPLETE",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].source_binding.{extra}",
                )
            )
        binding_missing = binding_expected - frozenset(binding_raw)
        for m in sorted(binding_missing):
            failures.append(
                _make_entry(
                    "SGC_SOURCE_BINDING_INCOMPLETE",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].source_binding.{m}",
                )
            )

        if binding_extras or binding_missing:
            continue
        # binding string fields raw type
        binding_ok = True
        for key in binding_expected:
            if not _is_nonempty_str(binding_raw.get(key)):
                failures.append(
                    _make_entry(
                        "SGC_RAW_TYPE_INVALID",
                        stage_rank=_STAGE_RECORD_FIELDS,
                        field_path=f"raw_catalog.records[{idx}].source_binding.{key}",
                    )
                )
                binding_ok = False
        if not binding_ok:
            continue
        binding = ShellSourceBinding(**{key: binding_raw[key] for key in binding_expected})

        # Reference arrays: canonical deduplication + sort
        perm_refs_raw = raw_rec.get("permission_evidence_refs")
        edge_refs_raw = raw_rec.get("provenance_edge_ids")
        evidence_refs_raw = raw_rec.get("evidence_refs")

        # evidence_refs on records: same-stage accumulation per index,
        # but we need values for further hash stage — defer validation
        # of non-empty-ness to stage 17. For now strict types only.
        if not _is_str_seq(perm_refs_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].permission_evidence_refs",
                )
            )
            continue
        if not _is_str_seq(edge_refs_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].provenance_edge_ids",
                )
            )
            continue
        if not _is_str_seq(evidence_refs_raw):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].evidence_refs",
                )
            )
            continue
        perm_refs_canon = _canonicalize_str_seq(perm_refs_raw, unique=True)
        edge_refs_canon = _canonicalize_str_seq(edge_refs_raw, unique=True)
        ev_refs_canon = _canonicalize_str_seq(evidence_refs_raw, unique=True)
        if perm_refs_canon is None or edge_refs_canon is None or ev_refs_canon is None:
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}]",
                )
            )
            continue

        # record_hash raw type
        rec_hash_in = raw_rec.get("record_hash")
        if not _is_nonempty_str(rec_hash_in) or not re.fullmatch(r"[0-9a-f]{64}", rec_hash_in):
            failures.append(
                _make_entry(
                    "SGC_RAW_TYPE_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].record_hash",
                )
            )
            continue

        # Stage 9 — duplicate stable geometry_id (within this run)
        # We split the raw geometry_id into (record_key, revision) and
        # check the canonical form. The raw value is the full stable id.
        # _verify_stable_geometry_identity carries its own occurrence
        # rank: the four-part check is itself a Stage-9 occurrence.
        parsed_id = _verify_stable_geometry_identity(
            catalog_id=catalog_id,
            raw_id=geom_id_raw,
            failures=failures,
            stage_rank=_STAGE_DUPLICATE_IDS,
        )
        if parsed_id is None:
            continue
        record_key, revision_in_id = parsed_id
        if revision_in_id != revision_raw:
            # The revision component embedded in the geometry_id MUST
            # equal the raw revision field. This is a record-fields
            # stage occurrence (Stage 8), not duplicate-ids.
            failures.append(
                _make_entry(
                    "SGC_REVISION_INVALID",
                    stage_rank=_STAGE_RECORD_FIELDS,
                    field_path=f"raw_catalog.records[{idx}].geometry_id",
                    details={
                        "geometry_id_revision": revision_in_id,
                        "record_revision": revision_raw,
                    },
                )
            )
            continue
        stable_id = geom_id_raw
        # Stage 9 — duplicate stable geometry_id (within this run).
        # Same-stage accumulation: when a duplicate is detected, ALL
        # subsequent stages still run on the duplicate record. Only
        # the first occurrence participates in the hash-domain
        # computation that produces the model record list.
        first_index = used_stable_ids.get(stable_id)
        if first_index is not None:
            failures.append(
                _make_entry(
                    "SGC_RECORD_DUPLICATE_ID",
                    stage_rank=_STAGE_DUPLICATE_IDS,
                    field_path=f"raw_catalog.records[{first_index}].geometry_id",
                    details={"stable_geometry_id": stable_id},
                )
            )
            failures.append(
                _make_entry(
                    "SGC_RECORD_DUPLICATE_ID",
                    stage_rank=_STAGE_DUPLICATE_IDS,
                    field_path=f"raw_catalog.records[{idx}].geometry_id",
                    details={"stable_geometry_id": stable_id},
                )
            )
            # Continue into stage 10+ validation of THIS record so the
            # same-stage accumulation contract holds — but do not let
            # it contribute to raw_records_seen (the model layer
            # contains only the first occurrence).
            duplicate_of_first = True
        else:
            used_stable_ids[stable_id] = idx
            duplicate_of_first = False
        # ``record_key`` is captured so the parser can use it
        # downstream (per-design stable-identity binding) without
        # recomputing from the raw geometry_id.
        _ = record_key

        # We collect raw dict + validated fields. Phase-2 stages (10+)
        # operate on each independently. Same-stage accumulation is
        # preserved by appending per-record failures to the master list
        # without short-circuiting the rest of the stage. Duplicate
        # records still run stages 10+ on the raw record but do not
        # contribute to the final catalog (only the first occurrence
        # does).
        if not duplicate_of_first:
            raw_records_seen.append(
                {
                    "raw": dict(raw_rec),
                    "binding": binding,
                    "license_raw": dict(license_raw),
                    "perm_refs": perm_refs_canon,
                    "edge_refs": edge_refs_canon,
                    "evidence_refs": ev_refs_canon,
                    "record_hash_in": rec_hash_in,
                    "stable_id": stable_id,
                    "geom_id": geom_id_raw,
                    "revision": revision_raw,
                    "approval_raw": approval_raw,
                    "src_cls": src_cls_raw,
                    "nominal_label": nominal_raw,
                    "sid_raw": sid_raw,
                }
            )
        else:
            # Duplicate record — skip model-layer contribution but
            # still execute stages 10+ on the SAME record by walking
            # through the type-narrowed locals below (approval,
            # diameter, source class, license, refs). They will
            # append additional per-record blockers (independent
            # same-stage accumulation).
            pass

    # ------------------------------------------------------------------
    # Stage 10–17 per-record validation
    # ------------------------------------------------------------------
    if not raw_records_seen:
        _raise(failures)

    # Compute stage 14 source_class/license disposition + stage 16 vendor
    # gate + stage 17 reference resolution using the collective bundle.
    perm_by_id = {p.permission_id: p for p in perm_records_tuple}
    edge_by_id = {e.edge_id: e for e in edge_records_tuple}

    # ------------------------------------------------------------------
    # Stage 17a — local_kernel_usage_scope (recorded on bundle) is not
    # a permission token. It only gates vendor usage_scope.
    # ------------------------------------------------------------------

    for ri, info in enumerate(raw_records_seen):
        src_cls = info["src_cls"]

        # Stage 13 — decimal
        # Stage 13 — decimal validation
        # Even if the raw-type check passed (empty/leading-+ rejections
        # the design explicitly tracks under DIAMETER_INVALID), the
        # canonical-decimal rules emit SGC_SHELL_INSIDE_DIAMETER_INVALID
        # for ALL invalid shapes — not SGC_RAW_TYPE_INVALID. The
        # raw-type gate at stage 8 is intentionally a fast-path only
        # for non-string numeric inputs.
        sid_raw = info["sid_raw"]
        try:
            _check_shell_inside_diameter_m(sid_raw)
        except ValueError:
            failures.append(
                _make_entry(
                    "SGC_SHELL_INSIDE_DIAMETER_INVALID",
                    stage_rank=_STAGE_DIAMETER_DECIMAL,
                    field_path=f"raw_catalog.records[{ri}].shell_inside_diameter_m",
                )
            )
            continue

        # Stage 10 — approval lexical
        approval_raw_v = info["approval_raw"]
        if approval_raw_v not in APPROVAL_STATES:
            failures.append(
                _make_entry(
                    "SGC_APPROVAL_STATE_INVALID",
                    stage_rank=_STAGE_APPROVAL_LEXICAL,
                    field_path=f"raw_catalog.records[{ri}].approval_state",
                    details={"value": approval_raw_v},
                )
            )
            continue
        # Stage 11 — approved only via parser
        if approval_raw_v != "approved":
            failures.append(
                _make_entry(
                    "SGC_RECORD_UNAPPROVED",
                    stage_rank=_STAGE_APPROVAL_STATE,
                    field_path=f"raw_catalog.records[{ri}].approval_state",
                    details={"value": approval_raw_v},
                )
            )
            continue

        # Stage 14 — license disposition gate
        try:
            # Validate the license form for any non-internal source class.
            # For internal sources we only verify that the form token
            # equals ``project_internal_authority`` (see gate below).
            if src_cls not in _INTERNAL_SOURCE_CLASSES:
                _ = _classify_license_form(info["license_raw"])
        except ValueError:
            failures.append(
                _make_entry(
                    "SGC_LICENSE_BLOCKED",
                    stage_rank=_STAGE_LICENSE_DISPOSITION,
                    field_path=f"raw_catalog.records[{ri}].license_evidence",
                )
            )
            continue

        # disposition: enforce internal-authority rule, vendor-scope rule.
        if src_cls in _INTERNAL_SOURCE_CLASSES:
            license_form_token = info["license_raw"].get("license_form", "")
            if license_form_token != _INTERNAL_AUTHORITY:
                failures.append(
                    _make_entry(
                        "SGC_LICENSE_BLOCKED",
                        stage_rank=_STAGE_LICENSE_DISPOSITION,
                        field_path=f"raw_catalog.records[{ri}].license_evidence",
                    )
                )
                continue
        # Stage 14 — vendor permission scope gate (and reference
        # resolution for non-vendor records).
        if src_cls == "VENDOR_PERMISSIONED":
            # every vendor record MUST have at least one permission ref
            # whose permission is RESOLVED in the bundle AND whose
            # permission_scope includes the required repository storage /
            # redistribution tokens, AND whose usage_scope intersects
            # the bundle's local_kernel_usage_scope.
            if not info["perm_refs"]:
                failures.append(
                    _make_entry(
                        "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
                        stage_rank=_STAGE_REF_RESOLUTION,
                        field_path=f"raw_catalog.records[{ri}].permission_evidence_refs",
                    )
                )
                continue
            ok = True
            for perm_ref in info["perm_refs"]:
                if perm_ref not in perm_by_id:
                    failures.append(
                        _make_entry(
                            "SGC_EVIDENCE_REFS_INVALID",
                            stage_rank=_STAGE_REF_RESOLUTION,
                            field_path=f"raw_catalog.records[{ri}].permission_evidence_refs",
                            evidence_refs=(perm_ref,),
                        )
                    )
                    ok = False
                    continue
                perm = perm_by_id[perm_ref]
                scope_list: list[str] = list(perm.permission_scope)
                scope_set = set(scope_list)
                required_tokens: list[str] = list(VENDOR_PERMISSION_REQUIRED_SCOPE_TOKENS)
                missing_scopes = [tok for tok in required_tokens if tok not in scope_set]
                if missing_scopes:
                    failures.append(
                        _make_entry(
                            "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
                            stage_rank=_STAGE_REF_RESOLUTION,
                            field_path=f"raw_catalog.records[{ri}].permission_evidence_refs",
                            evidence_refs=(perm_ref,),
                            details={"missing": missing_scopes},
                        )
                    )
                    ok = False
                    continue
                usage_set = set(perm.usage_scope)
                kernel_scope_set = set(local_kernel_usage_canon)
                if not usage_set:
                    # Amendment 001 §5: an empty vendor usage_scope
                    # means the vendor grants nothing; the record MUST
                    # block.
                    failures.append(
                        _make_entry(
                            "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
                            stage_rank=_STAGE_REF_RESOLUTION,
                            field_path=f"raw_catalog.records[{ri}].permission_evidence_refs",
                            evidence_refs=(perm_ref,),
                            details={
                                "missing": sorted(kernel_scope_set),
                                "usage_scope": [],
                                "local_kernel_usage_scope": sorted(kernel_scope_set),
                                "reason": "empty_vendor_usage_scope",
                            },
                        )
                    )
                    ok = False
                    continue
                # Amendment 001 §5 — semantics:
                #   vendor.usage_scope MUST be a non-empty SUBSET of
                #   kernel.local_kernel_usage_scope. The kernel
                #   declaring extra tokens beyond the vendor grant is
                #   allowed (kernel implements a superset of what the
                #   vendor authorized for this content). Vendor-only
                #   tokens the kernel does NOT support MUST block.
                not_authorized_by_kernel = sorted(usage_set - kernel_scope_set)
                if not_authorized_by_kernel:
                    failures.append(
                        _make_entry(
                            "SGC_VENDOR_PERMISSION_SCOPE_INCOMPLETE",
                            stage_rank=_STAGE_REF_RESOLUTION,
                            field_path=f"raw_catalog.records[{ri}].permission_evidence_refs",
                            evidence_refs=(perm_ref,),
                            details={
                                "vendor_usage_tokens_not_in_local_kernel_scope": (
                                    not_authorized_by_kernel
                                ),
                                "usage_scope": sorted(usage_set),
                                "local_kernel_usage_scope": sorted(kernel_scope_set),
                                "reason": "vendor_usage_token_not_in_local_kernel_scope",
                            },
                        )
                    )
                    ok = False
                    continue
            if not ok:
                continue

        else:
            # Non-vendor: permission refs (if any) must each resolve to a
            # known permission in the bundle. Empty permission refs are
            # permitted for PUBLIC_DOMAIN / INTERNAL / DERIVED source
            # classes; USER_PROVIDED_LICENSED_SUMMARY /
            # REFERENCE_ONLY_RESTRICTED_STANDARD require non-empty
            # permission_evidence_refs (TASK-012 license requires a
            # pointer token at parse time).
            for perm_ref in info["perm_refs"]:
                if perm_ref not in perm_by_id:
                    failures.append(
                        _make_entry(
                            "SGC_EVIDENCE_REFS_INVALID",
                            stage_rank=_STAGE_REF_RESOLUTION,
                            field_path=f"raw_catalog.records[{ri}].permission_evidence_refs",
                            evidence_refs=(perm_ref,),
                        )
                    )
            if (
                src_cls
                in {
                    "USER_PROVIDED_LICENSED_SUMMARY",
                    "REFERENCE_ONLY_RESTRICTED_STANDARD",
                }
                and not info["perm_refs"]
            ):
                failures.append(
                    _make_entry(
                        "SGC_EVIDENCE_REFS_INVALID",
                        stage_rank=_STAGE_REF_RESOLUTION,
                        field_path=f"raw_catalog.records[{ri}].permission_evidence_refs",
                    )
                )
                continue

        # Stage 16 — provenance_edge_ids must each resolve to a known edge
        # whose target_geometry_id matches THIS record's geometry_id.
        for edge_ref in info["edge_refs"]:
            if edge_ref not in edge_by_id:
                failures.append(
                    _make_entry(
                        "SGC_PROVENANCE_INCOMPLETE",
                        stage_rank=_STAGE_REF_RESOLUTION,
                        field_path=f"raw_catalog.records[{ri}].provenance_edge_ids",
                        evidence_refs=(edge_ref,),
                    )
                )
                continue
            edge = edge_by_id[edge_ref]
            if edge.target_geometry_id != info["geom_id"]:
                failures.append(
                    _make_entry(
                        "SGC_PROVENANCE_INCOMPLETE",
                        stage_rank=_STAGE_REF_RESOLUTION,
                        field_path=f"raw_catalog.records[{ri}].provenance_edge_ids",
                        evidence_refs=(edge_ref,),
                        details={
                            "edge_target": edge.target_geometry_id,
                            "record_id": info["geom_id"],
                        },
                    )
                )

        # Stage 17 preparation — evidence_refs on a record must be non-empty
        # and properly canonicalized BEFORE the record_hash domain is
        # computed. (Original loop ran at stage 8; the gate is now placed
        # in the ref-resolution stage so the failure is recorded at the
        # right occurrence rank.)
        if not info["evidence_refs"]:
            failures.append(
                _make_entry(
                    "SGC_EVIDENCE_REFS_INVALID",
                    stage_rank=_STAGE_REF_RESOLUTION,
                    field_path=f"raw_catalog.records[{ri}].evidence_refs",
                )
            )

        # If any failure-blocker was emitted during per-record resolution
        # above, continue to the next record to preserve same-stage
        # accumulation. The fail-closed model requires that records
        # with independent errors still attempt validation.
        # Continue.

    # ------------------------------------------------------------------
    # Recompute record hashes + collect valid records for catalog
    # ------------------------------------------------------------------
    if failures:
        # We emit any blockers accumulated so far before recomputing the
        # record-hash domain; per-stage gates apply at the end of each
        # stage, not after each record.
        pass

    constructed: list[ShellGeometryRecord] = []
    # Round 3 §4 — dependent-stage gating: track which records had any
    # upstream semantic-stage failure (stages 8/10/11/12/13/14) so we
    # do NOT compute the record_hash for those records. Computing the
    # hash from a half-validated record would produce a misleading
    # RECORD_HASH_MISMATCH layered on top of the true root cause.
    per_record_upstream_failures: dict[int, set[str]] = {}
    for ri, _ in enumerate(raw_records_seen):
        per_record_upstream_failures[ri] = set()
    # Re-scan the existing failures to bucket them by record index.
    for failure in failures:
        # field_path patterns like "raw_catalog.records[<idx>]..."
        if failure.field_path.startswith("raw_catalog.records["):
            try:
                bracket_close = failure.field_path.index("]")
                ri_str = failure.field_path[len("raw_catalog.records[") : bracket_close]
                ri = int(ri_str)
            except (ValueError, IndexError):
                continue
            per_record_upstream_failures.setdefault(ri, set()).add(failure.code)
    record_stage_fail_codes = {
        "SGC_RECORD_HASH_MISMATCH",
    }
    for ri, info in enumerate(raw_records_seen):
        rec_payload = {
            "schema_version": "task023.approved-shell-geometry-record.v1",
            "geometry_id": info["geom_id"],
            "geometry_type": "shell",
            "profile_id": PROFILE_ID,
            "revision": info["revision"],
            "approval_state": "approved",
            "shell_inside_diameter_m": info["sid_raw"],
            "source_class": info["src_cls"],
            "license_evidence": dict(info["license_raw"]),
            "source_binding": {
                "source_id": info["binding"].source_id,
                "source_type": info["binding"].source_type,
                "source_revision": info["binding"].source_revision,
                "source_location": info["binding"].source_location,
                "evidence_ref": info["binding"].evidence_ref,
                "approved_by": info["binding"].approved_by,
                "approved_at": info["binding"].approved_at,
            },
            "permission_evidence_refs": list(info["perm_refs"]),
            "provenance_edge_ids": list(info["edge_refs"]),
            "evidence_refs": list(info["evidence_refs"]),
        }
        # Exclude ``nominal_label`` and ``record_hash`` from the hash
        # domain (per the design contract §6).
        hash_payload = {
            k: v for k, v in rec_payload.items() if k not in {"nominal_label", "record_hash"}
        }
        # Round 3 §4 — dependent-stage gating: if THIS record already
        # has any upstream semantic-stage failure, do not compute its
        # record_hash. The expected hash would not match the supplied
        # raw hash (different content), producing a misleading
        # RECORD_HASH_MISMATCH layered on top of the true root cause.
        upstream_failures_for_record = per_record_upstream_failures.get(ri, set())
        semantic_upstream = upstream_failures_for_record - record_stage_fail_codes
        if semantic_upstream:
            continue
        expected_record_hash = canonical_sha256(hash_payload)

        if expected_record_hash != info["record_hash_in"]:
            failures.append(
                _make_entry(
                    "SGC_RECORD_HASH_MISMATCH",
                    stage_rank=_STAGE_HASHES,
                    field_path=f"raw_catalog.records[{ri}].record_hash",
                    details={
                        "expected": expected_record_hash,
                        "actual": info["record_hash_in"],
                    },
                )
            )
            continue

        record = ShellGeometryRecord(
            schema_version="task023.approved-shell-geometry-record.v1",
            geometry_id=info["geom_id"],
            geometry_type="shell",
            profile_id=PROFILE_ID,
            revision=info["revision"],
            approval_state="approved",
            shell_inside_diameter_m=info["sid_raw"],
            nominal_label=info["nominal_label"] if isinstance(info["nominal_label"], str) else None,
            source_class=info["src_cls"],
            license_evidence=_DeepFrozen(info["license_raw"]).view(),
            source_binding=info["binding"],
            permission_evidence_refs=info["perm_refs"],
            provenance_edge_ids=info["edge_refs"],
            evidence_refs=info["evidence_refs"],
            record_hash=info["record_hash_in"],
        )
        constructed.append(record)

    if not constructed:
        _raise(failures)
    if failures:
        _raise(failures)

    # ------------------------------------------------------------------
    # Stage 18 — catalog hash recomputation (covers records in
    # canonical identity order: (geometry_id, revision, record_hash)).
    # ------------------------------------------------------------------
    sorted_records = tuple(
        sorted(constructed, key=lambda r: (r.geometry_id, r.revision, r.record_hash))
    )
    record_hashes_canonical = tuple(r.record_hash for r in sorted_records)
    catalog_payload = {
        "schema_version": "task023.approved-shell-geometry-catalog.v1",
        "catalog_id": catalog_id,
        "catalog_version": catalog_version,
        "profile_id": PROFILE_ID,
        "authority": authority,
        "source_revision": source_revision,
        "effective_at": effective_at,
        "evidence_bundle_hash": expected_bundle_hash,
        "record_hashes": list(record_hashes_canonical),
    }
    expected_catalog_hash = canonical_sha256(catalog_payload)
    catalog_hash_in = raw_catalog.get("catalog_hash")
    if not _is_nonempty_str(catalog_hash_in) or not re.fullmatch(r"[0-9a-f]{64}", catalog_hash_in):
        failures.append(
            _make_entry(
                "SGC_CATALOG_HASH_MISMATCH",
                stage_rank=_STAGE_HASHES,
                field_path="raw_catalog.catalog_hash",
            )
        )
        _raise(failures)
    # Round 3 §4 — dependent-stage gating: if any record_hash failed
    # in the previous stage, do not even compare catalog_hash (which
    # would produce a spurious SGC_CATALOG_HASH_MISMATCH from the
    # incomplete constructed record set).
    if any(f.code == "SGC_RECORD_HASH_MISMATCH" for f in failures):
        _raise(failures)
    if expected_catalog_hash != catalog_hash_in:
        failures.append(
            _make_entry(
                "SGC_CATALOG_HASH_MISMATCH",
                stage_rank=_STAGE_HASHES,
                field_path="raw_catalog.catalog_hash",
                details={
                    "expected": expected_catalog_hash,
                    "actual": catalog_hash_in,
                },
            )
        )
        _raise(failures)

    # ------------------------------------------------------------------
    # Build catalog (frozen model layer freezes nested mapping via
    # ``_DeepFrozen`` view passed as license_evidence).
    # ------------------------------------------------------------------
    catalog = ShellGeometryCatalog(
        schema_version="task023.approved-shell-geometry-catalog.v1",
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        profile_id=PROFILE_ID,
        authority=authority,
        source_revision=source_revision,
        records=tuple(sorted_records),
        evidence_bundle_hash=expected_bundle_hash,
        catalog_hash=catalog_hash_in,
        effective_at=effective_at,
    )
    return catalog


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def select_approved_shell_geometry(
    *,
    catalog: ShellGeometryCatalog,
    geometry_id: str,
) -> ShellGeometryRecord:
    """Return the record matching ``geometry_id`` exactly.

    - ``geometry_id`` must be a non-empty string.
    - Lookup is exact-identity; no nearest / prefix / fallback /
      revision upgrade / ranking.
    - Returns the frozen record held by the catalog.
    """
    if not isinstance(geometry_id, str) or not geometry_id:
        # Stage 20 — selection raw input (occurrence: raw ID)
        raise ShellGeometryCatalogFailure(
            [
                _make_entry(
                    "SGC_RECORD_ID_INVALID",
                    stage_rank=_STAGE_SELECTION,
                    field_path="geometry_id",
                )
            ]
        )
    if not isinstance(catalog, ShellGeometryCatalog):
        # Stage 20 — selection raw input (occurrence: catalog type)
        raise ShellGeometryCatalogFailure(
            [
                _make_entry(
                    "SGC_RECORD_ID_INVALID",
                    stage_rank=_STAGE_SELECTION,
                    field_path="catalog",
                )
            ]
        )

    # Stage 20 — selection exact lookup
    for rec in catalog.records:
        if rec.geometry_id == geometry_id:
            # Stage 20 — selection approval recheck
            if rec.approval_state != "approved":
                raise ShellGeometryCatalogFailure(
                    [
                        _make_entry(
                            "SGC_SELECTION_NOT_APPROVED",
                            stage_rank=_STAGE_SELECTION,
                            field_path="geometry_id",
                            details={"geometry_id": geometry_id},
                        )
                    ]
                )
            return rec
    raise ShellGeometryCatalogFailure(
        [
            _make_entry(
                "SGC_RECORD_NOT_FOUND",
                stage_rank=_STAGE_SELECTION,
                field_path="geometry_id",
                details={"geometry_id": geometry_id},
            )
        ]
    )


# ---------------------------------------------------------------------------
# Internal helpers — types & deep-freeze
# ---------------------------------------------------------------------------


def _is_nonempty_str(value: Any) -> TypeGuard[str]:
    """TypeGuard: ``value`` is a non-empty ``str``."""
    return isinstance(value, str) and bool(value)


def _is_nonempty_mapping(value: Any) -> TypeGuard[Mapping[str, Any]]:
    return isinstance(value, Mapping) and bool(value)


def _is_str_seq(value: Any) -> TypeGuard[Sequence[Any]]:
    """TypeGuard: ``value`` is a list/tuple (not a string)."""
    return isinstance(value, (list, tuple)) and not isinstance(value, str)


def _canonicalize_str_seq(
    value: Any,
    *,
    unique: bool = False,
) -> tuple[str, ...] | None:
    """Return a canonical (sorted-by-Unicode-codepoint) tuple of strings.

    Returns ``None`` if any entry is not a non-empty string, or if
    ``unique`` is ``True`` and duplicates are detected.
    """
    if not _is_str_seq(value):
        return None
    items = list(value)
    for entry in items:
        if not _is_nonempty_str(entry):
            return None
    if unique:
        seen: dict[str, None] = {}
        for entry in items:
            if entry in seen:
                return None
            seen[entry] = None
    return tuple(sorted(items))


class _DeepFrozen:
    """Read-only dict proxy with frozen nested mappings / sequences.

    Used so the catalog surface carries the same caller-mutable
    isolation guarantee that the design contract §10 / Issue #151
    promise. ``view()`` returns a fresh ``MappingProxyType``.
    """

    __slots__ = ("_proxy",)

    def __init__(self, payload: Mapping[str, Any]) -> None:
        import types

        self._proxy = types.MappingProxyType(
            {key: _freeze_for_proxy(item) for key, item in payload.items()}
        )

    def view(self) -> Mapping[str, Any]:
        return self._proxy


def _freeze_for_proxy(value: Any) -> Any:
    """Return a read-only view of nested data for the license_evidence field."""
    import types

    if isinstance(value, Mapping):
        return types.MappingProxyType({key: _freeze_for_proxy(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_for_proxy(item) for item in value)
    return value


def _raise(failures: list[ShellGeometryCatalogBlockerEntry]) -> NoReturn:
    """Raise ShellGeometryCatalogFailure unconditionally.

    The signature is annotated ``NoReturn`` so mypy narrows the type
    of guard-protected values after the call returns.
    """
    raise ShellGeometryCatalogFailure(failures)


def _is_nonempty_str_strict(v: Any) -> bool:
    return isinstance(v, str) and bool(v)

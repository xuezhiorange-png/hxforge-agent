"""TASK-021 Slice B geometry adapter.

This module implements the frozen ``build_approved_tube_geometry_snapshot``
operation described in Issue #141 Record 2 / Record 5. It is a pure
adapter: it consumes an already-loaded TASK-016 ``GeometryCatalog``
instance, performs deterministic selection by an explicit ``geometry_id``
string, and on a successful path returns an immutable TASK-021
``ApprovedTubeGeometrySnapshot``.

The adapter never performs:

* filesystem I/O (no ``os`` / ``pathlib`` / ``open`` / ``glob`` /
  ``rglob``);
* network I/O (``socket`` / ``requests`` / ``httpx``);
* database I/O;
* environment lookups;
* clock / runtime-now reads;
* locale lookups;
* global registry writes;
* directory scans;
* nearest-size / first-match / default-record fallbacks.

The module deliberately reuses the canonical decimal / hash / ordering
authorities from ``.canonical`` and the snapshot-shape
``ApprovedTubeGeometrySnapshot`` + ``SourceBindingSnapshot`` from
``.models``. The 15-step verification order is binding (Record 5).

Failure model: every complete ``MessageEntry`` blocker produced by any
stage is retained and ordered per TASK-021 §11.3. The adapter raises
``AdapterFailure`` (from ``.adapter_blockers``) carrying the complete
ordered blocker list. The adapter never returns a partial snapshot.

Defensive terminal check: on a successful path the adapter calls the
existing slice-A ``verify_geometry_snapshot`` to re-confirm the emitted
``ApprovedTubeGeometrySnapshot`` is internally consistent. Any failure
from that hook is wrapped in ``AdapterFailure``.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_EVEN
from typing import Any, Final

from hexagent.geometry_catalogs.catalog import (
    compute_catalog_content_hash,
    compute_record_hash,
)
from hexagent.geometry_catalogs.models import (
    APPROVAL_STATE_APPROVED,
    GEOMETRY_TYPE_TUBE,
    GeometryCatalog,
    GeometryRecord,
    TubeGeometryRecord,
)
from hexagent.geometry_catalogs.models import (
    SourceBinding as GeometrySourceBinding,
)

from .adapter_blockers import (
    GEOMETRY_ADAPTER_DEFAULT_FIELD_PATH,
    GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY,
    AdapterFailure,
    GeometryAdapterBlockerCode,
    build_message_entry,
    sort_adapter_blockers,
)
from .authority import verify_geometry_snapshot
from .canonical import (
    DECIMAL_PRECISION,
    CanonicalizationError,
    decimal_string,
    parse_decimal,
    sha256_hex,
)
from .models import (
    ApprovedTubeGeometrySnapshot,
    MessageEntry,
    SourceBindingSnapshot,
)

# Geometric consistency tolerance inherited from TASK-016 (1e-9 m).
# Mirrors hexagent.geometry_catalogs.catalog.GEOMETRY_DIMENSION_TOLERANCE_M
# without importing I/O modules.
_GEOMETRY_DIMENSION_TOLERANCE_M: Final[float] = 1e-9


# Slice-A closed source-class token for catalog content hash fields.
_TUBE_REQUIRED_DIMENSION_FIELDS: Final[tuple[str, ...]] = (
    "outer_diameter_m",
    "inner_diameter_m",
    "wall_thickness_m",
)


def _coerce_dimension_string(
    value: Any,
    *,
    field_name: str,
    geometry_id: str,
    positive: bool = True,
) -> str:
    """Coerce an upstream value (float / int / Decimal / str) to a TASK-021
    canonical decimal string.

    The function accepts the upstream runtime shapes because the slice-A
    ``parse_decimal`` requires a string already in canonical lexical form;
    we therefore go through Decimal internally rather than calling
    ``float_to_canonical_decimal_string`` whenever possible.
    """
    from decimal import Decimal, localcontext

    if isinstance(value, str):
        # Already a string; pass through parse_decimal for validation
        # (returns the Decimal, which we serialize canonically).
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            if positive:
                return decimal_string(parse_decimal(value, positive=True))
            return decimal_string(parse_decimal(value, positive=False))
    if isinstance(value, bool):
        # bool is a forbidden shape here — slice-A bans booleans as numbers.
        raise CanonicalizationError(f"geometry {geometry_id} {field_name} is a bool, not a number")
    if isinstance(value, int):
        if positive and value <= 0:
            raise CanonicalizationError(f"geometry {geometry_id} {field_name} must be positive")
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(Decimal(value))
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalizationError(f"geometry {geometry_id} {field_name} is not finite")
        dec = Decimal(str(value))
        if not dec.is_finite():
            raise CanonicalizationError(f"geometry {geometry_id} {field_name} is not finite")
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(dec)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError(f"geometry {geometry_id} {field_name} is not finite")
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            return decimal_string(value)
    raise CanonicalizationError(
        f"geometry {geometry_id} {field_name} has unsupported type {type(value).__name__}"
    )


def _source_binding_to_snapshot(
    binding: GeometrySourceBinding,
) -> SourceBindingSnapshot:
    """Strict seven-field projection (one slice-A spec calls for it).

    The slice-A ``SourceBindingSnapshot`` requires every one of the seven
    fields to be non-empty strings; the upstream TASK-016 ``SourceBinding``
    dataclass exposes them with the same names, so the field-by-field
    projection is direct.
    """
    return SourceBindingSnapshot(
        source_id=binding.source_id,
        source_type=binding.source_type,
        source_revision=binding.source_revision,
        source_location=binding.source_location,
        evidence_ref=binding.evidence_ref,
        approved_by=binding.approved_by,
        approved_at=binding.approved_at,
    )


def _is_geometry_catalog(value: Any) -> bool:
    """Return True iff ``value`` is exactly a TASK-016 ``GeometryCatalog``.

    The runtime type is the ``@dataclass(frozen=True)`` from
    ``hexagent.geometry_catalogs.models``. Rejecting any duck-typed mapping
    or a non-catalog-bearing dict is part of the closed-internal-contract
    rule.
    """
    try:
        return isinstance(value, GeometryCatalog)
    except TypeError:
        return False


def build_approved_tube_geometry_snapshot(
    *,
    catalog: GeometryCatalog,
    geometry_id: str,
) -> ApprovedTubeGeometrySnapshot:
    """Build one TASK-021 ``ApprovedTubeGeometrySnapshot``.

    See Issue #141 Record 5 for the binding 15-step verification order.
    Raises ``AdapterFailure`` (from ``.adapter_blockers``) carrying the
    complete, slice-A §11.3-ordered blocker list on any failure path.
    The terminal defensive check calls the existing slice-A
    ``verify_geometry_snapshot`` so that the emission is internally
    consistent.
    """
    blockers: list[MessageEntry] = []

    # --- Step 1: raw input type validation ---------------------------
    if not isinstance(geometry_id, str):
        blockers.append(
            build_message_entry(
                code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID,
                field_path=GEOMETRY_ADAPTER_DEFAULT_FIELD_PATH[
                    GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID
                ],
                message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                    GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID
                ],
                details={
                    "expected_type": "str",
                    "actual_type": (
                        type(geometry_id).__name__ if not isinstance(geometry_id, str) else "str"
                    ),
                },
            )
        )
    if not _is_geometry_catalog(catalog):
        blockers.append(
            build_message_entry(
                code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID,
                field_path=GEOMETRY_ADAPTER_DEFAULT_FIELD_PATH[
                    GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID
                ],
                message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                    GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID
                ],
                details={
                    "expected_type": "hexagent.geometry_catalogs.models.GeometryCatalog",
                    "actual_type": type(catalog).__name__,
                },
            )
        )

    if blockers:
        raise AdapterFailure(blockers)  # noqa: B904

    # --- Step 2: catalog object validation (already isinstance) ----
    # --- Step 3: catalog identity validation ------------------------
    identity_fields = ("catalog_id", "catalog_version", "authority", "source_revision")
    for field_name in identity_fields:
        value = getattr(catalog, field_name, None)
        if not isinstance(value, str) or not value:
            blockers.append(
                build_message_entry(
                    code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID,
                    field_path=f"catalog.{field_name}",
                    message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                        GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID
                    ],
                    details={
                        "missing_field": field_name,
                    },
                )
            )

    # --- Step 4: catalog content-hash verification ------------------
    if not blockers:
        try:
            recomputed_catalog_hash = compute_catalog_content_hash(catalog)
        except Exception as exc:
            blockers.append(
                build_message_entry(
                    code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID,
                    field_path="catalog",
                    message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                        GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID
                    ],
                    details={
                        "diagnostic": type(exc).__name__,
                        "trace": "compute_catalog_content_hash",
                    },
                )
            )
            recomputed_catalog_hash = None
        if recomputed_catalog_hash is not None and recomputed_catalog_hash != catalog.content_hash:
            blockers.append(
                build_message_entry(
                    code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_CATALOG_HASH_MISMATCH,
                    field_path=GEOMETRY_ADAPTER_DEFAULT_FIELD_PATH[
                        GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_CATALOG_HASH_MISMATCH
                    ],
                    message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                        GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_CATALOG_HASH_MISMATCH
                    ],
                    details={
                        "expected_hash": recomputed_catalog_hash,
                        "actual_hash": catalog.content_hash,
                    },
                    evidence_refs=(),
                )
            )

    # --- Step 5: explicit geometry_id validation --------------------
    if not geometry_id or not isinstance(geometry_id, str):
        blockers.append(
            build_message_entry(
                code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID,
                field_path="geometry_id",
                message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                    GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID
                ],
                details={"reason": "geometry_id must be a non-empty string"},
            )
        )

    # --- Steps 6 + 7: duplicate detection + exact ID lookup ---------
    matching_records: list[GeometryRecord] = []
    if isinstance(catalog.records, tuple):
        # tuple from TASK-016 canonical order. iterate linearly to keep the
        # no-I/O discipline.
        records_iter: Iterable[GeometryRecord] = catalog.records
    else:
        records_iter = tuple(catalog.records)

    if not blocks_has_raw_type_or_upstream_invalid(blockers):
        for r in records_iter:
            if not isinstance(r, GeometryRecord):
                # Skip unrelated frozen shapes silently; the downstream
                # record extraction enforces the exact tube type. This
                # defensive branch exists so the adapter does not crash
                # if an upstream user injected a non-record into the
                # catalog before this adapter call.
                continue
            if getattr(r, "geometry_id", None) == geometry_id:
                matching_records.append(r)

    if not blockers:
        if not matching_records:
            blockers.append(
                build_message_entry(
                    code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_GEOMETRY_ID_NOT_FOUND,
                    field_path="geometry_id",
                    message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                        GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_GEOMETRY_ID_NOT_FOUND
                    ],
                    details={"geometry_id": geometry_id},
                )
            )
        elif len(matching_records) > 1:
            # duplicates in a TASK-016 catalog should not occur — the
            # upstream loader blocks them — but we defensively preserve
            # the closed-set invariant.
            blockers.append(
                build_message_entry(
                    code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_GEOMETRY_ID_DUPLICATE,
                    field_path="geometry_id",
                    message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                        GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_GEOMETRY_ID_DUPLICATE
                    ],
                    details={"geometry_id": geometry_id, "count": len(matching_records)},
                )
            )
        else:
            record = matching_records[0]

            # --- Step 8: tube-type check ----------------------------
            if not isinstance(record, TubeGeometryRecord):
                blockers.append(
                    build_message_entry(
                        code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_GEOMETRY_TYPE_NOT_TUBE,
                        field_path="geometry_id",
                        message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                            GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_GEOMETRY_TYPE_NOT_TUBE
                        ],
                        details={
                            "geometry_id": geometry_id,
                            "geometry_type": getattr(record, "geometry_type", "unknown"),
                        },
                    )
                )
            # --- Step 9: approval check ------------------------------
            if (
                "geometry_type" not in [b.code for b in blockers]
                and getattr(record, "approval_state", None) != APPROVAL_STATE_APPROVED
            ):
                blockers.append(
                    build_message_entry(
                        code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RECORD_NOT_APPROVED,
                        field_path="geometry_id",
                        message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                            GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RECORD_NOT_APPROVED
                        ],
                        details={
                            "geometry_id": geometry_id,
                            "approval_state": getattr(record, "approval_state", None),
                        },
                    )
                )

            # --- Step 10: record-hash verification -------------------
            if GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RECORD_NOT_APPROVED not in [
                b.code for b in blockers
            ] and GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_GEOMETRY_TYPE_NOT_TUBE not in [
                b.code for b in blockers
            ]:
                stored_hash = getattr(record, "record_hash", None)
                recomputed_hash = compute_record_hash(record)
                if stored_hash != recomputed_hash:
                    blockers.append(
                        build_message_entry(
                            code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RECORD_HASH_MISMATCH,
                            field_path="geometry_id",
                            message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                                GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RECORD_HASH_MISMATCH
                            ],
                            details={
                                "geometry_id": geometry_id,
                                "expected_hash": recomputed_hash,
                                "actual_hash": stored_hash,
                            },
                        )
                    )

            # --- Step 11: dimension validation -----------------------
            outer_text = inner_text = wall_text = ""
            try:
                outer_text = _coerce_dimension_string(
                    getattr(record, "outer_diameter_m", None),
                    field_name="outer_diameter_m",
                    geometry_id=geometry_id,
                    positive=True,
                )
                inner_text = _coerce_dimension_string(
                    getattr(record, "inner_diameter_m", None),
                    field_name="inner_diameter_m",
                    geometry_id=geometry_id,
                    positive=True,
                )
                wall_text = _coerce_dimension_string(
                    getattr(record, "wall_thickness_m", None),
                    field_name="wall_thickness_m",
                    geometry_id=geometry_id,
                    positive=True,
                )
            except CanonicalizationError as exc:
                blockers.append(
                    build_message_entry(
                        code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_PROJECTION_INVALID,
                        field_path="geometry_id",
                        message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                            GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_PROJECTION_INVALID
                        ],
                        details={
                            "geometry_id": geometry_id,
                            "diagnostic": str(exc),
                        },
                    )
                )
            else:
                # Algebraic consistency: inner < outer, and wall ==
                # (outer - inner) / 2 within GEOMETRY_DIMENSION_TOLERANCE_M.
                from decimal import Decimal, localcontext

                with localcontext() as ctx:
                    ctx.prec = DECIMAL_PRECISION
                    ctx.rounding = ROUND_HALF_EVEN
                    try:
                        od = Decimal(outer_text)
                        id_ = Decimal(inner_text)
                        wt = Decimal(wall_text)
                    except Exception:
                        blockers.append(
                            build_message_entry(
                                code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_PROJECTION_INVALID,
                                field_path="geometry_id",
                                message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                                    GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_PROJECTION_INVALID
                                ],
                                details={
                                    "geometry_id": geometry_id,
                                    "diagnostic": "decimal_parse_failed",
                                },
                            )
                        )
                    else:
                        if id_ >= od:
                            blockers.append(
                                build_message_entry(
                                    code="STL_TUBE_DIMENSION_INVALID",
                                    field_path="tube_geometry.inner_diameter_m",
                                    message_key="tube_inner_not_smaller_than_outer",
                                    details={
                                        "geometry_id": geometry_id,
                                        "outer_diameter_m": outer_text,
                                        "inner_diameter_m": inner_text,
                                    },
                                )
                            )
                        expected_wall = (od - id_) / Decimal(2)
                        if abs(wt - expected_wall) > Decimal(str(_GEOMETRY_DIMENSION_TOLERANCE_M)):
                            blockers.append(
                                build_message_entry(
                                    code="STL_TUBE_DIMENSION_INCONSISTENT",
                                    field_path="tube_geometry.wall_thickness_m",
                                    message_key="tube_wall_thickness_inconsistent",
                                    details={
                                        "geometry_id": geometry_id,
                                        "expected_wall_thickness_m": decimal_string(expected_wall),
                                        "actual_wall_thickness_m": wall_text,
                                    },
                                )
                            )

            # --- Step 12: source-binding validation -----------------
            binding = getattr(record, "source_binding", None)
            if not isinstance(binding, GeometrySourceBinding):
                blockers.append(
                    build_message_entry(
                        code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE,
                        field_path="geometry_id",
                        message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                            GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE
                        ],
                        details={"geometry_id": geometry_id, "reason": "missing_binding"},
                    )
                )
            else:
                missing = []
                for field_name in (
                    "source_id",
                    "source_type",
                    "source_revision",
                    "source_location",
                    "evidence_ref",
                    "approved_by",
                    "approved_at",
                ):
                    value = getattr(binding, field_name, None)
                    if not isinstance(value, str) or not value:
                        missing.append(field_name)
                if missing:
                    blockers.append(
                        build_message_entry(
                            code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE,
                            field_path="geometry_id",
                            message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                                GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_SOURCE_BINDING_INCOMPLETE
                            ],
                            details={"geometry_id": geometry_id, "missing_fields": missing},
                        )
                    )

    # --- Combine and order blockers per slice-A §11.3 --------------
    if blockers:
        ordered = sort_adapter_blockers(blockers)
        raise AdapterFailure(ordered)  # noqa: B904

    # Step 13: TASK-021 field projection (5 SourceBinding + 3 dimensions)
    record = matching_records[0]
    binding = record.source_binding
    source_binding_snapshot = _source_binding_to_snapshot(binding)

    # Project the three dimensions. We have already produced canonical
    # decimal strings under the slice-A Decimal context; reuse them.
    with_post_inline_dims = record  # alias for readability
    outer_text = _coerce_dimension_string(
        getattr(with_post_inline_dims, "outer_diameter_m", None),
        field_name="outer_diameter_m",
        geometry_id=geometry_id,
        positive=True,
    )
    inner_text = _coerce_dimension_string(
        getattr(with_post_inline_dims, "inner_diameter_m", None),
        field_name="inner_diameter_m",
        geometry_id=geometry_id,
        positive=True,
    )
    wall_text = _coerce_dimension_string(
        getattr(with_post_inline_dims, "wall_thickness_m", None),
        field_name="wall_thickness_m",
        geometry_id=geometry_id,
        positive=True,
    )

    # Step 14: snapshot_hash construction. Per TASK-021 §12.2:
    # snapshot_hash = SHA-256(canonical_json(all exact fields except snapshot_hash))
    # We construct the un-hashed dict, then exclude snapshot_hash before
    # hashing. The slice-A ``sha256_hex`` operates on canonical JSON.
    payload_for_hash: dict[str, Any] = {
        "geometry_id": geometry_id,
        "geometry_type": GEOMETRY_TYPE_TUBE,
        "revision": record.revision,
        "approval_state": APPROVAL_STATE_APPROVED,
        "outer_diameter_m": outer_text,
        "inner_diameter_m": inner_text,
        "wall_thickness_m": wall_text,
        "record_hash": getattr(record, "record_hash", None),
        "source_binding": _source_binding_to_mapping(source_binding_snapshot),
    }
    snapshot_hash_value = sha256_hex(payload_for_hash)

    # Step 15: output construction.
    snapshot = ApprovedTubeGeometrySnapshot(
        geometry_id=geometry_id,
        geometry_type=GEOMETRY_TYPE_TUBE,
        revision=record.revision,
        approval_state=APPROVAL_STATE_APPROVED,
        outer_diameter_m=outer_text,
        inner_diameter_m=inner_text,
        wall_thickness_m=wall_text,
        record_hash=getattr(record, "record_hash", None) or "",
        snapshot_hash=snapshot_hash_value,
        source_binding=source_binding_snapshot,
    )

    # Terminal defensive check via the existing slice-A hook.
    try:
        verify_geometry_snapshot(snapshot)
    except Exception as exc:
        # Wrap any unexpected failure as an adapter projection invalid
        # blocker so the surface is exactly the blocker set.
        detail_list = getattr(exc, "args", ())
        msg = "; ".join(str(d) for d in detail_list)
        raise AdapterFailure(  # noqa: B904
            sort_adapter_blockers(
                [
                    build_message_entry(
                        code=GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_PROJECTION_INVALID,
                        field_path="geometry_id",
                        message_key=GEOMETRY_ADAPTER_DEFAULT_MESSAGE_KEY[
                            GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_PROJECTION_INVALID
                        ],
                        details={
                            "geometry_id": geometry_id,
                            "diagnostic": "verify_geometry_snapshot_failed",
                            "message": msg,
                        },
                    )
                ]
            )
        ) from exc

    return snapshot


def _source_binding_to_mapping(snapshot: SourceBindingSnapshot) -> dict[str, Any]:
    """Convert a ``SourceBindingSnapshot`` to a JSON-compatible mapping.

    The slice-A ``verify_geometry_snapshot`` reads ``to_primitive(
    snapshot.source_binding).values()`` and checks every value is a
    non-empty string; we mirror the same shape here so the
    ``sha256_hex(payload)`` computation matches the slice-A convention.
    """
    return {
        "source_id": snapshot.source_id,
        "source_type": snapshot.source_type,
        "source_revision": snapshot.source_revision,
        "source_location": snapshot.source_location,
        "evidence_ref": snapshot.evidence_ref,
        "approved_by": snapshot.approved_by,
        "approved_at": snapshot.approved_at,
    }


def blocks_has_raw_type_or_upstream_invalid(
    blockers: list[MessageEntry],
) -> bool:
    """Predicate helper kept for the explicit early-exit in build_...snapshot.

    Steps 6/7 only need to run when the early steps have not already
    blocked; this helper keeps that intent visible at the call site.
    """
    return any(
        b.code
        in (
            GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_RAW_TYPE_INVALID,
            GeometryAdapterBlockerCode.STL_GEOMETRY_ADAPTER_UPSTREAM_OBJECT_INVALID,
        )
        for b in blockers
    )

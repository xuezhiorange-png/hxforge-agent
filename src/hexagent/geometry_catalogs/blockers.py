"""Structured validation blockers for the TASK-016 geometry catalog.

Implements the TASK-016 frozen design contract
(``docs/tasks/TASK-016-approved-geometry-catalog.md``,
Frozen Contract Authority SHA
``654a2708de808c9f1518f1a69eda92f95a4d37c5``) Section 9 (Validation
blockers).

Eleven deterministic ``error_code`` strings cover the full §9 blocker table.
Each blocker is exposed as:

* a constant string (the canonical ``error_code``),
* a :class:`GeometryCatalogBlockerError` exception class with the matching
  ``error_code``,
* and a small factory function that constructs the exception with the
  structured ``context`` dict required by Section 9.

Blockers are deterministic: identical input payloads produce identical
``error_code`` + ``context``. Invalid catalog states are NEVER converted to
warnings (Section 9 final paragraph).
"""

from __future__ import annotations

from typing import Any, Final

# --- Blocker codes (Section 9 table) ----------------------------------------

BLOCKER_GEOMETRY_CATALOG_MISSING: Final[str] = "geometry_catalog_missing"
BLOCKER_GEOMETRY_RECORD_MISSING_ID: Final[str] = "geometry_record_missing_id"
BLOCKER_GEOMETRY_RECORD_DUPLICATE_ID: Final[str] = "geometry_record_duplicate_id"
BLOCKER_GEOMETRY_RECORD_UNAPPROVED: Final[str] = "geometry_record_unapproved"
BLOCKER_GEOMETRY_TYPE_UNSUPPORTED: Final[str] = "geometry_type_unsupported"
BLOCKER_GEOMETRY_DIMENSION_NON_POSITIVE: Final[str] = "geometry_dimension_non_positive"
BLOCKER_GEOMETRY_DIMENSION_INCONSISTENT: Final[str] = "geometry_dimension_inconsistent"
BLOCKER_GEOMETRY_SOURCE_MISSING: Final[str] = "geometry_source_missing"
BLOCKER_GEOMETRY_HASH_MISMATCH: Final[str] = "geometry_hash_mismatch"
BLOCKER_GEOMETRY_REFERENCE_MISSING: Final[str] = "geometry_reference_missing"
BLOCKER_GEOMETRY_REFERENCE_UNAPPROVED: Final[str] = "geometry_reference_unapproved"

VALID_BLOCKER_CODES: Final[frozenset[str]] = frozenset(
    {
        BLOCKER_GEOMETRY_CATALOG_MISSING,
        BLOCKER_GEOMETRY_RECORD_MISSING_ID,
        BLOCKER_GEOMETRY_RECORD_DUPLICATE_ID,
        BLOCKER_GEOMETRY_RECORD_UNAPPROVED,
        BLOCKER_GEOMETRY_TYPE_UNSUPPORTED,
        BLOCKER_GEOMETRY_DIMENSION_NON_POSITIVE,
        BLOCKER_GEOMETRY_DIMENSION_INCONSISTENT,
        BLOCKER_GEOMETRY_SOURCE_MISSING,
        BLOCKER_GEOMETRY_HASH_MISMATCH,
        BLOCKER_GEOMETRY_REFERENCE_MISSING,
        BLOCKER_GEOMETRY_REFERENCE_UNAPPROVED,
    }
)


# --- Exception hierarchy -----------------------------------------------------


class GeometryCatalogError(Exception):
    """Base class for TASK-016 geometry catalog errors."""


class GeometryCatalogBlockerError(GeometryCatalogError):
    """Raised for any of the eleven §9 structured blockers.

    ``error_code`` is one of the eleven ``BLOCKER_*`` constants. ``context``
    is a structured dict carrying the offending record identifiers and the
    field/value that triggered the blocker.
    """

    error_code: str

    def __init__(self, error_code: str, context: dict[str, Any]) -> None:
        if error_code not in VALID_BLOCKER_CODES:
            raise ValueError(f"Unknown TASK-016 blocker error_code: {error_code!r}")
        self.error_code = error_code
        self.context = dict(context)
        super().__init__(
            f"{error_code}: " + ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        )


# --- Blocker factories (Section 9) -------------------------------------------


def geometry_catalog_missing(context: dict[str, Any] | None = None) -> GeometryCatalogBlockerError:
    """Section 9: Catalog payload is absent."""
    return GeometryCatalogBlockerError(
        BLOCKER_GEOMETRY_CATALOG_MISSING,
        dict(context or {}),
    )


def geometry_record_missing_id(*, index: int, **extra: Any) -> GeometryCatalogBlockerError:
    """Section 9: Record has no stable ``geometry_id``."""
    ctx = {"index": int(index)}
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_RECORD_MISSING_ID, ctx)


def geometry_record_duplicate_id(*, geometry_id: str, **extra: Any) -> GeometryCatalogBlockerError:
    """Section 9: Duplicate ``geometry_id`` after normalization."""
    ctx = {"geometry_id": str(geometry_id)}
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_RECORD_DUPLICATE_ID, ctx)


def geometry_record_unapproved(
    *, geometry_id: str, approval_state: str, **extra: Any
) -> GeometryCatalogBlockerError:
    """Section 9: Record is not explicitly approved."""
    ctx = {"geometry_id": str(geometry_id), "approval_state": str(approval_state)}
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_RECORD_UNAPPROVED, ctx)


def geometry_type_unsupported(
    *, geometry_id: str | None, geometry_type: Any, **extra: Any
) -> GeometryCatalogBlockerError:
    """Section 9: Record type is not tube, pipe, or hairpin."""
    ctx: dict[str, Any] = {"geometry_type": geometry_type}
    if geometry_id is not None:
        ctx["geometry_id"] = str(geometry_id)
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_TYPE_UNSUPPORTED, ctx)


def geometry_dimension_non_positive(
    *,
    geometry_id: str,
    field_name: str,
    value: float,
    **extra: Any,
) -> GeometryCatalogBlockerError:
    """Section 9: Diameter, length, area, or count is invalid (≤ 0)."""
    ctx = {
        "geometry_id": str(geometry_id),
        "field_name": str(field_name),
        "value": float(value),
    }
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_DIMENSION_NON_POSITIVE, ctx)


def geometry_dimension_inconsistent(
    *,
    geometry_id: str,
    field_name: str,
    expected: float,
    actual: float,
    tolerance: float,
    **extra: Any,
) -> GeometryCatalogBlockerError:
    """Section 9: Derived dimensions do not match canonical fields."""
    ctx = {
        "geometry_id": str(geometry_id),
        "field_name": str(field_name),
        "expected": float(expected),
        "actual": float(actual),
        "tolerance": float(tolerance),
    }
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_DIMENSION_INCONSISTENT, ctx)


def geometry_source_missing(
    *, geometry_id: str | None = None, **extra: Any
) -> GeometryCatalogBlockerError:
    """Section 9: Source binding is absent or incomplete."""
    ctx: dict[str, Any] = {}
    if geometry_id is not None:
        ctx["geometry_id"] = str(geometry_id)
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_SOURCE_MISSING, ctx)


def geometry_hash_mismatch(
    *,
    geometry_id: str,
    expected: str,
    actual: str,
    **extra: Any,
) -> GeometryCatalogBlockerError:
    """Section 9: Stored hash differs from canonical hash."""
    ctx = {
        "geometry_id": str(geometry_id),
        "expected": str(expected),
        "actual": str(actual),
    }
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_HASH_MISMATCH, ctx)


def geometry_reference_missing(
    *, hairpin_id: str, reference_field: str, missing_id: str, **extra: Any
) -> GeometryCatalogBlockerError:
    """Section 9: Hairpin references a missing tube or pipe record."""
    ctx = {
        "hairpin_id": str(hairpin_id),
        "reference_field": str(reference_field),
        "missing_id": str(missing_id),
    }
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_REFERENCE_MISSING, ctx)


def geometry_reference_unapproved(
    *,
    hairpin_id: str,
    reference_field: str,
    referenced_id: str,
    referenced_state: str,
    **extra: Any,
) -> GeometryCatalogBlockerError:
    """Section 9: Hairpin references a non-approved record."""
    ctx = {
        "hairpin_id": str(hairpin_id),
        "reference_field": str(reference_field),
        "referenced_id": str(referenced_id),
        "referenced_state": str(referenced_state),
    }
    ctx.update(extra)
    return GeometryCatalogBlockerError(BLOCKER_GEOMETRY_REFERENCE_UNAPPROVED, ctx)

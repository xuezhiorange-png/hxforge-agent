"""TASK-010 canonical scalar/quantity serialization for API request payloads.

Provides deterministic string representations of Decimal scalars and
recursive canonicalization of arbitrary API request objects.  All
numerical values are serialized as strings so that JSON round-trips
are lossless and content hashes are stable.
"""

from __future__ import annotations

import math
import unicodedata
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from hexagent.api.models import (
    CatalogSnapshotReference,
    DoublePipeGeometrySpec,
    RatingApiRequest,
    ResolvedProviderAuthority,
    SizingApiRequest,
    SolverParamsSpec,
    ValidationApiRequest,
)
from hexagent.core.canonical import sha256_digest
from hexagent.core.units import QuantityKind, convert_value, si_unit
from hexagent.domain.quantities import Quantity
from hexagent.optimization.models import CompleteDoublePipeCatalogSnapshot

# ---------------------------------------------------------------------------
# canonical_decimal_string
# ---------------------------------------------------------------------------


def canonical_decimal_string(value: Decimal) -> str:
    """Normalize Decimal to canonical string with 15 significant digits.

    Algorithm (Frozen Contract §8.1):
    1. Reject non-finite (NaN, Inf, -Inf).
    2. Reject signed negative zero (Decimal("-0"), float("-0.0")).
    3. Zero → "0".
    4. Determine adjusted exponent.
    5. Quantize to 15 significant digits via ROUND_HALF_EVEN.
    6. If rounding produces negative zero → reject.
    7. If -10 <= rounded.adjusted() <= 10: fixed notation,
       strip trailing zeros and trailing dot.
    8. Otherwise: scientific notation.
       Format: mantissa "E" sign exponent (e.g. "E+15", "E-30").
       No leading zeros in exponent.  Uppercase 'E'.

    Test vectors:
      0 → "0"
      -0 → REJECTED
      1 → "1"
      1.0 → "1"
      1.5000 → "1.5"
      1.234567890123445 → "1.23456789012344"
      1.234567890123455 → "1.23456789012346"
      999999999999999.5 → "1E+15"
      1E-30 → "1E-30"
      1E+30 → "1E+30"
      0.00000000001 → "1E-11"
      0.000000000001 → "1E-12"
      99999999999 → "99999999999"
      100000000000 → "1E+11"
      1E-7 → "0.0000001"
      1E-10 → "0.0000000001"
      1E-11 → "1E-11"
      1E+10 → "10000000000"
      1E+11 → "1E+11"
    """
    if not isinstance(value, Decimal):
        raise TypeError(f"Expected Decimal, got {type(value).__name__}")
    if not value.is_finite():
        raise ValueError("non-finite decimal")
    if value.is_zero() and value.is_signed():
        raise ValueError("negative zero")
    if value.is_zero():
        return "0"

    precision = 15
    adjusted = value.adjusted()
    quantum = Decimal(1).scaleb(adjusted - precision + 1)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)

    if rounded.is_zero() and rounded.is_signed():
        raise ValueError("rounding produced negative zero")

    rounded_adjusted = rounded.adjusted()
    if -10 <= rounded_adjusted <= 10:
        result = format(rounded, "f")
        if "." in result:
            result = result.rstrip("0").rstrip(".")
        return result

    # Scientific notation: mantissa "E" sign exponent
    normalized = rounded.normalize()
    mantissa_str = format(normalized, "E")
    parts = mantissa_str.split("E")
    mantissa = parts[0]
    exp = int(parts[1])
    return f"{mantissa}E{exp:+d}"


# ---------------------------------------------------------------------------
# canonical_quantity_payload — exact Decimal conversion
# ---------------------------------------------------------------------------

# Cache for Decimal conversion factors
_decimal_factor_cache: dict[tuple[str, str, QuantityKind], tuple[Decimal, Decimal]] = {}


def _get_decimal_conversion(
    from_unit: str, to_unit: str, kind: QuantityKind
) -> tuple[Decimal, Decimal]:
    """Get exact Decimal (factor, offset) for unit conversion.

    Uses pint to compute the factor and offset, captured as exact Decimals.
    For multiplicative conversions: result = value * factor + 0
    For offset conversions: result = value * factor + offset
    """
    cache_key = (from_unit, to_unit, kind)
    if cache_key in _decimal_factor_cache:
        return _decimal_factor_cache[cache_key]

    # Use the project's convert_value to get the conversion.
    # For a unit conversion: result = value * factor + offset
    # We extract factor and offset by converting two reference values.
    val_0 = convert_value(0.0, from_unit, to_unit, kind)
    val_1 = convert_value(1.0, from_unit, to_unit, kind)

    # factor = val_1 - val_0 (the multiplicative part)
    # offset = val_0 (the additive part)
    factor = Decimal(repr(val_1)) - Decimal(repr(val_0))
    offset = Decimal(repr(val_0))

    result = (factor, offset)
    _decimal_factor_cache[cache_key] = result
    return result


def canonical_quantity_payload(q: Quantity) -> dict[str, str]:
    """Convert a Quantity to canonical API dict representation.

    Frozen Contract §8.1 output schema:
        {"value": "<canonical SI decimal string>", "unit": "<SI unit symbol>"}

    Conversion uses exact Decimal arithmetic:
    1. Input value → Decimal(repr(value)) (exact binary-to-decimal)
    2. Get Decimal conversion factor from project infrastructure
    3. Apply: Decimal(repr(value)) * factor + offset
    4. Apply canonical_decimal_string()
    5. Output unit as SI symbol

    NEVER calls q.to_si() or q.si_value.
    NEVER uses binary float as intermediate canonical value.
    """
    kind = q.kind
    if kind is None:
        raise ValueError(f"Quantity {q!r} has no kind")
    si_symbol = si_unit(kind)
    from_unit = q.unit

    if from_unit == si_symbol:
        # Already in SI — just canonicalize the value
        decimal_value = Decimal(repr(q.value))
    else:
        factor, offset = _get_decimal_conversion(from_unit, si_symbol, kind)
        decimal_value = Decimal(repr(q.value)) * factor + offset

    return {
        "value": canonical_decimal_string(decimal_value),
        "unit": si_symbol,
    }


# ---------------------------------------------------------------------------
# Unified recursive canonicalizer
# ---------------------------------------------------------------------------


def _is_quantity(obj: Any) -> bool:
    """Return ``True`` if *obj* is a Quantity-like object."""
    return isinstance(obj, Quantity) or (
        hasattr(obj, "value")
        and hasattr(obj, "unit")
        and hasattr(obj, "kind")
        and hasattr(obj, "to_si")
    )


def _canonicalize(obj: Any, *, walk_pydantic: bool = False) -> Any:
    """Unified recursive canonicalizer for deterministic API serialization.

    Handles all scalar types, Quantity, dict, list/tuple, and optionally
    Pydantic models (walked by field name, retaining None values).

    Canonicalization rules:

    * ``Decimal`` / ``float`` → string via :func:`canonical_decimal_string`
    * ``int`` → JSON number (pass-through)
    * ``bool`` → JSON boolean (pass-through; checked **before** ``int``
      because ``bool`` is a subclass of ``int``)
    * ``None`` → JSON null (pass-through)
    * ``Enum`` → canonicalized ``.value``
    * ``UUID`` → string
    * ``str`` → Unicode NFC normalized
    * ``Quantity`` (or duck-typed equivalent) → canonical dict via
      :func:`canonical_quantity_payload`
    * ``dict`` → sorted keys, recursively canonicalized values
    * ``tuple`` / ``list`` → JSON array, recursively canonicalized elements
    * Pydantic model (when ``walk_pydantic=True``) → dict walked by field
      name (not alias), retaining None values, recursively canonicalized

    Parameters
    ----------
    obj:
        The object to canonicalize.
    walk_pydantic:
        If ``True``, walk Pydantic ``BaseModel`` instances by field name.
        If ``False``, encountering a Pydantic model raises ``TypeError``.
    """
    # Decimal → canonical string
    if isinstance(obj, Decimal):
        return canonical_decimal_string(obj)

    # float → canonical string (via Decimal for exact rounding)
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"Non-finite float {obj!r} cannot be canonicalized")
        return canonical_decimal_string(Decimal(repr(obj)))

    # bool — MUST be checked before int (bool is a subclass of int)
    if isinstance(obj, bool):
        return obj

    # int → pass-through (JSON number)
    if isinstance(obj, int):
        return obj

    # None → null
    if obj is None:
        return None

    # Enum → canonicalize the .value
    if isinstance(obj, Enum):
        return _canonicalize(obj.value, walk_pydantic=walk_pydantic)

    # UUID → string
    if isinstance(obj, UUID):
        return str(obj)

    # str → NFC normalize
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)

    # Quantity → canonical dict
    if _is_quantity(obj):
        return canonical_quantity_payload(obj)

    # dict → sorted keys, recursively canonicalized values
    if isinstance(obj, dict):
        return {
            k: _canonicalize(v, walk_pydantic=walk_pydantic)
            for k, v in sorted(obj.items(), key=lambda kv: kv[0])
        }

    # tuple / list → array, recursively canonicalized elements
    if isinstance(obj, (tuple, list)):
        return [_canonicalize(item, walk_pydantic=walk_pydantic) for item in obj]

    # Pydantic BaseModel → walk fields by name (when enabled)
    if walk_pydantic and hasattr(obj, "model_dump") and hasattr(type(obj), "model_fields"):
        result: dict[str, Any] = {}
        for field_name in type(obj).model_fields:
            if hasattr(obj, field_name):
                val = getattr(obj, field_name)
                result[field_name] = _canonicalize(val, walk_pydantic=True)
        return result

    raise TypeError(f"Cannot canonicalize object of type {type(obj).__name__}")


def canonicalize_api_payload(obj: Any) -> Any:
    """Recursively canonicalize *obj* for deterministic API serialization.

    This is the public entry point for general payload canonicalization.
    It NFC-normalizes strings, handles all scalar types, Quantity objects,
    dicts (sorted keys), and lists/tuples.

    For Pydantic model walking, use ``_canonicalize(obj, walk_pydantic=True)``.
    """
    return _canonicalize(obj, walk_pydantic=False)


# ---------------------------------------------------------------------------
# Unicode NFC helper (standalone, for individual string fields)
# ---------------------------------------------------------------------------


def _canonicalize_string(value: str) -> str:
    """Apply Unicode NFC normalization to a string."""
    return unicodedata.normalize("NFC", value)


# ---------------------------------------------------------------------------
# compute_api_request_digest
# ---------------------------------------------------------------------------


def compute_api_request_digest(obj: Any) -> str:
    """Return a SHA-256 content hash of *obj* after canonicalization.

    ``obj`` is first canonicalized via :func:`canonicalize_api_payload`,
    then serialized to canonical JSON and hashed with
    :func:`~hexagent.core.canonical.sha256_digest`.

    The return value is always ``"sha256:<64-char lowercase hex>"``.
    """
    canonical = canonicalize_api_payload(obj)
    return sha256_digest(canonical)


# ---------------------------------------------------------------------------
# Canonical builder helpers
# ---------------------------------------------------------------------------


def _effective_solver_params(spec: SolverParamsSpec | None) -> SolverParamsSpec:
    """Expand None to default SolverParamsSpec."""
    if spec is None:
        return SolverParamsSpec()
    return spec


def _canonical_provider_identity(
    resolved: ResolvedProviderAuthority,
) -> dict[str, Any]:
    """Build canonical provider identity dict from ResolvedProviderAuthority."""
    identity = resolved.identity
    return {
        "name": _canonicalize_string(str(identity.name)),
        "version": _canonicalize_string(str(identity.version)),
        "git_revision": _canonicalize_string(str(identity.git_revision)),
        "reference_state_policy": _canonicalize_string(str(identity.reference_state_policy)),
        "configuration_fingerprint": _canonicalize_string(str(identity.configuration_fingerprint)),
        "cache_policy_version": _canonicalize_string(str(identity.cache_policy_version)),
        "provider_ref": _canonicalize_string(str(resolved.provider_ref)),
        "identity_digest": _canonicalize_string(str(resolved.identity_digest)),
    }


def _canonical_case_fields(
    case: ValidationApiRequest,
) -> dict[str, Any]:
    """Build canonical dict of all ValidationApiRequest fields."""
    result: dict[str, Any] = _canonicalize(case, walk_pydantic=True)
    return result


def _canonical_geometry_fields(spec: DoublePipeGeometrySpec) -> dict[str, Any]:
    """Build canonical dict of all DoublePipeGeometrySpec fields."""
    result: dict[str, Any] = _canonicalize(spec, walk_pydantic=True)
    return result


def _canonical_solver_fields(
    spec: SolverParamsSpec,
) -> dict[str, Any]:
    """Build canonical dict of all SolverParamsSpec fields."""
    result: dict[str, Any] = _canonicalize(spec, walk_pydantic=True)
    return result


# ---------------------------------------------------------------------------
# build_rating_canonical_request_context
# ---------------------------------------------------------------------------


def build_rating_canonical_request_context(
    request: RatingApiRequest,
    resolved_provider: ResolvedProviderAuthority,
) -> dict[str, Any]:
    """Build canonical request context for a rating API request.

    Contract:
    - Accept validated RatingApiRequest
    - Expand all defaults (solver_params=None → SolverParamsSpec())
    - Use field names, not aliases
    - Retain None
    - Unicode NFC on all strings
    - Recursively sort map keys
    - Use canonical_quantity_payload for Quantities
    - Bind resolved provider authority (full identity)
    - solver_params=None and solver_params=SolverParamsSpec() produce same context

    Returns a deterministic dict suitable for hashing via
    :func:`compute_api_request_digest`.
    """
    effective_solver = _effective_solver_params(request.solver_params)

    context: dict[str, Any] = {
        "api_schema_version": _canonicalize_string(request.api_schema_version),
        "case": _canonical_case_fields(request.case),
        "geometry": _canonical_geometry_fields(request.geometry),
        "solver": _canonical_solver_fields(effective_solver),
        "tube_in_hot": request.tube_in_hot,
        "flow_arrangement": _canonicalize_string(request.flow_arrangement),
        "tube_boundary_condition": _canonicalize_string(request.tube_boundary_condition),
        "annulus_boundary_condition": _canonicalize_string(request.annulus_boundary_condition),
        "provider": _canonical_provider_identity(resolved_provider),
    }

    result: dict[str, Any] = _canonicalize(context)
    return result


# ---------------------------------------------------------------------------
# build_sizing_canonical_request_context
# ---------------------------------------------------------------------------


def canonical_catalog_ref_sort_key(
    ref: CatalogSnapshotReference,
) -> tuple[str, str, str, str, str]:
    """Canonical 5-field sort key for catalog references.

    Used uniformly at all stages: DTO validation, registry resolution,
    SizingRequest.catalogs, SizingRequestIdentity, canonical snapshot,
    and request digest.

    Frozen Contract sort key:
        (catalog_id, catalog_version, catalog_content_hash,
         source_identity, schema_version)
    """
    return (
        ref.catalog_id,
        ref.catalog_version,
        ref.catalog_content_hash,
        ref.source_identity,
        ref.schema_version,
    )


def canonicalize_catalog_refs(
    refs: tuple[CatalogSnapshotReference, ...],
) -> tuple[CatalogSnapshotReference, ...]:
    """Sort and validate catalog references for canonical ordering.

    Sort key: (catalog_id, catalog_version, catalog_content_hash,
               source_identity, schema_version)

    Uniqueness rules:
    - Completely identical five-field ref → reject
    - Same four-field identity (catalog_id, catalog_version,
      source_identity, schema_version) but different content_hash → reject
    """
    sorted_refs = sorted(refs, key=canonical_catalog_ref_sort_key)

    # Check for complete duplicates and same-identity-different-hash
    seen_identity: dict[tuple[str, str, str, str], str] = {}
    prev_key: tuple[str, str, str, str, str] | None = None
    for ref in sorted_refs:
        key = canonical_catalog_ref_sort_key(ref)
        if prev_key is not None and key == prev_key:
            raise ValueError(f"Duplicate catalog ref: {key!r}")
        prev_key = key

        identity_key = (
            ref.catalog_id,
            ref.catalog_version,
            ref.source_identity,
            ref.schema_version,
        )
        if identity_key in seen_identity:
            if seen_identity[identity_key] != ref.catalog_content_hash:
                raise ValueError(
                    f"Same catalog identity {identity_key!r} with different "
                    f"content hash: {seen_identity[identity_key]!r} vs "
                    f"{ref.catalog_content_hash!r}"
                )
        else:
            seen_identity[identity_key] = ref.catalog_content_hash

    return tuple(sorted_refs)


def _canonical_catalog_ref(ref: CatalogSnapshotReference) -> dict[str, Any]:
    """Build canonical dict from a CatalogSnapshotReference."""
    return {
        "catalog_id": _canonicalize_string(ref.catalog_id),
        "catalog_version": _canonicalize_string(ref.catalog_version),
        "catalog_content_hash": _canonicalize_string(ref.catalog_content_hash),
        "source_identity": _canonicalize_string(ref.source_identity),
        "schema_version": _canonicalize_string(ref.schema_version),
    }


def _canonical_catalog_snapshot(
    snapshot: CompleteDoublePipeCatalogSnapshot,
) -> dict[str, Any]:
    """Build canonical dict binding catalog identity + content hash."""
    return {
        "catalog_id": _canonicalize_string(snapshot.catalog_id),
        "catalog_version": _canonicalize_string(snapshot.catalog_version),
        "catalog_content_hash": _canonicalize_string(snapshot.catalog_content_hash),
        "source_identity": _canonicalize_string(snapshot.source_identity),
        "schema_version": _canonicalize_string(snapshot.schema_version),
    }


def build_sizing_canonical_request_context(
    request: SizingApiRequest,
    resolved_provider: ResolvedProviderAuthority,
    resolved_catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...],
) -> dict[str, Any]:
    """Build canonical request context for a sizing API request.

    Contract:
    - Same rules as rating
    - Bind expected provider identity AND actual resolved provider identity
    - Bind catalog refs (canonical order) + content hashes
    - Bind effective solver params
    - Include all sizing-specific fields

    Returns a deterministic dict suitable for hashing via
    :func:`compute_api_request_digest`.
    """
    from hexagent.optimization.catalog import catalog_identity_key

    effective_solver = _effective_solver_params(request.solver_params)

    # Sort catalog refs using the canonical 5-field sort key
    sorted_catalogs = sorted(resolved_catalogs, key=catalog_identity_key)

    # Build canonical catalog references with content hashes (sorted)
    canonical_catalogs = [_canonical_catalog_snapshot(cat) for cat in sorted_catalogs]

    # Build canonical catalog refs from request (sorted by same key)
    sorted_refs = sorted(request.catalog_refs, key=canonical_catalog_ref_sort_key)
    canonical_refs = [_canonical_catalog_ref(ref) for ref in sorted_refs]

    context: dict[str, Any] = {
        "api_schema_version": _canonicalize_string(request.api_schema_version),
        "case": _canonical_case_fields(request.case),
        "tube_in_hot": request.tube_in_hot,
        "flow_arrangement": _canonicalize_string(request.flow_arrangement),
        "tube_boundary_condition": _canonicalize_string(request.tube_boundary_condition),
        "annulus_boundary_condition": _canonicalize_string(request.annulus_boundary_condition),
        "solver": _canonical_solver_fields(effective_solver),
        "catalog_refs": canonical_refs,
        "resolved_catalogs": canonical_catalogs,
        "minimum_effective_length": (
            _canonicalize(request.minimum_effective_length, walk_pydantic=True)
            if request.minimum_effective_length is not None
            else None
        ),
        "maximum_effective_length": (
            _canonicalize(request.maximum_effective_length, walk_pydantic=True)
            if request.maximum_effective_length is not None
            else None
        ),
        "request_raw_combination_cap": request.request_raw_combination_cap,
        "duty_absolute_tolerance": _canonicalize(
            request.duty_absolute_tolerance, walk_pydantic=True
        ),
        "duty_relative_tolerance": _canonicalize(
            request.duty_relative_tolerance, walk_pydantic=True
        ),
        "optimization_objective": _canonicalize_string(
            request.optimization_objective.value
            if hasattr(request.optimization_objective, "value")
            else str(request.optimization_objective)
        ),
        "requested_top_n": request.requested_top_n,
        "expected_provider_identity": {
            "name": _canonicalize_string(request.expected_provider_identity.name),
            "version": _canonicalize_string(request.expected_provider_identity.version),
            "git_revision": _canonicalize_string(request.expected_provider_identity.git_revision),
            "reference_state_policy": _canonicalize_string(
                request.expected_provider_identity.reference_state_policy
            ),
            "configuration_fingerprint": (
                _canonicalize_string(request.expected_provider_identity.configuration_fingerprint)
                if request.expected_provider_identity.configuration_fingerprint is not None
                else None
            ),
            "cache_policy_version": (
                _canonicalize_string(request.expected_provider_identity.cache_policy_version)
                if request.expected_provider_identity.cache_policy_version is not None
                else None
            ),
        },
        "resolved_provider": _canonical_provider_identity(resolved_provider),
        "design_case_revision_id": (
            str(request.design_case_revision_id)
            if request.design_case_revision_id is not None
            else None
        ),
        "calculation_run_id": (
            str(request.calculation_run_id) if request.calculation_run_id is not None else None
        ),
        "rating_software_version": _canonicalize_string(request.rating_software_version),
        "execution_context_policy_version": _canonicalize_string(
            request.execution_context_policy_version
        ),
    }

    result: dict[str, Any] = _canonicalize(context)
    return result


__all__ = [
    "build_rating_canonical_request_context",
    "build_sizing_canonical_request_context",
    "canonical_decimal_string",
    "canonical_quantity_payload",
    "canonicalize_api_payload",
    "compute_api_request_digest",
]

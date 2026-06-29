"""TASK-010 canonical scalar/quantity serialization for API request payloads.

Provides deterministic string representations of Decimal scalars and
recursive canonicalization of arbitrary API request objects.  All
numerical values are serialized as strings so that JSON round-trips
are lossless and content hashes are stable.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import Enum
from fractions import Fraction
from types import MappingProxyType
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
from hexagent.core.units import (
    UNIT_RULES,
    QuantityKind,
    normalize_unit,
)
from hexagent.domain.quantities import Quantity
from hexagent.optimization.models import CompleteDoublePipeCatalogSnapshot

# ---------------------------------------------------------------------------
# canonical_decimal_string
# ---------------------------------------------------------------------------

_CANONICAL_DECIMAL_CONTEXT = Context(prec=80, rounding=ROUND_HALF_EVEN)


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

    with localcontext(_CANONICAL_DECIMAL_CONTEXT):
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

        normalized = rounded.normalize()
        mantissa_str = format(normalized, "E")
        parts = mantissa_str.split("E")
        mantissa = parts[0]
        exp = int(parts[1])
        return f"{mantissa}E{exp:+d}"


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Exact unit conversion registry — immutable, auditable, zero runtime fallback
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExactUnitConversion:
    """Immutable specification for converting a unit to its SI equivalent.

    Conversion formula: si_value = input_value * scale + offset
    Both scale and offset are exact Fraction values.
    """

    si_unit: str
    scale: Fraction
    offset: Fraction = Fraction(0)


# Btu definition: pint uses 1055.056 J exactly (= 131882/125)
_BTU_J = Fraction(131882, 125)
_IN_M = Fraction(127, 5000)  # 1 inch = 0.0254 m exactly
_FT_M = Fraction(381, 1250)  # 1 foot = 0.3048 m exactly
_LB_KG = Fraction(45359237, 100000000)  # 1 lb = 0.45359237 kg (NIST)
_GAL_M3 = Fraction(231, 1) * (_IN_M**3)  # 1 US gallon = 231 in^3
_L_M3 = Fraction(1, 1000)  # 1 litre = 0.001 m^3
_ATM_PA = Fraction(101325)  # 1 atm = 101325 Pa (exact)

# Fahrenheit absolute: K = °F × 5/9 + 45967/180
_DEGF_OFFSET_K = Fraction(45967, 180)

# Compound unit conversion factors (precomputed from exact definitions)
# 1 hour·ft²·°F/Btu = (3600 × ft² × 5/9) / Btu_W m²·K/W
_FOULING_IMPERIAL_TO_SI = Fraction(3600) * (_FT_M**2) * Fraction(5, 9) / _BTU_J
# 1 Btu/lb = Btu_J / lb_kg  J/kg
_BTU_LB_J_KG = _BTU_J / _LB_KG

_RAW_EXACT_UNIT_CONVERSIONS: dict[QuantityKind, dict[str, ExactUnitConversion]] = {
    QuantityKind.MASS_FLOW: {
        "kg/s": ExactUnitConversion("kg/s", Fraction(1)),
        "kg/h": ExactUnitConversion("kg/s", Fraction(1, 3600)),
        "g/s": ExactUnitConversion("kg/s", Fraction(1, 1000)),
        "g/min": ExactUnitConversion("kg/s", Fraction(1, 60000)),
        "lb/s": ExactUnitConversion("kg/s", _LB_KG),
        "lb/h": ExactUnitConversion("kg/s", _LB_KG / 3600),
    },
    QuantityKind.VOLUME_FLOW: {
        "m^3/s": ExactUnitConversion("m^3/s", Fraction(1)),
        "m^3/h": ExactUnitConversion("m^3/s", Fraction(1, 3600)),
        "L/s": ExactUnitConversion("m^3/s", _L_M3),
        "L/min": ExactUnitConversion("m^3/s", _L_M3 / 60),
        "L/h": ExactUnitConversion("m^3/s", _L_M3 / 3600),
        "ft^3/min": ExactUnitConversion("m^3/s", _FT_M**3 / 60),
        "gallon/minute": ExactUnitConversion("m^3/s", _GAL_M3 / 60),
    },
    QuantityKind.ABSOLUTE_TEMPERATURE: {
        "K": ExactUnitConversion("K", Fraction(1), Fraction(0)),
        "degC": ExactUnitConversion("K", Fraction(1), Fraction(27315, 100)),
        "degF": ExactUnitConversion("K", Fraction(5, 9), _DEGF_OFFSET_K),
        "degR": ExactUnitConversion("K", Fraction(5, 9), Fraction(0)),
    },
    QuantityKind.TEMPERATURE_DIFFERENCE: {
        "K": ExactUnitConversion("K", Fraction(1)),
        "delta_degC": ExactUnitConversion("K", Fraction(1)),
        "delta_degF": ExactUnitConversion("K", Fraction(5, 9)),
        "delta_degR": ExactUnitConversion("K", Fraction(5, 9)),
    },
    QuantityKind.ABSOLUTE_PRESSURE: {
        "Pa": ExactUnitConversion("Pa", Fraction(1)),
        "kPa": ExactUnitConversion("Pa", Fraction(1000)),
        "MPa": ExactUnitConversion("Pa", Fraction(1000000)),
        "bar": ExactUnitConversion("Pa", Fraction(100000)),
        "psi": ExactUnitConversion("Pa", _LB_KG * Fraction(980665, 100000) / (_IN_M**2)),
        "atm": ExactUnitConversion("Pa", _ATM_PA),
    },
    QuantityKind.PRESSURE_DIFFERENCE: {
        "Pa": ExactUnitConversion("Pa", Fraction(1)),
        "kPa": ExactUnitConversion("Pa", Fraction(1000)),
        "MPa": ExactUnitConversion("Pa", Fraction(1000000)),
        "bar": ExactUnitConversion("Pa", Fraction(100000)),
        "psi": ExactUnitConversion("Pa", _LB_KG * Fraction(980665, 100000) / (_IN_M**2)),
    },
    QuantityKind.POWER: {
        "W": ExactUnitConversion("W", Fraction(1)),
        "kW": ExactUnitConversion("W", Fraction(1000)),
        "MW": ExactUnitConversion("W", Fraction(1000000)),
        "Btu/hour": ExactUnitConversion("W", _BTU_J / 3600),
        "ton_refrigeration": ExactUnitConversion("W", 12000 * _BTU_J / 3600),
    },
    QuantityKind.AREA: {
        "m^2": ExactUnitConversion("m^2", Fraction(1)),
        "cm^2": ExactUnitConversion("m^2", Fraction(1, 10000)),
        "mm^2": ExactUnitConversion("m^2", Fraction(1, 1000000)),
        "ft^2": ExactUnitConversion("m^2", _FT_M**2),
        "in^2": ExactUnitConversion("m^2", _IN_M**2),
    },
    QuantityKind.LENGTH: {
        "m": ExactUnitConversion("m", Fraction(1)),
        "cm": ExactUnitConversion("m", Fraction(1, 100)),
        "mm": ExactUnitConversion("m", Fraction(1, 1000)),
        "um": ExactUnitConversion("m", Fraction(1, 1000000)),
        "ft": ExactUnitConversion("m", _FT_M),
        "in": ExactUnitConversion("m", _IN_M),
    },
    QuantityKind.VELOCITY: {
        "m/s": ExactUnitConversion("m/s", Fraction(1)),
        "m/min": ExactUnitConversion("m/s", Fraction(1, 60)),
        "m/h": ExactUnitConversion("m/s", Fraction(1, 3600)),
        "ft/s": ExactUnitConversion("m/s", _FT_M),
        "ft/min": ExactUnitConversion("m/s", _FT_M / 60),
    },
    QuantityKind.FOULING_RESISTANCE: {
        "m^2*K/W": ExactUnitConversion("m^2*K/W", Fraction(1)),
        "m^2*delta_degC/W": ExactUnitConversion("m^2*K/W", Fraction(1)),
        "hour*ft^2*delta_degF/Btu": ExactUnitConversion("m^2*K/W", _FOULING_IMPERIAL_TO_SI),
    },
    QuantityKind.SPECIFIC_ENTHALPY: {
        "J/kg": ExactUnitConversion("J/kg", Fraction(1)),
        "kJ/kg": ExactUnitConversion("J/kg", Fraction(1000)),
        "MJ/kg": ExactUnitConversion("J/kg", Fraction(1000000)),
        "Btu/lb": ExactUnitConversion("J/kg", _BTU_LB_J_KG),
    },
    QuantityKind.DIMENSIONLESS: {
        "dimensionless": ExactUnitConversion("dimensionless", Fraction(1)),
        "percent": ExactUnitConversion("dimensionless", Fraction(1, 100)),
    },
}

_EXACT_UNIT_CONVERSIONS: Mapping[
    QuantityKind,
    Mapping[str, ExactUnitConversion],
] = MappingProxyType(
    {
        kind: MappingProxyType(dict(conversions))
        for kind, conversions in _RAW_EXACT_UNIT_CONVERSIONS.items()
    }
)
del _RAW_EXACT_UNIT_CONVERSIONS


def verify_exact_unit_registry() -> None:
    """Verify that the exact conversion registry covers all UNIT_RULES canonical units.

    Called once at module import. Fails closed on any mismatch:
    - UNIT_RULES allows a unit but exact registry is missing it
    - exact registry has a unit not authorized by UNIT_RULES
    - SI unit mismatch
    - zero scale
    - missing QuantityKind
    """
    for kind in QuantityKind:
        if kind not in _EXACT_UNIT_CONVERSIONS:
            raise RuntimeError(f"Exact unit registry missing QuantityKind {kind.value!r}")
        allowed = set(UNIT_RULES[kind].aliases.values())
        registered = set(_EXACT_UNIT_CONVERSIONS[kind].keys())
        missing = allowed - registered
        extra = registered - allowed
        if missing:
            raise RuntimeError(
                f"QuantityKind {kind.value!r}: units in UNIT_RULES but not in "
                f"exact registry: {sorted(missing)}"
            )
        if extra:
            raise RuntimeError(
                f"QuantityKind {kind.value!r}: units in exact registry but not "
                f"in UNIT_RULES: {sorted(extra)}"
            )
        expected_si = UNIT_RULES[kind].si_unit
        for unit_name, spec in _EXACT_UNIT_CONVERSIONS[kind].items():
            if spec.si_unit != expected_si:
                raise RuntimeError(
                    f"{kind.value}/{unit_name}: si_unit is {spec.si_unit!r}, "
                    f"expected {expected_si!r}"
                )
            if spec.scale == 0:
                raise RuntimeError(f"{kind.value}/{unit_name}: scale is zero")


verify_exact_unit_registry()


def exact_decimal_conversion(
    value: float,
    unit: str,
    kind: QuantityKind,
) -> tuple[Decimal, str]:
    """Convert a float value + unit to exact Decimal SI value + SI unit symbol.

    Uses the immutable exact conversion registry. All arithmetic is performed
    with exact Fraction → Decimal. No float intermediate. No pint. No fallback.

    Returns (si_decimal_value, si_unit_symbol).
    """
    canonical_unit = normalize_unit(kind, unit)
    spec = _EXACT_UNIT_CONVERSIONS[kind][canonical_unit]
    input_decimal = Decimal(repr(value))
    with localcontext(_CANONICAL_DECIMAL_CONTEXT):
        factor = Decimal(spec.scale.numerator) / Decimal(spec.scale.denominator)
        offset = Decimal(spec.offset.numerator) / Decimal(spec.offset.denominator)
        si_value = input_decimal * factor + offset
    return si_value, spec.si_unit


def canonical_quantity_payload(q: Quantity) -> dict[str, str]:
    """Convert a Quantity to canonical API dict representation.

    Frozen Contract §8.1 output schema:
        {"value": "<canonical SI decimal string>", "unit": "<SI unit symbol>"}

    Uses exact_decimal_conversion — no float intermediate, no pint, no fallback.
    """
    kind = q.kind
    if kind is None:
        raise ValueError(f"Quantity {q!r} has no kind")
    si_value, si_symbol = exact_decimal_conversion(q.value, q.unit, kind)
    return {
        "value": canonical_decimal_string(si_value),
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
    sorted_refs = canonicalize_catalog_refs(request.catalog_refs)
    canonical_refs = [_canonical_catalog_ref(ref) for ref in sorted_refs]

    # Verify request refs match resolved catalogs exactly
    ref_identities = tuple(
        (
            ref.catalog_id,
            ref.catalog_version,
            ref.catalog_content_hash,
            ref.source_identity,
            ref.schema_version,
        )
        for ref in sorted_refs
    )
    resolved_identities = tuple(
        (
            cat.catalog_id,
            cat.catalog_version,
            cat.catalog_content_hash,
            cat.source_identity,
            cat.schema_version,
        )
        for cat in sorted_catalogs
    )
    if ref_identities != resolved_identities:
        raise ValueError(
            f"Request catalog refs do not match resolved catalogs: "
            f"ref identities {ref_identities} != resolved identities {resolved_identities}"
        )

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

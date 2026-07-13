"""Deterministic canonicalization helpers for TASK-021 Slice A.

Round 7 canonical-type-system unification.

The canonical helpers are organized in three disjoint layers:

* **Layer A — public canonical JSON boundary**:
  ``strict_public_json_snapshot``, ``canonical_json``,
  ``fragment_canonical``, ``fragment_canonical_json``,
  ``snapshot_then_to_primitive``, ``force_frozen_canonical``
  (alias ``freeze_deeply``), ``force_frozen_optional_canonical``,
  and ``canonical_raw_json_or_none``.
  These accept ONLY the section 6.1 canonical JSON domain
  (``None`` / ``bool`` / ``int`` / ``str`` / ordinary ``list`` /
  ordinary string-keyed ``dict``) and reject anything else — including
  raw ``tuple`` / ``set`` / ``frozenset`` / ``float`` / ``Decimal`` /
  ``bytes`` / ``bytearray`` / ``memoryview`` / ``dataclass`` /
  ``Enum`` / arbitrary object / ``MappingProxyType`` /
  :class:`FrozenJsonArray` / :class:`FrozenJsonObject` /
  non-string mapping keys.

* **Layer B — internal frozen representation**:
  :class:`FrozenJsonArray` and :class:`FrozenJsonObject` — the TWO and
  ONLY TWO canonical internal container markers. Any internal reducer
  or hash reducer accepts canonical atoms
  (``None`` / ``bool`` / ``int`` / ``str``) plus these two markers and
  rejects everything else. ``MappingProxyType`` is a private
  implementation detail of ``FrozenJsonObject.values`` and is NOT
  itself an acceptable canonical node outside that wrapper. Raw
  ``tuple`` / ``list`` / ``dict`` / arbitrary object are also NOT
  acceptable internal canonical nodes.

* **Layer C — explicit model reduction**: model ``__post_init__``
  dataclass fields and explicit internal converters move known-shape
  data across the boundary. Generic internal helpers
  (``refreeze_internal_fragment``) no longer accept raw ``tuple``,
  raw ``list``, raw ``dict``, raw ``MappingProxyType``, or arbitrary
  object as the Layer B canonical closed set — those must traverse
  the appropriate Layer-A or explicit converter path.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from types import MappingProxyType
from typing import Any

DECIMAL_PRECISION = 50
COORDINATE_QUANTUM = Decimal("0.000000000001")
SQRT_3 = Decimal("1.7320508075688772935274463415058723669428052538104")
UUID_NAMESPACE_URL = uuid.NAMESPACE_URL
POSITION_URN_PREFIX = "urn:hxforge:task021:tube-position:v1:"
LAYOUT_URN_PREFIX = "urn:hxforge:task021:tube-layout:v1:"
_DECIMAL_RE = __import__("re").compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

# The canonical atom types — only these non-container values are
# accepted at every layer. ``float``, ``Decimal``, ``bytes``,
# ``tuple``, etc. are NOT canonical atoms.
_FROZEN_ATOM_TYPES = (bool, int, str, type(None))


def _is_canonical_atom(value: Any) -> bool:
    """Return True iff ``value`` is a canonical atom (None / bool / int / str)."""
    return value is None or isinstance(value, _FROZEN_ATOM_TYPES)


def _is_layer_b_value(value: Any) -> bool:
    """Return True iff ``value`` is a valid Layer-B internal canonical node.

    Closed set: canonical atom / FrozenJsonArray / FrozenJsonObject.
    Anything else (raw tuple / list / dict / MappingProxyType / set /
    frozenset / arbitrary object / Decimal / etc.) returns False.
    """
    if _is_canonical_atom(value):
        return True
    return isinstance(value, (FrozenJsonArray, FrozenJsonObject))


# --------------------------------------------------------------------------- #
# Public-layer exception types
# --------------------------------------------------------------------------- #


class CanonicalizationError(ValueError):
    """Raised when a value is outside the TASK-021 canonical JSON domain."""


class PublicCanonicalDomainError(CanonicalizationError):
    """Raised when a value intended for the public canonical boundary is invalid.

    This is the only signal every Layer-A helper
    (``strict_public_json_snapshot``, ``force_frozen_canonical`` /
    ``freeze_deeply``, ``snapshot_then_to_primitive``, ``canonical_json``,
    ``fragment_canonical``, ``fragment_canonical_json``,
    ``force_frozen_optional_canonical``) uses to reject a value.
    Callers that want fail-closed semantics
    (``canonical_raw_json_or_none``) MUST catch this.
    """


class NonCanonicalFragmentError(CanonicalizationError):
    """Raised by :func:`internal_frozen_to_primitive` when an input is
    not a valid Layer-B internal canonical node (i.e. not a canonical
    atom, not a :class:`FrozenJsonArray`, not a
    :class:`FrozenJsonObject`).
    """


# --------------------------------------------------------------------------- #
# Layer B — internal frozen representation
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FrozenJsonArray:
    """Round 5 §6 + Round 6 §4 + Round 7 type-system unification.

    ONE of the TWO Layer-B internal canonical container markers
    (alongside :class:`FrozenJsonObject`). Nested elements must
    themselves be canonical atoms (``None`` / ``bool`` / ``int`` /
    ``str``) or further nested internal markers
    (:class:`FrozenJsonArray` / :class:`FrozenJsonObject`). Raw
    ``tuple``, raw ``list``, raw ``dict``, raw ``MappingProxyType``,
    arbitrary objects, dataclass, Enum, ``Decimal`` are NOT
    acceptable here — the closed Layer-B value type is exactly
    ``canonical atom | FrozenJsonArray | FrozenJsonObject``.
    """

    values: tuple[Any, ...]  # Layer-B closed-set only — verified at construction

    def __post_init__(self) -> None:
        for index, item in enumerate(self.values):
            if _is_layer_b_value(item):
                continue
            raise PublicCanonicalDomainError(
                f"FrozenJsonArray element at index {index} of type "
                f"{type(item).__name__} is not a Layer-B canonical atom "
                f"or nested internal marker"
            )


@dataclass(frozen=True)
class FrozenJsonObject:
    """Round 7 (P1-1) — second Layer-B internal canonical container marker.

    ``FrozenJsonObject`` is the explicit wrapper for an internal-frozen
    mapping. Its ``values`` field is a ``MappingProxyType`` (used as a
    private implementation detail for immutability) whose keys are
    strings and whose values are Layer-B closed-set values (canonical
    atoms or :class:`FrozenJsonArray` / :class:`FrozenJsonObject`).

    A raw ``MappingProxyType`` from an arbitrary caller is NOT itself a
    Layer-B canonical node — callers that already hold a raw
    ``MappingProxyType`` MUST wrap it in :class:`FrozenJsonObject` to
    pass it through the internal reducer pipeline, or pass it through
    the Layer-A public boundary (which will reject ``MappingProxyType``
    outright — wrap first).
    """

    values: MappingProxyType[str, Any]  # Layer-B closed-set only

    def __post_init__(self) -> None:
        for key, item in self.values.items():
            if not isinstance(key, str):
                raise PublicCanonicalDomainError(
                    f"FrozenJsonObject key {key!r} of type {type(key).__name__} is not a string"
                )
            if _is_layer_b_value(item):
                continue
            raise PublicCanonicalDomainError(
                f"FrozenJsonObject value for key {key!r} of type "
                f"{type(item).__name__} is not a Layer-B canonical atom "
                f"or nested internal marker"
            )


# --------------------------------------------------------------------------- #
# Decimal helpers
# --------------------------------------------------------------------------- #


def parse_decimal(value: str, *, positive: bool | None = None) -> Decimal:
    """Parse one canonical decimal string under the frozen Decimal context."""
    if not isinstance(value, str) or not _DECIMAL_RE.fullmatch(value):
        raise CanonicalizationError("decimal lexical form is invalid")
    if value.startswith("+") or value != value.strip() or "e" in value.lower():
        raise CanonicalizationError("decimal lexical form is invalid")
    try:
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            ctx.rounding = ROUND_HALF_EVEN
            result = Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - Decimal is defensive
        raise CanonicalizationError("decimal lexical form is invalid") from exc
    if not result.is_finite():
        raise CanonicalizationError("decimal must be finite")
    if result == 0:
        result = Decimal(0)
    if positive is True and result <= 0:
        raise CanonicalizationError("decimal must be positive")
    if positive is False and result < 0:
        raise CanonicalizationError("decimal must be non-negative")
    return result


def decimal_string(value: Decimal) -> str:
    """Return a non-exponent canonical decimal string."""
    if not value.is_finite():
        raise CanonicalizationError("decimal must be finite")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def quantized_decimal_string(value: Decimal) -> str:
    """Quantize a coordinate using the frozen quantum and rounding mode."""
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        return decimal_string(value.quantize(COORDINATE_QUANTUM))


# --------------------------------------------------------------------------- #
# Layer A — public canonical boundary
# --------------------------------------------------------------------------- #


def strict_public_json_snapshot(value: Any) -> Any:
    """Validate ``value`` against the Layer-A canonical JSON domain.

    Accepts ONLY ``None`` / ``bool`` / ``int`` / ``str`` /
    ordinary ``list`` / ordinary string-keyed ``dict`` (recursively).
    Ordinary ``list`` becomes :class:`FrozenJsonArray`. Ordinary
    ``dict`` becomes :class:`FrozenJsonObject`. Mapping keys are
    sorted at this boundary for canonical JSON stability.

    Rejects (with :class:`PublicCanonicalDomainError`):

    - raw ``tuple`` / ``frozenset`` / ``set`` (no JSON representation;
      ``tuple`` is reserved for the *internal* Layer-B path only)
    - ``float`` / ``Decimal`` / ``bytes`` / ``bytearray`` /
      ``memoryview`` (not in canonical JSON domain)
    - ``dataclass`` / ``Enum`` / arbitrary object
    - ``MappingProxyType`` (it is a private implementation detail of
      :class:`FrozenJsonObject.values` and is not itself a canonical
      node)
    - :class:`FrozenJsonArray` / :class:`FrozenJsonObject` themselves
      (internal markers must not re-enter the public boundary)
    - any mapping with a non-string key
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, (tuple, frozenset, set, bytes, bytearray, memoryview)):
        raise PublicCanonicalDomainError(
            f"value of type {type(value).__name__} is forbidden at the "
            f"public canonical boundary; pass a list of canonical values"
        )
    if isinstance(value, float):
        raise PublicCanonicalDomainError(
            "binary floating-point values are forbidden at the public "
            "canonical boundary; use a decimal string instead"
        )
    if isinstance(value, Decimal):
        raise PublicCanonicalDomainError(
            "Decimal objects are forbidden at the public canonical "
            "boundary; use a canonical decimal string instead"
        )
    if isinstance(value, (FrozenJsonArray, FrozenJsonObject)):
        raise PublicCanonicalDomainError(
            f"value of type {type(value).__name__} is an internal Layer-B "
            f"marker and cannot be passed through the public snapshot "
            f"boundary"
        )
    if isinstance(value, MappingProxyType):
        raise PublicCanonicalDomainError(
            "MappingProxyType is a private implementation detail of "
            "FrozenJsonObject.values and is not a canonical node at the "
            "public Layer-A boundary; wrap it in FrozenJsonObject or "
            "convert it to a regular dict first"
        )
    if dataclasses.is_dataclass(value):
        raise PublicCanonicalDomainError(
            "dataclass instances must be reduced via dataclass_to_mapping "
            "before crossing the public Layer-A boundary"
        )
    if isinstance(value, enum.Enum):
        raise PublicCanonicalDomainError(
            "Enum instances must be reduced via .value before crossing the public Layer-A boundary"
        )
    if isinstance(value, list):
        return FrozenJsonArray(tuple(strict_public_json_snapshot(item) for item in value))
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise PublicCanonicalDomainError(
                    "mapping keys must be strings at the public canonical boundary"
                )
        rebuilt: dict[str, Any] = {
            key: strict_public_json_snapshot(item) for key, item in value.items()
        }
        return FrozenJsonObject(MappingProxyType({key: rebuilt[key] for key in sorted(rebuilt)}))
    raise PublicCanonicalDomainError(
        f"value of type {type(value).__name__} is outside the public canonical domain"
    )


def fragment_canonical(value: Any) -> Any:
    """Reduce a public-domain value to its primitive sorted-key form.

    Equivalent to ``internal_frozen_to_primitive(strict_public_json_snapshot(value))``.
    """
    return internal_frozen_to_primitive(strict_public_json_snapshot(value))


def fragment_canonical_json(value: Any) -> str:
    """Return canonical JSON of a public-domain value (Layer A public path)."""
    return canonical_json(fragment_canonical(value))


def snapshot_then_to_primitive(value: Any) -> Any:
    """Public-boundary pass for a public-domain value (Layer A → primitive).

    Equivalent to :func:`fragment_canonical`. This helper exists for
    naming-clarity at the call site but rejects the exact same domain
    as :func:`strict_public_json_snapshot`.
    """
    return fragment_canonical(value)


def canonical_raw_json_or_none(value: Any) -> Any | None:
    """Return a detached primitive snapshot of ``value`` or ``None``.

    Implements section 12.8 semantics: ``raw_failing_field`` is the
    canonical raw JSON for a failing field, IF such canonical raw JSON
    exists. If the field is ``float`` / ``Decimal`` / ``bytes`` /
    non-string-keyed mapping / arbitrary object / ``tuple`` / ``set`` /
    ``frozenset``, return ``None`` (no canonical raw JSON exists).

    Never raises for unsupported inputs; always fail-closed.
    """
    if value is None:
        return None
    try:
        snapshot = strict_public_json_snapshot(value)
    except PublicCanonicalDomainError:
        return None
    try:
        return internal_frozen_to_primitive(snapshot)
    except NonCanonicalFragmentError:
        return None


def force_frozen_canonical(value: Any) -> Any:
    """Deep-freeze a public-canonical fragment for dataclass storage (Layer A).

    Returns :class:`FrozenJsonArray` for ordinary ``list`` inputs,
    :class:`FrozenJsonObject` for ordinary string-keyed ``dict``
    inputs, canonical atoms for atom inputs.

    Strict rejection (Layer A contract):

    - :class:`FrozenJsonArray` / :class:`FrozenJsonObject` /
      ``MappingProxyType`` / raw ``tuple`` / raw ``frozenset`` /
      raw ``set`` / ``bytes`` / ``bytearray`` / ``memoryview`` /
      ``float`` / ``Decimal`` / ``dataclass`` / ``Enum`` / arbitrary
      object / mapping with non-string keys.
    """
    frozen = strict_public_json_snapshot(value)
    return frozen


# freeze_deeply is the historical alias kept for callers in
# slice-a tests; it is NOT a public API for new code.
freeze_deeply = force_frozen_canonical


def force_frozen_optional_canonical(value: Any | None) -> Any | None:
    """Layer-A deep-freeze for an OPTIONAL public-canonical fragment.

    ``None`` passes through; any non-None value goes through
    :func:`force_frozen_canonical`.
    """
    if value is None:
        return None
    return force_frozen_canonical(value)


# --------------------------------------------------------------------------- #
# Layer B — internal helpers
# --------------------------------------------------------------------------- #


def internal_frozen_to_primitive(value: Any) -> Any:
    """Reduce a Layer-B internal canonical node to a JSON-compatible primitive.

    Layer-B accepts ONLY:

    * canonical atoms (``None`` / ``bool`` / ``int`` / ``str``)
    * :class:`FrozenJsonArray`
    * :class:`FrozenJsonObject`

    Anything else (``raw tuple`` / ``raw list`` / ``raw dict`` /
    ``MappingProxyType`` / ``Decimal`` / arbitrary object / etc.)
    raises :class:`NonCanonicalFragmentError`.

    The output is recursively a JSON-compatible ``list`` / ``dict`` /
    canonical atom — i.e. already in the public-domain primitive
    shape, ready to feed :func:`canonical_json`.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, FrozenJsonArray):
        return [internal_frozen_to_primitive(item) for item in value.values]
    if isinstance(value, FrozenJsonObject):
        return {
            key: internal_frozen_to_primitive(item) for key, item in sorted(value.values.items())
        }
    raise NonCanonicalFragmentError(
        f"input of type {type(value).__name__} is not a Layer-B canonical "
        f"node; expected canonical atom / FrozenJsonArray / FrozenJsonObject"
    )


def refreeze_internal_fragment(value: Any) -> Any:
    """Strict whitelist pass for an already-Layer-B canonical node.

    Round 7 canonical-type-system unification: this helper is no
    longer a generic reducer for raw internal shapes. It accepts
    ONLY:

    * canonical atoms (``None`` / ``bool`` / ``int`` / ``str``)
    * :class:`FrozenJsonArray`
    * :class:`FrozenJsonObject`

    Raw ``tuple`` / raw ``list`` / raw ``dict`` /
    ``MappingProxyType`` / arbitrary object / ``Decimal`` / ``bytes``
    are all REJECTED with
    :class:`PublicCanonicalDomainError`. The previous fail-open
    ``return value`` tail and the raw-tuple generic conversion have
    been removed (Round 6 §3 / Round 7 P1-2).

    Idempotent walk: :class:`FrozenJsonArray` values are reduced to a
    fresh :class:`FrozenJsonArray` of recursively walked children;
    same for :class:`FrozenJsonObject`.
    """

    if value is None or isinstance(value, _FROZEN_ATOM_TYPES):
        return value
    if isinstance(value, FrozenJsonArray):
        return FrozenJsonArray(tuple(refreeze_internal_fragment(item) for item in value.values))
    if isinstance(value, FrozenJsonObject):
        rebuilt: dict[str, Any] = {}
        for key in sorted(value.values.keys()):
            rebuilt[key] = refreeze_internal_fragment(value.values[key])
        return FrozenJsonObject(MappingProxyType(rebuilt))
    raise PublicCanonicalDomainError(
        f"refreeze_internal_fragment rejected value of type "
        f"{type(value).__name__}; only canonical atoms / FrozenJsonArray / "
        f"FrozenJsonObject are allowed at this Layer-B boundary. "
        f"Use force_frozen_canonical / snapshot_then_to_primitive for "
        f"raw public-domain inputs."
    )


def freeze_known_fragment(value: Any) -> Any:
    """Layer-C explicit converter for dataclass ``__post_init__`` use.

    Round 7 (Layer C): model ``__post_init__`` constructors receive
    fields that may already be in the public Layer-A canonical form
    (``dict`` / ``None``) or in the Layer-B internal form
    (:class:`FrozenJsonArray` / :class:`FrozenJsonObject`). This
    helper routes the input through the correct canonical path:

    * ``None`` / canonical atoms → pass through.
    * Public-domain ``list`` / string-keyed ``dict`` → call
      :func:`force_frozen_canonical` (Layer A → Layer B).
    * :class:`FrozenJsonArray` / :class:`FrozenJsonObject` → call
      :func:`refreeze_internal_fragment` (Layer B idempotent walk).
    * Anything else (``raw tuple`` / ``Decimal`` / arbitrary object /
      etc.) → :class:`PublicCanonicalDomainError`.

    This is NOT a public API and is not added to ``__all__``.
    """

    if value is None or _is_canonical_atom(value):
        return value
    if isinstance(value, (FrozenJsonArray, FrozenJsonObject)):
        return refreeze_internal_fragment(value)
    if isinstance(value, (list, dict)):
        return force_frozen_canonical(value)
    raise PublicCanonicalDomainError(
        f"freeze_known_fragment rejected value of type "
        f"{type(value).__name__}; allowed: canonical atoms / "
        f"FrozenJsonArray / FrozenJsonObject / list / dict / None"
    )


# --------------------------------------------------------------------------- #
# canonical_json — Layer-A serialization boundary
# --------------------------------------------------------------------------- #


def _canonical_value(value: Any) -> Any:
    """Top-level canonical serialization primitive (Layer A).

    Accepts the public canonical JSON domain only:
    ``None`` / ``bool`` / ``int`` / ``str`` / ordinary ``list`` /
    ordinary string-keyed ``dict``. Rejects:

    * ``float`` / ``Decimal`` / ``bytes`` / ``bytearray`` /
      ``memoryview`` / ``tuple`` / ``frozenset`` / ``set``
    * ``dataclass`` / ``Enum`` / arbitrary object
    * :class:`FrozenJsonArray` / :class:`FrozenJsonObject` /
      ``MappingProxyType`` (internal Layer-B markers — they MUST be
      reduced via :func:`internal_frozen_to_primitive` before reaching
      this function)

    Key sorting is enforced atomically for stability.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, (FrozenJsonArray, FrozenJsonObject)):
        raise CanonicalizationError(
            f"value of type {type(value).__name__} is an internal Layer-B "
            f"marker and cannot be passed to canonical_json directly; "
            f"reduce via internal_frozen_to_primitive first"
        )
    if isinstance(value, MappingProxyType):
        raise CanonicalizationError(
            "MappingProxyType is a private implementation detail of "
            "FrozenJsonObject.values and must not be passed to "
            "canonical_json directly; reduce via internal_frozen_to_primitive"
        )
    if isinstance(value, enum.Enum):
        raise CanonicalizationError("Enum values must be reduced via .value before serialization")
    if dataclasses.is_dataclass(value):
        raise CanonicalizationError(
            "dataclass values must be reduced via dataclass_to_mapping before serialization"
        )
    if isinstance(value, float):
        raise CanonicalizationError("binary floating-point values are forbidden")
    if isinstance(value, Decimal):
        raise CanonicalizationError("Decimal objects are forbidden at serialization boundary")
    if isinstance(value, (tuple, frozenset)):
        raise CanonicalizationError(
            f"sequence type {type(value).__name__} is forbidden at "
            f"serialization boundary; use a list of canonical primitives"
        )
    if isinstance(value, set):
        raise CanonicalizationError(
            "set is forbidden at serialization boundary; iteration order is not canonical"
        )
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("canonical object keys must be strings")
            normalized[key] = _canonical_value(item)
        return {key: normalized[key] for key in sorted(normalized)}
    raise CanonicalizationError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize a value under the TASK-021 canonical JSON rules (Layer A).

    Only the public canonical JSON domain is accepted; internal Layer-B
    markers must be reduced first via :func:`internal_frozen_to_primitive`.
    """
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_hex(value: Any) -> str:
    """Return SHA-256 over canonical JSON bytes."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def dataclass_to_mapping(value: Any) -> dict[str, Any]:
    """Convert a dataclass to a primitive-string-keyed mapping.

    Every field value is recursively reduced via :func:`to_primitive`
    (a broader helper that handles nested tuples/lists/mappings and
    ``Decimal``/etc. → canonical strings).
    """
    if not dataclasses.is_dataclass(value):
        raise TypeError("value must be a dataclass instance")
    result: dict[str, Any] = {}
    for field in dataclasses.fields(value):
        raw = getattr(value, field.name)
        result[field.name] = to_primitive(raw)
    return result


def to_primitive(value: Any) -> Any:
    """Convert arbitrary package values to JSON-compatible Python primitives.

    Unlike :func:`canonical_json` (Layer-A public path) which rejects
    ``tuple``, this helper accepts ``tuple`` (frozen-dataclass field
    shape) and emits it as a ``list`` — used by
    :func:`dataclass_to_mapping` for already-validated canonical
    dataclass field values that include ``tuple[str, ...]`` field
    shapes (e.g. evidence_refs).

    Round 7 type-system: ``FrozenJsonObject`` and ``FrozenJsonArray``
    are explicit Layer-B markers that are themselves dataclasses but
    MUST be reduced via their explicit ``.values`` accessor before any
    generic dataclass walk — the Layer-B ``.values`` field carries
    the canonical internal data.
    """

    if isinstance(value, FrozenJsonObject):
        return {key: to_primitive(item) for key, item in sorted(value.values.items())}
    if isinstance(value, FrozenJsonArray):
        return [to_primitive(item) for item in value.values]
    if dataclasses.is_dataclass(value):
        return dataclass_to_mapping(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, bytes | bytearray | memoryview):
        raise CanonicalizationError("byte strings are forbidden at serialization boundary")
    if isinstance(value, float):
        raise CanonicalizationError("binary floating-point values are forbidden")
    if isinstance(value, Decimal):
        raise CanonicalizationError("Decimal objects must be expressed as canonical strings")
    if isinstance(value, tuple):
        try:
            return [to_primitive(item) for item in value]
        except CanonicalizationError as exc:
            raise CanonicalizationError(
                f"tuple element of type {type(value).__name__} cannot be serialized: {exc}"
            ) from exc
    if isinstance(value, list):
        return [to_primitive(item) for item in value]
    if isinstance(value, Mapping):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError("canonical mapping keys must be strings")
        return {key: to_primitive(item) for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise CanonicalizationError(f"unsupported canonical value: {type(value).__name__}")


# --------------------------------------------------------------------------- #
# Auxiliary helpers (canonical arrays / messages / ids)
# --------------------------------------------------------------------------- #


def sorted_unique_strings(values: Sequence[str], *, allow_empty: bool = True) -> tuple[str, ...]:
    """Validate and sort a duplicate-free string array."""
    if not isinstance(values, list | tuple):
        raise TypeError("expected an array")
    if not allow_empty and not values:
        raise ValueError("array must be non-empty")
    if any(not isinstance(item, str) or not item for item in values):
        raise TypeError("array items must be non-empty strings")
    if len(set(values)) != len(values):
        raise ValueError("duplicate array item")
    return tuple(sorted(values))


def _reduce_for_hash(value: Any) -> Any:
    """Reduce a Layer-B value to a primitive form before hashing.

    Round 7 (P0-2 / hash-boundary corrective): this helper accepts
    ONLY canonical atoms / :class:`FrozenJsonArray` /
    :class:`FrozenJsonObject` / ``dataclass`` (explicit
    :func:`dataclass_to_mapping`) / ``Enum`` (``value.value``).
    Raw ``tuple`` / raw ``list`` / raw ``dict`` /
    ``MappingProxyType`` / arbitrary object / ``Decimal`` / ``bytes``
    are all rejected with :class:`CanonicalizationError`. The previous
    lenient ``Mapping`` branch was a security weakness: a raw
    ``MappingProxyType`` is exactly the pre-R7 frozen-mapping shape,
    not an explicit Layer-B marker, so it MUST be wrapped in
    :class:`FrozenJsonObject` first to enter this hash path.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, FrozenJsonObject):
        return {key: _reduce_for_hash(item) for key, item in sorted(value.values.items())}
    if isinstance(value, FrozenJsonArray):
        return [_reduce_for_hash(item) for item in value.values]
    if dataclasses.is_dataclass(value):
        return _reduce_for_hash(dataclass_to_mapping(value))
    if isinstance(value, enum.Enum):
        return value.value
    raise CanonicalizationError(
        f"_reduce_for_hash encountered unsupported value of type "
        f"{type(value).__name__}; the canonical hash accepts only "
        f"canonical atoms / FrozenJsonArray / FrozenJsonObject / "
        f"dataclass / Enum per Round 7 §P0-2"
    )


def message_sort_key(entry: Any) -> tuple[str, str, str, str, str]:
    """Return the frozen warning/blocker composite ordering key."""
    details = getattr(entry, "details", None)
    evidence_refs = list(getattr(entry, "evidence_refs", ()))
    return (
        str(entry.code),
        "" if getattr(entry, "field_path", None) is None else str(entry.field_path),
        str(entry.message_key),
        sha256_hex(_reduce_for_hash(details)),
        sha256_hex(evidence_refs),
    )


def sort_messages(entries: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(entries, key=message_sort_key))


def position_id(request_hash: str, u: int, v: int) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE_URL, f"{POSITION_URN_PREFIX}{request_hash}:{u}:{v}"))


def layout_id(layout_hash: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE_URL, LAYOUT_URN_PREFIX + layout_hash))


# --------------------------------------------------------------------------- #
# Public package surface (`__all__`)
# --------------------------------------------------------------------------- #
#
# Round 7: the public API surface is reduced to Layer A plus a small
# set of shared infrastructure (Decimal, ids, message_sort_key,
# sort_messages, sha256_hex). All Layer-B internal helpers and types
# are still importable via module-private path for in-package use
# (see ``models.py`` / ``validation.py``), but they MUST NOT be
# advertised as public API through `__all__`.

__all__ = [
    "COORDINATE_QUANTUM",
    "CanonicalizationError",
    "DECIMAL_PRECISION",
    "LAYOUT_URN_PREFIX",
    "POSITION_URN_PREFIX",
    "PublicCanonicalDomainError",
    "SQRT_3",
    "UUID_NAMESPACE_URL",
    "canonical_json",
    "canonical_raw_json_or_none",
    "decimal_string",
    "force_frozen_canonical",
    "force_frozen_optional_canonical",
    "fragment_canonical",
    "fragment_canonical_json",
    "freeze_deeply",
    "layout_id",
    "message_sort_key",
    "parse_decimal",
    "position_id",
    "quantized_decimal_string",
    "sha256_hex",
    "snapshot_then_to_primitive",
    "sort_messages",
    "sorted_unique_strings",
    "strict_public_json_snapshot",
]

from __future__ import annotations

import hashlib
import json
import math
import types
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from hexagent.domain.models import DesignCase

# ---------------------------------------------------------------------------
# Pre-processing: convert tuples to sorted lists before serialisation
# ---------------------------------------------------------------------------


def _preprocess(obj: Any) -> Any:
    """Recursively convert tuples/frozensets to sorted lists so
    ``json.dumps`` (which cannot invoke ``default`` for tuples)
    produces deterministic output.

    Also converts Pydantic models to dicts and Quantity-like objects
    to canonical dicts.
    """
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError(f"Non-finite float {obj!r} cannot be serialised")

    # Enum → value
    if isinstance(obj, Enum):
        return obj.value

    # UUID → string
    if isinstance(obj, UUID):
        return str(obj)

    # datetime → UTC ISO-8601
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            raise ValueError("datetime must be timezone-aware for canonical serialisation")
        utc = obj.astimezone(UTC)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Quantity-like → canonical dict using SI value + kind for
    # content-identity; display unit is metadata, not part of the hash.
    if hasattr(obj, "value") and hasattr(obj, "unit") and hasattr(obj, "kind"):
        kind = obj.kind
        # Compute SI value so that e.g. 100 °C and 373.15 K produce the
        # same content hash when the kind is ABSOLUTE_TEMPERATURE.
        # Fail closed: if SI conversion fails, raise immediately.
        si_val = obj.value
        if kind is not None and hasattr(obj, "to_si"):
            si_val = obj.to_si().value
        return {
            "si_value": si_val,
            "kind": kind.value if kind is not None else None,
        }

    # Pydantic BaseModel → dict
    if hasattr(obj, "model_dump"):
        return {k: _preprocess(v) for k, v in obj.model_dump().items()}

    # MappingProxyType (from deep_freeze) → recursively process values
    if isinstance(obj, types.MappingProxyType):
        return {k: _preprocess(v) for k, v in obj.items()}

    # dict → recursively process values
    if isinstance(obj, dict):
        return {k: _preprocess(v) for k, v in obj.items()}

    # frozenset → sorted list (sets are unordered by definition)
    if isinstance(obj, frozenset):
        items = [_preprocess(item) for item in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True))

    # tuple → ordered list (tuples preserve insertion order)
    if isinstance(obj, tuple):
        return [_preprocess(item) for item in obj]

    # set → sorted list
    if isinstance(obj, set):
        items = [_preprocess(item) for item in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True))

    # list → recursively process
    if isinstance(obj, list):
        return [_preprocess(item) for item in obj]

    # primitives pass through
    return obj


# ---------------------------------------------------------------------------
# Canonical JSON encoder (fallback for any remaining non-standard types)
# ---------------------------------------------------------------------------


def _canonical_encoder(obj: Any) -> Any:
    """Fallback encoder for :func:`json.dumps`. Most types are handled
    by :func:`_preprocess`, but this catches edge cases.
    """
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError(f"Non-finite float {obj!r} cannot be serialised")
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        utc = obj.astimezone(UTC)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if hasattr(obj, "value") and hasattr(obj, "unit") and hasattr(obj, "kind"):
        kind = obj.kind
        si_val = obj.value
        if kind is not None and hasattr(obj, "to_si"):
            si_val = obj.to_si().value
        return {
            "si_value": si_val,
            "kind": kind.value if kind is not None else None,
        }
    if hasattr(obj, "model_dump"):
        return {k: _canonical_encoder(v) for k, v in obj.model_dump().items()}
    if isinstance(obj, types.MappingProxyType):
        return {k: _canonical_encoder(v) for k, v in obj.items()}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON-serialisable")


def canonical_json(obj: Any) -> str:
    """Produce a deterministic, canonical JSON string.

    Output is UTF-8 encoded, uses compact separators (``','`` and
    ``':'``), keys are sorted recursively, and all non-primitive
    types are handled by :func:`_preprocess`.

    Raises ``ValueError`` if the object contains ``NaN`` or
    ``Infinity`` floats.
    """
    processed = _preprocess(obj)
    return json.dumps(
        processed,
        default=_canonical_encoder,
        sort_keys=True,
        separators=(",", ":"),
    )


# ---------------------------------------------------------------------------
# Design-case canonicalisation
# ---------------------------------------------------------------------------


def _is_quantity(obj: Any) -> bool:
    """Return True if *obj* is a Quantity-like object (before model_dump)."""
    return (
        hasattr(obj, "value")
        and hasattr(obj, "unit")
        and hasattr(obj, "kind")
        and hasattr(obj, "to_si")
    )


def _walk_model_value(obj: Any) -> Any:
    """Recursively walk a Pydantic model tree and produce canonical form.

    Unlike :func:`_preprocess`, this function processes objects *before*
    ``model_dump()`` is called, so Quantity objects retain their type
    semantics and can be correctly SI-normalized.
    """
    # Quantity-like → canonical dict using SI value + kind
    if _is_quantity(obj):
        kind = obj.kind
        si_val = obj.value
        if kind is not None:
            si_val = obj.to_si().value
        return {
            "si_value": si_val,
            "kind": kind.value if kind is not None else None,
        }

    # Pydantic BaseModel → recurse into fields
    if hasattr(obj, "model_dump") and hasattr(type(obj), "model_fields"):
        result: dict[str, Any] = {}
        for field_name in type(obj).model_fields:
            if hasattr(obj, field_name):
                val = getattr(obj, field_name)
                result[field_name] = _walk_model_value(val)
        return result

    # dict → recurse values
    if isinstance(obj, dict):
        return {k: _walk_model_value(v) for k, v in obj.items()}

    # frozenset → sorted list
    if isinstance(obj, frozenset):
        items = [_walk_model_value(item) for item in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, default=str))

    # tuple → ordered list (preserving order)
    if isinstance(obj, tuple):
        return [_walk_model_value(item) for item in obj]

    # set → sorted list
    if isinstance(obj, set):
        items = [_walk_model_value(item) for item in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, default=str))

    # list → recurse
    if isinstance(obj, list):
        return [_walk_model_value(item) for item in obj]

    # Enum → value
    if isinstance(obj, Enum):
        return obj.value

    # UUID → string
    if isinstance(obj, UUID):
        return str(obj)

    # datetime → UTC ISO-8601
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            raise ValueError("datetime must be timezone-aware for canonical serialisation")
        utc = obj.astimezone(UTC)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Non-finite float check
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError(f"Non-finite float {obj!r} cannot be serialised")

    # Primitives pass through
    return obj


def canonicalize_design_case(case: DesignCase) -> dict[str, Any]:
    """Produce a canonical dict from a :class:`DesignCase`.

    Walks the Pydantic model tree *before* ``model_dump()`` so that
    Quantity objects retain their type semantics and are SI-normalized
    during canonicalization.  The result is deterministic (sorted keys,
    canonical types) and suitable for hashing with :func:`sha256_digest`.
    """
    result: dict[str, Any] = _walk_model_value(case)
    return result


# ---------------------------------------------------------------------------
# SHA-256 digest
# ---------------------------------------------------------------------------


def sha256_digest(obj: Any) -> str:
    """Return a SHA-256 content hash of *obj*.

    ``obj`` is first serialised to canonical JSON via
    :func:`canonical_json`, then hashed.

    The return value is always ``"sha256:<64-char lowercase hex>"``.
    """
    payload = canonical_json(obj)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


__all__ = [
    "canonical_json",
    "canonicalize_design_case",
    "sha256_digest",
]

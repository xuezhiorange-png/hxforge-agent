from __future__ import annotations

import hashlib
import json
import math
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
            raise ValueError(
                "datetime must be timezone-aware for canonical serialisation"
            )
        utc = obj.astimezone(UTC)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Quantity-like → {value, unit, kind}
    if hasattr(obj, "value") and hasattr(obj, "unit") and hasattr(obj, "kind"):
        kind = obj.kind
        return {
            "value": obj.value,
            "unit": obj.unit,
            "kind": kind.value if kind is not None else None,
        }

    # Pydantic BaseModel → dict
    if hasattr(obj, "model_dump"):
        return {k: _preprocess(v) for k, v in obj.model_dump().items()}

    # tuple / frozenset → sorted list
    if isinstance(obj, (tuple, frozenset)):
        items = [_preprocess(item) for item in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True))

    # set → sorted list
    if isinstance(obj, set):
        items = [_preprocess(item) for item in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True))

    # list → recursively process
    if isinstance(obj, list):
        return [_preprocess(item) for item in obj]

    # dict → recursively process values
    if isinstance(obj, dict):
        return {k: _preprocess(v) for k, v in obj.items()}

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
        return {
            "value": obj.value,
            "unit": obj.unit,
            "kind": kind.value if kind is not None else None,
        }
    if hasattr(obj, "model_dump"):
        return {k: _canonical_encoder(v) for k, v in obj.model_dump().items()}
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


def canonicalize_design_case(case: DesignCase) -> dict[str, Any]:
    """Produce a canonical dict from a :class:`DesignCase`.

    The result is deterministic (sorted keys, canonical types) and
    suitable for hashing with :func:`sha256_digest`.
    """
    result: dict[str, Any] = _preprocess(case.model_dump())
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

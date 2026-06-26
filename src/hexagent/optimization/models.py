"""
TASK-009 Phase 1 data models — catalog snapshots, assembly options,
length source, grid specification, request structures, cap-blocked result,
and per-option audit records.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hexagent.optimization._quantum import canonicalize_length_quantum


class LengthEndpointPolicy(StrEnum):
    """Controls whether the grid maximum is included as a candidate length."""

    INCLUDE_MAX_IF_ALIGNED = "include_max_if_aligned"
    EXCLUDE_MAX = "exclude_max"


class LengthGridSpec(BaseModel):
    """Specifies a uniform grid of candidate lengths.  All lengths in metres."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    minimum_length_m: float
    maximum_length_m: float
    increment_m: float
    endpoint_policy: LengthEndpointPolicy


class LengthSource(BaseModel):
    """Length specification for an assembly option.

    Exactly one of ``allowed_effective_lengths_m`` (Mode A — explicit list)
    or ``grid`` (Mode B — uniform grid) must be provided.

    ``length_quantum_m`` is canonicalised on construction so that
    equivalent inputs (``"0.001"``, ``"0.0010"``, ``"1E-3"``)
    all store the same value.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    length_quantum_m: str
    allowed_effective_lengths_m: tuple[float, ...] | None = None
    grid: LengthGridSpec | None = None

    @field_validator("length_quantum_m", mode="before")
    @classmethod
    def _canonicalize_quantum(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError(f"length_quantum_m must be a str, got {type(value).__name__}")
        return canonicalize_length_quantum(value)

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        has_explicit = self.allowed_effective_lengths_m is not None
        has_grid = self.grid is not None
        if has_explicit == has_grid:
            msg = "Exactly one of allowed_effective_lengths_m or grid must be provided"
            raise ValueError(msg)
        return self


class CompleteDoublePipeAssemblyOption(BaseModel):
    """A single assembly option from a catalog.

    ``manufacturing_metadata`` normalises dict inputs to sorted
    ``(key, value)`` tuples with ASCII ordering and unique keys.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    assembly_option_id: str
    inner_tube_inner_diameter_m: float
    inner_tube_outer_diameter_m: float
    outer_pipe_inner_diameter_m: float
    wall_thermal_conductivity_w_m_k: float
    inner_surface_roughness_m: float
    annulus_surface_roughness_m: float
    inner_fouling_resistance_m2k_w: float
    outer_fouling_resistance_m2k_w: float
    length_source: LengthSource
    manufacturing_option_identity: str
    manufacturing_metadata: tuple[tuple[str, str], ...] = Field(default_factory=tuple)

    @field_validator("manufacturing_metadata", mode="before")
    @classmethod
    def _normalize_metadata(cls, value: object) -> tuple[tuple[str, str], ...]:
        """Normalise manufacturing metadata to sorted ASCII-key tuples.

        Accepts ``dict[str, str]`` or ``tuple[tuple[str, str], ...]``.
        """
        if isinstance(value, dict):
            items: list[tuple[str, str]] = []
            for k, v in value.items():
                if not isinstance(k, str):
                    raise TypeError(
                        f"manufacturing_metadata key must be str, got {type(k).__name__}"
                    )
                if not isinstance(v, str):
                    raise TypeError(
                        f"manufacturing_metadata value must be str, got {type(v).__name__}"
                    )
                if not k.isascii():
                    raise ValueError(f"manufacturing_metadata key must be ASCII: {k!r}")
                items.append((k, v))
            items.sort(key=lambda p: p[0])
            # Check duplicate keys
            seen: set[str] = set()
            for k, _v in items:
                if k in seen:
                    raise ValueError(f"Duplicate manufacturing_metadata key: {k!r}")
                seen.add(k)
            return tuple(items)
        elif isinstance(value, tuple):
            pairs: list[tuple[str, str]] = []
            for pair in value:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    raise TypeError(
                        f"Each manufacturing_metadata entry must be a 2-tuple, got {pair!r}"
                    )
                k_raw, v_raw = pair
                if not isinstance(k_raw, str):
                    raise TypeError(
                        f"manufacturing_metadata key must be str, got {type(k_raw).__name__}"
                    )
                if not isinstance(v_raw, str):
                    raise TypeError(
                        f"manufacturing_metadata value must be str, got {type(v_raw).__name__}"
                    )
                if not k_raw.isascii():
                    raise ValueError(f"manufacturing_metadata key must be ASCII: {k_raw!r}")
                pairs.append((k_raw, v_raw))
            pairs.sort(key=lambda p: p[0])
            seen2: set[str] = set()
            for k, _v in pairs:
                if k in seen2:
                    raise ValueError(f"Duplicate manufacturing_metadata key: {k!r}")
                seen2.add(k)
            return tuple(pairs)
        else:
            raise TypeError(
                f"manufacturing_metadata must be a dict or tuple, got {type(value).__name__}"
            )


class CompleteDoublePipeCatalogSnapshot(BaseModel):
    """A full catalog snapshot supplied by the caller."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalog_id: str
    catalog_version: str
    source_identity: str
    schema_version: str
    assembly_options: tuple[CompleteDoublePipeAssemblyOption, ...]
    catalog_content_hash: str


class CatalogSnapshotRef(BaseModel):
    """Reference derived from a catalog snapshot for identity payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalog_id: str
    catalog_version: str
    catalog_content_hash: str
    source_identity: str
    schema_version: str


class SizingRequest(BaseModel):
    """Top-level request container for a sizing + candidate optimisation run.

    Validates bounds and cap at construction time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...]
    minimum_effective_length_m: float | None = None
    maximum_effective_length_m: float | None = None
    request_raw_combination_cap: int | None = None

    @field_validator("minimum_effective_length_m", mode="before")
    @classmethod
    def _validate_min_bound(cls, value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise TypeError("minimum_effective_length_m must be float, not bool")
        fv = float(value)  # type: ignore[arg-type]
        if fv <= 0:
            raise ValueError(f"minimum_effective_length_m must be positive, got {fv}")
        import math

        if not math.isfinite(fv):
            raise ValueError(f"minimum_effective_length_m must be finite, got {fv}")
        return fv

    @field_validator("maximum_effective_length_m", mode="before")
    @classmethod
    def _validate_max_bound(cls, value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise TypeError("maximum_effective_length_m must be float, not bool")
        fv = float(value)  # type: ignore[arg-type]
        if fv <= 0:
            raise ValueError(f"maximum_effective_length_m must be positive, got {fv}")
        import math

        if not math.isfinite(fv):
            raise ValueError(f"maximum_effective_length_m must be finite, got {fv}")
        return fv

    @field_validator("request_raw_combination_cap", mode="before")
    @classmethod
    def _validate_cap(cls, value: object) -> int | None:
        if value is None:
            return None
        # bool is a strict subtype of int — reject it
        if type(value) is bool:
            raise TypeError("request_raw_combination_cap must be int, not bool")
        if not isinstance(value, int):
            raise TypeError(f"request_raw_combination_cap must be int, got {type(value).__name__}")
        if value <= 0:
            raise ValueError(f"request_raw_combination_cap must be positive, got {value}")
        if value > 10_000:
            raise ValueError(f"request_raw_combination_cap must be <= 10000, got {value}")
        return value

    @model_validator(mode="after")
    def _bounds_ordering(self) -> Self:
        lo = self.minimum_effective_length_m
        hi = self.maximum_effective_length_m
        if lo is not None and hi is not None and lo > hi:
            raise ValueError(
                f"minimum_effective_length_m ({lo}) must not exceed "
                f"maximum_effective_length_m ({hi})"
            )
        return self


# ---------------------------------------------------------------------------
# Per-option audit record
# ---------------------------------------------------------------------------


class OptionRawCountRecord(BaseModel):
    """Deterministic per-option raw-count audit record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalog_id: str
    catalog_version: str
    catalog_content_hash: str
    assembly_option_id: str
    canonical_length_quantum_m: str
    raw_count: int


# ---------------------------------------------------------------------------
# Aggregate raw combination count
# ---------------------------------------------------------------------------


class RawCombinationCount(BaseModel):
    """Aggregated raw combination count across all options and catalogs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_count: int
    effective_cap: int
    cap_exceeded: bool
    per_option: tuple[OptionRawCountRecord, ...]


# ---------------------------------------------------------------------------
# Blocked result (pre-materialization cap rejection)
# ---------------------------------------------------------------------------


class CapBlocker(BaseModel):
    """A structured blocker for cap-exceeded situations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = "cap_exceeded"
    message: str
    context: tuple[tuple[str, Any], ...] = Field(default_factory=tuple)


class BlockedSizingResult(BaseModel):
    """Result when cap is exceeded before any materialization or evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["blocked"] = "blocked"
    raw_combination_count: int
    effective_cap: int
    unique_candidate_count: int = 0
    evaluated_candidate_count: int = 0
    selected_candidate: None = None
    top_candidates: tuple[Any, ...] = Field(default_factory=tuple)
    failure: None = None
    blockers: tuple[CapBlocker, ...] = Field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Unsized result (cap-passed, continuing to materialization)
# ---------------------------------------------------------------------------


class SizingGateResult(BaseModel):
    """Intermediate result after cap gate passes but before evaluation.

    ``materialize_lengths``, ``build_candidate_identities``, and
    ``rating_evaluator`` are passed as callables and invoked in order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["gated"] = "gated"
    raw_combination_count: int
    effective_cap: int
    per_option: tuple[OptionRawCountRecord, ...]


class LengthSpecGridContext(BaseModel):
    """Result of the count-only grid algorithm before materialization.

    This is an internal intermediate value, not a persistence model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    lo_tick: int
    hi_tick: int
    step_tick: int
    delta: int
    remainder: int
    catalog_count: int
    endpoint_policy: LengthEndpointPolicy
    intersection_count: int
    first_idx: int
    last_idx: int


class LengthSpecExplicitContext(BaseModel):
    """Result of explicit-length canonicalization before materialization.

    This is an internal intermediate value, not a persistence model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalog_ticks: tuple[int, ...]
    catalog_lengths: tuple[str, ...]
    intersection_ticks: tuple[int, ...]
    intersection_count: int


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------

__all__ = [
    "BlockedSizingResult",
    "CapBlocker",
    "CatalogSnapshotRef",
    "CompleteDoublePipeAssemblyOption",
    "CompleteDoublePipeCatalogSnapshot",
    "LengthEndpointPolicy",
    "LengthGridSpec",
    "LengthSource",
    "LengthSpecExplicitContext",
    "LengthSpecGridContext",
    "OptionRawCountRecord",
    "RawCombinationCount",
    "SizingGateResult",
    "SizingRequest",
]

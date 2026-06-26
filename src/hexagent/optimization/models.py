"""
TASK-009 Phase 1 data models — catalog snapshots, assembly options,
length source, grid specification, and request structures.

Only the models listed in Phase 1 scope are included here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LengthEndpointPolicy(StrEnum):
    """Controls whether the grid maximum is included as a candidate length."""

    INCLUDE_MAX_IF_ALIGNED = "include_max_if_aligned"
    EXCLUDE_MAX = "exclude_max"


class LengthGridSpec(BaseModel):
    """Specifies a uniform grid of candidate lengths.

    All lengths are in metres.
    """

    model_config = ConfigDict(extra="forbid")

    minimum_length_m: float
    maximum_length_m: float
    increment_m: float
    endpoint_policy: LengthEndpointPolicy


class LengthSource(BaseModel):
    """Length specification for an assembly option.

    Exactly one of ``allowed_effective_lengths_m`` (Mode A — explicit list)
    or ``grid`` (Mode B — uniform grid) must be provided.  Both carry
    ``length_quantum_m`` as a canonical Decimal string.

    The quantum string is checked for power-of-10 form at the application
    layer (see ``length.validate_length_quantum``).
    """

    model_config = ConfigDict(extra="forbid")

    length_quantum_m: str
    allowed_effective_lengths_m: tuple[float, ...] | None = None
    grid: LengthGridSpec | None = None

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

    All geometry fields are SI (metres, W/m·K, m²K/W).
    """

    model_config = ConfigDict(extra="forbid")

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


class CompleteDoublePipeCatalogSnapshot(BaseModel):
    """A full catalog snapshot supplied by the caller.

    ``catalog_content_hash`` is the sha256 digest of all other fields
    in deterministic order, computed at the application layer.
    """

    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    catalog_version: str
    source_identity: str
    schema_version: str
    assembly_options: tuple[CompleteDoublePipeAssemblyOption, ...]
    catalog_content_hash: str


class CatalogSnapshotRef(BaseModel):
    """Reference derived from a catalog snapshot for identity payloads."""

    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    catalog_version: str
    catalog_content_hash: str
    source_identity: str
    schema_version: str


class SizingRequest(BaseModel):
    """Top-level request container for a sizing + candidate optimization run.

    This is the Phase 1 shell containing only the catalog snapshots
    and length-related request bounds.  It will be extended with
    rating parameters and fluid specifications in later phases.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...]
    minimum_effective_length_m: float | None = None
    maximum_effective_length_m: float | None = None
    request_raw_combination_cap: int | None = None


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


class RawCombinationCount(BaseModel):
    """Aggregated raw combination count across all catalogs.

    Used for the cap check before any materialization or evaluation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_count: int
    effective_cap: int
    cap_exceeded: bool
    per_option: tuple[tuple[str, int], ...]  # (assembly_option_id, count)


# ---------------------------------------------------------------------------
# Blocked result (pre-materialization cap rejection)
# ---------------------------------------------------------------------------


class BlockedSizingResult(BaseModel):
    """Result when cap is exceeded before any materialization or evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["BLOCKED"] = "BLOCKED"
    raw_combination_count: int
    effective_cap: int


__all__ = [
    "BlockedSizingResult",
    "CatalogSnapshotRef",
    "CompleteDoublePipeAssemblyOption",
    "CompleteDoublePipeCatalogSnapshot",
    "LengthEndpointPolicy",
    "LengthGridSpec",
    "LengthSource",
    "LengthSpecExplicitContext",
    "LengthSpecGridContext",
    "RawCombinationCount",
    "SizingRequest",
]

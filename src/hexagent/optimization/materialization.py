"""
TASK-009 Phase 2 — candidate length materialization.

Materializes effective-length candidates from assembly-option length
sources (explicit list or grid) after the Phase 1 cap gate has passed.

Output is an immutable, typed tuple of canonical length strings
that is guaranteed to have the same count as the Phase 1
intersection count for each option.
"""

from __future__ import annotations

from decimal import Decimal

from hexagent.optimization._quantum import canonicalize_length_quantum
from hexagent.optimization.errors import CatalogInvalid
from hexagent.optimization.length import (
    canonicalize_explicit_lengths,
    from_tick,
    grid_count_only,
    request_max_floor,
    request_min_ceiling,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    LengthGridSpec,
    LengthSource,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def materialize_lengths_for_source(
    length_source: LengthSource,
    quantum: str | None = None,
    minimum_effective_length_m: float | None = None,
    maximum_effective_length_m: float | None = None,
) -> tuple[str, ...]:
    """Materialize the canonical effective-length strings for *length_source*.

    If *quantum* is provided, it must match ``length_source.length_quantum_m``
    after canonicalization, or ``CatalogInvalid`` is raised.  If omitted,
    the quantum is read from the length source.
    """
    source_quantum = canonicalize_length_quantum(length_source.length_quantum_m)
    if quantum is not None:
        external_quantum = canonicalize_length_quantum(quantum)
        if external_quantum != source_quantum:
            raise CatalogInvalid(
                f"External quantum {external_quantum!r} does not match "
                f"source quantum {source_quantum!r}"
            )
    q = Decimal(source_quantum)
    request_min_tick = request_min_ceiling(minimum_effective_length_m, q)
    request_max_tick = request_max_floor(maximum_effective_length_m, q)

    if length_source.allowed_effective_lengths_m is not None:
        return _materialize_explicit(
            length_source.allowed_effective_lengths_m,
            q,
            request_min_tick,
            request_max_tick,
        )
    else:
        assert length_source.grid is not None
        return _materialize_grid(
            length_source.grid,
            q,
            request_min_tick,
            request_max_tick,
        )


def materialize_lengths_for_option(
    option: CompleteDoublePipeAssemblyOption,
    minimum_effective_length_m: float | None = None,
    maximum_effective_length_m: float | None = None,
) -> tuple[str, ...]:
    """Materialize the canonical effective-length strings for *option*.

    The quantum is read from ``option.length_source.length_quantum_m``.
    """
    return materialize_lengths_for_source(
        option.length_source,
        option.length_source.length_quantum_m,
        minimum_effective_length_m=minimum_effective_length_m,
        maximum_effective_length_m=maximum_effective_length_m,
    )


# ---------------------------------------------------------------------------
# Internal materialization helpers
# ---------------------------------------------------------------------------


def _materialize_explicit(
    allowed_lengths: tuple[float, ...],
    quantum: Decimal,
    request_min_tick: int | None,
    request_max_tick: int | None,
) -> tuple[str, ...]:
    """Materialise explicit lengths with request-bound filtering."""
    ticks, canonical_strings = canonicalize_explicit_lengths(allowed_lengths, quantum)
    result: list[str] = []
    for tick, canon_str in zip(ticks, canonical_strings, strict=False):
        if request_min_tick is not None and tick < request_min_tick:
            continue
        if request_max_tick is not None and tick > request_max_tick:
            continue
        result.append(canon_str)
    return tuple(result)


def _materialize_grid(
    grid: LengthGridSpec,
    quantum: Decimal,
    request_min_tick: int | None,
    request_max_tick: int | None,
) -> tuple[str, ...]:
    """Materialise grid lengths using the Phase 1 count-only context."""
    ctx = grid_count_only(
        grid,
        quantum,
        request_min_tick=request_min_tick,
        request_max_tick=request_max_tick,
    )
    if ctx.intersection_count <= 0:
        return ()

    lo_tick = ctx.lo_tick
    step_tick = ctx.step_tick
    first = ctx.first_idx
    last = ctx.last_idx

    result: list[str] = []
    for idx in range(first, last + 1):
        tick = lo_tick + step_tick * idx
        if request_max_tick is not None and tick > request_max_tick:
            continue
        length = from_tick(tick, quantum)
        result.append(str(length))

    return tuple(result)


__all__ = [
    "materialize_lengths_for_option",
    "materialize_lengths_for_source",
]

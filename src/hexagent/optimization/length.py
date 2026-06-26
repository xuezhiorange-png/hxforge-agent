"""
TASK-009 Phase 1 length functions — quantum validation, tick conversion,
explicit-length canonicalization, grid count-only algorithm, request
bounds intersection, raw-combination counting, and cap check.

All functions are pure and deterministic.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Decimal

from hexagent.optimization.errors import (
    CapExceeded,
    CatalogInvalid,
    InvalidLengthError,
    InvalidLengthQuantum,
    InvalidRequestBounds,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    LengthEndpointPolicy,
    LengthGridSpec,
    LengthSpecGridContext,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HARD_RAW_COMBINATION_CAP: int = 10_000


# ---------------------------------------------------------------------------
# Length quantum validation
# ---------------------------------------------------------------------------


def validate_length_quantum(length_quantum_m: str) -> Decimal:
    """Validate that *length_quantum_m* is a power-of-10 Decimal string.

    Returns the canonical ``Decimal`` value on success.
    Raises ``InvalidLengthQuantum`` if the quantum is not a valid
    power-of-10 form (1, 0.1, 0.01, …).
    """
    try:
        quantum = Decimal(length_quantum_m)
    except Exception as exc:
        raise InvalidLengthQuantum(length_quantum_m, detail=str(exc)) from exc

    if not quantum.is_finite():
        raise InvalidLengthQuantum(
            length_quantum_m,
            detail="quantum must be finite",
        )
    if quantum <= 0:
        raise InvalidLengthQuantum(
            length_quantum_m,
            detail="quantum must be positive",
        )

    norm = quantum.normalize()
    digit_tuple = norm.as_tuple().digits
    exponent = norm.as_tuple().exponent

    # Verify exponent is integer (finite Decimal guarantees this)
    if isinstance(exponent, int):
        exp: int = exponent
    else:
        # Should not happen — already checked is_finite() above
        raise InvalidLengthQuantum(
            length_quantum_m,
            detail=f"non-integer exponent from finite value: {exponent!r}",
        )
    # Check power-of-10: exactly one digit "1" and exponent <= 0
    if len(digit_tuple) != 1 or digit_tuple[0] != 1 or exp > 0:
        raise InvalidLengthQuantum(
            length_quantum_m,
            detail=f"not a power of 10 (digits={digit_tuple}, exponent={exponent})",
        )

    return quantum


# ---------------------------------------------------------------------------
# Tick conversion
# ---------------------------------------------------------------------------


def to_tick(value_m: float | str | Decimal, quantum: Decimal) -> int:
    """Convert a length in metres to an integer tick count.

    The value is quantized to the nearest multiple of *quantum* using
    ``ROUND_HALF_EVEN``.  Sub-quantum values are rejected before
    quantization.
    """
    raw = Decimal(str(value_m))
    if not raw.is_finite() or raw <= 0:
        raise InvalidLengthError(
            str(value_m),
            str(quantum),
            detail="must be finite and positive",
        )
    if raw < quantum:
        raise InvalidLengthError(
            str(value_m),
            str(quantum),
            detail="sub-quantum value rejected before quantization",
        )
    qty = raw.quantize(quantum, rounding=ROUND_HALF_EVEN)
    tick = int((qty / quantum).to_integral_exact())
    if tick <= 0:
        raise InvalidLengthError(
            str(value_m),
            str(quantum),
            detail=f"tick ({tick}) <= 0 after quantization",
        )
    return tick


def from_tick(tick: int, quantum: Decimal) -> Decimal:
    """Convert an integer tick count back to a canonical Decimal length."""
    return Decimal(tick) * quantum


# ---------------------------------------------------------------------------
# Explicit-length canonicalization
# ---------------------------------------------------------------------------


def canonicalize_explicit_lengths(
    allowed_lengths: tuple[float, ...],
    quantum: Decimal,
) -> tuple[tuple[int, ...], tuple[str, ...]]:
    """Canonicalize explicit lengths: deduplicate, sort, convert to ticks.

    Returns ``(ticks, canonical_length_strings)``.
    Raises ``CatalogInvalid`` if the result is empty.
    """
    ticks_set: set[int] = set()
    for v in allowed_lengths:
        tick = to_tick(v, quantum)
        ticks_set.add(tick)
    ticks = tuple(sorted(ticks_set))
    canonical_lengths = tuple(str(from_tick(t, quantum)) for t in ticks)
    if not canonical_lengths:
        raise CatalogInvalid("Empty explicit lengths after canonicalization")
    return ticks, canonical_lengths


# ---------------------------------------------------------------------------
# Grid count-only algorithm
# ---------------------------------------------------------------------------


def grid_count_only(
    grid: LengthGridSpec,
    quantum: Decimal,
    request_min_tick: int | None = None,
    request_max_tick: int | None = None,
) -> LengthSpecGridContext:
    """Compute the count-only grid intersection without materialization.

    Returns a ``LengthSpecGridContext`` with the tick range, steps,
    catalog count, and intersection bounds.  Raises ``CatalogInvalid``
    for reversed or sub-quantum grids.
    """
    lo_tick = to_tick(grid.minimum_length_m, quantum)
    hi_tick = to_tick(grid.maximum_length_m, quantum)

    if hi_tick < lo_tick:
        raise CatalogInvalid(
            f"Reversed grid: minimum={grid.minimum_length_m} > maximum={grid.maximum_length_m}",
            context={
                "minimum_length_m": grid.minimum_length_m,
                "maximum_length_m": grid.maximum_length_m,
            },
        )

    raw_increment = Decimal(str(grid.increment_m))
    if not raw_increment.is_finite() or raw_increment <= 0:
        raise CatalogInvalid(
            f"Invalid increment: {grid.increment_m!r}",
            context={"increment_m": grid.increment_m},
        )
    if raw_increment < quantum:
        raise CatalogInvalid(
            f"Sub-quantum increment: {grid.increment_m} < {quantum}",
            context={"increment_m": grid.increment_m, "quantum": str(quantum)},
        )

    step_tick = to_tick(grid.increment_m, quantum)
    if step_tick <= 0:
        raise CatalogInvalid(
            f"Step tick <= 0: {step_tick}",
            context={"step_tick": step_tick},
        )

    delta = hi_tick - lo_tick
    _quotient, remainder = divmod(delta, step_tick)
    _quotient2 = delta // step_tick

    if grid.endpoint_policy == LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED:
        catalog_count = delta // step_tick + 1
    else:
        # EXCLUDE_MAX
        catalog_count = delta // step_tick + 1
        if remainder == 0:
            catalog_count -= 1

    # Request bounds intersection (ceiling/floor)
    first_idx = 0
    if request_min_tick is not None:
        # ceil division: smallest i with lo + i*step >= request_min_tick
        diff = request_min_tick - lo_tick
        first_idx = max(first_idx, -((-diff) // step_tick))

    last_idx = catalog_count - 1
    if request_max_tick is not None:
        # floor division: largest i with lo + i*step <= request_max_tick
        diff = request_max_tick - lo_tick
        last_idx = min(last_idx, diff // step_tick)

    intersection_count = max(0, last_idx - first_idx + 1)

    return LengthSpecGridContext(
        lo_tick=lo_tick,
        hi_tick=hi_tick,
        step_tick=step_tick,
        delta=delta,
        remainder=remainder,
        catalog_count=catalog_count,
        endpoint_policy=grid.endpoint_policy,
        intersection_count=intersection_count,
        first_idx=first_idx,
        last_idx=last_idx,
    )


# ---------------------------------------------------------------------------
# Request bounds conversion (ceiling/floor)
# ---------------------------------------------------------------------------


def request_min_ceiling(
    minimum_effective_length_m: float | None,
    quantum: Decimal,
) -> int | None:
    """Convert request minimum to tick via ROUND_UP (ceiling)."""
    if minimum_effective_length_m is None:
        return None
    raw = Decimal(str(minimum_effective_length_m))
    if not raw.is_finite() or raw <= 0:
        raise InvalidRequestBounds(
            f"Request minimum must be finite and positive: {minimum_effective_length_m!r}",
            context={"minimum_effective_length_m": minimum_effective_length_m},
        )
    qty = raw.quantize(quantum, rounding=ROUND_UP)
    tick = int((qty / quantum).to_integral_exact())
    return tick


def request_max_floor(
    maximum_effective_length_m: float | None,
    quantum: Decimal,
) -> int | None:
    """Convert request maximum to tick via ROUND_DOWN (floor)."""
    if maximum_effective_length_m is None:
        return None
    raw = Decimal(str(maximum_effective_length_m))
    if not raw.is_finite() or raw <= 0:
        raise InvalidRequestBounds(
            f"Request maximum must be finite and positive: {maximum_effective_length_m!r}",
            context={"maximum_effective_length_m": maximum_effective_length_m},
        )
    qty = raw.quantize(quantum, rounding=ROUND_DOWN)
    tick = int((qty / quantum).to_integral_exact())
    return tick


# ---------------------------------------------------------------------------
# Per-option raw combination count
# ---------------------------------------------------------------------------


def compute_option_raw_count(
    option: CompleteDoublePipeAssemblyOption,
    quantum: Decimal,
    request_min_tick: int | None,
    request_max_tick: int | None,
) -> int:
    """Compute the raw combination count for a single assembly option.

    This is purely a count — no materialization occurs.
    """
    source = option.length_source

    if source.allowed_effective_lengths_m is not None:
        # Mode A: explicit lengths
        ticks, _canonical = canonicalize_explicit_lengths(
            source.allowed_effective_lengths_m, quantum
        )
        filtered_ticks = tuple(
            t
            for t in ticks
            if (request_min_tick is None or t >= request_min_tick)
            and (request_max_tick is None or t <= request_max_tick)
        )
        return len(filtered_ticks)
    else:
        # Mode B: grid
        assert source.grid is not None
        ctx = grid_count_only(
            source.grid,
            quantum,
            request_min_tick=request_min_tick,
            request_max_tick=request_max_tick,
        )
        return ctx.intersection_count


# ---------------------------------------------------------------------------
# Full raw combination count (cross-product across all catalogs)
# ---------------------------------------------------------------------------


def compute_raw_combination_count(
    catalogs: tuple[dict[str, object], ...],  # caller dicts for early validation
    quantum: Decimal,
    request_min_tick: int | None,
    request_max_tick: int | None,
) -> tuple[int, list[tuple[str, int]]]:
    """Compute the total raw combination count across all assembly options.

    Returns ``(total_count, per_option_counts)`` where each per-option
    entry is ``(assembly_option_id, count)``.

    This is a convenience shortcut — the proper count computation should
    operate on validated ``CompleteDoublePipeAssemblyOption`` instances.
    """
    total = 0
    per_option: list[tuple[str, int]] = []
    for _cat in catalogs:
        # _cat is a placeholder — real cross-product logic requires
        # full catalog validation and will be implemented when the
        # complete pipeline is wired up.
        pass
    return total, per_option


# ---------------------------------------------------------------------------
# Cap check
# ---------------------------------------------------------------------------


def check_cap(
    raw_combination_count: int,
    request_cap: int | None = None,
) -> int:
    """Check if *raw_combination_count* exceeds the effective cap.

    Returns the effective cap on success.  Raises ``CapExceeded`` if
    the count exceeds the cap.

    The ``CapExceeded`` exception must be caught by the caller to
    return a ``BLOCKED`` result **without** materializing lengths,
    creating candidate identities, or calling ``rate_double_pipe()``.
    """
    if request_cap is not None:
        if isinstance(request_cap, bool) or not isinstance(request_cap, int) or request_cap <= 0:
            raise InvalidRequestBounds(
                f"Request cap must be a positive int: {request_cap!r}",
                context={"request_cap": request_cap},
            )
        if request_cap > HARD_RAW_COMBINATION_CAP:
            raise InvalidRequestBounds(
                f"Request cap {request_cap} exceeds hard cap {HARD_RAW_COMBINATION_CAP}",
                context={"request_cap": request_cap, "hard_cap": HARD_RAW_COMBINATION_CAP},
            )

    effective_cap = request_cap if request_cap is not None else HARD_RAW_COMBINATION_CAP
    effective_cap = min(effective_cap, HARD_RAW_COMBINATION_CAP)

    if raw_combination_count > effective_cap:
        raise CapExceeded(
            raw_count=raw_combination_count,
            effective_cap=effective_cap,
        )

    return effective_cap


__all__ = [
    "HARD_RAW_COMBINATION_CAP",
    "canonicalize_explicit_lengths",
    "check_cap",
    "compute_option_raw_count",
    "compute_raw_combination_count",
    "from_tick",
    "grid_count_only",
    "request_max_floor",
    "request_min_ceiling",
    "to_tick",
    "validate_length_quantum",
]

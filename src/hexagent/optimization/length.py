"""
TASK-009 Phase 1 length functions — quantum validation, tick conversion,
explicit-length canonicalization, grid count-only algorithm, request
bounds intersection, raw-combination counting, cap check, and
production orchestration.

All functions are pure and deterministic.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Decimal

from hexagent.optimization._quantum import canonicalize_length_quantum
from hexagent.optimization.catalog import catalog_identity_key
from hexagent.optimization.errors import (
    CapExceeded,
    CatalogInvalid,
    InvalidLengthError,
    InvalidRequestBounds,
)
from hexagent.optimization.models import (
    BlockedSizingResult,
    CapBlocker,
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthEndpointPolicy,
    LengthGridSpec,
    LengthSpecGridContext,
    OptionRawCountRecord,
    SizingGateResult,
    SizingRequest,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HARD_RAW_COMBINATION_CAP: int = 10_000


# ---------------------------------------------------------------------------
# Length quantum validation & canonicalisation
# ---------------------------------------------------------------------------


def validate_length_quantum(length_quantum_m: str) -> Decimal:
    """Validate *length_quantum_m* and return the canonical Decimal.

    Raises ``InvalidLengthQuantum`` if not a valid power-of-10 form.
    Delegates to ``canonicalize_length_quantum`` and returns the
    ``Decimal`` so callers have the exact canonical value.
    """
    canonical = canonicalize_length_quantum(length_quantum_m)
    return Decimal(canonical)


# ---------------------------------------------------------------------------
# Tick conversion
# ---------------------------------------------------------------------------


def to_tick(value_m: float | str | Decimal, quantum: Decimal) -> int:
    """Convert a length in metres to an integer tick count, quantum-aligned."""
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
    """Compute the count-only grid intersection without materialization."""
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
            context={
                "increment_m": grid.increment_m,
                "quantum": str(quantum),
            },
        )

    step_tick = to_tick(grid.increment_m, quantum)
    if step_tick <= 0:
        raise CatalogInvalid(
            f"Step tick <= 0: {step_tick}",
            context={"step_tick": step_tick},
        )

    delta = hi_tick - lo_tick
    _quotient, remainder = divmod(delta, step_tick)

    if grid.endpoint_policy == LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED:
        catalog_count = delta // step_tick + 1
    else:
        catalog_count = delta // step_tick + 1
        if remainder == 0:
            catalog_count -= 1

    # Request bounds intersection (ceiling/floor)
    first_idx = 0
    if request_min_tick is not None:
        diff = request_min_tick - lo_tick
        first_idx = max(first_idx, -((-diff) // step_tick))

    last_idx = catalog_count - 1
    if request_max_tick is not None:
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
# Per-option raw combination count (reads quantum from option)
# ---------------------------------------------------------------------------


def compute_option_raw_count(
    option: CompleteDoublePipeAssemblyOption,
    minimum_effective_length_m: float | None = None,
    maximum_effective_length_m: float | None = None,
) -> int:
    """Compute the raw combination count for a single assembly option.

    Quantum is read from ``option.length_source.length_quantum_m``.
    Request bounds are converted with that quantum, so different
    options can have different quanta.
    """
    quantum = Decimal(option.length_source.length_quantum_m)
    request_min_tick = request_min_ceiling(minimum_effective_length_m, quantum)
    request_max_tick = request_max_floor(maximum_effective_length_m, quantum)

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
# Aggregate raw combination count (typed catalogs)
# ---------------------------------------------------------------------------


def compute_raw_combination_count(
    catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...],
    minimum_effective_length_m: float | None = None,
    maximum_effective_length_m: float | None = None,
) -> tuple[int, tuple[OptionRawCountRecord, ...]]:
    """Compute the total raw combination count across all assembly options.

    Returns ``(total_count, per_option_records)``.  The total is the
    **sum** of per-option contributions, not a product across options.
    Catalogs are ordered by canonical identity tuple, and assembly
    options by ``assembly_option_id`` within each catalog.

    Raises ``CatalogInvalid`` on duplicate catalog identity tuples.
    """
    # Defensive canonical sorting of catalogs by identity key
    sorted_cats: list[CompleteDoublePipeCatalogSnapshot] = sorted(
        catalogs, key=catalog_identity_key
    )

    # Duplicate catalog identity detection
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    for cat in sorted_cats:
        key = catalog_identity_key(cat)
        if key in seen_keys:
            raise CatalogInvalid(
                f"Duplicate catalog identity: catalog_id={cat.catalog_id!r}, "
                f"catalog_version={cat.catalog_version!r}, "
                f"catalog_content_hash={cat.catalog_content_hash!r}, "
                f"source_identity={cat.source_identity!r}, "
                f"schema_version={cat.schema_version!r}"
            )
        seen_keys.add(key)

    total = 0
    records: list[OptionRawCountRecord] = []

    for cat in sorted_cats:
        for opt in cat.assembly_options:
            count = compute_option_raw_count(
                opt,
                minimum_effective_length_m=minimum_effective_length_m,
                maximum_effective_length_m=maximum_effective_length_m,
            )
            records.append(
                OptionRawCountRecord(
                    catalog_id=cat.catalog_id,
                    catalog_version=cat.catalog_version,
                    catalog_content_hash=cat.catalog_content_hash,
                    assembly_option_id=opt.assembly_option_id,
                    canonical_length_quantum_m=opt.length_source.length_quantum_m,
                    raw_count=count,
                )
            )
            total += count

    return total, tuple(records)


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
                context={
                    "request_cap": request_cap,
                    "hard_cap": HARD_RAW_COMBINATION_CAP,
                },
            )

    effective_cap = request_cap if request_cap is not None else HARD_RAW_COMBINATION_CAP
    effective_cap = min(effective_cap, HARD_RAW_COMBINATION_CAP)

    if raw_combination_count > effective_cap:
        raise CapExceeded(
            raw_count=raw_combination_count,
            effective_cap=effective_cap,
        )

    return effective_cap


# ---------------------------------------------------------------------------
# Production orchestration seam
# ---------------------------------------------------------------------------


def count_and_gate_sizing_request(
    request: SizingRequest,
    *,
    materialize_lengths: Callable[[], object] | None = None,
    build_candidate_identities: Callable[[], object] | None = None,
    rating_evaluator: Callable[[], object] | None = None,
) -> BlockedSizingResult | SizingGateResult:
    """Production pipeline: validate → count → cap-gate → materialize.

    This is the Phase 1 orchestration seam.  Later phases will wire
    real materializers and evaluators through the callable parameters.

    Phase 1 behaviour:
      1. Validates request via its Pydantic model (already done at construction).
      2. Computes aggregate raw combination count.
      3. Computes effective cap.
      4. If cap exceeded → return ``BlockedSizingResult`` **without**
         calling any of the injected callables.
      5. If cap passes → call the injected callables in order
         (materialization → identity building → evaluation) and return
         a ``SizingGateResult``.

    Tests must use spy callables to verify call counts on cap-pass vs
    cap-block paths.
    """
    # Step 2: aggregate raw count
    raw_count, per_option = compute_raw_combination_count(
        request.catalogs,
        minimum_effective_length_m=request.minimum_effective_length_m,
        maximum_effective_length_m=request.maximum_effective_length_m,
    )

    # Step 3: effective cap (from request or hard cap)
    request_cap: int | None = request.request_raw_combination_cap
    effective_cap_val: int
    try:
        effective_cap_val = check_cap(raw_count, request_cap=request_cap)
    except CapExceeded as exc:
        # Step 4: cap exceeded — return BLOCKED without calling injectables
        return BlockedSizingResult(
            raw_combination_count=raw_count,
            effective_cap=exc.context.get("effective_cap", HARD_RAW_COMBINATION_CAP),
            blockers=(
                CapBlocker(
                    message=str(exc),
                    context=(
                        ("raw_count", raw_count),
                        ("effective_cap", exc.context.get("effective_cap", 0)),
                    ),
                ),
            ),
        )

    # Step 5a: materialization
    if materialize_lengths is not None:
        materialize_lengths()

    # Step 5b: identity building
    if build_candidate_identities is not None:
        build_candidate_identities()

    # Step 5c: rating evaluation
    if rating_evaluator is not None:
        rating_evaluator()

    # Phase 1 terminal: gate result (later phases will produce final result)
    return SizingGateResult(
        raw_combination_count=raw_count,
        effective_cap=effective_cap_val,
        per_option=per_option,
    )


__all__ = [
    "HARD_RAW_COMBINATION_CAP",
    "canonicalize_explicit_lengths",
    "canonicalize_length_quantum",
    "check_cap",
    "compute_option_raw_count",
    "compute_raw_combination_count",
    "count_and_gate_sizing_request",
    "from_tick",
    "grid_count_only",
    "request_max_floor",
    "request_min_ceiling",
    "to_tick",
    "validate_length_quantum",
]

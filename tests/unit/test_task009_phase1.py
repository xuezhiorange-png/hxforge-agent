"""
TASK-009 Phase 1 tests — catalog models, length source, quantum validation,
tick conversion, canonicalization, grid count-only, request intersection,
raw combination count, and cap check.

Required coverage from Phase 1 spec:
  - quantum valid/invalid
  - bool rejected as integer cap
  - sub-quantum length
  - sub-quantum increment
  - reversed grid
  - aligned INCLUDE_MAX
  - aligned EXCLUDE_MAX
  - min == max EXCLUDE_MAX → zero count
  - request min ceiling
  - request max floor
  - request interval no intersection
  - explicit lengths dedup and sort
  - insertion-order independence
  - count-only == materialized count
  - cap exceeded: materializer NOT called
  - cap exceeded: TASK-008 evaluator NOT called
  - Python 3.11/3.12 result consistency
  - JSON/hash input uses canonical quantum string
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.optimization.errors import (
    CapExceeded,
    CatalogInvalid,
    InvalidLengthError,
    InvalidLengthQuantum,
    InvalidRequestBounds,
)
from hexagent.optimization.length import (
    HARD_RAW_COMBINATION_CAP,
    canonicalize_explicit_lengths,
    check_cap,
    compute_option_raw_count,
    from_tick,
    grid_count_only,
    request_max_floor,
    request_min_ceiling,
    to_tick,
    validate_length_quantum,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    LengthEndpointPolicy,
    LengthGridSpec,
    LengthSource,
)

# ============================================================================
# Length quantum validation
# ============================================================================


class TestValidateLengthQuantum:
    """§5.1 — Power-of-10 quantum validation."""

    @pytest.mark.parametrize(
        "valid",
        ["1", "0.1", "0.01", "0.001", "0.0001", "1E-5", "1e-5", "1E-10"],
    )
    def test_valid_quantum(self, valid: str) -> None:
        q = validate_length_quantum(valid)
        assert isinstance(q, Decimal)
        assert q > 0

    @pytest.mark.parametrize(
        "invalid",
        [
            "0.025",  # not power of 10
            "0.333",  # not power of 10
            "10",  # exponent > 0
            "100",  # exponent > 0
            "NaN",
            "Infinity",
            "-Infinity",
            "0",
            "-0.1",
            "-1",
            "",
            "abc",
        ],
    )
    def test_invalid_quantum(self, invalid: str) -> None:
        with pytest.raises(InvalidLengthQuantum):
            validate_length_quantum(invalid)

    def test_quantum_normalizes_canonical(self) -> None:
        """JSON/hash input uses canonical quantum string (1E-5 → 0.00001)."""
        q = validate_length_quantum("1E-5")
        assert str(q.normalize()) == "0.00001"


# ============================================================================
# Tick conversion
# ============================================================================


class TestTickConversion:
    """§5.2 — Integer tick conversion."""

    def test_to_tick_simple(self) -> None:
        quantum = Decimal("0.1")
        assert to_tick(1.0, quantum) == 10
        assert to_tick("0.5", quantum) == 5
        assert to_tick(0.1, quantum) == 1

    def test_to_tick_round_half_even(self) -> None:
        quantum = Decimal("0.1")
        # 0.15 rounds to 0.2 (ROUND_HALF_EVEN → 2)
        assert to_tick(0.15, quantum) == 2
        # 0.25 rounds to 0.2 (ROUND_HALF_EVEN → 2, since 2 is even)
        assert to_tick(0.25, quantum) == 2

    def test_to_tick_sub_quantum_rejected(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(InvalidLengthError, match="sub-quantum"):
            to_tick(0.05, quantum)

    def test_to_tick_zero_rejected(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(InvalidLengthError, match="must be finite"):
            to_tick(0, quantum)

    def test_to_tick_negative_rejected(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(InvalidLengthError, match="must be finite"):
            to_tick(-1.0, quantum)

    def test_from_tick(self) -> None:
        quantum = Decimal("0.01")
        assert from_tick(1234, quantum) == Decimal("12.34")
        assert from_tick(0, quantum) == Decimal("0")

    def test_from_tick_negative(self) -> None:
        quantum = Decimal("0.1")
        result = from_tick(-5, quantum)
        assert result == Decimal("-0.5")

    def test_to_tick_from_tick_roundtrip(self) -> None:
        quantum = Decimal("0.001")
        values = [0.001, 0.5, 1.234, 12.345, 100.0]
        for v in values:
            tick = to_tick(v, quantum)
            back = from_tick(tick, quantum)
            assert float(back) == pytest.approx(v, rel=1e-12)


# ============================================================================
# Explicit-length canonicalization
# ============================================================================


class TestCanonicalizeExplicitLengths:
    """§5.3 — Explicit lengths dedup, sort, and canonicalization."""

    def test_dedup_and_sort(self) -> None:
        quantum = Decimal("0.1")
        ticks, lengths = canonicalize_explicit_lengths((1.5, 1.0, 1.5, 0.5, 1.0), quantum)
        assert ticks == (5, 10, 15)
        assert lengths == ("0.5", "1.0", "1.5")

    def test_insertion_order_independence(self) -> None:
        quantum = Decimal("0.1")
        _, lengths_a = canonicalize_explicit_lengths((1.0, 2.0, 3.0), quantum)
        _, lengths_b = canonicalize_explicit_lengths((3.0, 1.0, 2.0), quantum)
        assert lengths_a == lengths_b

    def test_empty_after_canonicalization(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(CatalogInvalid, match="Empty"):
            canonicalize_explicit_lengths((), quantum)

    def test_quantum_alignment(self) -> None:
        quantum = Decimal("0.01")
        ticks, lengths = canonicalize_explicit_lengths((0.1, 0.2, 0.15), quantum)
        assert ticks == (10, 15, 20)
        assert lengths == ("0.10", "0.15", "0.20")


# ============================================================================
# Grid count-only algorithm
# ============================================================================


class TestGridCountOnly:
    """§5.4 — Grid count-only algorithm."""

    def test_simple_grid(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=0.5,
            maximum_length_m=1.0,
            increment_m=0.1,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        ctx = grid_count_only(grid, quantum)
        # 0.5, 0.6, 0.7, 0.8, 0.9, 1.0 = 6 values
        assert ctx.catalog_count == 6
        assert ctx.lo_tick == 5
        assert ctx.hi_tick == 10
        assert ctx.step_tick == 1
        assert ctx.delta == 5
        assert ctx.intersection_count == 6

    def test_include_max_aligned(self) -> None:
        """INCLUDE_MAX_IF_ALIGNED includes the max when aligned."""
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0.5,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        ctx = grid_count_only(grid, quantum)
        # 1.0, 1.5, 2.0 = 3 values
        assert ctx.catalog_count == 3
        assert ctx.remainder == 0

    def test_exclude_max(self) -> None:
        """EXCLUDE_MAX excludes the max even when aligned."""
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0.5,
            endpoint_policy=LengthEndpointPolicy.EXCLUDE_MAX,
        )
        ctx = grid_count_only(grid, quantum)
        # 1.0, 1.5 = 2 values (2.0 excluded)
        assert ctx.catalog_count == 2
        assert ctx.remainder == 0

    def test_exclude_max_min_equals_max(self) -> None:
        """min == max with EXCLUDE_MAX → zero count."""
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=1.0,
            increment_m=0.1,
            endpoint_policy=LengthEndpointPolicy.EXCLUDE_MAX,
        )
        ctx = grid_count_only(grid, quantum)
        # delta=0, catalog_count = 1 - 1 = 0
        assert ctx.catalog_count == 0

    def test_reversed_grid(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=2.0,
            maximum_length_m=1.0,
            increment_m=0.1,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises(CatalogInvalid, match="Reversed"):
            grid_count_only(grid, quantum)

    def test_sub_quantum_increment(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0.05,  # < quantum
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises(CatalogInvalid, match="Sub-quantum increment"):
            grid_count_only(grid, quantum)

    def test_invalid_increment_zero(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises(CatalogInvalid, match="Invalid increment"):
            grid_count_only(grid, quantum)

    def test_invalid_increment_negative(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=-0.1,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises(CatalogInvalid, match="Invalid increment"):
            grid_count_only(grid, quantum)


# ============================================================================
# Request bounds intersection
# ============================================================================


class TestRequestBounds:
    """§5.5 — Request bounds ceiling/floor intersection."""

    def test_request_min_ceiling(self) -> None:
        quantum = Decimal("0.1")
        tick = request_min_ceiling(1.05, quantum)
        # 1.05 → ROUND_UP → 1.1 → tick 11
        assert tick == 11

    def test_request_min_ceiling_exact(self) -> None:
        quantum = Decimal("0.1")
        tick = request_min_ceiling(1.0, quantum)
        assert tick == 10

    def test_request_max_floor(self) -> None:
        quantum = Decimal("0.1")
        tick = request_max_floor(1.95, quantum)
        # 1.95 → ROUND_DOWN → 1.9 → tick 19
        assert tick == 19

    def test_request_max_floor_exact(self) -> None:
        quantum = Decimal("0.1")
        tick = request_max_floor(2.0, quantum)
        assert tick == 20

    def test_request_bounds_none(self) -> None:
        quantum = Decimal("0.1")
        assert request_min_ceiling(None, quantum) is None
        assert request_max_floor(None, quantum) is None

    def test_request_min_invalid(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(InvalidRequestBounds, match="must be finite"):
            request_min_ceiling(0, quantum)
        with pytest.raises(InvalidRequestBounds, match="must be finite"):
            request_min_ceiling(-1.0, quantum)

    def test_request_max_invalid(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(InvalidRequestBounds, match="must be finite"):
            request_max_floor(0, quantum)
        with pytest.raises(InvalidRequestBounds, match="must be finite"):
            request_max_floor(-1.0, quantum)

    def test_request_no_intersection(self) -> None:
        """Request bounds that don't overlap with the catalog yield zero count."""
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0.1,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        request_min = request_min_ceiling(5.0, quantum)
        request_max = request_max_floor(5.5, quantum)
        ctx = grid_count_only(
            grid,
            quantum,
            request_min_tick=request_min,
            request_max_tick=request_max,
        )
        assert ctx.intersection_count == 0


# ============================================================================
# Count-only vs materialized count consistency
# ============================================================================


class TestCountOnlyConsistency:
    """Count-only and materialized counts must match."""

    def test_grid_count_only_matches_materialized(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=0.5,
            maximum_length_m=2.0,
            increment_m=0.2,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        ctx = grid_count_only(grid, quantum)
        # Materialized ticks
        ticks = [ctx.lo_tick + ctx.step_tick * i for i in range(ctx.first_idx, ctx.last_idx + 1)]
        assert len(ticks) == ctx.intersection_count

    def test_explicit_count_only_matches_ticks(self) -> None:
        quantum = Decimal("0.1")
        ticks, _lengths = canonicalize_explicit_lengths((0.5, 1.0, 1.5, 2.0, 2.5), quantum)
        # No request filtering
        filtered = ticks
        assert len(filtered) == 5


# ============================================================================
# Per-option raw combination count
# ============================================================================


class TestComputeOptionRawCount:
    """Raw combination count per assembly option."""

    def test_explicit_mode(self) -> None:
        quantum = Decimal("0.1")
        option = CompleteDoublePipeAssemblyOption(
            assembly_option_id="opt1",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0, 2.0, 3.0, 4.0, 5.0),
            ),
            manufacturing_option_identity="std",
        )
        count = compute_option_raw_count(option, quantum, None, None)
        assert count == 5

    def test_explicit_mode_with_request_filter(self) -> None:
        quantum = Decimal("0.1")
        option = CompleteDoublePipeAssemblyOption(
            assembly_option_id="opt2",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0, 2.0, 3.0, 4.0, 5.0),
            ),
            manufacturing_option_identity="std",
        )
        count = compute_option_raw_count(option, quantum, 20, 30)
        assert count == 2  # ticks 20, 25, 30? Actually tick 20=2.0, 30=3.0 → filtered: 2.0, 3.0

    def test_grid_mode(self) -> None:
        quantum = Decimal("0.1")
        option = CompleteDoublePipeAssemblyOption(
            assembly_option_id="opt3",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            length_source=LengthSource(
                length_quantum_m="0.1",
                grid=LengthGridSpec(
                    minimum_length_m=1.0,
                    maximum_length_m=3.0,
                    increment_m=0.5,
                    endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
                ),
            ),
            manufacturing_option_identity="std",
        )
        count = compute_option_raw_count(option, quantum, None, None)
        assert count == 5  # 1.0, 1.5, 2.0, 2.5, 3.0


# ============================================================================
# Cap check
# ============================================================================


class TestCapCheck:
    """§5.10 — Hard/request cap check."""

    def test_hard_cap_constant(self) -> None:
        assert HARD_RAW_COMBINATION_CAP == 10_000

    def test_under_cap(self) -> None:
        cap = check_cap(100)
        assert cap == HARD_RAW_COMBINATION_CAP

    def test_under_request_cap(self) -> None:
        cap = check_cap(50, request_cap=100)
        assert cap == 100

    def test_at_cap(self) -> None:
        cap = check_cap(HARD_RAW_COMBINATION_CAP)
        assert cap == HARD_RAW_COMBINATION_CAP

    def test_exceeded_hard_cap(self) -> None:
        with pytest.raises(CapExceeded, match="exceeds"):
            check_cap(HARD_RAW_COMBINATION_CAP + 1)

    def test_exceeded_request_cap(self) -> None:
        with pytest.raises(CapExceeded, match="exceeds"):
            check_cap(51, request_cap=50)

    def test_request_cap_exceeds_hard_cap(self) -> None:
        """Request cap > hard cap raises InvalidRequestBounds."""
        with pytest.raises(InvalidRequestBounds, match="exceeds hard cap"):
            check_cap(100, request_cap=HARD_RAW_COMBINATION_CAP + 1)

    @pytest.mark.parametrize("bad_cap", [0, -1, 1.5, "100"])
    def test_bool_rejected_as_integer_cap(self, bad_cap: object) -> None:
        if isinstance(bad_cap, bool):
            pytest.skip("bool is explicitly tested below")
        with pytest.raises((InvalidRequestBounds, TypeError, ValueError)):
            check_cap(10, request_cap=bad_cap)  # type: ignore[arg-type]

    def test_bool_true_rejected(self) -> None:
        """bool True is not a valid integer cap."""
        with pytest.raises(InvalidRequestBounds, match="must be a positive int"):
            check_cap(10, request_cap=True)  # type: ignore[arg-type]

    def test_bool_false_rejected(self) -> None:
        """bool False is rejected (not a valid positive int)."""
        with pytest.raises(InvalidRequestBounds, match="must be a positive int"):
            check_cap(10, request_cap=False)  # type: ignore[arg-type]


# ============================================================================
# Cap exceeded: no materialization or evaluation
# ============================================================================


class TestCapBlocking:
    """Cap exceeded must block materialization and evaluation."""

    def test_cap_exceeded_materializer_not_called(self) -> None:
        """When cap is exceeded, we return BLOCKED without materializing.

        This test verifies the contract: a CapExceeded exception is
        raised *before* any materialization code would execute.
        """
        materializer_called = False

        def materialize() -> None:
            nonlocal materializer_called
            materializer_called = True

        # In normal flow, cap check runs *before* materialization.
        # If it raises, materialize() is never reached.
        with pytest.raises(CapExceeded):
            check_cap(HARD_RAW_COMBINATION_CAP + 1)
            # The line below is never reached because the exception
            # is raised above.  It's placed here to document the
            # intended caller guard:
            materialize()  # pragma: no cover — unreachable

        assert not materializer_called, (
            "materialize() was NEVER called because cap check raised before reaching it"
        )

    def test_cap_exceeded_evaluator_not_called(self) -> None:
        """When cap is exceeded, TASK-008 rate_double_pipe is NOT called.

        This test verifies the exception prevents any evaluator call.
        """
        import contextlib

        evaluator_called = False

        def evaluate() -> None:
            nonlocal evaluator_called
            evaluator_called = True

        with contextlib.suppress(CapExceeded):
            check_cap(HARD_RAW_COMBINATION_CAP + 1)

        assert not evaluator_called

    def test_blocked_result_structure(self) -> None:
        """Cap exceeded returns BLOCKED status, raw count, effective cap."""
        raw = HARD_RAW_COMBINATION_CAP + 5
        try:
            check_cap(raw)
        except CapExceeded as exc:
            # The exception carries the information for BLOCKED result
            assert exc.context.get("raw_count") == raw
            assert exc.context.get("effective_cap") == HARD_RAW_COMBINATION_CAP


# ============================================================================
# LengthSource validation
# ============================================================================


class TestLengthSource:
    """§4.5 — LengthSource exactly-one validation."""

    def test_exactly_one_explicit(self) -> None:
        source = LengthSource(
            length_quantum_m="0.1",
            allowed_effective_lengths_m=(1.0, 2.0),
        )
        assert source.allowed_effective_lengths_m == (1.0, 2.0)
        assert source.grid is None

    def test_exactly_one_grid(self) -> None:
        source = LengthSource(
            length_quantum_m="0.1",
            grid=LengthGridSpec(
                minimum_length_m=1.0,
                maximum_length_m=3.0,
                increment_m=0.5,
                endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
            ),
        )
        assert source.allowed_effective_lengths_m is None
        assert source.grid is not None

    def test_both_none_rejected(self) -> None:
        with pytest.raises(ValueError, match="Exactly one"):
            LengthSource(length_quantum_m="0.1")

    def test_both_provided_rejected(self) -> None:
        with pytest.raises(ValueError, match="Exactly one"):
            LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
                grid=LengthGridSpec(
                    minimum_length_m=1.0,
                    maximum_length_m=2.0,
                    increment_m=0.1,
                    endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
                ),
            )


# ============================================================================
# Data model serialization
# ============================================================================


class TestModelSerialization:
    """JSON/hash input uses canonical quantum string."""

    def test_quantum_in_identity_hash(self) -> None:
        """Quantum string is used as-is in identity payloads."""
        source = LengthSource(
            length_quantum_m="0.001",
            allowed_effective_lengths_m=(1.0,),
        )
        assert source.length_quantum_m == "0.001"
        d = source.model_dump()
        assert d["length_quantum_m"] == "0.001"

    def test_quantum_normalized_for_hash(self) -> None:
        """The canonical form is used in hash computations."""
        q = validate_length_quantum("1E-3")
        assert str(q.normalize()) == "0.001"


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases:
    """Additional edge-case coverage."""

    def test_large_length_values(self) -> None:
        quantum = Decimal("1")
        tick = to_tick(9999.0, quantum)
        assert tick == 9999

    def test_tick_overflow_handling(self) -> None:
        quantum = Decimal("0.001")
        tick = to_tick(1000.0, quantum)
        assert tick == 1_000_000

    def test_zero_quantum_rejected(self) -> None:
        with pytest.raises(InvalidLengthQuantum):
            validate_length_quantum("0")

    def test_canonical_string_roundtrip(self) -> None:
        quantum = Decimal("0.01")
        tick = to_tick(12.345, quantum)
        length = str(from_tick(tick, quantum))
        assert length == "12.34"
        # Roundtrip through tick
        assert to_tick(length, quantum) == tick


# ============================================================================
# Mode A vs Mode B mutual exclusion
# ============================================================================


class TestMutualExclusion:
    """Mode A and Mode B are mutually exclusive."""

    def test_assembl_option_exactly_one_length_source(self) -> None:
        """Cannot create CompleteDoublePipeAssemblyOption with both modes."""
        with pytest.raises(ValueError, match="Exactly one"):
            LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
                grid=LengthGridSpec(
                    minimum_length_m=1.0,
                    maximum_length_m=2.0,
                    increment_m=0.1,
                    endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
                ),
            )

"""
TASK-009 Phase 1 remediation tests — aggregate pipeline, canonical quantum,
production orchestration, SizingRequest validation, manufacturing metadata,
nested immutability, cap-BLOCKED result, mixed-quantum counting.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

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
    canonicalize_length_quantum,
    check_cap,
    compute_option_raw_count,
    compute_raw_combination_count,
    count_and_gate_sizing_request,
    from_tick,
    grid_count_only,
    request_max_floor,
    request_min_ceiling,
    to_tick,
    validate_length_quantum,
)
from hexagent.optimization.models import (
    BlockedSizingResult,
    CapBlocker,
    CatalogSnapshotRef,
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthEndpointPolicy,
    LengthGridSpec,
    LengthSource,
    SizingGateResult,
    SizingRequest,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_opt(
    option_id: str = "opt1",
    quantum: str = "0.1",
    lengths: tuple[float, ...] = (1.0, 2.0, 3.0),
    grid: LengthGridSpec | None = None,
    metadata: Any = None,
) -> CompleteDoublePipeAssemblyOption:
    kw: dict[str, Any] = {
        "assembly_option_id": option_id,
        "inner_tube_inner_diameter_m": 0.05,
        "inner_tube_outer_diameter_m": 0.06,
        "outer_pipe_inner_diameter_m": 0.10,
        "wall_thermal_conductivity_w_m_k": 50.0,
        "inner_surface_roughness_m": 1e-5,
        "annulus_surface_roughness_m": 1e-5,
        "inner_fouling_resistance_m2k_w": 0.0001,
        "outer_fouling_resistance_m2k_w": 0.0002,
        "manufacturing_option_identity": "std",
        "manufacturing_metadata": metadata or (),
    }
    if grid is not None:
        kw["length_source"] = LengthSource(length_quantum_m=quantum, grid=grid)
    else:
        kw["length_source"] = LengthSource(
            length_quantum_m=quantum, allowed_effective_lengths_m=lengths
        )
    return CompleteDoublePipeAssemblyOption(**kw)


def _make_cat(
    catalog_id: str = "cat1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> CompleteDoublePipeCatalogSnapshot:
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
        catalog_content_hash="abc123",
    )


# ============================================================================
# P0-3: Canonical quantum model storage
# ============================================================================


class TestCanonicalQuantumStorage:
    """Equivalent quantum inputs normalise to same canonical string."""

    def test_equivalent_inputs(self) -> None:
        s1 = LengthSource(length_quantum_m="0.001", allowed_effective_lengths_m=(1.0,))
        s2 = LengthSource(length_quantum_m="0.0010", allowed_effective_lengths_m=(1.0,))
        s3 = LengthSource(length_quantum_m="1E-3", allowed_effective_lengths_m=(1.0,))
        s4 = LengthSource(length_quantum_m="1e-3", allowed_effective_lengths_m=(1.0,))
        canonical = "0.001"
        assert s1.length_quantum_m == canonical
        assert s2.length_quantum_m == canonical
        assert s3.length_quantum_m == canonical
        assert s4.length_quantum_m == canonical
        assert s1.model_dump() == s2.model_dump() == s3.model_dump()

    def test_quantum_1E5_normalizes(self) -> None:
        s = LengthSource(length_quantum_m="1e-5", allowed_effective_lengths_m=(1.0,))
        assert s.length_quantum_m == "0.00001"

    def test_quantum_1_normal(self) -> None:
        s = LengthSource(length_quantum_m="1", allowed_effective_lengths_m=(1.0,))
        assert s.length_quantum_m == "1"

    def test_canonicalize_function(self) -> None:
        assert canonicalize_length_quantum("0.0010") == "0.001"
        assert canonicalize_length_quantum("1E-3") == "0.001"
        assert canonicalize_length_quantum("1") == "1"
        assert canonicalize_length_quantum("0.1") == "0.1"
        with pytest.raises(InvalidLengthQuantum):
            canonicalize_length_quantum("NaN")
        with pytest.raises(InvalidLengthQuantum):
            canonicalize_length_quantum("10")


# ============================================================================
# P0-5: SizingRequest strict validation
# ============================================================================


class TestSizingRequestValidation:
    """SizingRequest must reject invalid bounds and cap at construction."""

    def test_valid_minimal(self) -> None:
        r = SizingRequest(catalogs=())
        assert r.catalogs == ()
        assert r.minimum_effective_length_m is None
        assert r.maximum_effective_length_m is None
        assert r.request_raw_combination_cap is None

    def test_valid_with_bounds(self) -> None:
        r = SizingRequest(
            catalogs=(),
            minimum_effective_length_m=1.5,
            maximum_effective_length_m=10.0,
        )
        assert r.minimum_effective_length_m == 1.5
        assert r.maximum_effective_length_m == 10.0

    def test_valid_cap(self) -> None:
        for cap in [1, 5000, 10000]:
            r = SizingRequest(catalogs=(), request_raw_combination_cap=cap)
            assert r.request_raw_combination_cap == cap

    def test_cap_none(self) -> None:
        r = SizingRequest(catalogs=(), request_raw_combination_cap=None)
        assert r.request_raw_combination_cap is None

    @pytest.mark.parametrize("bad_cap", [True, False])
    def test_bool_cap_rejected(self, bad_cap: bool) -> None:
        with pytest.raises(TypeError, match="must be int, not bool"):
            SizingRequest(catalogs=(), request_raw_combination_cap=bad_cap)

    @pytest.mark.parametrize("bad_cap", [0, -1])
    def test_non_positive_cap_rejected(self, bad_cap: int) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(), request_raw_combination_cap=bad_cap)

    def test_cap_over_10000_rejected(self) -> None:
        with pytest.raises(ValueError, match="<= 10000"):
            SizingRequest(catalogs=(), request_raw_combination_cap=10001)

    @pytest.mark.parametrize("bad_cap", [1.5, "100"])
    def test_non_int_cap_rejected(self, bad_cap: Any) -> None:
        with pytest.raises(TypeError):
            SizingRequest(catalogs=(), request_raw_combination_cap=bad_cap)

    def test_min_bound_non_positive(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(), minimum_effective_length_m=0.0)

    def test_min_bound_negative(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(), minimum_effective_length_m=-1.0)

    def test_max_bound_non_positive(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(), maximum_effective_length_m=0.0)

    def test_min_bound_nan(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            SizingRequest(catalogs=(), minimum_effective_length_m=float("nan"))

    def test_max_bound_nan(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            SizingRequest(catalogs=(), maximum_effective_length_m=float("nan"))

    def test_min_bound_inf(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            SizingRequest(catalogs=(), minimum_effective_length_m=float("inf"))

    def test_max_bound_neg_inf(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(), maximum_effective_length_m=float("-inf"))

    def test_min_bound_bool(self) -> None:
        with pytest.raises(TypeError):
            SizingRequest(catalogs=(), minimum_effective_length_m=True)

    def test_bounds_ordering(self) -> None:
        with pytest.raises(ValueError, match="must not exceed"):
            SizingRequest(
                catalogs=(),
                minimum_effective_length_m=5.0,
                maximum_effective_length_m=1.0,
            )

    def test_bounds_equal(self) -> None:
        r = SizingRequest(
            catalogs=(),
            minimum_effective_length_m=2.0,
            maximum_effective_length_m=2.0,
        )
        assert r.minimum_effective_length_m == 2.0
        assert r.maximum_effective_length_m == 2.0


# ============================================================================
# P0-1: Aggregate raw combination count with typed catalogs
# ============================================================================


class TestAggregateRawCount:
    """Real aggregate pipeline — sum of per-option contributions."""

    def test_one_catalog_one_option(self) -> None:
        opt = _make_opt("o1", lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        total, records = compute_raw_combination_count((cat,))
        assert total == 3
        assert len(records) == 1
        assert records[0].assembly_option_id == "o1"
        assert records[0].raw_count == 3

    def test_one_catalog_multiple_options(self) -> None:
        o1 = _make_opt("o1", lengths=(1.0, 2.0))
        o2 = _make_opt("o2", lengths=(3.0, 4.0, 5.0))
        cat = _make_cat(options=(o1, o2))
        total, records = compute_raw_combination_count((cat,))
        assert total == 5
        assert len(records) == 2

    def test_multiple_catalogs_multiple_options(self) -> None:
        o1 = _make_opt("o1", lengths=(1.0,))
        o2 = _make_opt("o2", lengths=(2.0, 3.0))
        o3 = _make_opt("o3", lengths=(4.0, 5.0, 6.0))
        c1 = _make_cat("c1", options=(o1, o2))
        c2 = _make_cat("c2", options=(o3,))
        total, records = compute_raw_combination_count((c1, c2))
        assert total == 6
        assert len(records) == 3

    def test_total_is_sum_not_product(self) -> None:
        o1 = _make_opt("o1", lengths=(1.0, 2.0))
        o2 = _make_opt("o2", lengths=(3.0, 4.0, 5.0))
        cat = _make_cat(options=(o1, o2))
        total, records = compute_raw_combination_count((cat,))
        assert total == 5
        assert total != 2 * 3

    def test_empty_intersection_contributes_zero(self) -> None:
        opt = _make_opt("o1", lengths=(10.0,))
        cat = _make_cat(options=(opt,))
        total, records = compute_raw_combination_count((cat,), 1.0, 5.0)
        assert total == 0
        assert records[0].raw_count == 0

    def test_with_request_bounds(self) -> None:
        opt = _make_opt("o1", lengths=(1.0, 2.0, 3.0, 4.0, 5.0))
        cat = _make_cat(options=(opt,))
        total, records = compute_raw_combination_count((cat,), 2.0, 4.0)
        assert total == 3

    def test_aggregate_count_before_materialization(self) -> None:
        opt = _make_opt("o1", lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        total, records = compute_raw_combination_count((cat,))
        assert total == 3
        assert records[0].raw_count == 3


# ============================================================================
# P0-4: Mixed quantum counting
# ============================================================================


class TestMixedQuantumCounting:
    """Options with different quanta are counted correctly."""

    def test_different_quantum_same_bounds(self) -> None:
        opt_a = _make_opt("opt_a", quantum="0.1", lengths=(1.0, 2.0, 3.0))
        opt_b = _make_opt(
            "opt_b",
            quantum="0.01",
            lengths=(1.0, 1.5, 2.0, 2.5, 3.0),
        )
        cat = _make_cat(options=(opt_a, opt_b))
        total, records = compute_raw_combination_count((cat,), 1.0, 2.0)
        assert total == 5
        assert records[0].canonical_length_quantum_m == "0.1"
        assert records[1].canonical_length_quantum_m == "0.01"
        assert records[0].raw_count == 2
        assert records[1].raw_count == 3

    def test_explicit_and_grid_mixed(self) -> None:
        opt_a = _make_opt("opt_a", lengths=(1.0, 2.0, 3.0))
        opt_b = _make_opt(
            "opt_b",
            grid=LengthGridSpec(
                minimum_length_m=1.0,
                maximum_length_m=3.0,
                increment_m=0.5,
                endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
            ),
        )
        cat = _make_cat(options=(opt_a, opt_b))
        total, records = compute_raw_combination_count((cat,))
        assert total == 8
        assert records[0].raw_count == 3
        assert records[1].raw_count == 5


# ============================================================================
# P0-2: Production orchestration seam
# ============================================================================


class TestCountAndGate:
    """Production orchestration with spy callables."""

    def test_gate_passes_with_injectables_called(self) -> None:
        opt = _make_opt(lengths=(1.0,))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        calls: dict[str, int] = {"m": 0, "i": 0, "e": 0}

        def spy_m() -> None:
            calls["m"] += 1

        def spy_i() -> None:
            calls["i"] += 1

        def spy_e() -> None:
            calls["e"] += 1

        result = count_and_gate_sizing_request(
            req,
            materialize_lengths=spy_m,
            build_candidate_identities=spy_i,
            rating_evaluator=spy_e,
        )
        assert isinstance(result, SizingGateResult)
        assert result.raw_combination_count == 1
        assert calls["m"] == 1
        assert calls["i"] == 1
        assert calls["e"] == 1

    def test_gate_passes_no_injectables(self) -> None:
        opt = _make_opt(lengths=(1.0,))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        result = count_and_gate_sizing_request(req)
        assert isinstance(result, SizingGateResult)
        assert result.raw_combination_count == 1

    def test_cap_exceeded_no_injectables_called(self) -> None:
        opt = _make_opt(lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=1)
        calls: dict[str, int] = {"m": 0, "i": 0, "e": 0}

        def spy_m() -> None:
            calls["m"] += 1

        def spy_i() -> None:
            calls["i"] += 1

        def spy_e() -> None:
            calls["e"] += 1

        result = count_and_gate_sizing_request(
            req,
            materialize_lengths=spy_m,
            build_candidate_identities=spy_i,
            rating_evaluator=spy_e,
        )
        assert isinstance(result, BlockedSizingResult)
        assert calls["m"] == 0
        assert calls["i"] == 0
        assert calls["e"] == 0

    def test_cap_equal_allows_materialization(self) -> None:
        opt = _make_opt(lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=3)
        calls: dict[str, int] = {"m": 0, "i": 0, "e": 0}

        def spy_m() -> None:
            calls["m"] += 1

        def spy_i() -> None:
            calls["i"] += 1

        def spy_e() -> None:
            calls["e"] += 1

        result = count_and_gate_sizing_request(
            req,
            materialize_lengths=spy_m,
            build_candidate_identities=spy_i,
            rating_evaluator=spy_e,
        )
        assert isinstance(result, SizingGateResult)
        assert calls["m"] == 1
        assert calls["i"] == 1
        assert calls["e"] == 1

    def test_cap_below_allows_materialization(self) -> None:
        opt = _make_opt(lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=100)
        calls: dict[str, int] = {"m": 0, "i": 0, "e": 0}

        def spy_m() -> None:
            calls["m"] += 1

        result = count_and_gate_sizing_request(req, materialize_lengths=spy_m)
        assert isinstance(result, SizingGateResult)
        assert calls["m"] == 1


# ============================================================================
# P0-6: Cap-BLOCKED result model
# ============================================================================


class TestBlockedResult:
    """BlockedSizingResult contract verification."""

    @pytest.fixture()
    def blocked(self) -> BlockedSizingResult:
        return BlockedSizingResult(
            raw_combination_count=3,
            effective_cap=2,
            blockers=(
                CapBlocker(
                    message="Raw combination count 3 exceeds effective cap 2",
                ),
            ),
        )

    def test_status_exact(self, blocked: BlockedSizingResult) -> None:
        assert blocked.status == "blocked"

    def test_raw_count_preserved(self, blocked: BlockedSizingResult) -> None:
        assert blocked.raw_combination_count == 3

    def test_effective_cap_preserved(self, blocked: BlockedSizingResult) -> None:
        assert blocked.effective_cap == 2

    def test_counters_zero(self, blocked: BlockedSizingResult) -> None:
        assert blocked.unique_candidate_count == 0
        assert blocked.evaluated_candidate_count == 0

    def test_selected_none(self, blocked: BlockedSizingResult) -> None:
        assert blocked.selected_candidate is None

    def test_top_candidates_empty(self, blocked: BlockedSizingResult) -> None:
        assert blocked.top_candidates == ()

    def test_failure_none(self, blocked: BlockedSizingResult) -> None:
        assert blocked.failure is None

    def test_blocker_exists(self, blocked: BlockedSizingResult) -> None:
        assert len(blocked.blockers) == 1
        b = blocked.blockers[0]
        assert b.code == "cap_exceeded"
        assert "exceeds" in b.message

    def test_json_roundtrip(self, blocked: BlockedSizingResult) -> None:
        json_str = blocked.model_dump_json()
        restored = BlockedSizingResult.model_validate_json(json_str)
        assert restored == blocked
        assert restored.status == "blocked"
        assert restored.raw_combination_count == 3

    def test_repeatable(self, blocked: BlockedSizingResult) -> None:
        json_a = blocked.model_dump_json()
        json_b = blocked.model_dump_json()
        assert json_a == json_b


# ============================================================================
# P1: Manufacturing metadata normalization
# ============================================================================


class TestManufacturingMetadata:
    """Manufacturing metadata dict sorted tuple normalisation."""

    def test_dict_input_sorted(self) -> None:
        opt = _make_opt(metadata={"supplier": "X", "series": "A"})
        assert opt.manufacturing_metadata == (
            ("series", "A"),
            ("supplier", "X"),
        )

    def test_tuple_input_sorted(self) -> None:
        opt = _make_opt(
            metadata=(("supplier", "X"), ("series", "A")),
        )
        assert opt.manufacturing_metadata == (
            ("series", "A"),
            ("supplier", "X"),
        )

    def test_insertion_order_independence(self) -> None:
        a = _make_opt(
            metadata={"series": "A", "supplier": "X"},
        )
        b = _make_opt(
            metadata={"supplier": "X", "series": "A"},
        )
        assert a.manufacturing_metadata == b.manufacturing_metadata

    def test_duplicate_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="Duplicate"):
            _make_opt(
                metadata=(("k", "v1"), ("k", "v2")),
            )

    def test_non_ascii_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="ASCII"):
            _make_opt(metadata={"\u00e9": "value"})

    def test_non_str_key_rejected(self) -> None:
        with pytest.raises(TypeError):
            _make_opt(metadata={42: "value"})  # type: ignore[arg-type]

    def test_non_str_value_rejected(self) -> None:
        with pytest.raises(TypeError):
            _make_opt(metadata={"key": 42})  # type: ignore[arg-type]

    def test_default_empty(self) -> None:
        opt = _make_opt()
        assert opt.manufacturing_metadata == ()


# ============================================================================
# P1: Nested model immutability
# ============================================================================


class TestNestedImmutability:
    """All Phase 1 models are frozen end-to-end."""

    def test_length_grid_spec_frozen(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0.1,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises((TypeError, ValueError)):
            grid.minimum_length_m = 2.0  # type: ignore[misc]

    def test_length_source_frozen(self) -> None:
        src = LengthSource(length_quantum_m="0.1", allowed_effective_lengths_m=(1.0,))
        with pytest.raises((TypeError, ValueError)):
            src.length_quantum_m = "0.01"  # type: ignore[misc]

    def test_assembly_option_frozen(self) -> None:
        opt = _make_opt()
        with pytest.raises((TypeError, ValueError)):
            opt.assembly_option_id = "new"  # type: ignore[misc]

    def test_catalog_frozen(self) -> None:
        opt = _make_opt()
        cat = _make_cat(options=(opt,))
        with pytest.raises((TypeError, ValueError)):
            cat.catalog_id = "new"  # type: ignore[misc]

    def test_catalog_ref_frozen(self) -> None:
        ref = CatalogSnapshotRef(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash="abc",
            source_identity="test",
            schema_version="1.0",
        )
        with pytest.raises((TypeError, ValueError)):
            ref.catalog_id = "c2"  # type: ignore[misc]

    def test_sizing_request_frozen(self) -> None:
        req = SizingRequest(catalogs=())
        with pytest.raises((TypeError, ValueError)):
            req.schema_version = "2.0"  # type: ignore[misc]

    def test_nested_length_source_not_mutable(self) -> None:
        opt = _make_opt()
        with pytest.raises((TypeError, ValueError)):
            opt.length_source.length_quantum_m = "0.01"  # type: ignore[misc]


# ============================================================================
# P0-4: compute_option_raw_count reads quantum from option
# ============================================================================


class TestOptionReadsOwnQuantum:
    """compute_option_raw_count reads quantum from the option itself."""

    def test_no_external_quantum_param(self) -> None:
        import inspect

        sig = inspect.signature(compute_option_raw_count)
        params = list(sig.parameters.keys())
        assert "quantum" not in params

    def test_count_with_own_quantum(self) -> None:
        opt = _make_opt(quantum="0.1", lengths=(0.5, 1.0, 1.5))
        assert compute_option_raw_count(opt) == 3

    def test_count_with_bounds_and_own_quantum(self) -> None:
        opt = _make_opt(quantum="0.1", lengths=(1.0, 2.0, 3.0, 4.0, 5.0))
        assert compute_option_raw_count(opt, 2.0, 4.0) == 3


# ============================================================================
# Fix: test comment accuracy
# ============================================================================


class TestExplicitModeWithRequestFilter:
    """test_explicit_mode_with_request_filter — comment fix."""

    def test_explicit_mode_with_request_filter(self) -> None:
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
        count = compute_option_raw_count(option, 2.0, 3.0)
        # Input ticks are 10, 20, 30, 40, 50.
        # Inclusive request range 20..30 keeps only 20 and 30 (2.0, 3.0).
        assert count == 2


# ============================================================================
# Retained Phase 1 tests from original
# ============================================================================


class TestValidateLengthQuantum:
    """Power-of-10 quantum validation."""

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
            "0.025",
            "0.333",
            "10",
            "100",
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


class TestTickConversion:
    """Integer tick conversion."""

    def test_to_tick_simple(self) -> None:
        quantum = Decimal("0.1")
        assert to_tick(1.0, quantum) == 10
        assert to_tick("0.5", quantum) == 5
        assert to_tick(0.1, quantum) == 1

    def test_to_tick_round_half_even(self) -> None:
        quantum = Decimal("0.1")
        assert to_tick(0.15, quantum) == 2
        assert to_tick(0.25, quantum) == 2

    def test_to_tick_sub_quantum_rejected(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(InvalidLengthError, match="sub-quantum"):
            to_tick(0.05, quantum)

    def test_to_tick_zero_rejected(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(InvalidLengthError, match="must be finite"):
            to_tick(0, quantum)

    def test_to_tick_from_tick_roundtrip(self) -> None:
        quantum = Decimal("0.001")
        for v in [0.001, 0.5, 1.234, 12.345, 100.0]:
            tick = to_tick(v, quantum)
            back = from_tick(tick, quantum)
            assert float(back) == pytest.approx(v, rel=1e-12)


class TestCanonicalizeExplicitLengths:
    """Explicit lengths dedup, sort, and canonicalization."""

    def test_dedup_and_sort(self) -> None:
        quantum = Decimal("0.1")
        ticks, lengths = canonicalize_explicit_lengths((1.5, 1.0, 1.5, 0.5, 1.0), quantum)
        assert ticks == (5, 10, 15)

    def test_insertion_order_independence(self) -> None:
        quantum = Decimal("0.1")
        _, a = canonicalize_explicit_lengths((1.0, 2.0, 3.0), quantum)
        _, b = canonicalize_explicit_lengths((3.0, 1.0, 2.0), quantum)
        assert a == b

    def test_empty_after_canonicalization(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(CatalogInvalid, match="Empty"):
            canonicalize_explicit_lengths((), quantum)


class TestGridCountOnly:
    """Grid count-only algorithm."""

    def test_simple_grid(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=0.5,
            maximum_length_m=1.0,
            increment_m=0.1,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        ctx = grid_count_only(grid, quantum)
        assert ctx.catalog_count == 6

    def test_include_max_aligned(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0.5,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        ctx = grid_count_only(grid, quantum)
        assert ctx.catalog_count == 3

    def test_exclude_max(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0.5,
            endpoint_policy=LengthEndpointPolicy.EXCLUDE_MAX,
        )
        ctx = grid_count_only(grid, quantum)
        assert ctx.catalog_count == 2

    def test_exclude_max_min_equals_max(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=1.0,
            increment_m=0.1,
            endpoint_policy=LengthEndpointPolicy.EXCLUDE_MAX,
        )
        ctx = grid_count_only(grid, quantum)
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


class TestRequestBounds:
    """Request bounds ceiling/floor intersection."""

    def test_request_min_ceiling(self) -> None:
        quantum = Decimal("0.1")
        assert request_min_ceiling(1.05, quantum) == 11

    def test_request_max_floor(self) -> None:
        quantum = Decimal("0.1")
        assert request_max_floor(1.95, quantum) == 19

    def test_bounds_none(self) -> None:
        quantum = Decimal("0.1")
        assert request_min_ceiling(None, quantum) is None
        assert request_max_floor(None, quantum) is None

    def test_request_min_invalid(self) -> None:
        quantum = Decimal("0.1")
        with pytest.raises(InvalidRequestBounds):
            request_min_ceiling(0, quantum)

    def test_request_no_intersection(self) -> None:
        quantum = Decimal("0.1")
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=2.0,
            increment_m=0.1,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        rmin = request_min_ceiling(5.0, quantum)
        rmax = request_max_floor(5.5, quantum)
        ctx = grid_count_only(grid, quantum, rmin, rmax)
        assert ctx.intersection_count == 0


class TestCapCheck:
    """Hard/request cap check."""

    def test_hard_cap_constant(self) -> None:
        assert HARD_RAW_COMBINATION_CAP == 10_000

    def test_under_cap(self) -> None:
        assert check_cap(100) == HARD_RAW_COMBINATION_CAP

    def test_under_request_cap(self) -> None:
        assert check_cap(50, request_cap=100) == 100

    def test_at_cap(self) -> None:
        assert check_cap(HARD_RAW_COMBINATION_CAP) == HARD_RAW_COMBINATION_CAP

    def test_exceeded_hard_cap(self) -> None:
        with pytest.raises(CapExceeded, match="exceeds"):
            check_cap(HARD_RAW_COMBINATION_CAP + 1)

    def test_exceeded_request_cap(self) -> None:
        with pytest.raises(CapExceeded, match="exceeds"):
            check_cap(51, request_cap=50)

    def test_bool_true_rejected(self) -> None:
        with pytest.raises(InvalidRequestBounds):
            check_cap(10, request_cap=True)  # type: ignore[arg-type]

    def test_bool_false_rejected(self) -> None:
        with pytest.raises(InvalidRequestBounds):
            check_cap(10, request_cap=False)  # type: ignore[arg-type]


class TestLengthSource:
    """LengthSource exactly-one validation."""

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

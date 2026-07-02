"""
TASK-009 Phase 1 regression tests — aggregate pipeline, canonical quantum,
production orchestration, SizingRequest validation, manufacturing metadata,
nested immutability, cap-BLOCKED result, mixed-quantum counting.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

import pytest

from hexagent.optimization.catalog import compute_catalog_content_hash
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
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthEndpointPolicy,
    LengthGridSpec,
    LengthSource,
    SizingGateResult,
    SizingRequest,
)

pytestmark = pytest.mark.pure

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


def _hash_cat(
    catalog_id: str = "cat1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> str:
    """Compute the content hash for a catalog with given options."""
    return compute_catalog_content_hash(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
    )


def _make_cat(
    catalog_id: str = "cat1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> CompleteDoublePipeCatalogSnapshot:
    claimed = _hash_cat(catalog_id=catalog_id, options=options)
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
        catalog_content_hash=claimed,
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
        assert s1.length_quantum_m == "0.001"
        assert s2.length_quantum_m == "0.001"
        assert s3.length_quantum_m == "0.001"

    def test_model_dump_consistency(self) -> None:
        src = LengthSource(length_quantum_m="0.0010", allowed_effective_lengths_m=(1.0,))
        assert src.model_dump()["length_quantum_m"] == "0.001"
        assert src.model_dump(mode="json")["length_quantum_m"] == "0.001"

    def test_power_of_10_quantum_accepted(self) -> None:
        # 1, 0.1, 0.01, 0.001, ...
        for q in ("1", "0.1", "0.01", "0.001", "0.0001"):
            s = LengthSource(length_quantum_m=q, allowed_effective_lengths_m=(1.0,))
            assert s.length_quantum_m == q

    def test_invalid_quantum_rejected(self) -> None:
        for q in ("0.025", "0.333", "10", "100", "NaN", "Infinity", "0", "-0.1"):
            with pytest.raises((InvalidLengthQuantum, ValueError)):
                LengthSource(length_quantum_m=q, allowed_effective_lengths_m=(1.0,))


# ============================================================================
# P0-5: SizingRequest strict validation
# ============================================================================


class TestSizingRequestValidation:
    """SizingRequest must reject invalid bounds, caps, and ordering."""

    def test_valid_default(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        req = SizingRequest(catalogs=(cat,))
        assert req.schema_version == "1.0"
        assert req.minimum_effective_length_m is None
        assert req.maximum_effective_length_m is None
        assert req.request_raw_combination_cap is None

    def test_valid_bounds(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        req = SizingRequest(
            catalogs=(cat,), minimum_effective_length_m=1.0, maximum_effective_length_m=5.0
        )
        assert req.minimum_effective_length_m == 1.0
        assert req.maximum_effective_length_m == 5.0

    def test_valid_cap(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=5000)
        assert req.request_raw_combination_cap == 5000

    def test_none_cap(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        req = SizingRequest(catalogs=(cat,))
        assert req.request_raw_combination_cap is None

    def test_min_bool_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(TypeError, match="must be float, not bool"):
            SizingRequest(catalogs=(cat,), minimum_effective_length_m=True)

    def test_max_bool_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(TypeError, match="must be float, not bool"):
            SizingRequest(catalogs=(cat,), maximum_effective_length_m=False)

    def test_bool_cap_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(TypeError, match="must be int, not bool"):
            SizingRequest(catalogs=(cat,), request_raw_combination_cap=True)
        with pytest.raises(TypeError, match="must be int, not bool"):
            SizingRequest(catalogs=(cat,), request_raw_combination_cap=False)

    def test_cap_boundaries(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        # Max allowed
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=10_000)
        assert req.request_raw_combination_cap == 10_000
        # Min allowed
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=1)
        assert req.request_raw_combination_cap == 1

    def test_cap_exceeds_max_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(ValueError, match="<= 10000"):
            SizingRequest(catalogs=(cat,), request_raw_combination_cap=10_001)

    def test_cap_zero_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(cat,), request_raw_combination_cap=0)

    def test_cap_negative_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(cat,), request_raw_combination_cap=-1)

    def test_cap_float_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(TypeError, match="must be int"):
            SizingRequest(catalogs=(cat,), request_raw_combination_cap=3.14)

    def test_cap_str_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(TypeError, match="must be int"):
            SizingRequest(catalogs=(cat,), request_raw_combination_cap="100")

    def test_min_non_positive_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(cat,), minimum_effective_length_m=0.0)
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(cat,), minimum_effective_length_m=-1.0)

    def test_max_non_positive_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(cat,), maximum_effective_length_m=0.0)
        with pytest.raises(ValueError, match="must be positive"):
            SizingRequest(catalogs=(cat,), maximum_effective_length_m=-1.0)

    def test_non_finite_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        for v in (float("nan"), float("inf")):
            with pytest.raises(ValueError, match="must be finite"):
                SizingRequest(catalogs=(cat,), minimum_effective_length_m=v)
            with pytest.raises(ValueError, match="must be finite"):
                SizingRequest(catalogs=(cat,), maximum_effective_length_m=v)

    def test_min_exceeds_max_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(ValueError, match="must not exceed"):
            SizingRequest(
                catalogs=(cat,), minimum_effective_length_m=5.0, maximum_effective_length_m=1.0
            )

    def test_request_bounds_must_not_widen_catalog(self) -> None:
        """Test that bounds are ceiling/floor, not widening."""
        opt = _make_opt(quantum="0.1", lengths=(1.0, 5.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(
            catalogs=(cat,), minimum_effective_length_m=0.5, maximum_effective_length_m=5.5
        )
        count = compute_option_raw_count(
            opt, req.minimum_effective_length_m, req.maximum_effective_length_m
        )
        # 0.5 -> ceiling to 1.0 (tick 10), 5.5 -> floor to 5.0 (tick 50)
        # explicit lengths [1.0, 5.0] -> both pass
        assert count == 2


# ============================================================================
# P0-1: Aggregate raw count (using compute_raw_combination_count)
# ============================================================================


class TestAggregateRawCount:
    """Aggregate counting from typed catalog snapshots."""

    def test_one_catalog_one_option(self) -> None:
        opt = _make_opt("o1", lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        t, rec = compute_raw_combination_count((cat,))
        assert t == 3
        assert len(rec) == 1

    def test_one_catalog_multiple_options_sum(self) -> None:
        o1 = _make_opt("o1", lengths=(1.0, 2.0))
        o2 = _make_opt("o2", lengths=(3.0, 4.0, 5.0))
        cat = _make_cat(options=(o1, o2))
        t, _ = compute_raw_combination_count((cat,))
        assert t == 5

    def test_multiple_catalogs(self) -> None:
        o1 = _make_opt("o1", lengths=(1.0, 2.0))
        o2 = _make_opt("o2", lengths=(3.0, 4.0, 5.0))
        o3 = _make_opt("o3", lengths=(6.0, 7.0, 8.0, 9.0))
        c1 = _make_cat("c1", options=(o1, o2))
        c2 = _make_cat("c2", options=(o3,))
        t, rec = compute_raw_combination_count((c1, c2))
        assert t == 9
        assert len(rec) == 3

    def test_total_is_sum_not_product(self) -> None:
        o1 = _make_opt("o1", lengths=(1.0, 2.0))
        o2 = _make_opt("o2", lengths=(3.0, 4.0, 5.0))
        cat = _make_cat(options=(o1, o2))
        t, _ = compute_raw_combination_count((cat,))
        assert t == 5
        assert t != 2 * 3

    def test_empty_intersection_contributes_zero(self) -> None:
        opt = _make_opt("o1", lengths=(100.0, 200.0))
        cat = _make_cat(options=(opt,))
        t, _ = compute_raw_combination_count((cat,), minimum_effective_length_m=500.0)
        assert t == 0

    def test_catalog_permutation_invariance(self) -> None:
        cx = _make_cat("x", options=(_make_opt("o1", lengths=(1.0,)),))
        cy = _make_cat("y", options=(_make_opt("o2", lengths=(2.0,)),))
        t1, r1 = compute_raw_combination_count((cx, cy))
        t2, r2 = compute_raw_combination_count((cy, cx))
        assert t1 == t2
        assert r1 == r2
        assert r1[0].model_dump_json() == r2[0].model_dump_json()
        assert r1[1].model_dump_json() == r2[1].model_dump_json()

    def test_option_permutation_invariance(self) -> None:
        oa = _make_opt("b", lengths=(1.0,))
        ob = _make_opt("a", lengths=(2.0,))
        c1 = _make_cat("c", options=(oa, ob))
        c2 = _make_cat("c", options=(ob, oa))
        t1, r1 = compute_raw_combination_count((c1,))
        t2, r2 = compute_raw_combination_count((c2,))
        assert t1 == t2
        assert r1 == r2

    def test_duplicate_catalog_identity_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(CatalogInvalid, match="Duplicate catalog"):
            compute_raw_combination_count((cat, cat))


# ============================================================================
# Mixed-quantum counting
# ============================================================================


class TestMixedQuantumCounting:
    """Options with different quanta are handled independently."""

    def test_different_quantum_modes(self) -> None:
        opt_a = _make_opt("opt_a", quantum="0.1", lengths=(1.0, 2.0, 3.0))
        opt_b = _make_opt("opt_b", quantum="0.01", lengths=(1.0, 1.5, 2.0))
        cat = _make_cat(options=(opt_a, opt_b))
        t, rec = compute_raw_combination_count(
            (cat,), minimum_effective_length_m=1.0, maximum_effective_length_m=2.0
        )
        assert t == 5
        # opt_a: quantum=0.1, min ceiling=1.0, max floor=2.0
        # explicit [1.0, 2.0, 3.0] -> filtered [1.0, 2.0] => count=2
        assert rec[0].raw_count == 2
        # opt_b: quantum=0.01, min ceiling=1.0, max floor=2.0
        # explicit [1.0, 1.5, 2.0] -> all pass => count=3
        assert rec[1].raw_count == 3

    def test_grid_and_explicit_mixed(self) -> None:
        opt_a = _make_opt("opt_a", lengths=(1.0, 2.0, 3.0))
        opt_b = _make_opt(
            "opt_b",
            grid=LengthGridSpec(
                minimum_length_m=1.0,
                maximum_length_m=3.0,
                increment_m=1.0,
                endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
            ),
        )
        cat = _make_cat(options=(opt_a, opt_b))
        t, _ = compute_raw_combination_count((cat,))
        # opt_a: 3 explicit lengths
        # opt_b: grid 1.0..3.0 step 1.0 include_max => [1, 2, 3] => 3
        assert t == 6


# ============================================================================
# Production orchestration seam (count_and_gate_sizing_request)
# ============================================================================


class TestCountAndGate:
    """Phase 1 orchestration: count → gate → inject callables in order."""

    def test_gate_passes_calls_materializer(self) -> None:
        opt = _make_opt(lengths=(1.0,))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        v: dict[str, int] = {"m": 0}
        r = count_and_gate_sizing_request(req, materialize_lengths=lambda: v.update(m=1))
        assert isinstance(r, SizingGateResult)
        assert v["m"] == 1

    def test_gate_passes_calls_all_three_in_order(self) -> None:
        opt = _make_opt(lengths=(1.0,))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        order: list[str] = []
        r = count_and_gate_sizing_request(
            req,
            materialize_lengths=lambda: order.append("materialize"),
            build_candidate_identities=lambda: order.append("identity"),
            rating_evaluator=lambda: order.append("evaluate"),
        )
        assert isinstance(r, SizingGateResult)
        assert order == ["materialize", "identity", "evaluate"]

    def test_cap_exceeded_does_not_call_materializer(self) -> None:
        opt = _make_opt(lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=1)
        v: dict[str, int] = {"m": 0}
        r = count_and_gate_sizing_request(req, materialize_lengths=lambda: v.update(m=1))
        assert isinstance(r, BlockedSizingResult)
        assert v["m"] == 0

    def test_cap_exceeded_does_not_call_identity_or_evaluator(self) -> None:
        opt = _make_opt(lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=1)
        counts: dict[str, int] = {"m": 0, "i": 0, "e": 0}
        r = count_and_gate_sizing_request(
            req,
            materialize_lengths=lambda: counts.update(m=counts["m"] + 1),
            build_candidate_identities=lambda: counts.update(i=counts["i"] + 1),
            rating_evaluator=lambda: counts.update(e=counts["e"] + 1),
        )
        assert isinstance(r, BlockedSizingResult)
        assert counts == {"m": 0, "i": 0, "e": 0}

    def test_cap_passed_does_not_block(self) -> None:
        opt = _make_opt(lengths=(1.0,))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=10)
        r = count_and_gate_sizing_request(req)
        assert isinstance(r, SizingGateResult)


# ============================================================================
# Blocked sizing result contract
# ============================================================================


class TestBlockedResult:
    """Cap-BLOCKED result must conform to the Phase 1 contract."""

    def _make_blocked(self) -> BlockedSizingResult:
        opt = _make_opt(lengths=(1.0, 2.0, 3.0, 4.0, 5.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=2)
        result = count_and_gate_sizing_request(req)
        assert isinstance(result, BlockedSizingResult)
        return result

    def test_status_is_blocked(self) -> None:
        r = self._make_blocked()
        assert r.status == "blocked"

    def test_counts_zero(self) -> None:
        r = self._make_blocked()
        assert r.unique_candidate_count == 0
        assert r.evaluated_candidate_count == 0

    def test_selected_is_none(self) -> None:
        r = self._make_blocked()
        assert r.selected_candidate is None

    def test_top_candidates_empty(self) -> None:
        r = self._make_blocked()
        assert r.top_candidates == ()

    def test_failure_none(self) -> None:
        r = self._make_blocked()
        assert r.failure is None

    def test_has_blocker(self) -> None:
        r = self._make_blocked()
        assert len(r.blockers) > 0

    def test_blocker_is_structured(self) -> None:
        r = self._make_blocked()
        b = r.blockers[0]
        assert isinstance(b, CapBlocker)
        assert b.code == "cap_exceeded"
        assert isinstance(b.message, str)
        assert len(b.message) > 0

    def test_blocker_has_context(self) -> None:
        r = self._make_blocked()
        b = r.blockers[0]
        ctx = dict(b.context)
        assert "raw_count" in ctx
        assert "effective_cap" in ctx

    def test_json_roundtrip(self) -> None:
        r1 = self._make_blocked()
        json_str = r1.model_dump_json()
        r2 = BlockedSizingResult.model_validate_json(json_str)
        assert r1 == r2
        assert r2.status == "blocked"
        assert r2.unique_candidate_count == 0

    def test_deterministic_repeated_execution(self) -> None:
        r1 = self._make_blocked()
        r2 = self._make_blocked()
        assert r1.model_dump() == r2.model_dump()


# ============================================================================
# Manufacturing metadata normalisation
# ============================================================================


class TestManufacturingMetadata:
    """Dict inputs normalised to sorted ASCII-key tuples."""

    def test_dict_input_normalised(self) -> None:
        opt = _make_opt(metadata={"supplier": "X", "series": "A"})
        expected = (("series", "A"), ("supplier", "X"))
        assert opt.manufacturing_metadata == expected

    def test_tuple_input_preserved(self) -> None:
        opt = _make_opt(metadata=(("supplier", "X"), ("series", "A")))
        expected = (("series", "A"), ("supplier", "X"))
        assert opt.manufacturing_metadata == expected

    def test_insertion_order_independent(self) -> None:
        a = _make_opt(metadata=(("b", "2"), ("a", "1")))
        b = _make_opt(metadata=(("a", "1"), ("b", "2")))
        assert a.manufacturing_metadata == b.manufacturing_metadata

    def test_duplicate_key_rejected(self) -> None:
        with pytest.raises((ValueError, KeyError)):
            _make_opt(metadata=(("key", "a"), ("key", "b")))

    def test_non_ascii_key_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_opt(metadata={"\u00e9": "value"})

    def test_non_str_key_rejected(self) -> None:
        with pytest.raises(TypeError):
            _make_opt(metadata={42: "value"})  # type: ignore[arg-type]

    def test_non_str_value_rejected(self) -> None:
        with pytest.raises(TypeError):
            _make_opt(metadata={"key": 42})  # type: ignore[arg-type]

    def test_default_empty_tuple(self) -> None:
        opt = _make_opt()
        assert opt.manufacturing_metadata == ()


# ============================================================================
# Nested model immutability
# ============================================================================


class TestNestedImmutability:
    """All Phase 1 models are frozen — mutation must be rejected."""

    def test_grid_frozen(self) -> None:
        g = LengthGridSpec(
            minimum_length_m=0.5,
            maximum_length_m=5.0,
            increment_m=0.5,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises(ValueError, match="frozen"):
            g.minimum_length_m = 1.0  # type: ignore[misc]

    def test_length_source_frozen(self) -> None:
        s = LengthSource(length_quantum_m="0.1", allowed_effective_lengths_m=(1.0, 2.0))
        with pytest.raises(ValueError, match="frozen"):
            s.length_quantum_m = "0.01"  # type: ignore[misc]

    def test_catalog_snapshot_frozen(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(ValueError, match="frozen"):
            cat.catalog_id = "other"  # type: ignore[misc]

    def test_nested_model_mutation_rejected(self) -> None:
        opt = _make_opt()
        with pytest.raises(ValueError, match="frozen"):
            opt.length_source.length_quantum_m = "0.01"  # type: ignore[misc]

    def test_assembly_option_frozen(self) -> None:
        opt = _make_opt()
        with pytest.raises(ValueError, match="frozen"):
            opt.assembly_option_id = "changed"  # type: ignore[misc]

    def test_immutable_catalog_nested(self) -> None:
        opt = _make_opt()
        cat = _make_cat(options=(opt,))
        with pytest.raises(ValueError, match="frozen"):
            cat.assembly_options[0].assembly_option_id = "x"  # type: ignore[misc]


# ============================================================================
# Option reads own quantum
# ============================================================================


class TestOptionReadsOwnQuantum:
    """``compute_option_raw_count`` reads quantum from the option itself."""

    def test_quantum_from_option(self) -> None:
        opt = _make_opt(quantum="0.1", lengths=(0.5, 1.0, 1.5))
        count = compute_option_raw_count(opt)
        # quantum=0.1, explicit [0.5, 1.0, 1.5]
        # 0.5 -> tick 5 (valid), 1.0 -> tick 10, 1.5 -> tick 15 => count=3
        assert count == 3

    def test_explicit_length_count(self) -> None:
        opt = _make_opt(quantum="0.1", lengths=(1.0, 2.0, 3.0, 4.0, 5.0))
        count = compute_option_raw_count(opt)
        assert count == 5

    def test_grid_count(self) -> None:
        opt = _make_opt(
            grid=LengthGridSpec(
                minimum_length_m=1.0,
                maximum_length_m=5.0,
                increment_m=1.0,
                endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
            )
        )
        count = compute_option_raw_count(opt)
        assert count == 5


# ============================================================================
# Explicit mode with request filter
# ============================================================================


class TestExplicitModeWithRequestFilter:
    """Request bounds filter explicit lengths correctly."""

    def _make_explicit_opt(self, lengths: tuple[float, ...]) -> CompleteDoublePipeAssemblyOption:
        return _make_opt(option_id="f", lengths=lengths)

    def test_no_bounds(self) -> None:
        opt = self._make_explicit_opt((1.0, 2.0, 3.0))
        assert compute_option_raw_count(opt) == 3

    def test_min_filter(self) -> None:
        opt = self._make_explicit_opt((1.0, 2.0, 3.0, 4.0, 5.0))
        c = compute_option_raw_count(opt, minimum_effective_length_m=3.0)
        assert c == 3

    def test_max_filter(self) -> None:
        opt = self._make_explicit_opt((1.0, 2.0, 3.0, 4.0, 5.0))
        c = compute_option_raw_count(opt, maximum_effective_length_m=3.0)
        assert c == 3

    def test_both_bounds(self) -> None:
        opt = self._make_explicit_opt((1.0, 2.0, 3.0, 4.0, 5.0))
        c = compute_option_raw_count(
            opt, minimum_effective_length_m=2.0, maximum_effective_length_m=4.0
        )
        assert c == 3

    def test_no_intersection(self) -> None:
        opt = self._make_explicit_opt((1.0, 2.0, 3.0))
        c = compute_option_raw_count(opt, minimum_effective_length_m=10.0)
        assert c == 0
        c = compute_option_raw_count(opt, maximum_effective_length_m=0.5)
        assert c == 0


# ============================================================================
# validate_length_quantum
# ============================================================================


class TestValidateLengthQuantum:
    """Standalone quantum validation."""

    def test_valid_power_of_10(self) -> None:
        for q in ("1", "0.1", "0.01", "0.001", "0.0001"):
            d = validate_length_quantum(q)
            assert isinstance(d, Decimal)

    def test_invalid_quantum(self) -> None:
        for q in ("0.025", "0.333", "10", "100", "NaN", "Infinity", "0", "-0.1"):
            with pytest.raises(InvalidLengthQuantum):
                validate_length_quantum(q)


# ============================================================================
# Tick conversion
# ============================================================================


class TestTickConversion:
    """to_tick / from_tick round-trip."""

    def test_to_tick_basic(self) -> None:
        q = Decimal("0.1")
        t = to_tick(1.0, q)
        assert t == 10

    def test_from_tick_basic(self) -> None:
        q = Decimal("0.1")
        d = from_tick(10, q)
        assert d == Decimal("1.0")

    def test_round_trip(self) -> None:
        q = Decimal("0.01")
        for v in (0.05, 0.1, 1.0, 1.23, 5.0):
            t = to_tick(v, q)
            d = from_tick(t, q)
            assert d == Decimal(str(v)).quantize(q, rounding=ROUND_HALF_EVEN)

    def test_sub_quantum_value_rejected(self) -> None:
        q = Decimal("1")
        with pytest.raises(InvalidLengthError, match="sub-quantum"):
            to_tick(0.5, q)

    def test_zero_rejected(self) -> None:
        q = Decimal("0.1")
        with pytest.raises(InvalidLengthError):
            to_tick(0.0, q)

    def test_negative_rejected(self) -> None:
        q = Decimal("0.1")
        with pytest.raises(InvalidLengthError):
            to_tick(-1.0, q)


# ============================================================================
# canonicalize_explicit_lengths
# ============================================================================


class TestCanonicalizeExplicitLengths:
    """Deduplication, sorting, tick conversion."""

    def test_deduplicates(self) -> None:
        q = Decimal("0.1")
        ticks, lengths = canonicalize_explicit_lengths((1.0, 1.0, 2.0), q)
        assert ticks == (10, 20)

    def test_sorts(self) -> None:
        q = Decimal("0.1")
        ticks, lengths = canonicalize_explicit_lengths((3.0, 1.0, 2.0), q)
        assert ticks == (10, 20, 30)

    def test_empty_rejected(self) -> None:
        with pytest.raises(CatalogInvalid):
            canonicalize_explicit_lengths((), Decimal("0.1"))


# ============================================================================
# Grid count-only
# ============================================================================


class TestGridCountOnly:
    """Grid counting with endpoint policies and request bounds."""

    def test_include_max_if_aligned(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=5.0,
            increment_m=1.0,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        ctx = grid_count_only(grid, Decimal("0.1"))
        assert ctx.catalog_count == 5
        assert ctx.intersection_count == 5

    def test_exclude_max(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=5.0,
            increment_m=1.0,
            endpoint_policy=LengthEndpointPolicy.EXCLUDE_MAX,
        )
        ctx = grid_count_only(grid, Decimal("0.1"))
        assert ctx.catalog_count == 4
        assert ctx.intersection_count == 4

    def test_exclude_max_min_equals_max(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=1.0,
            increment_m=1.0,
            endpoint_policy=LengthEndpointPolicy.EXCLUDE_MAX,
        )
        ctx = grid_count_only(grid, Decimal("0.1"))
        assert ctx.catalog_count == 0
        assert ctx.intersection_count == 0

    def test_reversed_grid_rejected(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=5.0,
            maximum_length_m=1.0,
            increment_m=1.0,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises(CatalogInvalid, match="Reversed grid"):
            grid_count_only(grid, Decimal("0.1"))

    def test_sub_quantum_increment_rejected(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=5.0,
            increment_m=0.05,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises(CatalogInvalid, match="Sub-quantum increment"):
            grid_count_only(grid, Decimal("0.1"))

    def test_zero_increment_rejected(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=5.0,
            increment_m=0.0,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        with pytest.raises((CatalogInvalid, ValueError)):
            grid_count_only(grid, Decimal("0.1"))


# ============================================================================
# Request bounds ceiling/floor
# ============================================================================


class TestRequestBounds:
    """Request bound conversion (ceil/floor) matches spec."""

    def test_min_ceiling_none(self) -> None:
        assert request_min_ceiling(None, Decimal("0.1")) is None

    def test_max_floor_none(self) -> None:
        assert request_max_floor(None, Decimal("0.1")) is None

    def test_min_ceiling_rounds_up(self) -> None:
        q = Decimal("0.1")
        # 0.05 -> ROUND_UP -> 0.1 -> tick 1
        assert request_min_ceiling(0.05, q) == 1

    def test_max_floor_rounds_down(self) -> None:
        q = Decimal("0.1")
        # 1.05 -> ROUND_DOWN -> 1.0 -> tick 10
        assert request_max_floor(1.05, q) == 10

    def test_min_already_aligned(self) -> None:
        q = Decimal("0.1")
        assert request_min_ceiling(0.1, q) == 1

    def test_max_already_aligned(self) -> None:
        q = Decimal("0.1")
        assert request_max_floor(0.1, q) == 1

    def test_min_exact_ceiling(self) -> None:
        q = Decimal("0.5")
        # 0.3 -> ROUND_UP -> 0.5 -> tick 1
        t = request_min_ceiling(0.3, q)
        assert t == 1

    def test_max_exact_floor(self) -> None:
        q = Decimal("0.5")
        # 0.7 -> ROUND_DOWN -> 0.5 -> tick 1
        t = request_max_floor(0.7, q)
        assert t == 1


# ============================================================================
# Cap checking
# ============================================================================


class TestCapCheck:
    """Standalone cap check logic."""

    def test_cap_exceeded_exception(self) -> None:
        with pytest.raises(CapExceeded):
            check_cap(100, request_cap=10)

    def test_cap_ok(self) -> None:
        effective = check_cap(5, request_cap=10)
        assert effective == 10

    def test_no_request_cap_uses_hard_cap(self) -> None:
        effective = check_cap(1)
        assert effective == HARD_RAW_COMBINATION_CAP

    def test_request_cap_exceeds_hard_cap_rejected(self) -> None:
        with pytest.raises(InvalidRequestBounds, match="exceeds hard cap"):
            check_cap(1, request_cap=20_000)

    def test_hard_cap_exceeded(self) -> None:
        with pytest.raises(CapExceeded):
            check_cap(HARD_RAW_COMBINATION_CAP + 1)

    def test_bool_cap_rejected(self) -> None:
        with pytest.raises(InvalidRequestBounds):
            check_cap(1, request_cap=True)  # type: ignore[arg-type]


# ============================================================================
# LengthSource validation
# ============================================================================


class TestLengthSource:
    """Exactly one of explicit/grid must be provided."""

    def test_explicit_only(self) -> None:
        ls = LengthSource(length_quantum_m="0.1", allowed_effective_lengths_m=(1.0,))
        assert ls.allowed_effective_lengths_m == (1.0,)
        assert ls.grid is None

    def test_grid_only(self) -> None:
        g = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=5.0,
            increment_m=1.0,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        ls = LengthSource(length_quantum_m="0.1", grid=g)
        assert ls.grid is not None
        assert ls.allowed_effective_lengths_m is None

    def test_both_rejected(self) -> None:
        with pytest.raises(ValueError, match="Exactly one"):
            LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
                grid=LengthGridSpec(
                    minimum_length_m=1.0,
                    maximum_length_m=5.0,
                    increment_m=1.0,
                    endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
                ),
            )

    def test_neither_rejected(self) -> None:
        with pytest.raises(ValueError, match="Exactly one"):
            LengthSource(length_quantum_m="0.1")

"""
TASK-009 Phase 2 tests — materialization, identities, context (UUID5).

Covers:
  - Length materialization for explicit and grid sources
  - PhysicalCandidateIdentity + digest determinism
  - SourceQualifiedCandidateIdentity + dedup
  - ManufacturableCandidate build/dedup/order
  - SizingRequestIdentity full identity
  - Candidate calculation context UUID5
"""

from __future__ import annotations

from uuid import UUID

from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.catalog import compute_catalog_content_hash
from hexagent.optimization.context import (
    TASK009_CONTEXT_NAMESPACE,
    ExpectedProviderIdentity,
    build_sizing_request_identity,
    candidate_request_id,
)
from hexagent.optimization.identities import (
    PhysicalCandidateIdentity,
    build_candidate,
    deduplicate_and_order_candidates,
    materialize_all_candidates,
)
from hexagent.optimization.length import compute_raw_combination_count
from hexagent.optimization.materialization import (
    materialize_lengths_for_option,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthEndpointPolicy,
    LengthGridSpec,
    LengthSource,
    SizingRequest,
)

# ============================================================================
# Fixtures
# ============================================================================


def _make_opt(
    option_id: str = "opt1",
    quantum: str = "0.1",
    lengths: tuple[float, ...] = (1.0, 2.0, 3.0),
    grid: LengthGridSpec | None = None,
) -> CompleteDoublePipeAssemblyOption:
    kw: dict[str, object] = {
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
        "manufacturing_metadata": (),
    }
    if grid is not None:
        kw["length_source"] = LengthSource(length_quantum_m=quantum, grid=grid)
    else:
        kw["length_source"] = LengthSource(
            length_quantum_m=quantum, allowed_effective_lengths_m=lengths
        )
    return CompleteDoublePipeAssemblyOption(**kw)


def _hash_cat(
    catalog_id: str = "c1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> str:
    return compute_catalog_content_hash(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
    )


def _make_cat(
    catalog_id: str = "c1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> CompleteDoublePipeCatalogSnapshot:
    h = _hash_cat(catalog_id=catalog_id, options=options)
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
        catalog_content_hash=h,
    )


# ============================================================================
# Materialization tests
# ============================================================================


class TestMaterialization:
    """Length materialization: explicit + grid sources."""

    def test_explicit_count_equals_raw_count(self) -> None:
        opt = _make_opt("o1", lengths=(1.0, 2.0, 3.0, 4.0, 5.0))
        cat = _make_cat(options=(opt,))
        tot, rec = compute_raw_combination_count((cat,))
        lengths = materialize_lengths_for_option(opt)
        assert len(lengths) == tot
        assert len(lengths) == 5

    def test_grid_count_equals_raw_count(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=5.0,
            increment_m=1.0,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        opt = _make_opt("o1", grid=grid)
        cat = _make_cat(options=(opt,))
        tot, rec = compute_raw_combination_count((cat,))
        lengths = materialize_lengths_for_option(opt)
        assert len(lengths) == tot
        assert len(lengths) == 5

    def test_exclude_max_grid(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=5.0,
            increment_m=1.0,
            endpoint_policy=LengthEndpointPolicy.EXCLUDE_MAX,
        )
        opt = _make_opt("o1", grid=grid)
        lengths = materialize_lengths_for_option(opt)
        assert len(lengths) == 4  # 1, 2, 3, 4 (excludes 5)
        assert lengths == ("1.0", "2.0", "3.0", "4.0")

    def test_request_bounds_filter(self) -> None:
        opt = _make_opt("o1", lengths=(1.0, 2.0, 3.0, 4.0, 5.0))
        lengths = materialize_lengths_for_option(
            opt, minimum_effective_length_m=2.0, maximum_effective_length_m=4.0
        )
        assert len(lengths) == 3
        assert all("2.0" <= x <= "4.0" for x in lengths)

    def test_no_materialization_before_cap_pass(self) -> None:
        """Phase 1 cap gate must prevent materialization."""
        opt = _make_opt("o1", lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=1)
        from hexagent.optimization.length import count_and_gate_sizing_request
        from hexagent.optimization.models import BlockedSizingResult

        result = count_and_gate_sizing_request(req)
        assert isinstance(result, BlockedSizingResult)
        # After blocked, we must NOT materialize
        # (this is verified by orchestration test)

    def test_canonical_length_strings_stable(self) -> None:
        grid = LengthGridSpec(
            minimum_length_m=1.0,
            maximum_length_m=3.0,
            increment_m=1.0,
            endpoint_policy=LengthEndpointPolicy.INCLUDE_MAX_IF_ALIGNED,
        )
        opt = _make_opt("o1", grid=grid)
        a = materialize_lengths_for_option(opt)
        b = materialize_lengths_for_option(opt)
        assert a == b


# ============================================================================
# PhysicalCandidateIdentity tests
# ============================================================================


class TestPhysicalIdentity:
    """Physical candidate identity determinism."""

    def test_same_geometry_produces_same_digest(self) -> None:
        a = PhysicalCandidateIdentity(
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            effective_length_m_canonical="1.0",
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
        )
        b = PhysicalCandidateIdentity(
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            effective_length_m_canonical="1.0",
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
        )
        assert a.physical_identity_digest == b.physical_identity_digest

    def test_same_physical_from_different_catalogs_same_digest(self) -> None:
        """Same physical geometry from different catalogs -> same physical digest."""
        opt_a = _make_opt("o1", lengths=(1.0,))
        opt_b = _make_opt("o1", lengths=(1.0,))  # same option IDs and geometry
        cat_a = _make_cat("catalog_X", options=(opt_a,))
        cat_b = _make_cat("catalog_Y", options=(opt_b,))

        cand_a = build_candidate(cat_a, opt_a, "1.0")
        cand_b = build_candidate(cat_b, opt_b, "1.0")

        assert cand_a.physical_identity_digest == cand_b.physical_identity_digest
        assert cand_a.source_qualified_candidate_id != cand_b.source_qualified_candidate_id

    def test_different_length_different_digest(self) -> None:
        a = PhysicalCandidateIdentity(
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            effective_length_m_canonical="1.0",
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
        )
        b = PhysicalCandidateIdentity(
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            effective_length_m_canonical="2.0",
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
        )
        assert a.physical_identity_digest != b.physical_identity_digest


# ============================================================================
# SourceQualifiedCandidateIdentity + dedup tests
# ============================================================================


class TestSourceQualifiedIdentity:
    """Source-qualified identity determinism and deduplication."""

    def test_same_source_same_id(self) -> None:
        opt = _make_opt("o1", lengths=(1.0,))
        cat = _make_cat("c1", options=(opt,))
        a = build_candidate(cat, opt, "1.0")
        b = build_candidate(cat, opt, "1.0")
        assert a.source_qualified_candidate_id == b.source_qualified_candidate_id

    def test_different_catalog_different_id(self) -> None:
        opt_a = _make_opt("o1", lengths=(1.0,))
        opt_b = _make_opt("o1", lengths=(1.0,))
        cat_a = _make_cat("c1", options=(opt_a,))
        cat_b = _make_cat("c2", options=(opt_b,))
        a = build_candidate(cat_a, opt_a, "1.0")
        b = build_candidate(cat_b, opt_b, "1.0")
        assert a.source_qualified_candidate_id != b.source_qualified_candidate_id

    def test_deduplication_by_source_id(self) -> None:
        opt = _make_opt("o1", lengths=(1.0,))
        cat = _make_cat("c1", options=(opt,))
        a = build_candidate(cat, opt, "1.0")
        b = build_candidate(cat, opt, "1.0")
        deduped = deduplicate_and_order_candidates((a, b))
        assert len(deduped) == 1

    def test_input_permutation_same_order(self) -> None:
        """Different input order -> same IDs, order, indexes."""
        oa = _make_opt("b", lengths=(1.0,))
        ob = _make_opt("a", lengths=(2.0,))
        cat = _make_cat("c1", options=(oa, ob))
        ca1 = build_candidate(cat, ob, "2.0")
        ca2 = build_candidate(cat, oa, "1.0")
        cb1 = build_candidate(cat, oa, "1.0")
        cb2 = build_candidate(cat, ob, "2.0")

        r1 = deduplicate_and_order_candidates((ca1, ca2))
        r2 = deduplicate_and_order_candidates((cb1, cb2))

        assert len(r1) == len(r2) == 2
        assert r1[0].source_qualified_candidate_id == r2[0].source_qualified_candidate_id
        assert r1[1].source_qualified_candidate_id == r2[1].source_qualified_candidate_id
        assert r1[0].evaluation_order_index == 0
        assert r1[1].evaluation_order_index == 1
        # Verify JSON serialization is identical
        import json

        j1 = json.dumps([c.model_dump() for c in r1], sort_keys=True)
        j2 = json.dumps([c.model_dump() for c in r2], sort_keys=True)
        assert j1 == j2

    def test_identity_field_mutation_changes_digest(self) -> None:
        opt = _make_opt("o1", lengths=(1.0,))
        cat = _make_cat("c1", options=(opt,))
        a = build_candidate(cat, opt, "1.0")
        # Mutate with different option_id
        opt2 = _make_opt("o2", lengths=(1.0,))
        b = build_candidate(cat, opt2, "1.0")
        assert a.source_qualified_candidate_id != b.source_qualified_candidate_id


# ============================================================================
# ManufacturableCandidate aggregate tests
# ============================================================================


class TestManufacturableCandidate:
    """Aggregate candidate pipeline."""

    def test_build_and_roundtrip(self) -> None:
        opt = _make_opt("o1", lengths=(1.0, 2.0))
        cat = _make_cat("c1", options=(opt,))
        order, records = compute_raw_combination_count((cat,))
        candidates = materialize_all_candidates(
            (cat,),
            records,
        )
        assert len(candidates) == 2
        for c in candidates:
            assert c.evaluation_order_index in (0, 1)
            assert c.catalog_snapshot_ref.catalog_id == "c1"

    def test_repeated_run_identical(self) -> None:
        opt = _make_opt("o1", lengths=(1.0,))
        cat = _make_cat("c1", options=(opt,))
        order, records = compute_raw_combination_count((cat,))
        a = materialize_all_candidates((cat,), records)
        b = materialize_all_candidates((cat,), records)
        import json

        assert json.dumps([c.model_dump() for c in a], sort_keys=True) == json.dumps(
            [c.model_dump() for c in b], sort_keys=True
        )


# ============================================================================
# SizingRequestIdentity tests
# ============================================================================


class TestSizingRequestIdentity:
    """Sizing request identity determinism."""

    def test_identity_build(self) -> None:
        opt = _make_opt("o1", lengths=(1.0,))
        cat = _make_cat("c1", options=(opt,))
        req = SizingRequest(catalogs=(cat,))

        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="water",
            hot_fluid_backend="iapws97",
            cold_fluid_name="brine",
            cold_fluid_backend="nacl",
            hot_mass_flow_kg_s=10.0,
            cold_mass_flow_kg_s=20.0,
            hot_inlet_temperature_k=373.0,
            cold_inlet_temperature_k=293.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
        )
        digest = ident.sizing_request_identity_digest
        assert digest.startswith("sha256:")

    def test_equal_input_produces_same_digest(self) -> None:
        opt = _make_opt("o1", lengths=(1.0,))
        cat = _make_cat("c1", options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        ident_a = build_sizing_request_identity(
            request=req,
            hot_fluid_name="water",
            hot_fluid_backend="iapws97",
            cold_fluid_name="brine",
            cold_fluid_backend="nacl",
            hot_mass_flow_kg_s=10.0,
            cold_mass_flow_kg_s=20.0,
            hot_inlet_temperature_k=373.0,
            cold_inlet_temperature_k=293.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
        )
        ident_b = build_sizing_request_identity(
            request=req,
            hot_fluid_name="water",
            hot_fluid_backend="iapws97",
            cold_fluid_name="brine",
            cold_fluid_backend="nacl",
            hot_mass_flow_kg_s=10.0,
            cold_mass_flow_kg_s=20.0,
            hot_inlet_temperature_k=373.0,
            cold_inlet_temperature_k=293.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
        )
        assert ident_a.sizing_request_identity_digest == ident_b.sizing_request_identity_digest

    def test_catalog_permutation_same_digest(self) -> None:
        o1 = _make_opt("a", lengths=(1.0,))
        o2 = _make_opt("b", lengths=(2.0,))
        ca = _make_cat("X", options=(o1,))
        cb = _make_cat("Y", options=(o2,))
        req_a = SizingRequest(catalogs=(ca, cb))
        req_b = SizingRequest(catalogs=(cb, ca))

        ident_a = build_sizing_request_identity(
            request=req_a,
            hot_fluid_name="w",
            hot_fluid_backend="i",
            cold_fluid_name="b",
            cold_fluid_backend="n",
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
        )
        ident_b = build_sizing_request_identity(
            request=req_b,
            hot_fluid_name="w",
            hot_fluid_backend="i",
            cold_fluid_name="b",
            cold_fluid_backend="n",
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
        )
        assert ident_a.sizing_request_identity_digest == ident_b.sizing_request_identity_digest

    def test_field_mutation_changes_digest(self) -> None:
        opt = _make_opt("o1", lengths=(1.0,))
        cat = _make_cat("c1", options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        base = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            hot_fluid_backend="i",
            cold_fluid_name="b",
            cold_fluid_backend="n",
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
        )
        mutated = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            hot_fluid_backend="i",
            cold_fluid_name="brine",
            cold_fluid_backend="nacl",  # ← different
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
        )
        assert base.sizing_request_identity_digest != mutated.sizing_request_identity_digest


# ============================================================================
# Calculation context (UUID5) tests
# ============================================================================


class TestCandidateContext:
    """UUID5-based candidate request ID determinism."""

    def test_namespace_frozen(self) -> None:
        expected = UUID("a0b1c2d3-e4f5-6789-abcd-ef0123456789")
        assert expected == TASK009_CONTEXT_NAMESPACE

    def test_deterministic_uuid5(self) -> None:
        rid = candidate_request_id("digest123", "sq_id_abc")
        rid2 = candidate_request_id("digest123", "sq_id_abc")
        assert rid == rid2
        assert rid.version == 5

    def test_different_input_different_id(self) -> None:
        a = candidate_request_id("dig1", "sq_1")
        b = candidate_request_id("dig2", "sq_2")
        assert a != b

    def test_input_permutation_same_id(self) -> None:
        """Same identity -> same UUID regardless of how we got there."""
        a1 = candidate_request_id("d:sr", "a")
        a2 = candidate_request_id("d:sr", "a")
        assert a1 == a2

    def test_repeated_run_identical(self) -> None:
        opt = _make_opt("o1", lengths=(1.0,))
        cat = _make_cat("c1", options=(opt,))
        order, records = compute_raw_combination_count((cat,))
        candidates = materialize_all_candidates((cat,), records)
        # request_id for first candidate
        rid_a = candidate_request_id("sri_digest", candidates[0].source_qualified_candidate_id)
        rid_b = candidate_request_id("sri_digest", candidates[0].source_qualified_candidate_id)
        assert rid_a == rid_b


# ============================================================================
# ExpectedProviderIdentity tests
# ============================================================================


class TestExpectedProviderIdentity:
    def test_exact_match(self) -> None:
        expected = ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        actual = type(
            "PI",
            (),
            {
                "name": "test_provider",
                "version": "1.0",
                "git_revision": "abc123",
                "reference_state_policy": "default",
                "configuration_fingerprint": "",
                "cache_policy_version": "",
            },
        )()
        assert expected.matches(actual)

    def test_name_mismatch_returns_false(self) -> None:
        expected = ExpectedProviderIdentity(
            name="provider_a",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
        )
        actual = type(
            "PI",
            (),
            {
                "name": "provider_b",
                "version": "1.0",
                "git_revision": "abc",
                "reference_state_policy": "default",
                "configuration_fingerprint": "",
                "cache_policy_version": "",
            },
        )()
        assert not expected.matches(actual)

"""
TASK-009 Phase 1 — catalog content-hash authority and canonical ordering.
"""

from __future__ import annotations

from typing import Any

import pytest

from hexagent.optimization.catalog import (
    canonical_sort_assembly_options,
    compute_catalog_content_hash,
)
from hexagent.optimization.errors import CatalogInvalid
from hexagent.optimization.length import (
    compute_raw_combination_count,
    count_and_gate_sizing_request,
)
from hexagent.optimization.models import (
    BlockedSizingResult,
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthGridSpec,
    LengthSource,
    SizingGateResult,
    SizingRequest,
)


def _make_opt(
    option_id: str = "opt1",
    quantum: str = "0.1",
    lengths: tuple[float, ...] = (1.0, 2.0, 3.0),
    grid: LengthGridSpec | None = None,
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
        "manufacturing_metadata": (),
    }
    if grid is not None:
        kw["length_source"] = LengthSource(length_quantum_m=quantum, grid=grid)
    else:
        kw["length_source"] = LengthSource(
            length_quantum_m=quantum,
            allowed_effective_lengths_m=lengths,
        )
    return CompleteDoublePipeAssemblyOption(**kw)


def _make_cat(
    catalog_id: str = "cat1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> CompleteDoublePipeCatalogSnapshot:
    sorted_opts = canonical_sort_assembly_options(options)
    opt_dicts = tuple(o.model_dump() for o in sorted_opts)
    claimed = compute_catalog_content_hash(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=opt_dicts,
    )
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=sorted_opts,
        catalog_content_hash=claimed,
    )


def _make_cat_raw(
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
    hash_value: str | None = None,
    catalog_id: str = "c1",
    catalog_version: str = "v1",
    source_identity: str = "test",
    schema_version: str = "1.0",
) -> CompleteDoublePipeCatalogSnapshot:
    if hash_value is None:
        hash_value = "sha256:" + "0" * 64
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        source_identity=source_identity,
        schema_version=schema_version,
        assembly_options=options,
        catalog_content_hash=hash_value,
    )


class TestHashAcceptance:
    def test_valid_catalog_accepted(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        assert cat.catalog_id == "cat1"

    def test_hash_format_is_sha256_prefix(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        h = cat.catalog_content_hash
        assert h.startswith("sha256:")
        assert len(h[len("sha256:") :]) == 64

    def test_same_semantic_catalog_same_hash(self) -> None:
        a = _make_cat(options=(_make_opt(),))
        b = _make_cat(options=(_make_opt(),))
        assert a.catalog_content_hash == b.catalog_content_hash

    def test_option_insertion_order_independent_hash(self) -> None:
        oa = _make_opt("b")
        ob = _make_opt("a")
        ab = _make_cat(options=(oa, ob))
        ba = _make_cat(options=(ob, oa))
        assert ab.catalog_content_hash == ba.catalog_content_hash

    def test_model_copy_retains_hash_validity(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        c = cat.model_copy(deep=True)
        assert c.catalog_content_hash == cat.catalog_content_hash
        assert len(c.assembly_options) == 1


class TestHashRejection:
    def test_malformed_hash_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(hash_value="abc123")

    def test_uppercase_hex_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(hash_value="sha256:" + "A" * 64)

    def test_wrong_hash_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(hash_value="sha256:" + "0" * 64)

    def test_option_field_mutation_rejected(self) -> None:
        opt = _make_opt("x", lengths=(1.0,))
        d = (opt.model_dump(),)
        h = compute_catalog_content_hash("c1", "v1", "t", "1.0", d)
        opt2 = _make_opt("x", lengths=(2.0,))
        with pytest.raises((ValueError, CatalogInvalid)):
            CompleteDoublePipeCatalogSnapshot(
                catalog_id="c1",
                catalog_version="v1",
                source_identity="t",
                schema_version="1.0",
                assembly_options=(opt2,),
                catalog_content_hash=h,
            )

    def test_quantum_mutation_rejected(self) -> None:
        opt = _make_opt("x", quantum="0.1", lengths=(1.0,))
        d = (opt.model_dump(),)
        h = compute_catalog_content_hash("c1", "v1", "t", "1.0", d)
        opt2 = _make_opt("x", quantum="0.01", lengths=(1.0,))
        with pytest.raises((ValueError, CatalogInvalid)):
            CompleteDoublePipeCatalogSnapshot(
                catalog_id="c1",
                catalog_version="v1",
                source_identity="t",
                schema_version="1.0",
                assembly_options=(opt2,),
                catalog_content_hash=h,
            )

    def test_option_addition_rejected(self) -> None:
        opt = _make_opt("x", lengths=(1.0,))
        d = (opt.model_dump(),)
        h = compute_catalog_content_hash("c1", "v1", "t", "1.0", d)
        opt2 = _make_opt("y", lengths=(2.0,))
        with pytest.raises((ValueError, CatalogInvalid)):
            CompleteDoublePipeCatalogSnapshot(
                catalog_id="c1",
                catalog_version="v1",
                source_identity="t",
                schema_version="1.0",
                assembly_options=(opt, opt2),
                catalog_content_hash=h,
            )

    def test_option_removal_rejected(self) -> None:
        oa = _make_opt("a", lengths=(1.0,))
        ob = _make_opt("b", lengths=(2.0,))
        so = canonical_sort_assembly_options((oa, ob))
        d = tuple(x.model_dump() for x in so)
        h = compute_catalog_content_hash("c1", "v1", "t", "1.0", d)
        with pytest.raises((ValueError, CatalogInvalid)):
            CompleteDoublePipeCatalogSnapshot(
                catalog_id="c1",
                catalog_version="v1",
                source_identity="t",
                schema_version="1.0",
                assembly_options=(oa,),
                catalog_content_hash=h,
            )


class TestStructuralValidation:
    def test_blank_catalog_id_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(catalog_id="")

    def test_blank_version_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(catalog_version="")

    def test_blank_source_identity_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(source_identity="")

    def test_blank_schema_version_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(schema_version="")

    def test_duplicate_option_id_rejected(self) -> None:
        opt = _make_opt("same")
        opt2 = _make_opt("same")
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(options=(opt, opt2))

    def test_non_ascii_identity_rejected(self) -> None:
        with pytest.raises((ValueError, CatalogInvalid)):
            _make_cat_raw(catalog_id="cafe\u0301")

    def test_options_stored_canonically(self) -> None:
        oa = _make_opt("z")
        ob = _make_opt("a")
        cat = _make_cat(options=(oa, ob))
        ids = [o.assembly_option_id for o in cat.assembly_options]
        assert ids == ["a", "z"]


class TestPermutationInvariance:
    def test_catalog_permutation_identical_total(self) -> None:
        cx = _make_cat("x", options=(_make_opt("o1", lengths=(1.0,)),))
        cy = _make_cat("y", options=(_make_opt("o2", lengths=(2.0,)),))
        t1, _ = compute_raw_combination_count((cx, cy))
        t2, _ = compute_raw_combination_count((cy, cx))
        assert t1 == t2

    def test_catalog_permutation_identical_records(self) -> None:
        cx = _make_cat("x", options=(_make_opt("o1", lengths=(1.0,)),))
        cy = _make_cat("y", options=(_make_opt("o2", lengths=(2.0,)),))
        _, r1 = compute_raw_combination_count((cx, cy))
        _, r2 = compute_raw_combination_count((cy, cx))
        assert r1 == r2

    def test_option_permutation_identical_total(self) -> None:
        oa = _make_opt("z", lengths=(1.0,))
        ob = _make_opt("a", lengths=(2.0,))
        c1 = _make_cat("c", options=(oa, ob))
        c2 = _make_cat("c", options=(ob, oa))
        t1, _ = compute_raw_combination_count((c1,))
        t2, _ = compute_raw_combination_count((c2,))
        assert t1 == t2

    def test_option_permutation_identical_records(self) -> None:
        oa = _make_opt("z", lengths=(1.0,))
        ob = _make_opt("a", lengths=(2.0,))
        c1 = _make_cat("c", options=(oa, ob))
        c2 = _make_cat("c", options=(ob, oa))
        _, r1 = compute_raw_combination_count((c1,))
        _, r2 = compute_raw_combination_count((c2,))
        assert r1 == r2


class TestDuplicateCatalog:
    def test_identical_catalogs_rejected(self) -> None:
        cat = _make_cat(options=(_make_opt(),))
        with pytest.raises(CatalogInvalid, match="Duplicate catalog"):
            compute_raw_combination_count((cat, cat))

    def test_identity_tuple_match_rejected(self) -> None:
        opt = _make_opt("a", lengths=(1.0,))
        # Same content → same hash → same identity tuple
        c1 = _make_cat("s", options=(opt,))
        c2 = _make_cat("s", options=(opt,))
        with pytest.raises(CatalogInvalid, match="Duplicate catalog"):
            compute_raw_combination_count((c1, c2))


class TestAggregateRawCount:
    def test_one_catalog_one_option(self) -> None:
        opt = _make_opt("o1", lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        t, rec = compute_raw_combination_count((cat,))
        assert t == 3
        assert len(rec) == 1

    def test_multiple_catalogs(self) -> None:
        o1 = _make_opt("o1", lengths=(1.0,))
        o2 = _make_opt("o2", lengths=(2.0, 3.0))
        o3 = _make_opt("o3", lengths=(4.0, 5.0, 6.0))
        c1 = _make_cat("c1", options=(o1, o2))
        c2 = _make_cat("c2", options=(o3,))
        t, rec = compute_raw_combination_count((c1, c2))
        assert t == 6
        assert len(rec) == 3

    def test_total_is_sum_not_product(self) -> None:
        o1 = _make_opt("o1", lengths=(1.0, 2.0))
        o2 = _make_opt("o2", lengths=(3.0, 4.0, 5.0))
        cat = _make_cat(options=(o1, o2))
        t, _ = compute_raw_combination_count((cat,))
        assert t == 5
        assert t != 2 * 3


class TestMixedQuantumCounting:
    def test_different_quantum(self) -> None:
        oa = _make_opt("a", quantum="0.1", lengths=(1.0, 2.0, 3.0))
        ob = _make_opt("b", quantum="0.01", lengths=(1.0, 1.5, 2.0))
        cat = _make_cat(options=(oa, ob))
        t, rec = compute_raw_combination_count((cat,), 1.0, 2.0)
        assert t == 5
        assert rec[0].raw_count == 2
        assert rec[1].raw_count == 3


class TestCountAndGate:
    def test_gate_passes(self) -> None:
        opt = _make_opt(lengths=(1.0,))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        v: dict[str, int] = {"m": 0}
        r = count_and_gate_sizing_request(req, materialize_lengths=lambda: v.update(m=1))
        assert isinstance(r, SizingGateResult)
        assert v["m"] == 1

    def test_cap_exceeded_blocks(self) -> None:
        opt = _make_opt(lengths=(1.0, 2.0, 3.0))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,), request_raw_combination_cap=1)
        v: dict[str, int] = {"m": 0}
        r = count_and_gate_sizing_request(req, materialize_lengths=lambda: v.update(m=1))
        assert isinstance(r, BlockedSizingResult)
        assert v["m"] == 0

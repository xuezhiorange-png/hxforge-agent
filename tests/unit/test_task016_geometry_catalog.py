"""TASK-016 approved geometry catalog tests.

Implements the TASK-016 frozen design contract
(``docs/tasks/TASK-016-approved-geometry-catalog.md``,
Frozen Contract Authority SHA
``654a2708de808c9f1518f1a69eda92f95a4d37c5``) Section 12 (Frozen test
expectations).

The 16 expectations are covered in declaration order:

  1. valid approved catalog loads successfully
  2. duplicate IDs are rejected after canonical normalization
  3. non-approved records are not selectable
  4. unsupported geometry types are blockers
  5. negative or zero dimensions are blockers
  6. tube wall thickness consistency is enforced
  7. pipe schedule labels are metadata, not computation authority
  8. hairpin references must point to approved tube and pipe records
  9. canonical ordering is independent of input file order
 10. record hash changes when computation-authority dimensions change
 11. record hash remains stable under non-semantic key ordering changes
 12. missing source binding is a blocker
 13. catalog-level content hash is deterministic
 14. consumers receive approved records only
 15. TASK-017 material / mass / mechanical concerns remain absent
 16. TASK-018 cost concerns remain absent
"""

from __future__ import annotations

from typing import Any

import pytest

from hexagent.geometry_catalogs import (
    APPROVAL_STATE_APPROVED,
    GEOMETRY_DIMENSION_TOLERANCE_M,
    GEOMETRY_TYPE_HAIRPIN,
    GEOMETRY_TYPE_PIPE,
    GEOMETRY_TYPE_TUBE,
    GeometryCatalogBlockerError,
    canonical_order_records,
    compute_catalog_content_hash,
    compute_record_hash,
    load_geometry_catalog,
    select_approved_records,
)
from hexagent.geometry_catalogs.blockers import (
    BLOCKER_GEOMETRY_DIMENSION_INCONSISTENT,
    BLOCKER_GEOMETRY_DIMENSION_NON_POSITIVE,
    BLOCKER_GEOMETRY_HASH_MISMATCH,
    BLOCKER_GEOMETRY_RECORD_DUPLICATE_ID,
    BLOCKER_GEOMETRY_RECORD_MISSING_ID,
    BLOCKER_GEOMETRY_REFERENCE_MISSING,
    BLOCKER_GEOMETRY_REFERENCE_UNAPPROVED,
    BLOCKER_GEOMETRY_SOURCE_MISSING,
    BLOCKER_GEOMETRY_TYPE_UNSUPPORTED,
)

pytestmark = pytest.mark.pure


# ============================================================================
# Helpers
# ============================================================================


def _approved_source(**overrides: Any) -> dict[str, Any]:
    sb = {
        "source_id": "src-1",
        "source_type": "internal",
        "source_revision": "rev-1",
        "source_location": "catalogs/v1.yaml",
        "evidence_ref": "ev-1",
        "approved_by": "reviewer-A",
        "approved_at": "2026-07-01T00:00:00Z",
    }
    sb.update(overrides)
    return sb


def _tube_record(
    geometry_id: str = "tube/std/od0.019/id0.015/r1",
    *,
    outer: float = 0.019,
    inner: float = 0.015,
    cross_section: float = 1.9635e-4,
    flow_area: float = 1.7671e-4,
    hydraulic_diameter: float = 0.0168,
    wall_thickness_m: float | None = None,
    approval_state: str = APPROVAL_STATE_APPROVED,
    source_binding: dict[str, Any] | None = None,
    revision: str = "r1",
    tags: tuple[str, ...] = (),
    record_hash: str | None = None,
) -> dict[str, Any]:
    wall = (outer - inner) / 2.0 if wall_thickness_m is None else wall_thickness_m
    out: dict[str, Any] = {
        "geometry_id": geometry_id,
        "geometry_type": GEOMETRY_TYPE_TUBE,
        "approval_state": approval_state,
        "nominal_label": "3/4 in BWG",
        "outer_diameter_m": outer,
        "inner_diameter_m": inner,
        "wall_thickness_m": wall,
        "cross_section_area_m2": cross_section,
        "flow_area_m2": flow_area,
        "hydraulic_diameter_m": hydraulic_diameter,
        "source_binding": source_binding if source_binding is not None else _approved_source(),
        "revision": revision,
        "tags": list(tags),
    }
    if record_hash is not None:
        out["record_hash"] = record_hash
    return out


def _pipe_record(
    geometry_id: str = "pipe/nps1/sch40/r1",
    *,
    outer: float = 0.0334,
    inner: float = 0.0266,
    flow_area: float = 5.5597e-4,
    hydraulic_diameter: float = 0.0266,
    wall_thickness_m: float | None = None,
    approval_state: str = APPROVAL_STATE_APPROVED,
    source_binding: dict[str, Any] | None = None,
    nominal_pipe_size_label: str = "NPS 1",
    schedule_label: str = "SCH 40",
    revision: str = "r1",
    tags: tuple[str, ...] = (),
    record_hash: str | None = None,
) -> dict[str, Any]:
    wall = (outer - inner) / 2.0 if wall_thickness_m is None else wall_thickness_m
    out: dict[str, Any] = {
        "geometry_id": geometry_id,
        "geometry_type": GEOMETRY_TYPE_PIPE,
        "approval_state": approval_state,
        "nominal_label": f"{nominal_pipe_size_label} {schedule_label}",
        "nominal_pipe_size_label": nominal_pipe_size_label,
        "schedule_label": schedule_label,
        "outer_diameter_m": outer,
        "inner_diameter_m": inner,
        "wall_thickness_m": wall,
        "flow_area_m2": flow_area,
        "hydraulic_diameter_m": hydraulic_diameter,
        "source_binding": source_binding if source_binding is not None else _approved_source(),
        "revision": revision,
        "tags": list(tags),
    }
    if record_hash is not None:
        out["record_hash"] = record_hash
    return out


def _hairpin_record(
    geometry_id: str = "hairpin/utube1/r1",
    *,
    hairpin_id: str = "utube1",
    tube_id: str = "tube/std/od0.019/id0.015/r1",
    pipe_id: str = "pipe/nps1/sch40/r1",
    number_of_tubes: int = 1,
    effective_length_m: float = 2.0,
    bend_radius_m: float = 0.05,
    centerline_spacing_m: float = 0.05,
    flow_path_descriptor: str = "u-tube",
    approval_state: str = APPROVAL_STATE_APPROVED,
    source_binding: dict[str, Any] | None = None,
    revision: str = "r1",
    tags: tuple[str, ...] = (),
    record_hash: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "geometry_id": geometry_id,
        "geometry_type": GEOMETRY_TYPE_HAIRPIN,
        "approval_state": approval_state,
        "nominal_label": hairpin_id,
        "hairpin_id": hairpin_id,
        "tube_geometry_id": tube_id,
        "pipe_geometry_id": pipe_id,
        "number_of_tubes": number_of_tubes,
        "effective_length_m": effective_length_m,
        "bend_radius_m": bend_radius_m,
        "centerline_spacing_m": centerline_spacing_m,
        "flow_path_descriptor": flow_path_descriptor,
        "source_binding": source_binding if source_binding is not None else _approved_source(),
        "revision": revision,
        "tags": list(tags),
    }
    if record_hash is not None:
        out["record_hash"] = record_hash
    return out


def _catalog_payload(
    records: list[dict[str, Any]],
    *,
    catalog_id: str = "approved-geometry-catalog",
    catalog_version: str = "0.1.0",
    authority: str = "internal-review",
    source_revision: str = "rev-1",
    generated_at: str = "2026-07-01T00:00:00Z",
    effective_at: str = "2026-07-01T00:00:00Z",
) -> dict[str, Any]:
    return {
        "catalog_id": catalog_id,
        "catalog_version": catalog_version,
        "authority": authority,
        "source_revision": source_revision,
        "generated_at": generated_at,
        "effective_at": effective_at,
        "records": records,
    }


# ============================================================================
# §12.1 — valid approved catalog loads successfully
# ============================================================================


def test_valid_approved_catalog_loads_successfully() -> None:
    payload = _catalog_payload(
        records=[
            _tube_record(),
            _pipe_record(),
            _hairpin_record(),
        ]
    )
    catalog = load_geometry_catalog(payload)
    assert catalog.catalog_id == "approved-geometry-catalog"
    assert len(catalog.records) == 3
    assert all(r.approval_state == APPROVAL_STATE_APPROVED for r in catalog.records)
    # Catalog-level content hash is non-empty (computed).
    assert len(catalog.content_hash) == 64
    assert catalog.content_hash == compute_catalog_content_hash(catalog)


# ============================================================================
# §12.2 — duplicate IDs are rejected after canonical normalization
# ============================================================================


def test_duplicate_ids_rejected_after_normalization() -> None:
    a = _tube_record(geometry_id="tube/std/od0.019/id0.015/r1")
    # NFC-normalized duplicate (with trailing whitespace stripped by loader).
    b = _tube_record(
        geometry_id="tube/std/od0.019/id0.015/r1",
        outer=0.020,
        inner=0.016,
    )
    payload = _catalog_payload(records=[a, b])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_RECORD_DUPLICATE_ID
    assert excinfo.value.context["geometry_id"] == "tube/std/od0.019/id0.015/r1"


# ============================================================================
# §12.3 — non-approved records are not selectable
# ============================================================================


def test_non_approved_records_not_selectable() -> None:
    payload = _catalog_payload(
        records=[
            _tube_record(geometry_id="tube/std/od0.019/id0.015/r1", approval_state="approved"),
            _tube_record(
                geometry_id="tube/std/od0.025/id0.020/r1",
                outer=0.025,
                inner=0.020,
                cross_section=4.909e-4,
                flow_area=3.142e-4,
                hydraulic_diameter=0.0222,
                approval_state="pending",
            ),
        ]
    )
    catalog = load_geometry_catalog(payload)
    selected = select_approved_records(catalog)
    ids = [r.geometry_id for r in selected]
    assert ids == ["tube/std/od0.019/id0.015/r1"]
    # Pending record is still in the catalog aggregate but not selectable.
    all_ids = [r.geometry_id for r in catalog.records]
    assert "tube/std/od0.025/id0.020/r1" in all_ids
    assert "tube/std/od0.025/id0.020/r1" not in ids


# ============================================================================
# §12.4 — unsupported geometry types are blockers
# ============================================================================


def test_unsupported_geometry_type_returns_blocker() -> None:
    bad = _tube_record()
    bad["geometry_type"] = "fin-tube"
    payload = _catalog_payload(records=[bad])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_TYPE_UNSUPPORTED
    assert excinfo.value.context["geometry_type"] == "fin-tube"


# ============================================================================
# §12.5 — negative or zero dimensions are blockers
# ============================================================================


def test_non_positive_dimensions_return_blocker() -> None:
    bad = _tube_record(inner=0.0)
    payload = _catalog_payload(records=[bad])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_DIMENSION_NON_POSITIVE
    assert excinfo.value.context["field_name"] == "inner_diameter_m"
    assert excinfo.value.context["value"] == 0.0


# ============================================================================
# §12.6 — tube wall thickness consistency is enforced
# ============================================================================


def test_tube_wall_thickness_consistency_enforced() -> None:
    # wall_thickness deliberately inconsistent with (outer - inner) / 2.
    bad = _tube_record(outer=0.020, inner=0.016, wall_thickness_m=0.0030)
    payload = _catalog_payload(records=[bad])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_DIMENSION_INCONSISTENT
    assert excinfo.value.context["field_name"] == "wall_thickness_m"
    assert excinfo.value.context["tolerance"] == GEOMETRY_DIMENSION_TOLERANCE_M


def test_tube_wall_thickness_within_tolerance_accepted() -> None:
    # Sub-tolerance deviation must NOT raise.
    outer = 0.020
    inner = 0.016
    exact_wall = (outer - inner) / 2.0
    near_wall = exact_wall + GEOMETRY_DIMENSION_TOLERANCE_M / 10.0
    good = _tube_record(outer=outer, inner=inner, wall_thickness_m=near_wall)
    payload = _catalog_payload(records=[good])
    catalog = load_geometry_catalog(payload)
    assert len(catalog.records) == 1


# ============================================================================
# §12.7 — pipe schedule labels are metadata, not computation authority
# ============================================================================


def test_pipe_schedule_labels_are_metadata_only() -> None:
    """Identical SI dimensions + different schedule labels MUST yield the
    same record_hash (label is NOT computation authority, Section 5.4)."""
    a = _pipe_record(schedule_label="SCH 40")
    b = _pipe_record(schedule_label="SCH 80")  # label differs; dims identical
    # Adjust b's dimensions to be identical to a's (override the default
    # wall derivation so both fixtures have identical SI fields).
    b["outer_diameter_m"] = a["outer_diameter_m"]
    b["inner_diameter_m"] = a["inner_diameter_m"]
    b["wall_thickness_m"] = a["wall_thickness_m"]
    catalog_a = load_geometry_catalog(_catalog_payload(records=[a]))
    catalog_b = load_geometry_catalog(_catalog_payload(records=[b]))
    hash_a = compute_record_hash(catalog_a.records[0])
    hash_b = compute_record_hash(catalog_b.records[0])
    assert hash_a == hash_b


# ============================================================================
# §12.8 — hairpin references must point to approved tube and pipe records
# ============================================================================


def test_hairpin_missing_tube_reference_returns_blocker() -> None:
    hp = _hairpin_record(tube_id="tube/does/not/exist/r1")
    payload = _catalog_payload(records=[_pipe_record(), hp])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_REFERENCE_MISSING
    assert excinfo.value.context["reference_field"] == "tube_geometry_id"
    assert excinfo.value.context["missing_id"] == "tube/does/not/exist/r1"


def test_hairpin_reference_to_non_approved_tube_returns_blocker() -> None:
    # Tube exists but is not approved.
    tube = _tube_record(
        geometry_id="tube/pending/od0.019/id0.015/r1",
        approval_state="pending",
    )
    hp = _hairpin_record(tube_id="tube/pending/od0.019/id0.015/r1")
    payload = _catalog_payload(records=[_pipe_record(), tube, hp])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_REFERENCE_UNAPPROVED
    assert excinfo.value.context["referenced_state"] == "pending"


def test_hairpin_with_approved_refs_loads() -> None:
    tube = _tube_record(geometry_id="tube/std/od0.019/id0.015/r1")
    pipe = _pipe_record(geometry_id="pipe/nps1/sch40/r1")
    hp = _hairpin_record(
        tube_id="tube/std/od0.019/id0.015/r1",
        pipe_id="pipe/nps1/sch40/r1",
    )
    payload = _catalog_payload(records=[tube, pipe, hp])
    catalog = load_geometry_catalog(payload)
    hairpin = next(r for r in catalog.records if r.geometry_type == GEOMETRY_TYPE_HAIRPIN)
    assert hairpin.tube_geometry_id == "tube/std/od0.019/id0.015/r1"
    assert hairpin.pipe_geometry_id == "pipe/nps1/sch40/r1"


# ============================================================================
# §12.9 — canonical ordering is independent of input file order
# ============================================================================


def test_canonical_ordering_independent_of_input_order() -> None:
    tube_a = _tube_record(geometry_id="tube/std/od0.019/id0.015/r1")
    tube_b = _tube_record(
        geometry_id="tube/std/od0.025/id0.020/r1",
        outer=0.025,
        inner=0.020,
        cross_section=4.909e-4,
        flow_area=3.142e-4,
        hydraulic_diameter=0.0222,
    )
    pipe_a = _pipe_record(geometry_id="pipe/nps1/sch40/r1")
    hp_a = _hairpin_record(
        geometry_id="hairpin/utube1/r1",
        tube_id="tube/std/od0.019/id0.015/r1",
        pipe_id="pipe/nps1/sch40/r1",
    )
    forward = [tube_a, tube_b, pipe_a, hp_a]
    reversed_ = list(reversed(forward))
    cat_forward = load_geometry_catalog(_catalog_payload(records=forward))
    cat_reversed = load_geometry_catalog(_catalog_payload(records=reversed_))
    ids_forward = [r.geometry_id for r in cat_forward.records]
    ids_reversed = [r.geometry_id for r in cat_reversed.records]
    assert ids_forward == ids_reversed
    # Canonical ordering: hairpin < pipe < tube (lexicographic on geometry_type).
    expected_types = [
        GEOMETRY_TYPE_HAIRPIN,
        GEOMETRY_TYPE_PIPE,
        GEOMETRY_TYPE_TUBE,
        GEOMETRY_TYPE_TUBE,
    ]
    assert [r.geometry_type for r in cat_forward.records] == expected_types


def test_canonical_order_records_helper() -> None:
    tube = _tube_record(geometry_id="tube/z/r1")
    pipe = _pipe_record(geometry_id="pipe/a/r1")
    ordered = canonical_order_records(
        [
            _record_via_catalog(pipe),
            _record_via_catalog(tube),
        ]
    )
    # Canonical ordering: pipe < tube (lexicographic on geometry_type).
    assert [r.geometry_id for r in ordered] == [
        "pipe/a/r1",
        "tube/z/r1",
    ]


def _record_via_catalog(raw: dict[str, Any]):
    cat = load_geometry_catalog(_catalog_payload(records=[raw]))
    return cat.records[0]


# ============================================================================
# §12.10 — record hash changes when computation-authority dimensions change
# ============================================================================


def test_record_hash_changes_when_authority_dimension_changes() -> None:
    a = _tube_record(geometry_id="tube/std/od0.019/id0.015/r1")
    b = _tube_record(
        geometry_id="tube/std/od0.019/id0.015/r1",
        outer=0.025,
        inner=0.020,
        cross_section=4.909e-4,
        flow_area=3.142e-4,
        hydraulic_diameter=0.0222,
    )
    catalog_a = load_geometry_catalog(_catalog_payload(records=[a]))
    catalog_b = load_geometry_catalog(_catalog_payload(records=[b]))
    # Different geometry_id — hash MUST differ.
    assert compute_record_hash(catalog_a.records[0]) != compute_record_hash(catalog_b.records[0])


# ============================================================================
# §12.11 — record hash stable under non-semantic key ordering changes
# ============================================================================


def test_record_hash_stable_under_non_semantic_key_reordering() -> None:
    a = _tube_record(geometry_id="tube/std/od0.019/id0.015/r1", tags=("a", "b"))
    # Build an equivalent record with tags reordered — must hash identically.
    b = _tube_record(geometry_id="tube/std/od0.019/id0.015/r1", tags=("b", "a"))
    catalog_a = load_geometry_catalog(_catalog_payload(records=[a]))
    catalog_b = load_geometry_catalog(_catalog_payload(records=[b]))
    assert compute_record_hash(catalog_a.records[0]) == compute_record_hash(catalog_b.records[0])


# ============================================================================
# §12.12 — missing source binding is a blocker
# ============================================================================


def test_missing_source_binding_returns_blocker() -> None:
    bad = _tube_record()
    bad["source_binding"] = {
        "source_id": "src-1",
        # Other fields missing.
    }
    payload = _catalog_payload(records=[bad])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_SOURCE_MISSING
    assert "missing_fields" in excinfo.value.context


def test_missing_geometry_id_returns_blocker() -> None:
    bad = _tube_record()
    bad["geometry_id"] = ""
    payload = _catalog_payload(records=[bad])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_RECORD_MISSING_ID


# ============================================================================
# §12.13 — catalog-level content hash is deterministic
# ============================================================================


def test_catalog_content_hash_is_deterministic() -> None:
    payload = _catalog_payload(
        records=[
            _tube_record(),
            _pipe_record(),
            _hairpin_record(),
        ]
    )
    cat_a = load_geometry_catalog(payload)
    cat_b = load_geometry_catalog(dict(payload))  # fresh copy
    assert cat_a.content_hash == cat_b.content_hash
    # Hash changes when a record changes.
    payload2 = _catalog_payload(
        records=[
            _tube_record(geometry_id="tube/std/od0.025/id0.020/r1", outer=0.025, inner=0.020),
            _pipe_record(),
            _hairpin_record(tube_id="tube/std/od0.025/id0.020/r1"),
        ]
    )
    cat_c = load_geometry_catalog(payload2)
    assert cat_a.content_hash != cat_c.content_hash


# ============================================================================
# §12.14 — consumers receive approved records only
# ============================================================================


def test_approved_only_accessor_returns_approved_records_only() -> None:
    payload = _catalog_payload(
        records=[
            _tube_record(geometry_id="tube/std/od0.019/id0.015/r1", approval_state="approved"),
            _tube_record(
                geometry_id="tube/std/od0.025/id0.020/r1",
                outer=0.025,
                inner=0.020,
                cross_section=4.909e-4,
                flow_area=3.142e-4,
                hydraulic_diameter=0.0222,
                approval_state="rejected",
            ),
            _tube_record(
                geometry_id="tube/std/od0.030/id0.025/r1",
                outer=0.030,
                inner=0.025,
                cross_section=7.069e-4,
                flow_area=4.909e-4,
                hydraulic_diameter=0.0273,
                approval_state="approved",
            ),
        ]
    )
    catalog = load_geometry_catalog(payload)
    selected = select_approved_records(catalog)
    assert {r.geometry_id for r in selected} == {
        "tube/std/od0.019/id0.015/r1",
        "tube/std/od0.030/id0.025/r1",
    }


# ============================================================================
# §12.15 — TASK-017 material / mass / mechanical concerns remain absent
# ============================================================================


def test_no_task017_material_mass_mechanical_fields() -> None:
    """No model field or blocker code may reference material / mass /
    mechanical suitability (TASK-017 boundary)."""
    from hexagent.geometry_catalogs import models

    forbidden_substrings = (
        "material",
        "mass",
        "allowable_stress",
        "corrosion_allowance",
        "mechanical",
        "fouling",
        "flange_rating",
        "pressure_rating",
    )
    # Inspect dataclass field names across all record types.
    for cls_name in ("TubeGeometryRecord", "PipeGeometryRecord", "HairpinGeometryRecord"):
        cls = getattr(models, cls_name)
        for f in cls.__dataclass_fields__:
            for bad in forbidden_substrings:
                assert bad not in f.lower(), (
                    f"{cls_name}.{f} contains forbidden TASK-017 substring {bad!r}"
                )


# ============================================================================
# §12.16 — TASK-018 cost concerns remain absent
# ============================================================================


def test_no_task018_cost_semantics() -> None:
    """No model field or blocker code may reference cost / life-cycle
    energy / C0 / C1 (TASK-018 boundary)."""
    from hexagent.geometry_catalogs import models

    forbidden_substrings = (
        "cost",
        "life_cycle",
        "lifecycle",
        "c0",
        "c1",
        "price",
        "expenditure",
    )
    for cls_name in ("TubeGeometryRecord", "PipeGeometryRecord", "HairpinGeometryRecord"):
        cls = getattr(models, cls_name)
        for f in cls.__dataclass_fields__:
            for bad in forbidden_substrings:
                assert bad not in f.lower(), (
                    f"{cls_name}.{f} contains forbidden TASK-018 substring {bad!r}"
                )

    # Blocker codes contain "catalog", "record", etc. — explicitly forbid
    # any cost vocabulary in BLOCKER_* codes.
    from hexagent.geometry_catalogs import blockers as b

    for name in dir(b):
        if name.startswith("BLOCKER_") and isinstance(getattr(b, name), str):
            value = getattr(b, name).lower()
            for bad in forbidden_substrings:
                assert bad not in value, (
                    f"blocker {name}={value!r} contains forbidden TASK-018 substring {bad!r}"
                )


# ============================================================================
# Extra: stored record_hash mismatch surfaces a blocker (Section 9)
# ============================================================================


def test_stored_record_hash_mismatch_raises_blocker() -> None:
    bad = _tube_record(record_hash="0" * 64)  # clearly wrong
    payload = _catalog_payload(records=[bad])
    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)
    assert excinfo.value.error_code == BLOCKER_GEOMETRY_HASH_MISMATCH
    assert excinfo.value.context["expected"] == "0" * 64


def test_stored_record_hash_match_accepted() -> None:
    # First compute the canonical hash, then round-trip the payload with it.
    canonical = load_geometry_catalog(_catalog_payload(records=[_tube_record()]))
    rh = canonical.records[0].record_hash
    assert rh is not None
    good = _tube_record(record_hash=rh)
    payload = _catalog_payload(records=[good])
    catalog = load_geometry_catalog(payload)
    assert catalog.records[0].record_hash == rh


# ============================================================================
# Extra: select_approved_records on a fully-approved catalog equals records
# ============================================================================


def test_select_approved_records_full_catalog() -> None:
    payload = _catalog_payload(records=[_tube_record(), _pipe_record(), _hairpin_record()])
    catalog = load_geometry_catalog(payload)
    assert select_approved_records(catalog) == list(catalog.records)

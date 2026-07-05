"""Deterministic catalog loader, validator, canonical ordering, hashing.

Implements the TASK-016 frozen design contract
(``docs/tasks/TASK-016-approved-geometry-catalog.md``,
Frozen Contract Authority SHA
``654a2708de808c9f1518f1a69eda92f95a4d37c5``) Section 7 (Identity, ordering,
hashing) and Section 11 (Future implementation contract).

Public surface in this first slice:

* :func:`load_geometry_catalog` — load + validate from a Python mapping.
* :func:`canonical_order_records` — sort records by ``(geometry_type,
  geometry_id, revision, record_hash)`` (Section 7.2).
* :func:`compute_record_hash` — SHA-256 hex digest of the canonical JSON
  representation of a single record (Section 7.3).
* :func:`compute_catalog_content_hash` — SHA-256 hex digest of the canonical
  JSON representation of the catalog aggregate (Section 5.1 / 7.3).
* :func:`select_approved_records` — approved-only accessor (Section 5.2 +
  Section 10).

Hashing uses the shared canonical JSON helper
(``hexagent.canonical_json``), which already implements RFC 8785 with NFC
normalization, deterministic key ordering, and shortest-round-trippable
numeric serialization. The TASK-016 implementation deliberately reuses this
helper rather than introducing parallel infrastructure (Section 11
"canonical hash helper integration").

The deterministic dimensional tolerance is exposed as
:data:`GEOMETRY_DIMENSION_TOLERANCE_M` (Section 5.3 + Section 6 + Section
8). It is a single internal constant covered by tests (Section 12 frozen
test expectations).
"""

from __future__ import annotations

from typing import Any, Final

from hexagent.canonical_json import canonical_sha256
from hexagent.geometry_catalogs.blockers import (
    GeometryCatalogBlockerError,
    geometry_catalog_missing,
    geometry_dimension_inconsistent,
    geometry_dimension_non_positive,
    geometry_hash_mismatch,
    geometry_record_duplicate_id,
    geometry_record_missing_id,
    geometry_record_unapproved,
    geometry_reference_missing,
    geometry_reference_unapproved,
    geometry_source_missing,
    geometry_type_unsupported,
)
from hexagent.geometry_catalogs.models import (
    APPROVAL_STATE_APPROVED,
    GEOMETRY_TYPE_PIPE,
    GEOMETRY_TYPE_TUBE,
    SELECTABLE_APPROVAL_STATES,
    VALID_APPROVAL_STATES,
    VALID_GEOMETRY_TYPES,
    GeometryCatalog,
    GeometryRecord,
    HairpinGeometryRecord,
    PipeGeometryRecord,
    SourceBinding,
    TubeGeometryRecord,
)

# --- Tolerances (Section 5.3 + Section 6 + Section 8) -----------------------

# Single internal constant for derived dimensional consistency checks.
# 1e-9 m = 1 nm — strict enough to reject inconsistent records (e.g., tube
# wall-thickness identity), generous enough to absorb IEEE-754 round-off
# from in-memory catalog fixtures. Covered by tests (Section 12 #6).
GEOMETRY_DIMENSION_TOLERANCE_M: Final[float] = 1e-9


# --- Canonical record hashing (Section 7) -----------------------------------


def _record_to_canonical_dict(record: GeometryRecord) -> dict[str, Any]:
    """Convert a record to the JSON-compatible dict used for hashing.

    Only the seven §8 SourceBinding fields plus the dimensional / identifier
    fields are hashed; ``record_hash`` itself is excluded (mirrors the
    ``canonical_hash`` exclusion in ``hexagent.canonical_json``). Display
    labels (``nominal_label``, ``nominal_pipe_size_label``, ``schedule_label``,
    ``flow_path_descriptor``) are metadata per §5.4 and are excluded from
    the hash so that label-only changes do not perturb ``record_hash``.
    """
    sb = record.source_binding
    base: dict[str, Any] = {
        "geometry_id": record.geometry_id,
        "geometry_type": record.geometry_type,
        "approval_state": record.approval_state,
        "revision": record.revision,
        "source_binding": {
            "source_id": sb.source_id,
            "source_type": sb.source_type,
            "source_revision": sb.source_revision,
            "source_location": sb.source_location,
            "evidence_ref": sb.evidence_ref,
            "approved_by": sb.approved_by,
            "approved_at": sb.approved_at,
        },
        "tags": sorted(record.tags),
    }
    if isinstance(record, TubeGeometryRecord):
        base["outer_diameter_m"] = record.outer_diameter_m
        base["inner_diameter_m"] = record.inner_diameter_m
        base["wall_thickness_m"] = record.wall_thickness_m
        base["cross_section_area_m2"] = record.cross_section_area_m2
        base["flow_area_m2"] = record.flow_area_m2
        base["hydraulic_diameter_m"] = record.hydraulic_diameter_m
    elif isinstance(record, PipeGeometryRecord):
        base["outer_diameter_m"] = record.outer_diameter_m
        base["inner_diameter_m"] = record.inner_diameter_m
        base["wall_thickness_m"] = record.wall_thickness_m
        base["flow_area_m2"] = record.flow_area_m2
        base["hydraulic_diameter_m"] = record.hydraulic_diameter_m
    elif isinstance(record, HairpinGeometryRecord):
        base["hairpin_id"] = record.hairpin_id
        base["tube_geometry_id"] = record.tube_geometry_id
        base["pipe_geometry_id"] = record.pipe_geometry_id
        base["number_of_tubes"] = record.number_of_tubes
        base["effective_length_m"] = record.effective_length_m
        base["bend_radius_m"] = record.bend_radius_m
        base["centerline_spacing_m"] = record.centerline_spacing_m
    else:
        raise TypeError(f"Unsupported record type: {type(record).__name__}")
    return base


def compute_record_hash(record: GeometryRecord) -> str:
    """Return the SHA-256 hex digest of the canonical record representation.

    Hash MUST change when computation-authority fields change (Section 7.3)
    and MUST remain stable under non-semantic key ordering changes (Section
    7.3). The latter property is inherited from
    :func:`hexagent.canonical_json.canonical_sha256` which uses RFC 8785
    deterministic key ordering + NFC normalization.
    """
    return canonical_sha256(_record_to_canonical_dict(record))


# --- Canonical ordering (Section 7.2) --------------------------------------


def canonical_order_records(
    records: list[GeometryRecord],
) -> list[GeometryRecord]:
    """Sort records by (geometry_type, geometry_id, revision, record_hash).

    Section 7.2: consumers MUST NOT depend on input file order.
    """
    return sorted(
        records,
        key=lambda r: (
            r.geometry_type,
            r.geometry_id,
            r.revision,
            compute_record_hash(r),
        ),
    )


# --- Catalog content hashing (Section 5.1) ---------------------------------


def compute_catalog_content_hash(catalog: GeometryCatalog) -> str:
    """Return the SHA-256 hex digest of the canonical catalog aggregate.

    Hash scope: per-catalog (Section 5.1). The hash covers catalog metadata
    plus the canonical sequence of record hashes; volatile runtime fields
    (e.g., ``generated_at``, ``effective_at``) are excluded so the hash is
    stable across replays.
    """
    payload: dict[str, Any] = {
        "catalog_id": catalog.catalog_id,
        "catalog_version": catalog.catalog_version,
        "authority": catalog.authority,
        "source_revision": catalog.source_revision,
        "record_hashes": [compute_record_hash(r) for r in catalog.records],
    }
    return canonical_sha256(payload)


# --- Approved-only accessor (Section 5.2 / Section 10) ---------------------


def select_approved_records(
    catalog: GeometryCatalog,
) -> list[GeometryRecord]:
    """Return only the records whose ``approval_state`` is approved.

    Non-approved records are NOT selectable (Section 5.2 + Section 10).
    Order of the returned list follows the canonical order already imposed
    on ``catalog.records`` (Section 7.2).
    """
    return [r for r in catalog.records if r.approval_state in SELECTABLE_APPROVAL_STATES]


# --- Catalog loader / validator ---------------------------------------------


_REQUIRED_SOURCE_FIELDS: Final[tuple[str, ...]] = (
    "source_id",
    "source_type",
    "source_revision",
    "source_location",
    "evidence_ref",
    "approved_by",
    "approved_at",
)


def _require_source_binding(
    raw: dict[str, Any],
    geometry_id: str | None,
) -> SourceBinding:
    sb_raw = raw.get("source_binding")
    if not isinstance(sb_raw, dict):
        raise geometry_source_missing(geometry_id=geometry_id)
    missing = [f for f in _REQUIRED_SOURCE_FIELDS if not sb_raw.get(f)]
    if missing:
        raise geometry_source_missing(geometry_id=geometry_id, missing_fields=list(missing))
    return SourceBinding(
        source_id=str(sb_raw["source_id"]),
        source_type=str(sb_raw["source_type"]),
        source_revision=str(sb_raw["source_revision"]),
        source_location=str(sb_raw["source_location"]),
        evidence_ref=str(sb_raw["evidence_ref"]),
        approved_by=str(sb_raw["approved_by"]),
        approved_at=str(sb_raw["approved_at"]),
    )


def _require_positive(name: str, value: Any, geometry_id: str) -> float:
    f = float(value)
    if not (f > 0.0):
        raise geometry_dimension_non_positive(geometry_id=geometry_id, field_name=name, value=f)
    return f


def _require_dimension(
    name: str,
    value: Any,
    geometry_id: str,
) -> float:
    """Accept finite values; reject ≤ 0 and reject non-finite (NaN/inf)."""
    f = float(value)
    # ``f != f`` is True iff f is NaN; ``abs(f) == float("inf")`` is True iff inf.
    if f != f or f == float("inf") or f == float("-inf"):
        raise geometry_dimension_non_positive(geometry_id=geometry_id, field_name=name, value=f)
    return _require_positive(name, f, geometry_id)


def _build_tube(raw: dict[str, Any], geometry_id: str) -> TubeGeometryRecord:
    outer = _require_dimension("outer_diameter_m", raw["outer_diameter_m"], geometry_id)
    inner = _require_dimension("inner_diameter_m", raw["inner_diameter_m"], geometry_id)
    wall = _require_dimension("wall_thickness_m", raw["wall_thickness_m"], geometry_id)
    cross = _require_dimension("cross_section_area_m2", raw["cross_section_area_m2"], geometry_id)
    flow = _require_dimension("flow_area_m2", raw["flow_area_m2"], geometry_id)
    dh = _require_dimension("hydraulic_diameter_m", raw["hydraulic_diameter_m"], geometry_id)
    expected_wall = (outer - inner) / 2.0
    if abs(wall - expected_wall) > GEOMETRY_DIMENSION_TOLERANCE_M:
        raise geometry_dimension_inconsistent(
            geometry_id=geometry_id,
            field_name="wall_thickness_m",
            expected=expected_wall,
            actual=wall,
            tolerance=GEOMETRY_DIMENSION_TOLERANCE_M,
        )
    if outer <= inner:
        raise geometry_dimension_inconsistent(
            geometry_id=geometry_id,
            field_name="outer_diameter_m_vs_inner_diameter_m",
            expected=1.0,
            actual=0.0,
            tolerance=0.0,
        )
    return TubeGeometryRecord(
        geometry_id=geometry_id,
        approval_state=str(raw["approval_state"]),
        nominal_label=str(raw.get("nominal_label", "")),
        outer_diameter_m=outer,
        inner_diameter_m=inner,
        wall_thickness_m=wall,
        cross_section_area_m2=cross,
        flow_area_m2=flow,
        hydraulic_diameter_m=dh,
        source_binding=_require_source_binding(raw, geometry_id),
        revision=str(raw.get("revision", "")),
        tags=tuple(raw.get("tags", ())),
        record_hash=str(raw["record_hash"]) if "record_hash" in raw else None,
    )


def _build_pipe(raw: dict[str, Any], geometry_id: str) -> PipeGeometryRecord:
    outer = _require_dimension("outer_diameter_m", raw["outer_diameter_m"], geometry_id)
    inner = _require_dimension("inner_diameter_m", raw["inner_diameter_m"], geometry_id)
    wall = _require_dimension("wall_thickness_m", raw["wall_thickness_m"], geometry_id)
    flow = _require_dimension("flow_area_m2", raw["flow_area_m2"], geometry_id)
    dh = _require_dimension("hydraulic_diameter_m", raw["hydraulic_diameter_m"], geometry_id)
    if outer <= inner:
        raise geometry_dimension_inconsistent(
            geometry_id=geometry_id,
            field_name="outer_diameter_m_vs_inner_diameter_m",
            expected=1.0,
            actual=0.0,
            tolerance=0.0,
        )
    return PipeGeometryRecord(
        geometry_id=geometry_id,
        approval_state=str(raw["approval_state"]),
        nominal_label=str(raw.get("nominal_label", "")),
        nominal_pipe_size_label=str(raw.get("nominal_pipe_size_label", "")),
        schedule_label=str(raw.get("schedule_label", "")),
        outer_diameter_m=outer,
        inner_diameter_m=inner,
        wall_thickness_m=wall,
        flow_area_m2=flow,
        hydraulic_diameter_m=dh,
        source_binding=_require_source_binding(raw, geometry_id),
        revision=str(raw.get("revision", "")),
        tags=tuple(raw.get("tags", ())),
        record_hash=str(raw["record_hash"]) if "record_hash" in raw else None,
    )


def _build_hairpin(raw: dict[str, Any], geometry_id: str) -> HairpinGeometryRecord:
    n_tubes = int(raw["number_of_tubes"])
    if n_tubes <= 0:
        raise geometry_dimension_non_positive(
            geometry_id=geometry_id, field_name="number_of_tubes", value=float(n_tubes)
        )
    return HairpinGeometryRecord(
        geometry_id=geometry_id,
        hairpin_id=str(raw.get("hairpin_id", geometry_id)),
        approval_state=str(raw["approval_state"]),
        nominal_label=str(raw.get("nominal_label", "")),
        tube_geometry_id=str(raw["tube_geometry_id"]),
        pipe_geometry_id=str(raw["pipe_geometry_id"]),
        number_of_tubes=n_tubes,
        effective_length_m=_require_dimension(
            "effective_length_m", raw["effective_length_m"], geometry_id
        ),
        bend_radius_m=_require_dimension("bend_radius_m", raw["bend_radius_m"], geometry_id),
        centerline_spacing_m=_require_dimension(
            "centerline_spacing_m", raw["centerline_spacing_m"], geometry_id
        ),
        flow_path_descriptor=str(raw.get("flow_path_descriptor", "")),
        source_binding=_require_source_binding(raw, geometry_id),
        revision=str(raw.get("revision", "")),
        tags=tuple(raw.get("tags", ())),
        record_hash=str(raw["record_hash"]) if "record_hash" in raw else None,
    )


def _coerce_record(
    raw: dict[str, Any],
    index: int,
    seen_ids: dict[str, int],
) -> GeometryRecord:
    geometry_id_raw = raw.get("geometry_id")
    geometry_id = "" if geometry_id_raw is None else str(geometry_id_raw).strip()
    if not geometry_id:
        raise geometry_record_missing_id(index=index)
    # NFC normalization for canonical id (mirrors hexagent.canonical_json).
    import unicodedata

    geometry_id = unicodedata.normalize("NFC", geometry_id)
    if geometry_id in seen_ids:
        raise geometry_record_duplicate_id(geometry_id=geometry_id)
    seen_ids[geometry_id] = index

    geometry_type = raw.get("geometry_type")
    if geometry_type not in VALID_GEOMETRY_TYPES:
        raise geometry_type_unsupported(geometry_id=geometry_id, geometry_type=geometry_type)

    approval_state = raw.get("approval_state")
    if approval_state not in VALID_APPROVAL_STATES:
        raise geometry_record_unapproved(
            geometry_id=geometry_id,
            approval_state="" if approval_state is None else str(approval_state),
        )

    record: GeometryRecord
    if geometry_type == GEOMETRY_TYPE_TUBE:
        record = _build_tube(raw, geometry_id)
    elif geometry_type == GEOMETRY_TYPE_PIPE:
        record = _build_pipe(raw, geometry_id)
    else:
        record = _build_hairpin(raw, geometry_id)

    # Stored hash cross-check, if present; otherwise fill in canonical hash.
    canonical = compute_record_hash(record)
    stored = raw.get("record_hash")
    if stored is not None and str(stored) != canonical:
        raise geometry_hash_mismatch(
            geometry_id=geometry_id, expected=str(stored), actual=canonical
        )
    # Always attach canonical hash to the record (frozen dataclass requires
    # ``object.__setattr__``).
    object.__setattr__(record, "record_hash", canonical)
    return record


def _enforce_approved_and_references(
    records: list[GeometryRecord],
) -> None:
    """Section 9: enforce approved-only + hairpin reference integrity."""
    by_id: dict[str, GeometryRecord] = {r.geometry_id: r for r in records}
    for record in records:
        if record.approval_state != APPROVAL_STATE_APPROVED:
            # Non-approved records are still part of the catalog aggregate but
            # are flagged here to prevent accidental promotion to selectable
            # set. (Loader continues to include them; accessor filters.)
            continue
        if isinstance(record, HairpinGeometryRecord):
            for ref_field, ref_id in (
                ("tube_geometry_id", record.tube_geometry_id),
                ("pipe_geometry_id", record.pipe_geometry_id),
            ):
                target = by_id.get(ref_id)
                if target is None:
                    raise geometry_reference_missing(
                        hairpin_id=record.hairpin_id,
                        reference_field=ref_field,
                        missing_id=ref_id,
                    )
                if target.approval_state != APPROVAL_STATE_APPROVED:
                    raise geometry_reference_unapproved(
                        hairpin_id=record.hairpin_id,
                        reference_field=ref_field,
                        referenced_id=ref_id,
                        referenced_state=target.approval_state,
                    )


def load_geometry_catalog(payload: dict[str, Any]) -> GeometryCatalog:
    """Load, validate, canonicalize, and hash a geometry catalog payload.

    Accepts a JSON-compatible mapping with the shape::

        {
          "catalog_id": str,
          "catalog_version": str,
          "authority": str,
          "source_revision": str,
          "records": [ {record}, {record}, ... ],
          "generated_at": str (optional),
          "effective_at": str (optional)
        }

    Raises :class:`GeometryCatalogBlockerError` (subclass of
    :class:`GeometryCatalogError`) on any blocker condition. The returned
    catalog is the immutable, deterministically ordered, deterministically
    hashed aggregate.
    """
    if not isinstance(payload, dict):
        raise geometry_catalog_missing({"reason": "payload_not_mapping"})
    records_raw = payload.get("records")
    if not isinstance(records_raw, list):
        raise geometry_catalog_missing({"reason": "records_missing"})

    seen_ids: dict[str, int] = {}
    records: list[GeometryRecord] = []
    for index, raw in enumerate(records_raw):
        if not isinstance(raw, dict):
            raise geometry_record_missing_id(index=index)
        records.append(_coerce_record(raw, index, seen_ids))

    _enforce_approved_and_references(records)

    ordered = canonical_order_records(records)
    catalog = GeometryCatalog(
        catalog_id=str(payload.get("catalog_id", "")),
        catalog_version=str(payload.get("catalog_version", "")),
        authority=str(payload.get("authority", "")),
        source_revision=str(payload.get("source_revision", "")),
        records=tuple(ordered),
        content_hash="",  # placeholder; computed below
        generated_at=payload.get("generated_at"),
        effective_at=payload.get("effective_at"),
    )
    # Compute content hash via the shared canonical helper.
    object.__setattr__(catalog, "content_hash", compute_catalog_content_hash(catalog))
    return catalog


__all__ = [
    "GEOMETRY_DIMENSION_TOLERANCE_M",
    "canonical_order_records",
    "compute_catalog_content_hash",
    "compute_record_hash",
    "load_geometry_catalog",
    "select_approved_records",
    # Re-exported for downstream convenience:
    "GeometryCatalogBlockerError",
]

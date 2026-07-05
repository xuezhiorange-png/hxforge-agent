"""TASK-016 approved tube, pipe and hairpin geometry catalog.

Implements the TASK-016 frozen design contract
(``docs/tasks/TASK-016-approved-geometry-catalog.md``,
Frozen Contract Authority SHA
``654a2708de808c9f1518f1a69eda92f95a4d37c5``).

The catalog is approved-only: consumers may select only records whose
``approval_state`` is explicitly ``approved``. The catalog is deterministic:
records are sorted by ``(geometry_type, geometry_id, revision, record_hash)``,
the SHA-256 record hash is computed via the shared canonical JSON helper
(``hexagent.canonical_json``), and the catalog-level ``content_hash`` is
deterministic across platforms and Python versions.

This package introduces NO public API surface, NO report rendering, NO
database / ORM / Alembic migration, and NO material / cost / pressure-drop
semantics. Implementation is strictly limited to the §11 envelope of the
frozen design contract.
"""

from __future__ import annotations

from hexagent.geometry_catalogs.blockers import (
    GeometryCatalogBlockerError,
    GeometryCatalogError,
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
from hexagent.geometry_catalogs.catalog import (
    GEOMETRY_DIMENSION_TOLERANCE_M,
    canonical_order_records,
    compute_catalog_content_hash,
    compute_record_hash,
    load_geometry_catalog,
    select_approved_records,
)
from hexagent.geometry_catalogs.models import (
    APPROVAL_STATE_APPROVED,
    GEOMETRY_TYPE_HAIRPIN,
    GEOMETRY_TYPE_PIPE,
    GEOMETRY_TYPE_TUBE,
    GeometryCatalog,
    GeometryRecord,
    HairpinGeometryRecord,
    PipeGeometryRecord,
    SourceBinding,
    TubeGeometryRecord,
)

__all__ = [
    "APPROVAL_STATE_APPROVED",
    "GEOMETRY_DIMENSION_TOLERANCE_M",
    "GEOMETRY_TYPE_HAIRPIN",
    "GEOMETRY_TYPE_PIPE",
    "GEOMETRY_TYPE_TUBE",
    "GeometryCatalog",
    "GeometryCatalogBlockerError",
    "GeometryCatalogError",
    "GeometryRecord",
    "HairpinGeometryRecord",
    "PipeGeometryRecord",
    "SourceBinding",
    "TubeGeometryRecord",
    "canonical_order_records",
    "compute_catalog_content_hash",
    "compute_record_hash",
    "geometry_catalog_missing",
    "geometry_dimension_inconsistent",
    "geometry_dimension_non_positive",
    "geometry_hash_mismatch",
    "geometry_record_duplicate_id",
    "geometry_record_missing_id",
    "geometry_record_unapproved",
    "geometry_reference_missing",
    "geometry_reference_unapproved",
    "geometry_source_missing",
    "geometry_type_unsupported",
    "load_geometry_catalog",
    "select_approved_records",
]

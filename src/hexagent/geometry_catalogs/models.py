"""Immutable domain models for the TASK-016 approved geometry catalog.

Implements the TASK-016 frozen design contract
(``docs/tasks/TASK-016-approved-geometry-catalog.md``,
Frozen Contract Authority SHA
``654a2708de808c9f1518f1a69eda92f95a4d37c5``) Section 5 (Domain model).

The catalog aggregate (``GeometryCatalog``) holds a canonical sequence of
geometry records. Every record is effectively immutable (frozen dataclass);
mutations are rejected by ``dataclasses.FrozenInstanceError``. Records are
identified by a stable ``geometry_id`` (string), classified by an explicit
``geometry_type`` enum, and gated by an explicit ``approval_state`` value of
``"approved"``. Non-approved records cannot be selected by consumers.

Dimensional fields are stored in canonical SI base units (metres / m²). The
``SourceBinding`` aggregates the seven provenance fields mandated by §8:
``source_id``, ``source_type``, ``source_revision``, ``source_location``,
``evidence_ref``, ``approved_by``, ``approved_at``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

# --- Enumerations (Section 5.2) ----------------------------------------------

GeometryType = Literal["tube", "pipe", "hairpin"]

GEOMETRY_TYPE_TUBE: Final[str] = "tube"
GEOMETRY_TYPE_PIPE: Final[str] = "pipe"
GEOMETRY_TYPE_HAIRPIN: Final[str] = "hairpin"

VALID_GEOMETRY_TYPES: Final[frozenset[str]] = frozenset(
    {GEOMETRY_TYPE_TUBE, GEOMETRY_TYPE_PIPE, GEOMETRY_TYPE_HAIRPIN}
)

ApprovalState = Literal["approved", "pending", "rejected", "retired"]

APPROVAL_STATE_APPROVED: Final[str] = "approved"
APPROVAL_STATE_PENDING: Final[str] = "pending"
APPROVAL_STATE_REJECTED: Final[str] = "rejected"
APPROVAL_STATE_RETIRED: Final[str] = "retired"

VALID_APPROVAL_STATES: Final[frozenset[str]] = frozenset(
    {
        APPROVAL_STATE_APPROVED,
        APPROVAL_STATE_PENDING,
        APPROVAL_STATE_REJECTED,
        APPROVAL_STATE_RETIRED,
    }
)

SELECTABLE_APPROVAL_STATES: Final[frozenset[str]] = frozenset({APPROVAL_STATE_APPROVED})

# --- Provenance (Section 5.2 + Section 8) ------------------------------------


@dataclass(frozen=True)
class SourceBinding:
    """Section 8 — provenance required for every approved geometry record.

    The seven fields are the canonical, deterministic representation of
    source evidence and approval authority. ``source_*`` fields identify
    the upstream document; ``approved_by`` / ``approved_at`` record the
    approval authority.
    """

    source_id: str
    source_type: str
    source_revision: str
    source_location: str
    evidence_ref: str
    approved_by: str
    approved_at: str


# --- Geometry record hierarchy (Section 5.2 / 5.3 / 5.4 / 5.5) ---------------


@dataclass(frozen=True)
class TubeGeometryRecord:
    """Section 5.3 — approved tube geometry (dimensions only).

    Algebraic consistency invariant (Section 5.3):
        wall_thickness_m == (outer_diameter_m - inner_diameter_m) / 2

    Records do NOT encode material grade, allowable stress, corrosion
    allowance, fouling, pressure rating, or cost (Section 5.3 final
    paragraph).
    """

    geometry_id: str
    approval_state: str
    nominal_label: str
    outer_diameter_m: float
    inner_diameter_m: float
    wall_thickness_m: float
    cross_section_area_m2: float
    flow_area_m2: float
    hydraulic_diameter_m: float
    source_binding: SourceBinding
    revision: str
    tags: tuple[str, ...] = ()
    record_hash: str | None = None

    @property
    def geometry_type(self) -> str:
        return GEOMETRY_TYPE_TUBE


@dataclass(frozen=True)
class PipeGeometryRecord:
    """Section 5.4 — approved pipe geometry (dimensions only).

    ``nominal_pipe_size_label`` and ``schedule_label`` are deterministic
    labels, NOT computation authority (Section 5.4 paragraph 3).
    Computation MUST use the canonical SI dimensional fields.

    Records do NOT encode material grade, flange rating, code compliance,
    mechanical pressure rating, or cost (Section 5.4 final paragraph).
    """

    geometry_id: str
    approval_state: str
    nominal_label: str
    nominal_pipe_size_label: str
    schedule_label: str
    outer_diameter_m: float
    inner_diameter_m: float
    wall_thickness_m: float
    flow_area_m2: float
    hydraulic_diameter_m: float
    source_binding: SourceBinding
    revision: str
    tags: tuple[str, ...] = ()
    record_hash: str | None = None

    @property
    def geometry_type(self) -> str:
        return GEOMETRY_TYPE_PIPE


@dataclass(frozen=True)
class HairpinGeometryRecord:
    """Section 5.5 — approved hairpin bundle-level geometry.

    Hairpin records reference approved tube and pipe records by stable
    ``geometry_id``. They MUST NOT introduce pressure-drop, mechanical,
    material, or cost conclusions (Section 5.5 final paragraph).
    """

    geometry_id: str
    hairpin_id: str
    approval_state: str
    nominal_label: str
    tube_geometry_id: str
    pipe_geometry_id: str
    number_of_tubes: int
    effective_length_m: float
    bend_radius_m: float
    centerline_spacing_m: float
    flow_path_descriptor: str
    source_binding: SourceBinding
    revision: str
    tags: tuple[str, ...] = ()
    record_hash: str | None = None

    @property
    def geometry_type(self) -> str:
        return GEOMETRY_TYPE_HAIRPIN


# Union type alias used by ``GeometryCatalog.records`` and accessors.
GeometryRecord = TubeGeometryRecord | PipeGeometryRecord | HairpinGeometryRecord


# --- Catalog aggregate (Section 5.1) -----------------------------------------


@dataclass(frozen=True)
class GeometryCatalog:
    """Section 5.1 — immutable validated aggregate of approved geometry.

    ``records`` MUST be the canonical sequence produced by
    :func:`canonical_order_records` before the catalog is instantiated.
    ``content_hash`` is computed by :func:`compute_catalog_content_hash`
    and is deterministic across platforms and Python versions.
    """

    catalog_id: str
    catalog_version: str
    authority: str
    source_revision: str
    records: tuple[GeometryRecord, ...]
    content_hash: str
    generated_at: str | None = None
    effective_at: str | None = None

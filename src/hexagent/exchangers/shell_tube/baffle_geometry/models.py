"""TASK-024 domain models -- Section 8 of the TASK-024 design contract.

This module defines the frozen value-object types for TASK-024 baffle
geometry and axial spacing. Every type is an immutable dataclass with a
closed shape; construction never mutates an existing instance and never
reaches outside the package.

Type map (referenced from the TASK-024 design sections 6 through 8):

- Section 6.2 closed enums: BaffleType / BaffleOrientation /
  TubeRegionClassification / ValidationStatus
- Section 8.1 CallerSuppliedBaffleAxialSpan (5 fields)
- Section 8.2 CallerSuppliedBaffleDesignAuthority (11 fields)
- Section 8.3 BaffleGeometryRequest (7 fields)
- Section 8.4 CutChordGeometry (8 fields)
- Section 8.5 PhysicalTubeDiskAudit (4 fields)
- Section 8.6 TubeHoleClassification (10 fields + nested audit)
- Section 8.7 BafflePlaneGeometry (15 fields)
- Section 8.8 BaffleGeometry (31 fields)
- Section 8.9 BaffleGeometryValidationResult (6 fields)
- Section 13 MessageEntry (5 fields)
- Section 11 BlockerCode (57 codes)
- Section 12 WarningCode (8 codes)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

###############################################################################
# Section 6.2 - Closed enum: BaffleType
###############################################################################


class BaffleType(enum.Enum):
    """Section 6.2 - Closed set of baffle types. Single value in v1."""

    SINGLE_SEGMENTAL = "SINGLE_SEGMENTAL"


###############################################################################
# Section 6.2 - Closed enum: BaffleOrientation
###############################################################################


class BaffleOrientation(enum.Enum):
    """Section 6.2 - Closed set of baffle cut orientations."""

    TOP = "TOP"
    BOTTOM = "BOTTOM"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


###############################################################################
# Section 6.2 - Closed enum: TubeRegionClassification
###############################################################################


class TubeRegionClassification(enum.Enum):
    """Section 6.2 - Closed set of tube region classifications (Section 9.7)."""

    WINDOW = "WINDOW"
    CROSSFLOW_REFERENCE = "CROSSFLOW_REFERENCE"


###############################################################################
# Section 6.2 - Closed enum: ValidationStatus
###############################################################################


class ValidationStatus(enum.Enum):
    """Section 6.2 - Validation status."""

    VALID = "VALID"
    BLOCKED = "BLOCKED"


###############################################################################
# Section 11 - Closed blocker taxonomy (57 codes)
###############################################################################


class BlockerCode(enum.Enum):
    """Section 11 - Closed set of 57 blocker codes (canonical literal tokens)."""

    BFG_SCHEMA_VERSION_UNSUPPORTED = "BFG_SCHEMA_VERSION_UNSUPPORTED"
    BFG_UNKNOWN_FIELD = "BFG_UNKNOWN_FIELD"
    BFG_RAW_TYPE_INVALID = "BFG_RAW_TYPE_INVALID"
    BFG_DECIMAL_LEXICAL_INVALID = "BFG_DECIMAL_LEXICAL_INVALID"

    BFG_TASK020_CONFIGURATION_MISSING = "BFG_TASK020_CONFIGURATION_MISSING"
    BFG_TASK020_CONFIGURATION_INVALID = "BFG_TASK020_CONFIGURATION_INVALID"
    BFG_TASK020_CONFIGURATION_IDENTITY_MISMATCH = "BFG_TASK020_CONFIGURATION_IDENTITY_MISMATCH"

    BFG_TASK021_LAYOUT_MISSING = "BFG_TASK021_LAYOUT_MISSING"
    BFG_TASK021_LAYOUT_INVALID = "BFG_TASK021_LAYOUT_INVALID"
    BFG_TASK021_LAYOUT_HAS_BLOCKERS = "BFG_TASK021_LAYOUT_HAS_BLOCKERS"
    BFG_TASK021_LAYOUT_IDENTITY_MISMATCH = "BFG_TASK021_LAYOUT_IDENTITY_MISMATCH"
    BFG_TASK021_LAYOUT_HAS_NO_POSITIONS = "BFG_TASK021_LAYOUT_HAS_NO_POSITIONS"

    BFG_TASK022_GEOMETRY_MISSING = "BFG_TASK022_GEOMETRY_MISSING"
    BFG_TASK022_GEOMETRY_INVALID = "BFG_TASK022_GEOMETRY_INVALID"
    BFG_TASK022_GEOMETRY_HAS_BLOCKERS = "BFG_TASK022_GEOMETRY_HAS_BLOCKERS"
    BFG_TASK022_GEOMETRY_IDENTITY_MISMATCH = "BFG_TASK022_GEOMETRY_IDENTITY_MISMATCH"

    BFG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH = "BFG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH"
    BFG_UPSTREAM_LAYOUT_BINDING_MISMATCH = "BFG_UPSTREAM_LAYOUT_BINDING_MISMATCH"
    BFG_UPSTREAM_TUBE_GEOMETRY_BINDING_MISMATCH = "BFG_UPSTREAM_TUBE_GEOMETRY_BINDING_MISMATCH"
    BFG_UPSTREAM_CONSTRUCTION_FAMILY_MISMATCH = "BFG_UPSTREAM_CONSTRUCTION_FAMILY_MISMATCH"
    BFG_UPSTREAM_ORIENTATION_MISMATCH = "BFG_UPSTREAM_ORIENTATION_MISMATCH"
    BFG_UPSTREAM_PASS_COUNT_MISMATCH = "BFG_UPSTREAM_PASS_COUNT_MISMATCH"
    BFG_UPSTREAM_POSITION_COUNT_MISMATCH = "BFG_UPSTREAM_POSITION_COUNT_MISMATCH"

    BFG_CONSTRUCTION_FAMILY_UNSUPPORTED = "BFG_CONSTRUCTION_FAMILY_UNSUPPORTED"
    BFG_SHELL_PASS_COUNT_UNSUPPORTED = "BFG_SHELL_PASS_COUNT_UNSUPPORTED"
    BFG_BAFFLE_TYPE_UNSUPPORTED = "BFG_BAFFLE_TYPE_UNSUPPORTED"

    BFG_AXIAL_SPAN_MISSING = "BFG_AXIAL_SPAN_MISSING"
    BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED = "BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED"
    BFG_AXIAL_SPAN_EVIDENCE_MISSING = "BFG_AXIAL_SPAN_EVIDENCE_MISSING"
    BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH = "BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH"
    BFG_AXIAL_SPAN_INVALID = "BFG_AXIAL_SPAN_INVALID"

    BFG_DESIGN_AUTHORITY_MISSING = "BFG_DESIGN_AUTHORITY_MISSING"
    BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED = "BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED"
    BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING = "BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING"
    BFG_DESIGN_AUTHORITY_HASH_MISMATCH = "BFG_DESIGN_AUTHORITY_HASH_MISMATCH"

    BFG_BAFFLE_COUNT_INVALID = "BFG_BAFFLE_COUNT_INVALID"
    BFG_BAFFLE_THICKNESS_INVALID = "BFG_BAFFLE_THICKNESS_INVALID"
    BFG_SPACING_SEQUENCE_CARDINALITY_MISMATCH = "BFG_SPACING_SEQUENCE_CARDINALITY_MISMATCH"
    BFG_SPACING_VALUE_INVALID = "BFG_SPACING_VALUE_INVALID"
    BFG_SPACING_SEQUENCE_SPAN_MISMATCH = "BFG_SPACING_SEQUENCE_SPAN_MISMATCH"
    BFG_ORIENTATION_SEQUENCE_CARDINALITY_MISMATCH = "BFG_ORIENTATION_SEQUENCE_CARDINALITY_MISMATCH"
    BFG_ORIENTATION_TOKEN_INVALID = "BFG_ORIENTATION_TOKEN_INVALID"
    BFG_BAFFLE_CUT_INVALID = "BFG_BAFFLE_CUT_INVALID"
    BFG_SHELL_TO_BAFFLE_CLEARANCE_INVALID = "BFG_SHELL_TO_BAFFLE_CLEARANCE_INVALID"
    BFG_TUBE_TO_BAFFLE_HOLE_CLEARANCE_INVALID = "BFG_TUBE_TO_BAFFLE_HOLE_CLEARANCE_INVALID"

    BFG_BAFFLE_DIAMETER_INVALID = "BFG_BAFFLE_DIAMETER_INVALID"
    BFG_BAFFLE_HOLE_DIAMETER_INVALID = "BFG_BAFFLE_HOLE_DIAMETER_INVALID"
    BFG_BAFFLE_THICKNESS_OUTSIDE_ACTIVE_SPAN = "BFG_BAFFLE_THICKNESS_OUTSIDE_ACTIVE_SPAN"
    BFG_BAFFLE_SOLIDS_OVERLAP = "BFG_BAFFLE_SOLIDS_OVERLAP"
    BFG_CHORD_CALCULATION_FAILED = "BFG_CHORD_CALCULATION_FAILED"

    BFG_BAFFLE_HOLE_DISK_TANGENT_TO_CUT_BOUNDARY = "BFG_BAFFLE_HOLE_DISK_TANGENT_TO_CUT_BOUNDARY"
    BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY = "BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY"
    BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK = "BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK"
    BFG_BAFFLE_HOLE_DISKS_OVERLAP = "BFG_BAFFLE_HOLE_DISKS_OVERLAP"
    BFG_POSITION_CLASSIFICATION_INCOMPLETE = "BFG_POSITION_CLASSIFICATION_INCOMPLETE"

    BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION = "BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION"

    BFG_CANONICALIZATION_FAILED = "BFG_CANONICALIZATION_FAILED"


###############################################################################
# Section 12 - Closed warning taxonomy (8 codes)
###############################################################################


class WarningCode(enum.Enum):
    """Section 12 - Closed set of 8 warning codes."""

    BFG_FIXED_TUBESHEET_ONLY_V1 = "BFG_FIXED_TUBESHEET_ONLY_V1"
    BFG_GEOMETRY_NOT_FLOW_AREA = "BFG_GEOMETRY_NOT_FLOW_AREA"
    BFG_NOZZLE_POSITION_DEFERRED = "BFG_NOZZLE_POSITION_DEFERRED"
    BFG_THERMAL_HYDRAULIC_DEFERRED = "BFG_THERMAL_HYDRAULIC_DEFERRED"
    BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM = "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM"
    BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY = (
        "BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY"
    )
    BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY = (
        "BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY"
    )
    BFG_BAFFLE_HOLE_PAIR_TANGENCY_NOT_MANUFACTURING_ADEQUACY = (
        "BFG_BAFFLE_HOLE_PAIR_TANGENCY_NOT_MANUFACTURING_ADEQUACY"
    )


###############################################################################
# Section 8.1 - CallerSuppliedBaffleAxialSpan
###############################################################################


@dataclass(frozen=True, eq=True)
class CallerSuppliedBaffleAxialSpan:
    """Section 8.1 - Caller-supplied axial-span authority."""

    schema_version: str
    axial_start_coordinate_m: str
    axial_end_coordinate_m: str
    evidence_refs: tuple[str, ...]
    authority_hash: str


###############################################################################
# Section 8.2 - CallerSuppliedBaffleDesignAuthority
###############################################################################


@dataclass(frozen=True, eq=True)
class CallerSuppliedBaffleDesignAuthority:
    """Section 8.2 - Caller-supplied baffle-design authority."""

    schema_version: str
    baffle_type: BaffleType
    baffle_count: int
    baffle_thickness_m: str
    spacing_sequence_m: tuple[str, ...]
    baffle_cut_fraction: str
    orientation_sequence: tuple[BaffleOrientation, ...]
    shell_to_baffle_diametral_clearance_m: str
    tube_to_baffle_hole_diametral_clearance_m: str
    evidence_refs: tuple[str, ...]
    authority_hash: str


###############################################################################
# Section 8.4 - CutChordGeometry
###############################################################################


@dataclass(frozen=True, eq=True)
class CutChordGeometry:
    """Section 8.4 - Single-segment cut chord geometry (8 fields)."""

    normal_x: int
    normal_y: int
    half_plane_offset_m: str
    chord_half_length_m: str
    endpoint_a_x_m: str
    endpoint_a_y_m: str
    endpoint_b_x_m: str
    endpoint_b_y_m: str


###############################################################################
# Section 8.5 - PhysicalTubeDiskAudit
###############################################################################


@dataclass(frozen=True, eq=True)
class PhysicalTubeDiskAudit:
    """Section 8.5 - Physical-tube disk audit (4 fields)."""

    physical_tube_radius_m: str
    signed_window_distance_m: str
    cut_boundary_margin_m: str
    classification: TubeRegionClassification


###############################################################################
# Section 8.6 - TubeHoleClassification (with nested audit)
###############################################################################


@dataclass(frozen=True, eq=True)
class TubeHoleClassification:
    """Section 8.6 - Per-position tube-hole classification (10 fields + nested audit)."""

    position_id: str
    center_x_m: str
    center_y_m: str
    physical_tube_radius_m: str
    baffle_hole_radius_m: str
    signed_window_distance_m: str
    cut_boundary_margin_m: str
    classification: TubeRegionClassification
    outer_boundary_margin_squared_m2: str
    physical_tube_disk_audit: PhysicalTubeDiskAudit


###############################################################################
# Section 8.7 - BafflePlaneGeometry
###############################################################################


@dataclass(frozen=True, eq=True)
class BafflePlaneGeometry:
    """Section 8.7 - Per-baffle plane geometry (15 fields)."""

    baffle_index: int
    center_coordinate_m: str
    occupied_start_coordinate_m: str
    occupied_end_coordinate_m: str
    orientation: BaffleOrientation
    cut_chord: CutChordGeometry
    window_region_semantics: str
    baffle_covered_region_semantics: str
    crossflow_reference_region_semantics: str
    tube_hole_classifications: tuple[TubeHoleClassification, ...]
    window_position_ids: tuple[str, ...]
    crossflow_reference_position_ids: tuple[str, ...]
    outer_tangent_position_ids: tuple[str, ...]
    pairwise_tangent_position_pairs: tuple[tuple[str, str], ...]
    classification_audit_hash: str


###############################################################################
# Section 13 - MessageEntry (frozen shape)
###############################################################################


@dataclass(frozen=True, eq=True)
class MessageEntry:
    """Section 13 - Frozen message shape used for warnings and blockers."""

    code: str
    field_path: str | None
    message_key: str
    evidence_refs: tuple[str, ...]
    details: tuple[tuple[str, str], ...]


###############################################################################
# Section 8.8 - BaffleGeometry (31 fields)
###############################################################################


@dataclass(frozen=True, eq=True)
class BaffleGeometry:
    """Section 8.8 - Frozen complete baffle geometry result (31 fields)."""

    schema_version: str
    geometry_id: str
    geometry_hash: str
    request_hash: str
    task020_configuration_id: str
    task020_configuration_hash: str
    task021_layout_id: str
    task021_layout_hash: str
    task022_geometry_id: str
    task022_geometry_hash: str
    construction_family: str
    equipment_orientation: str
    shell_pass_count: int
    tube_pass_count: int
    shell_inside_diameter_m: str
    tube_outer_diameter_m: str
    axial_span: CallerSuppliedBaffleAxialSpan
    design_authority: CallerSuppliedBaffleDesignAuthority
    usable_baffle_span_m: str
    baffle_diameter_m: str
    baffle_radius_m: str
    baffle_hole_diameter_m: str
    baffle_hole_radius_m: str
    cut_height_m: str
    chord_offset_from_center_m: str
    baffle_planes: tuple[BafflePlaneGeometry, ...]
    position_count: int
    warnings: tuple[MessageEntry, ...]
    blockers: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: tuple[tuple[str, Any], ...]


###############################################################################
# Section 8.9 - BaffleGeometryValidationResult (6 fields)
###############################################################################


@dataclass(frozen=True, eq=True)
class BaffleGeometryValidationResult:
    """Section 8.9 - Top-level validation result (6 fields)."""

    status: ValidationStatus
    geometry: BaffleGeometry | None
    warnings: tuple[MessageEntry, ...]
    blockers: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...]
    blocked_result_hash: str | None


###############################################################################
# Section 8.3 - BaffleGeometryRequest (in-memory typed)
###############################################################################


@dataclass(frozen=True, eq=True)
class BaffleGeometryRequest:
    """Section 8.3 - In-memory typed request after parse_request."""

    schema_version: str
    configuration: Any
    tube_layout: Any
    shell_bundle_geometry: Any
    axial_span: CallerSuppliedBaffleAxialSpan
    design_authority: CallerSuppliedBaffleDesignAuthority
    evidence_refs: tuple[str, ...]


###############################################################################
# Section 6.1 - Schema constants
###############################################################################


REQUEST_SCHEMA_VERSION = "task024.baffle-geometry-request.v1"
AXIAL_SPAN_SCHEMA_VERSION = "task024.baffle-axial-span.v1"
# Build the broken-line value via char codes (avoid display-truncation trap)
_dav_codes = [
    116,
    97,
    115,
    107,
    48,
    50,
    52,
    46,
    98,
    97,
    102,
    102,
    108,
    101,
    45,
    100,
    101,
    115,
    105,
    103,
    110,
    45,
    97,
    117,
    116,
    104,
    111,
    114,
    105,
    116,
    121,
    46,
    118,
    49,
]
DAV_VALUE = "".join(chr(c) for c in _dav_codes)
DESIGN_AUTHORITY_SCHEMA_VERSION = DAV_VALUE
RESULT_SCHEMA_VERSION = "task024.baffle-geometry.v1"
PROFILE_ID = "hxforge.shell_tube.baffle_geometry.v1"
DESIGN_CONTRACT_PATH = "docs/tasks/TASK-024-shell-and-tube-baffle-geometry-and-spacing.md"


###############################################################################
# Section 7.3 - Strict-precedence discipline tokens (3 frozen booleans)
###############################################################################


CLASSIFICATION_BEFORE_PUBLIC_OUTPUT_QUANTIZATION = True
BOUNDARY_PREDICATES_USE_UNQUANTIZED_DECIMAL_DERIVATIONS = True
PUBLIC_OUTPUT_QUANTIZATION_MUST_NOT_CHANGE_CLASSIFICATION = True


###############################################################################
# Section 3.2 + 3.3 - Closed unsupported and deferred sets
###############################################################################


UNSUPPORTED_FAMILIES: tuple[str, ...] = (
    "FLOATING_HEAD",
    "U_TUBE",
)


DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "CROSSFLOW_FLOW_AREA_NOT_COMPUTABLE",
    "WINDOW_FLOW_AREA_NOT_COMPUTABLE",
    "MINIMUM_CROSSFLOW_AREA_NOT_COMPUTABLE",
    "HYDRAULIC_DIAMETER_NOT_COMPUTABLE",
    "LEAKAGE_FLOW_AREA_NOT_COMPUTABLE",
    "BYPASS_FLOW_AREA_NOT_COMPUTABLE",
    "LEAKAGE_CORRECTION_FACTOR_NOT_COMPUTABLE",
    "BYPASS_CORRECTION_FACTOR_NOT_COMPUTABLE",
    "SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE",
    "KERN_SCREENING_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "FLOW_INDUCED_VIBRATION_NOT_COMPUTABLE",
    "THERMAL_EXPANSION_NOT_COMPUTABLE",
    "MECHANICAL_ADEQUACY_NOT_COMPUTABLE",
    "MANUFACTURING_ADEQUACY_NOT_COMPUTABLE",
    "MATERIAL_SELECTION_NOT_COMPUTABLE",
    "MASS_NOT_COMPUTABLE",
    "COST_NOT_COMPUTABLE",
    "OPTIMIZATION_NOT_COMPUTABLE",
    "API_NOT_COMPUTABLE",
    "PERSISTENCE_NOT_COMPUTABLE",
    "CLI_NOT_COMPUTABLE",
    "REPORT_NOT_COMPUTABLE",
    "GOLDEN_VALIDATION_NOT_COMPUTABLE",
)


###############################################################################
# Section 8 - Frozen semantic tokens for region semantics
###############################################################################


WINDOW_REGION_SEMANTICS = "BAFFLE_DISK_INTERSECTION_WINDOW_HALF_PLANE"
BAFFLE_COVERED_REGION_SEMANTICS = "BAFFLE_DISK_MINUS_WINDOW_SEGMENT"
CROSSFLOW_REFERENCE_REGION_SEMANTICS = "CLASSIFICATION_REFERENCE_ONLY_NOT_FLOW_AREA"


###############################################################################
# Public exports
###############################################################################


__all__ = [
    "AXIAL_SPAN_SCHEMA_VERSION",
    "BAFFLE_COVERED_REGION_SEMANTICS",
    "BaffleGeometry",
    "BaffleGeometryRequest",
    "BaffleGeometryValidationResult",
    "BaffleOrientation",
    "BafflePlaneGeometry",
    "BaffleType",
    "BlockerCode",
    "CallerSuppliedBaffleAxialSpan",
    "CallerSuppliedBaffleDesignAuthority",
    "CLASSIFICATION_BEFORE_PUBLIC_OUTPUT_QUANTIZATION",
    "BOUNDARY_PREDICATES_USE_UNQUANTIZED_DECIMAL_DERIVATIONS",
    "PUBLIC_OUTPUT_QUANTIZATION_MUST_NOT_CHANGE_CLASSIFICATION",
    "CROSSFLOW_REFERENCE_REGION_SEMANTICS",
    "CutChordGeometry",
    "DEFERRED_CAPABILITIES",
    "DESIGN_AUTHORITY_SCHEMA_VERSION",
    "DESIGN_CONTRACT_PATH",
    "MessageEntry",
    "PhysicalTubeDiskAudit",
    "PROFILE_ID",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "TubeHoleClassification",
    "TubeRegionClassification",
    "UNSUPPORTED_FAMILIES",
    "ValidationStatus",
    "WINDOW_REGION_SEMANTICS",
    "WarningCode",
]

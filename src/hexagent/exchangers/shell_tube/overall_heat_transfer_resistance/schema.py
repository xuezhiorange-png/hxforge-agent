"""Frozen TASK-037 schema and source-synchronization constants.

The module is intentionally declarative.  Engineering equations live in
``engineering.py`` and canonical identity projections live in ``canonical.py``;
neither module is allowed to silently add fields to these ordered contracts.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

TASK_ID: Final[str] = "TASK037"
TASK037_VERSION: Final[str] = "task037.overall-heat-transfer-resistance.v1"
PROFILE_ID: Final[str] = "hxforge.shell_tube.overall_heat_transfer_resistance.v1"
REQUEST_SCHEMA_VERSION: Final[str] = "task037.request.v1"
RESULT_SCHEMA_VERSION: Final[str] = "task037.success-result.v1"
TYPED_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task037.typed-blocked-result.v1"
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task037.raw-boundary-blocked-result.v1"
IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "task037.overall-heat-transfer-resistance.impl-v1"
DESIGN_CONTRACT_PATH: Final[str] = (
    "docs/tasks/TASK-037-shell-and-tube-overall-heat-transfer-resistance.md"
)

# R7 is the final runtime identity authority retained by the frozen R10
# contract.  This is deliberately not the proposal revision token.
SOURCE_DEFINITION_ISSUE: Final[int] = 208
SOURCE_DEFINITION_REVISION: Final[str] = "R3_FROZEN"
SOURCE_DEFINITION_REVIEW_AUDIT_COMMENT: Final[int] = 5461369330
DESIGN_ISSUE: Final[int] = 209
R7_FINAL_RUNTIME_DESIGN_AUTHORITY: Final[str] = "R7_FINAL_FROZEN"
DESIGN_REVISION: Final[str] = R7_FINAL_RUNTIME_DESIGN_AUTHORITY

SURFACE_TRANSFORM_NAMESPACE: Final[str] = "task037.surface-transform-authority.v1"
WALL_RESISTANCE_NAMESPACE: Final[str] = "task037.wall-resistance-authority.v1"
FOULING_AUTHORITY_NAMESPACE: Final[str] = "task037.fouling-authority.v1"
FROZEN_IDENTITY_NAMESPACE: Final[str] = "hexagent.frozen-identity.v1"
PROVENANCE_NAMESPACE: Final[str] = "task037.provenance.v1"
SUCCESS_RESULT_NAMESPACE: Final[str] = "task037.success-result.v1"
REQUEST_HASH_NAMESPACE: Final[str] = "task037.request.v1"
TYPED_BLOCKED_RESULT_HASH_NAMESPACE: Final[str] = "task037.typed-blocked-result.v1"
RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE: Final[str] = "task037.raw-boundary-blocked-result.v1"
RAW_PROJECTION_NAMESPACE: Final[str] = "task037.raw-projection.v1"

REQUEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "task037_version",
    "implementation_software_version",
    "wall_material_authority",
    "wall_thermal_conductivity_authority",
    "inside_fouling_authority",
    "outside_fouling_authority",
    "evidence_refs",
)
TASK037_REQUEST_FIELDS: Final[tuple[str, ...]] = REQUEST_FIELDS

SURFACE_TRANSFORM_FIELDS: Final[tuple[str, ...]] = (
    "task021_layout_hash",
    "task025_result_hash",
    "task025_hydraulic_authority_hash",
    "tube_geometry_snapshot_hash",
    "tube_inner_diameter_m",
    "tube_outer_diameter_m",
    "tube_side_film_reference_surface",
    "overall_u_reference_surface",
    "outer_to_inner_area_ratio",
    "engineering_source_id",
    "engineering_source_locations",
)
TASK037_SURFACE_TRANSFORM_FIELDS: Final[tuple[str, ...]] = SURFACE_TRANSFORM_FIELDS

WALL_RESISTANCE_FIELDS: Final[tuple[str, ...]] = (
    "surface_transform_authority_hash",
    "task025_result_hash",
    "task025_hydraulic_authority_hash",
    "task025_internal_heat_transfer_surface_area_m2",
    "task025_area_quantum_m2",
    "task025_area_rounding_mode",
    "producer_area_precision_policy_id",
    "producer_area_precision_policy_hash",
    "producer_precision_limitation_disclosed",
    "producer_precision_threshold_defined",
    "wall_bundle_numerical_basis",
    "wall_material_authority_hash",
    "wall_conductivity_authority_hash",
    "wall_bundle_conduction_resistance_k_w",
    "wall_resistance_outer_surface_m2_k_w",
    "engineering_source_id",
    "engineering_source_location",
    "source_formula_identity",
    "thin_wall_approximation_used",
)
TASK037_WALL_RESISTANCE_FIELDS: Final[tuple[str, ...]] = WALL_RESISTANCE_FIELDS

FOULING_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "authority_id",
    "reference_surface",
    "resistance_value_m2_k_w",
    "resistance_units",
    "fluid_service_id",
    "source_id",
    "source_version",
    "source_location",
    "permission_status",
    "approval_status",
    "applicability",
    "authority_hash",
)

FROZEN_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "identity_type",
    "identity_id",
    "identity_hash",
)

SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "request_hash",
    "task021_identity",
    "task025_identity",
    "task025_hydraulic_authority_hash",
    "tube_geometry_snapshot_hash",
    "heat_transfer_length_hash",
    "tube_side_film_reference_surface",
    "overall_u_reference_surface",
    "outer_to_inner_area_ratio",
    "surface_transform_authority_hash",
    "wall_material_authority_hash",
    "wall_conductivity_authority_hash",
    "wall_bundle_conduction_resistance_k_w",
    "wall_resistance_outer_surface_m2_k_w",
    "inside_fouling_authority",
    "outside_fouling_authority",
    "fouling_authority_ledger",
    "applicability_ledger",
    "completeness_ledger",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)
TASK037_SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = SUCCESS_RESULT_FIELDS

PROVENANCE_FIELDS: Final[tuple[str, ...]] = (
    "task_id",
    "source_definition_issue",
    "source_definition_revision",
    "source_definition_review_audit_comment",
    "design_issue",
    "design_revision",
    "implementation_software_version",
    "request_hash",
    "task021_layout_hash",
    "task025_result_hash",
    "task025_hydraulic_authority_hash",
    "tube_geometry_snapshot_hash",
    "heat_transfer_length_hash",
    "task025_internal_heat_transfer_surface_area_m2",
    "task025_area_quantum_m2",
    "task025_area_rounding_mode",
    "producer_area_precision_policy_id",
    "producer_area_precision_policy_hash",
    "producer_precision_limitation_disclosed",
    "producer_precision_threshold_defined",
    "wall_material_authority_hash",
    "wall_conductivity_authority_hash",
    "inside_fouling_authority_hash",
    "outside_fouling_authority_hash",
    "surface_transform_authority_hash",
    "wall_resistance_authority_hash",
    "source_identity_hashes",
    "producer_edges",
    "evidence_refs",
    "deferred_capabilities",
    "provenance_hash",
)
PROVENANCE_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in PROVENANCE_FIELDS if field != "provenance_hash"
)

# The public models include the schema/identity envelope around the semantic
# result projection above.  Hashing is intentionally restricted to the frozen
# SUCCESS_RESULT_FIELDS tuple.
PUBLIC_SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "task037_version",
    "implementation_software_version",
    *SUCCESS_RESULT_FIELDS,
    "result_hash",
    "result_id",
)

TYPED_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "task037_version",
    "implementation_software_version",
    "failure_stage",
    "request_hash",
    "task021_identity",
    "task025_identity",
    "task025_hydraulic_authority_hash",
    "tube_geometry_snapshot_hash",
    "heat_transfer_length_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "provenance",
    "blocked_result_hash",
)
TASK037_TYPED_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = TYPED_BLOCKED_RESULT_FIELDS

RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "task037_version",
    "implementation_software_version",
    "raw_request_projection",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
)
TASK037_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    RAW_BOUNDARY_BLOCKED_RESULT_FIELDS
)

APPLICABILITY_ROWS: Final[tuple[str, ...]] = (
    "A01_TASK021_VALID",
    "A02_TASK025_VALID",
    "A03_TASK021_TASK025_IDENTITY_COMPATIBLE",
    "A04_CYLINDRICAL_GEOMETRY_VALID",
    "A05_TUBE_SIDE_FILM_SURFACE_AUTHORITY_ESTABLISHED",
    "A06_SURFACE_TRANSFORM_APPLICABLE",
    "A07_WALL_MATERIAL_AUTHORITY_ADMISSIBLE",
    "A08_WALL_CONDUCTIVITY_AUTHORITY_ADMISSIBLE",
    "A09_INSIDE_FOULING_AUTHORITY_ADMISSIBLE",
    "A10_OUTSIDE_FOULING_AUTHORITY_ADMISSIBLE",
)
COMPLETENESS_ROWS: Final[tuple[str, ...]] = (
    "C01_SURFACE_BASIS_AUTHORITY_COMPLETE",
    "C02_WALL_RESISTANCE_AUTHORITY_COMPLETE",
    "C03_INSIDE_FOULING_AUTHORITY_COMPLETE",
    "C04_OUTSIDE_FOULING_AUTHORITY_COMPLETE",
    "C05_FOULING_AUTHORITY_LEDGER_COMPLETE",
    "C06_TASK038_FORWARD_CONSUMER_CONTRACT_COMPLETE",
)
APPLICABILITY_STATUSES: Final[tuple[str, ...]] = (
    "PASS",
    "BLOCKED_MISSING",
    "BLOCKED_INVALID",
    "BLOCKED_INCOMPATIBLE",
    "BLOCKED_UNAPPROVED",
    "BLOCKED_SOURCE_INCOMPLETE",
    "BLOCKED_PERMISSION",
)

DEFERRED_CAPABILITIES: Final[tuple[str, ...]] = (
    "OVERALL_U",
    "UA",
    "LMTD",
    "HEAT_DUTY",
    "OUTLET_TEMPERATURES",
    "FULL_EXCHANGER_THERMAL_RATING",
)

STAGE_ORDER: Final[tuple[str, ...]] = (
    "S00_RAW_INPUT_BOUNDARY",
    "S01_TYPED_REQUEST_SCHEMA_VALIDATION",
    "S02_TASK021_UPSTREAM_VALIDATION",
    "S03_TASK025_UPSTREAM_VALIDATION",
    "S04_TASK021_TASK025_CROSS_BINDING",
    "S05_GEOMETRY_AND_SURFACE_SEMANTIC_VALIDATION",
    "S06_WALL_MATERIAL_AND_CONDUCTIVITY_AUTHORITY_ADMISSIBILITY_VALIDATION",
    "S07_FOULING_AUTHORITY_ADMISSIBILITY_VALIDATION",
    "S08_SURFACE_TRANSFORM_COMPUTATION",
    "S09_CYLINDRICAL_WALL_RESISTANCE_COMPUTATION",
    "S10_APPLICABILITY_AND_COMPLETENESS_FINALIZATION",
    "S11_CANONICAL_HASH_UUID_PROVENANCE",
)
STAGE_RANKS: Final[dict[str, int]] = {stage: index for index, stage in enumerate(STAGE_ORDER)}

TUBE_SIDE_FILM_REFERENCE_SURFACE: Final[str] = "INNER_TUBE_SURFACE"
OVERALL_U_REFERENCE_SURFACE: Final[str] = "OUTER_TUBE_SURFACE"
SURFACE_SEMANTIC_AUTHORITY_MODE: Final[str] = "CONTRACT_AND_ENGINEERING_SOURCE_DERIVED"

TASK025_PUBLIC_AREA_QUANTUM_M2: Final[str] = "1E-10"
TASK025_PUBLIC_AREA_ROUNDING_MODE: Final[str] = "ROUND_HALF_EVEN"
TASK025_PUBLIC_AREA_PRECISION_POLICY_ID: Final[str] = (
    "task037.task025-public-area-authority.accept-positive-v1"
)
# Names used by the frozen public producer-authority wording.  The existing
# TASK025_PUBLIC_* names remain the canonical internal spelling; these are
# exact aliases, not additional identity fields or hash contracts.
PRODUCER_AREA_PRECISION_POLICY_ID: Final[str] = TASK025_PUBLIC_AREA_PRECISION_POLICY_ID
TASK025_AREA_QUANTUM_M2: Final[Decimal] = Decimal("1E-10")
TASK025_AREA_ROUNDING_MODE: Final[str] = TASK025_PUBLIC_AREA_ROUNDING_MODE
PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII: Final[str] = (
    "task037.task025-public-area-authority.accept-positive-v1|"
    "quantum_m2=0.0000000001|rounding=ROUND_HALF_EVEN|full_positive_domain=true|"
    "threshold_defined=false|limitation_disclosed=true|"
    "max_relative_divergence_approaches=0.5|runtime_warning=false"
)
PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII_BYTES: Final[int] = 242
PRODUCER_AREA_PRECISION_POLICY_HASH: Final[str] = (
    "9d813406416e734d7f4ece78adcdb9e05155c5f43a3e5cbe18b8f73917ae85e9"
)

RATIO_QUANTUM: Final[str] = "1E-15"
WALL_OUTPUT_QUANTUM: Final[str] = "1E-15"
NOMINAL_DECIMAL_PRECISION: Final[int] = 160
WORKING_DECIMAL_PRECISION: Final[int] = 200
WORKING_GUARD_DIGITS: Final[int] = 40
ROUNDING_MODE: Final[str] = "ROUND_HALF_EVEN"

UUID_NAMESPACE: Final[str] = "a0370000-0000-5000-8000-000000000037"
UUID_VERSION: Final[int] = 5
UUID_NAME_PREFIX: Final[str] = "task037-result-v1::"
SELF_EDGE_COUNT: Final[int] = 0

# R7 static identity literals.  These are public expected-value oracles for
# tests and replay; production never derives an expected value from them.
R7_SURFACE_HASH: Final[str] = "19690b6fd6694284daa1daa7a001f261555dcd08c6d21ec99940e35ee97612bc"
R7_WALL_HASH: Final[str] = "3086bcae0faf0a2b92b626740fa0e913200ddbe3615aa7aaad33dec60f41b29c"
R7_PROVENANCE_HASH_A: Final[str] = (
    "b9d17f8547da700e09e34650ea643931d31b8ee8a18bb764c98f5210552c1760"
)
R7_PROVENANCE_HASH_B: Final[str] = (
    "5d841a64b2215a9d8c89424431f29516b4c9c6e781064f1c35a1e796f5671fb4"
)
R7_RESULT_HASH_A: Final[str] = "09c5ecbbfe86f0ae403009f1ed45298250432b55d90c68a43e7c98b3f66595c9"
R7_RESULT_HASH_B: Final[str] = "c8c6b8ac1e31e663b7128edb7755246ffdc53cbe704a06df7149d617cf282d3f"
R7_RESULT_ID_A: Final[str] = "537d256e-ac25-51da-b74c-698f2e36df05"
R7_RESULT_ID_B: Final[str] = "7649d8a5-8f20-5abb-9144-3f01bf2bd2c8"
R7_SURFACE_BYTES: Final[int] = 1041
R7_WALL_BYTES: Final[int] = 1724
R7_PROVENANCE_PREIMAGE_BYTES: Final[int] = 3133
R7_PROVENANCE_BYTES: Final[int] = 3234
R7_RESULT_BYTES: Final[int] = 7723

SOURCE_FORMULA_IDENTITY: Final[str] = "EXACT_CYLINDRICAL_WALL_RESISTANCE"
WALL_BUNDLE_NUMERICAL_BASIS: Final[str] = "TASK025_PUBLIC_INNER_AREA_PROJECTION_V1"
ENGINEERING_SOURCE_ID: Final[str] = "T037-S01-DOE-HDBK-1012-2-92"
ENGINEERING_SOURCE_LOCATIONS: Final[tuple[str, ...]] = (
    "T037-S01-L01|HT-02_Page_12|PDF_ZERO_BASED_PAGE=33|EQUATION=2-7",
    "T037-S01-L04|HT-02_Page_22|PDF_ZERO_BASED_PAGE=43|EQUATION=2-10",
)
ENGINEERING_SOURCE_LOCATION_WALL: Final[str] = (
    "T037-S01-L02|HT-02_Page_13|PDF_ZERO_BASED_PAGE=34|EQUATION=2-8"
)

__all__ = [name for name in globals() if name.isupper()]

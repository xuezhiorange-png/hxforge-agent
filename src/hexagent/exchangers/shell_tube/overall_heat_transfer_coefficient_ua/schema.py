"""Frozen TASK-038 overall-U/UA schema and identity constants.

The module contains only the declarative contract.  In particular, the
published literals below are test oracles; runtime code never derives an
expected value from them.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

TASK_ID: Final[str] = "TASK038"
TASK038_VERSION: Final[str] = "task038.overall-u-ua.v1"
PROFILE_ID: Final[str] = "hxforge.shell_tube.overall_u_ua.v1"
REQUEST_SCHEMA_VERSION: Final[str] = "task038.request.v1"
SUCCESS_RESULT_SCHEMA_VERSION: Final[str] = "task038.success-result.v1"
TYPED_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task038.typed-blocked-result.v1"
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task038.raw-boundary-blocked-result.v1"
IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "task038.overall-u-ua.impl-v1"

SOURCE_DEFINITION_ISSUE: Final[int] = 211
SOURCE_DEFINITION_REVISION: Final[str] = "R1_FROZEN"
DESIGN_ISSUE: Final[int] = 212
DESIGN_REVISION: Final[str] = "R4_FINAL_FROZEN"
RUNTIME_DESIGN_AUTHORITY_TOKEN: Final[str] = "R4_FINAL_FROZEN"
BASE_MAIN_SHA: Final[str] = "9a6ca44726357b683590b51d2d727002ca756d2e"
BASE_MAIN_TREE: Final[str] = "e57ee630365b87ffff70b93d89e070de55461374"
BASELINE_REPAIR_GOVERNANCE_COMMENT_ID: Final[str] = "5472639060"

SERVICE_BINDING_NAMESPACE: Final[str] = "task038.tube-side-service-binding-authority.v1"
PRODUCER_ENVELOPE_IDENTITY_NAMESPACE: Final[str] = "task038.producer-envelope-identity.v1"
ENGINEERING_SOURCE_IDENTITY_NAMESPACE: Final[str] = "task038.engineering-source-identity.v1"
REQUEST_HASH_NAMESPACE: Final[str] = "task038.request.v1"
CROSS_PRODUCER_COMPATIBILITY_NAMESPACE: Final[str] = "task038.cross-producer-compatibility.v1"
RESISTANCE_COMPOSITION_AUTHORITY_NAMESPACE: Final[str] = (
    "task038.resistance-composition-authority.v1"
)
OUTER_AREA_PROJECTION_AUTHORITY_NAMESPACE: Final[str] = "task038.outer-area-projection-authority.v1"
UA_COMPOSITION_AUTHORITY_NAMESPACE: Final[str] = "task038.ua-composition-authority.v1"
THERMAL_RESISTANCE_LEDGER_ROW_NAMESPACE: Final[str] = "task038.thermal-resistance-ledger-row.v1"
APPLICABILITY_LEDGER_ROW_NAMESPACE: Final[str] = "task038.applicability-ledger-row.v1"
COMPLETENESS_LEDGER_ROW_NAMESPACE: Final[str] = "task038.completeness-ledger-row.v1"
BLOCKER_ENTRY_NAMESPACE: Final[str] = "task038.blocker-entry.v1"
WARNING_ENTRY_NAMESPACE: Final[str] = "task038.warning-entry.v1"
RAW_PROJECTION_NAMESPACE: Final[str] = "task038.raw-projection.v1"
PROVENANCE_NAMESPACE: Final[str] = "task038.provenance.v1"
SUCCESS_RESULT_NAMESPACE: Final[str] = "task038.success-result.v1"
TYPED_BLOCKED_RESULT_HASH_NAMESPACE: Final[str] = "task038.typed-blocked-result.v1"
RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE: Final[str] = "task038.raw-boundary-blocked-result.v1"

REQUEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "task025_result",
    "task026_result",
    "task035_result",
    "task037_result",
    "tube_side_service_binding_authority",
    "evidence_refs",
)
REQUEST_FIELD_COUNT: Final[int] = 8
REQUEST_HASH_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "task025_result_identity",
    "task026_result_identity",
    "task035_result_identity",
    "task037_result_identity",
    "tube_side_service_binding_authority_hash",
    "evidence_refs",
)

PRODUCER_ENVELOPE_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "producer_task_id",
    "branch",
    "native_result_id",
    "native_result_hash",
    "producer_evidence_hash",
)
CROSS_PRODUCER_COMPATIBILITY_FIELDS: Final[tuple[str, ...]] = (
    "task025_result_hash",
    "task026_result_hash",
    "task035_result_hash",
    "task037_result_hash",
    "tube_side_service_binding_authority_hash",
    "task025_hydraulic_authority_hash",
    "task021_layout_id",
    "task021_layout_hash",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task026_property_snapshot_hash",
    "task035_shell_side_fluid_id",
    "task037_inside_fouling_fluid_service_id",
    "task037_outside_fouling_fluid_service_id",
    "tube_side_film_reference_surface",
    "shell_side_film_reference_surface",
    "overall_u_reference_surface",
)

SERVICE_BINDING_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "authority_id",
    "tube_side_fluid_service_id",
    "task026_result_hash",
    "task026_property_snapshot_hash",
    "source_id",
    "source_version",
    "source_location",
    "source_class",
    "permission_status",
    "approval_status",
    "evidence_refs",
)
ENGINEERING_SOURCE_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "source_id",
    "source_version",
    "source_class",
    "source_locations",
    "permission_status",
)

RESISTANCE_COMPOSITION_FIELDS: Final[tuple[str, ...]] = (
    "cross_producer_compatibility_hash",
    "engineering_source_identity_hashes",
    "overall_u_reference_surface",
    "outer_to_inner_area_ratio",
    "tube_side_heat_transfer_coefficient_w_m2_k",
    "shell_side_heat_transfer_coefficient_w_m2_k",
    "inside_fouling_resistance_inner_surface_m2_k_w",
    "wall_resistance_outer_surface_m2_k_w",
    "outside_fouling_resistance_outer_surface_m2_k_w",
    "overall_u_quantum_w_m2_k",
    "rounding_mode",
)
OUTER_AREA_PROJECTION_FIELDS: Final[tuple[str, ...]] = (
    "task025_result_hash",
    "task025_internal_heat_transfer_surface_area_m2",
    "task037_result_hash",
    "task037_surface_transform_authority_hash",
    "outer_to_inner_area_ratio",
    "task025_area_quantum_m2",
    "task025_area_rounding_mode",
    "producer_area_precision_policy_id",
    "producer_area_precision_policy_hash",
    "producer_precision_limitation_disclosed",
    "producer_precision_threshold_defined",
    "outer_area_quantum_m2",
    "rounding_mode",
)
UA_COMPOSITION_FIELDS: Final[tuple[str, ...]] = (
    "resistance_composition_authority_hash",
    "outer_area_projection_authority_hash",
    "modeled_overall_heat_transfer_coefficient_w_m2_k",
    "outer_tube_surface_effective_area_m2",
    "ua_quantum_w_k",
    "rounding_mode",
)
THERMAL_RESISTANCE_LEDGER_ROW_FIELDS: Final[tuple[str, ...]] = (
    "term_id",
    "producer_owner",
    "source_field_or_projection",
    "native_reference_surface",
    "composed_reference_surface",
    "transformation_authority_hash_or_none",
    "value_m2_k_w",
    "status",
)
LEDGER_ROW_FIELDS: Final[tuple[str, ...]] = ("row_id", "status")

PROVENANCE_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "task_id",
    "source_definition_issue",
    "source_definition_revision",
    "design_issue",
    "design_revision",
    "implementation_software_version",
    "base_main_sha",
    "base_main_tree",
    "baseline_repair_governance_comment_id",
    "request_hash",
    "task025_result_hash",
    "task025_result_id",
    "task025_hydraulic_authority_hash",
    "task026_result_hash",
    "task026_result_id",
    "task026_property_snapshot_hash",
    "task035_result_hash",
    "task035_result_id",
    "task035_shell_side_fluid_id",
    "task037_result_hash",
    "task037_result_id",
    "task037_surface_transform_authority_hash",
    "task037_inside_fouling_authority_hash",
    "task037_outside_fouling_authority_hash",
    "task037_task025_area_quantum_m2",
    "task037_task025_area_rounding_mode",
    "task037_producer_area_precision_policy_id",
    "task037_producer_area_precision_policy_hash",
    "task037_producer_precision_limitation_disclosed",
    "task037_producer_precision_threshold_defined",
    "tube_side_service_binding_authority_hash",
    "engineering_source_identity_hashes",
    "cross_producer_compatibility_hash",
    "resistance_composition_authority_hash",
    "outer_area_projection_authority_hash",
    "ua_composition_authority_hash",
    "overall_u_reference_surface",
    "modeled_overall_heat_transfer_coefficient_w_m2_k",
    "outer_tube_surface_effective_area_m2",
    "modeled_ua_w_k",
    "evidence_refs",
    "deferred_capabilities",
)
PROVENANCE_FIELDS: Final[tuple[str, ...]] = (*PROVENANCE_PREHASH_FIELDS, "provenance_hash")

SUCCESS_RESULT_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "task038_version",
    "profile_id",
    "implementation_software_version",
    "request_hash",
    "overall_u_reference_surface",
    "full_thermal_resistance_composition_ledger",
    "modeled_overall_heat_transfer_coefficient_w_m2_k",
    "outer_tube_surface_effective_area_m2",
    "modeled_ua_w_k",
    "applicability_ledger",
    "completeness_ledger",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)
SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    *SUCCESS_RESULT_PREHASH_FIELDS,
    "result_hash",
    "result_id",
)
TYPED_BLOCKED_RESULT_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "task038_version",
    "implementation_software_version",
    "failure_stage",
    "request_hash",
    "producer_result_identities",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "provenance_or_none",
)
TYPED_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    *TYPED_BLOCKED_RESULT_PREHASH_FIELDS,
    "blocked_result_hash",
)
RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "task038_version",
    "implementation_software_version",
    "raw_request_projection",
    "blockers",
    "warnings",
    "deferred_capabilities",
)
RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    *RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS,
    "blocked_result_hash",
)

APPLICABILITY_ROWS: Final[tuple[str, ...]] = (
    "A01_TASK025_RESULT_VALID",
    "A02_TASK026_RESULT_VALID",
    "A03_TASK035_RESULT_VALID",
    "A04_TASK037_RESULT_VALID",
    "A05_HYDRAULIC_AUTHORITY_COMPATIBLE",
    "A06_TASK021_LAYOUT_COMPATIBLE",
    "A07_TASK020_CONFIGURATION_COMPATIBLE",
    "A08_TUBE_SIDE_FILM_SURFACE_COMPATIBLE",
    "A09_SHELL_SIDE_FILM_SURFACE_COMPATIBLE",
    "A10_TASK037_SURFACE_TRANSFORM_APPLICABLE",
    "A11_TUBE_SIDE_SERVICE_BINDING_VALID",
    "A12_INSIDE_FOULING_RUNTIME_SERVICE_COMPATIBLE",
    "A13_OUTSIDE_FOULING_RUNTIME_SERVICE_COMPATIBLE",
    "A14_REQUIRED_RESISTANCE_LEDGER_COMPLETE",
    "A15_OVERALL_U_NUMERIC_DOMAIN_VALID",
    "A16_TASK025_PUBLIC_AREA_VALID",
    "A17_OUTER_AREA_PROJECTION_VALID",
    "A18_OUTER_AREA_PUBLIC_QUANTIZATION_VALID",
    "A19_OVERALL_U_PUBLIC_VALUE_VALID",
    "A20_UA_NUMERIC_DOMAIN_VALID",
)
COMPLETENESS_ROWS: Final[tuple[str, ...]] = (
    "C01_ALL_DIRECT_PRODUCER_IDENTITIES_COMPLETE",
    "C02_CROSS_PRODUCER_COMPATIBILITY_COMPLETE",
    "C03_RUNTIME_SERVICE_BINDING_COMPLETE",
    "C04_FULL_THERMAL_RESISTANCE_LEDGER_COMPLETE",
    "C05_OVERALL_U_COMPLETE",
    "C06_OUTER_REFERENCE_AREA_COMPLETE",
    "C07_UA_COMPLETE",
    "C08_PROVENANCE_COMPLETE",
    "C09_TASK039_FORWARD_CONSUMER_CONTRACT_COMPLETE",
)
THERMAL_RESISTANCE_TERM_IDS: Final[tuple[str, ...]] = (
    "R01_TUBE_SIDE_FILM_OUTER_REFERENCE",
    "R02_INSIDE_FOULING_OUTER_REFERENCE",
    "R03_TUBE_WALL_CONDUCTION_OUTER_REFERENCE",
    "R04_OUTSIDE_FOULING_OUTER_REFERENCE",
    "R05_SHELL_SIDE_FILM_OUTER_REFERENCE",
)
DEFERRED_CAPABILITIES: Final[tuple[str, ...]] = (
    "LMTD",
    "HEAT_DUTY",
    "OUTLET_TEMPERATURES",
    "FULL_EXCHANGER_THERMAL_RATING",
)

STAGE_ORDER: Final[tuple[str, ...]] = (
    "S00_RAW_INPUT_BOUNDARY",
    "S01_REQUEST_AND_AUTHORITY_SCHEMA",
    "S02_TASK025_RESULT_REPLAY",
    "S03_TASK026_RESULT_REPLAY",
    "S04_TASK035_RESULT_REPLAY",
    "S05_TASK037_RESULT_REPLAY",
    "S06_HYDRAULIC_AND_TASK025_JOIN",
    "S07_TASK021_TASK020_ANCESTRY_JOIN",
    "S08_REFERENCE_SURFACE_JOIN",
    "S09_TUBE_SIDE_SERVICE_BINDING",
    "S10_SHELL_SIDE_SERVICE_AND_FOULING_BINDING",
    "S11_OVERALL_U_APPLICABILITY_INTERSECTION",
    "S12_FULL_RESISTANCE_COMPOSITION",
    "S13_OVERALL_U_PUBLIC_QUANTIZATION",
    "S14_OUTER_AREA_AUTHORITY_AND_TRANSFORM",
    "S15_OUTER_AREA_PUBLIC_QUANTIZATION",
    "S16_UA_COMPOSITION_AND_PUBLIC_QUANTIZATION",
    "S17_APPLICABILITY_COMPLETENESS_FINALIZATION",
    "S18_PROVENANCE_CANONICALIZATION",
    "S19_RESULT_HASH_UUID_FINALIZATION",
)
STAGE_RANKS: Final[dict[str, int]] = {stage: index for index, stage in enumerate(STAGE_ORDER)}

OVERALL_U_REFERENCE_SURFACE: Final[str] = "OUTER_TUBE_SURFACE"
TUBE_SIDE_FILM_REFERENCE_SURFACE: Final[str] = "INNER_TUBE_SURFACE"
SHELL_SIDE_FILM_REFERENCE_SURFACE: Final[str] = "OUTER_TUBE_SURFACE"

TASK038_OVERALL_U_QUANTUM_W_M2_K: Final[str] = "1E-9"
TASK038_OUTER_AREA_QUANTUM_M2: Final[str] = "1E-10"
TASK038_UA_QUANTUM_W_K: Final[str] = "1E-9"
OVERALL_U_QUANTUM: Final[Decimal] = Decimal(TASK038_OVERALL_U_QUANTUM_W_M2_K)
OUTER_AREA_QUANTUM: Final[Decimal] = Decimal(TASK038_OUTER_AREA_QUANTUM_M2)
UA_QUANTUM: Final[Decimal] = Decimal(TASK038_UA_QUANTUM_W_K)
ROUNDING_MODE: Final[str] = "ROUND_HALF_EVEN"
NOMINAL_DECIMAL_PRECISION: Final[int] = 160
WORKING_DECIMAL_PRECISION: Final[int] = 200
WORKING_GUARD_DIGITS: Final[int] = 40

TASK025_AREA_QUANTUM_M2: Final[Decimal] = Decimal("1E-10")
TASK025_AREA_ROUNDING_MODE: Final[str] = "ROUND_HALF_EVEN"
TASK025_PRODUCER_AREA_PRECISION_POLICY_ID: Final[str] = (
    "task037.task025-public-area-authority.accept-positive-v1"
)
PRODUCER_AREA_PRECISION_POLICY_ID: Final[str] = TASK025_PRODUCER_AREA_PRECISION_POLICY_ID
PRODUCER_AREA_PRECISION_POLICY_HASH: Final[str] = (
    "e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5"
)

UUID_NAMESPACE: Final[str] = "a0380000-0000-5000-8000-000000000038"
UUID_VERSION: Final[int] = 5
UUID_NAME_PREFIX: Final[str] = "task038-result-v1::"

ENGINEERING_SOURCE_S01_ID: Final[str] = "T038-S01-DOE-HDBK-1012-2-92"
ENGINEERING_SOURCE_S01_VERSION: Final[str] = "REV_0_JUNE_1992"
ENGINEERING_SOURCE_S01_CLASS: Final[str] = "US_GOVERNMENT_ENGINEERING_HANDBOOK"
ENGINEERING_SOURCE_S01_LOCATIONS: Final[tuple[str, ...]] = (
    "HT-02_Page_12|PDF_ZERO_BASED_PAGE=33|EQUATION=2-7",
    "HT-02_Page_20|PDF_ZERO_BASED_PAGE=41|FLUID-WALL-FLUID_PATH",
    "HT-02_Page_22|PDF_ZERO_BASED_PAGE=43|EQUATION=2-10",
)
ENGINEERING_SOURCE_S01_PERMISSION: Final[str] = "APPROVED_FOR_PUBLIC_RELEASE_DISTRIBUTION_UNLIMITED"
ENGINEERING_SOURCE_S02_ID: Final[str] = "T038-S02-NASA-CR-173469"
ENGINEERING_SOURCE_S02_VERSION: Final[str] = "NASA-CR-173469_JPL-PUB-83-74_1983-11-01"
ENGINEERING_SOURCE_S02_CLASS: Final[str] = "PUBLIC_CONTRACTOR_REPORT"
ENGINEERING_SOURCE_S02_LOCATIONS: Final[tuple[str, ...]] = ("Section_3.1_Page_3-1_Equation_3-2",)
ENGINEERING_SOURCE_S02_PERMISSION: Final[str] = "WORK_OF_US_GOV_PUBLIC_USE_PERMITTED"

R4_SURFACE_BYTES: Final[int] = 1041
R4_WALL_BYTES: Final[int] = 1724
TASK026_RAW_FIXTURE_CANONICAL_BYTES: Final[int] = 1390
TASK026_RAW_FIXTURE_SHA256: Final[str] = (
    "0b1b69c93361f01ff6ccee9aecf7724ddbca27844c3f0539cd998aaa29ed1433"
)
REQUEST_A_CANONICAL_BYTES: Final[int] = 2184
REQUEST_HASH_A: Final[str] = "3b5076d5cc1004d1a24d2dbc72677bc3e22b18c256a98214d8e2640c5348cffd"
REQUEST_B_CANONICAL_BYTES: Final[int] = 2186
REQUEST_HASH_B: Final[str] = "eae2ffae128e1e7e078de067005b1afa8c926c9c57cc84c3c3d8c676fc0f03b6"
PROVENANCE_PREIMAGE_BYTES_A: Final[int] = 3936
PROVENANCE_FULL_BYTES_A: Final[int] = 4037
PROVENANCE_HASH_A: Final[str] = "2fc1206f9343057cd28a113e43fced24ae5eead088bbc798c2c7e3a37e9f7086"
PROVENANCE_PREIMAGE_BYTES_B: Final[int] = 3938
PROVENANCE_FULL_BYTES_B: Final[int] = 4039
PROVENANCE_HASH_B: Final[str] = "f4e9c105a0586adc9807d0a6e753ae0ea3c6ff6e00001ecf44d16d45a46bfc90"
SUCCESS_RESULT_CANONICAL_BYTES_A: Final[int] = 12382
SUCCESS_RESULT_HASH_A: Final[str] = (
    "400aada8e58c347bdeed96e50b5dd6e02021e0a68100acaf54df62da64bc8bf8"
)
RESULT_ID_A: Final[str] = "f169b858-8221-569f-b841-dbfab7179d84"
SUCCESS_RESULT_CANONICAL_BYTES_B: Final[int] = 12384
SUCCESS_RESULT_HASH_B: Final[str] = (
    "fba6cb50931f39b80757b146e05c0d5a54aab05898d0be2c9522a1682ac29375"
)
RESULT_ID_B: Final[str] = "b60eb764-ee80-57bc-99e3-df3a52c8be6b"

GV01_GAMMA: Final[Decimal] = Decimal("1.2")
GV01_H_I: Final[Decimal] = Decimal("1000")
GV01_H_O: Final[Decimal] = Decimal("800")
GV01_R_FI_I: Final[Decimal] = Decimal("0.0002")
GV01_R_W_O: Final[Decimal] = Decimal("0.0001")
GV01_R_FO_O: Final[Decimal] = Decimal("0.0003")
GV01_A_I_PUB: Final[Decimal] = Decimal("10.0000000000")
GV01_PUBLIC_U: Final[Decimal] = Decimal("323.624595469")
GV01_PUBLIC_A_O: Final[Decimal] = Decimal("12.0000000000")
GV01_PUBLIC_UA: Final[Decimal] = Decimal("3883.495145628")

__all__ = [name for name in globals() if name.isupper()]

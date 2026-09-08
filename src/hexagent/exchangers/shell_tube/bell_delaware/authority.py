"""Frozen TASK-166 Bell--Delaware authority identifiers.

This module contains identifiers and the deliberately narrow applicability
envelope.  It does not contain a second copy of any upstream TASK-032--034
authority.
"""

from __future__ import annotations

from typing import Final

TASK_ID: Final[str] = "TASK-166"
REQUEST_SCHEMA_VERSION: Final[str] = "task166.bell-delaware-request.v1"
RESULT_SCHEMA_VERSION: Final[str] = "task166.bell-delaware-result.v1"
BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task166.bell-delaware-blocked.v1"
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = (
    "task166.bell-delaware-raw-boundary-blocked.v1"
)
IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "task166.bell-delaware-impl-v1"
SOURCE_DEFINITION_ID: Final[str] = "TASK165_R3_BELL_DELAWARE_SOURCE_AUTHORITY_V1"
DESIGN_CONTRACT_PATH: Final[str] = (
    "docs/tasks/TASK-166-bell-delaware-shell-side-thermal-hydraulic-model.md"
)

METHOD_ORIGIN_SOURCE_ID: Final[str] = "SRC-UDEL-BELL-1963-FINAL-REPORT"
PRIMARY_IMPLEMENTATION_SOURCE_ID: Final[str] = (
    "SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE"
)
JAMIL_PARAMETER_SOURCE_ID: Final[str] = (
    "SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS"
)
SAIF_TARIQ_JS_SOURCE_ID: Final[str] = "SRC-SAIF-TARIQ-2025-JMES-UNEQUAL-BAFFLE-SPACING-JS"
TASK032_SOURCE_ID: Final[str] = "TASK032_ACCEPTED_SHELL_SIDE_FLOW_STATE"

PRIMARY_SOURCE_LOCATION: Final[str] = "AIChE Journal 65(8), e16602 (2019), equations 36--73"
JAMIL_SOURCE_LOCATION: Final[str] = "Appendix A, Table A.1, accepted manuscript p.57"
JS_SOURCE_LOCATION: Final[str] = "JMES 19(4) (2025), section 2.1.3, equation 21, p.10882"
BELL_ORIGIN_LOCATION: Final[str] = (
    "University of Delaware Engineering Experimental Station final report (1963)"
)

SUPPORTED_LAYOUTS: Final[tuple[str, ...]] = ("LAYOUT_30_DEG", "LAYOUT_45_DEG", "LAYOUT_90_DEG")
SUPPORTED_SHELL_TYPE: Final[str] = "TEMA_E"
SUPPORTED_CONSTRUCTION_FAMILY: Final[str] = "FIXED_TUBESHEET"
SUPPORTED_BAFFLE_TYPE: Final[str] = "SINGLE_SEGMENTAL"
SUPPORTED_PHASE: Final[str] = "SINGLE_PHASE"
SUPPORTED_RHEOLOGY: Final[str] = "NEWTONIAN"
SUPPORTED_SHELL_PASS_COUNT: Final[int] = 1
MIN_REYNOLDS: Final[str] = "0"
MAX_REYNOLDS: Final[str] = "100000"

RAW_MAX_DEPTH: Final[int] = 16
RAW_MAX_NODES: Final[int] = 512
RAW_MAX_SCALAR_BYTES: Final[int] = 16384

JAMIL_TABLE_ROWS: Final[tuple[str, ...]] = (
    "RE_LT_10",
    "RE_10_TO_LT_100",
    "RE_100_TO_LT_1000",
    "RE_1000_TO_LT_10000",
    "RE_10000_TO_100000",
)

SOURCE_ROLE_BY_ID: Final[dict[str, str]] = {
    METHOD_ORIGIN_SOURCE_ID: "METHOD_ORIGIN_AND_PROVENANCE",
    PRIMARY_IMPLEMENTATION_SOURCE_ID: "PRIMARY_IMPLEMENTATION_EQUATION_AUTHORITY",
    JAMIL_PARAMETER_SOURCE_ID: "SUPPLEMENTAL_IMPLEMENTATION_AUTHORITY_FOR_A1_A4_AND_B1_B4",
    SAIF_TARIQ_JS_SOURCE_ID: "SUPPLEMENTAL_IMPLEMENTATION_AUTHORITY_FOR_JS_ONLY",
    TASK032_SOURCE_ID: "UPSTREAM_REYNOLDS_PRANDTL_AND_FLOW_STATE_AUTHORITY",
}

SOURCE_CONFLICT_POLICY: Final[str] = "FAIL_CLOSED"
WILEY_SI_BYTES_OBTAINED: Final[bool] = False
WILEY_SI_TABLE_CONTENT_VERIFIED: Final[bool] = False
PSI_N_REQUIRED_BY_TASK166: Final[bool] = False

# Retrieved public evidence identities used by the provenance projection.
# The Gonçalves article is retained by URL because the admitted copy has no
# repository-managed byte artifact; the two supplemental artifacts have
# stable byte identities from source verification.
GONCALVES_SOURCE_URL: Final[str] = (
    "https://www.ou.edu/class/che-design/pub-papers/"
    "Linear%20method%20for%20the%20design%20of%20shell%20and%20tube%20heat%20"
    "exchangers%20using%20the%20Bell-Delaware%20Method%28Goncalves%20et%20al%29-19.pdf"
)
JAMIL_SOURCE_SHA256: Final[str] = "a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970"
SAIF_TARIQ_SOURCE_SHA256: Final[str] = (
    "0f66f8efbb4ce071a5408bed5f938d4d659189c199231289e674b92f1d0c9571"
)

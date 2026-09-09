"""TASK-167 authority identifiers and closed semantic constants."""

from __future__ import annotations

from typing import Final

TASK_ID: Final[str] = "TASK-167"
TASK167_VERSION: Final[str] = "1.0"
REQUEST_SCHEMA_VERSION: Final[str] = "task167.engineering-screening-request.v1"
RESULT_SCHEMA_VERSION: Final[str] = "task167.engineering-screening-result.v1"
BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task167.engineering-screening-blocked.v1"
RAW_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = (
    "task167.engineering-screening-raw-boundary-blocked.v1"
)
IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "task167.engineering-screening-impl-v1"
SOURCE_DEFINITION_ID: Final[str] = "TASK165_V0_6_SCOPE_SOURCE_ACCEPTANCE_FREEZE_R3"
DESIGN_CONTRACT_PATH: Final[str] = "docs/tasks/TASK-167-shell-and-tube-engineering-screening.md"

# Public method / qualitative source identities.  These identifiers are
# intentionally narrow; none is a standard-limit authority.
SOURCE_PETTIGREW_TAYLOR_PART1: Final[str] = "SRC-PETTIGREW-TAYLOR-2003-JFS-PART1-FIV"
SOURCE_PETTIGREW_TAYLOR_PART2: Final[str] = "SRC-PETTIGREW-TAYLOR-2003-JFS-PART2-FIV"
SOURCE_NIST_THERMAL_EXPANSION: Final[str] = (
    "SRC-NIST-BUREAU-STANDARDS-CIRCULAR-486-LINEAR-EXPANSION"
)
SOURCE_BELL_GOSSETT_UTUBE: Final[str] = "SRC-BELL-GOSSETT-UTUBE-CONSTRUCTION"
SOURCE_CHEMICAL_ENGINEER_CONSTRUCTION: Final[str] = "SRC-CHEMICAL-ENGINEER-SHELL-TUBE-OVERVIEW"
SOURCE_ELSEVIER_SHELL_TUBE_OVERVIEW: Final[str] = "SRC-ELSEVIER-SHELL-TUBE-OVERVIEW"
SOURCE_TASK020_RULE_PACK: Final[str] = "TASK020_TASK012_APPROVED_RULE_PACK_AUTHORITY"

PETTIGREW_PART1_DOI: Final[str] = "10.1016/S0889974603001208"
PETTIGREW_PART2_DOI: Final[str] = "10.1016/S088997460300121X"
NIST_SOURCE_URL: Final[str] = (
    "https://www.govinfo.gov/content/pkg/GOVPUB-C13-be29bf9d79f4605d85ee2b3e8b840df3/"
    "pdf/GOVPUB-C13-be29bf9d79f4605d85ee2b3e8b840df3.pdf"
)
BELL_GOSSETT_SOURCE_URL: Final[str] = (
    "https://www.bellgossett.org/Heat-Exchangers/Shell-and-Tube/U-Tube.html"
)
CHEMICAL_ENGINEER_SOURCE_URL: Final[str] = (
    "https://www.thechemicalengineer.com/features/getting-started-part-1-shell-and-tube-heat-exchangers/"
)
ELSEVIER_SOURCE_URL: Final[str] = (
    "https://www.sciencedirect.com/topics/engineering/shell-and-tube-exchangers"
)

SUPPORTED_PHASE: Final[str] = "SINGLE_PHASE"
SUPPORTED_RHEOLOGY: Final[str] = "NEWTONIAN"
SCREEN_STATUSES: Final[tuple[str, ...]] = ("PASS", "WARN", "BLOCKED")
AGGREGATE_STATUS_ORDER: Final[tuple[str, ...]] = ("BLOCKED", "WARN", "PASS")

TASK167_APPLICABILITY_CHECKS: Final[tuple[str, ...]] = (
    "CONFIGURATION_ACCEPTED",
    "TASK166_ACCEPTED",
    "TUBE_SIDE_ACCEPTED",
    "REQUIRED_SCREENS_EVALUATED",
    "STANDARD_AUTHORITY_BOUNDARY_SATISFIED",
    "PRELIMINARY_ONLY_SCOPE_SATISFIED",
)

TASK167_COMPLETENESS_FIELDS: Final[tuple[str, ...]] = (
    "configuration_evidence",
    "task166_evidence",
    "tube_side_evidence",
    "screening_requirements_evidence",
    "screening_property_evidence",
    "velocity_screens",
    "erosion_screen",
    "fouling_cleanability_screen",
    "thermal_expansion_screen",
    "construction_family_suitability_screen",
    "fiv_screen",
    "applicability",
    "provenance",
)

DEFERRED_CAPABILITIES: Final[tuple[str, ...]] = (
    "DETAILED_MECHANICAL_DESIGN_NOT_COMPUTABLE",
    "PRESSURE_VESSEL_CODE_COMPLIANCE_NOT_COMPUTABLE",
    "DETAILED_TUBESHEET_STRESS_NOT_COMPUTABLE",
    "DETAILED_VIBRATION_ANALYSIS_NOT_COMPUTABLE",
    "FATIGUE_NOT_COMPUTABLE",
    "TASK168_CANDIDATE_GENERATION_NOT_COMPUTABLE",
    "TASK169_RANKING_AND_RELEASE_ACCEPTANCE_NOT_COMPUTABLE",
)

RAW_MAX_DEPTH: Final[int] = 16
RAW_MAX_NODES: Final[int] = 512
RAW_MAX_SCALAR_BYTES: Final[int] = 16384

# This is a diagnostic source only.  No critical-velocity coefficient is
# present here, so FIV numeric limit output is deliberately not implemented.
FIV_NUMERIC_LIMIT_AUTHORITY_AVAILABLE: Final[bool] = False

__all__ = [name for name in globals() if name.isupper()]

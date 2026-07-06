"""TASK-017 material / mass / preliminary mechanical application layer.

Implements the TASK-017 frozen design contract
(docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md,
Frozen Contract Authority Commit SHA
``6ed5b7dc7d8df163796eacb838afcf5702a4c53a``,
Frozen Contract Authority Base SHA
``fbb05ae71f21e6cfd4d1041afb5958c863166248``) as a read-only
consumer of the TASK-013 frozen material / cost governance records
and the TASK-016 approved geometry catalog.

Slice A: MaterialSelector only.
Slice B: MassCalculator + MassBreakdown (consumes Slice A).
Slice C: PreliminaryMechanicalChecker (allowable-stress check only; consumes Slice A).
Slice D: PreliminaryMechanicalChecker extended with minimum-wall (§9.2)
        and straight-pipe-span (§9.3) preliminary screening checks;
        plus a §5.3 ``MechanicalCheckReport`` orchestrator.
Slice E (closeout) is NOT YET IMPLEMENTED.
The TASK-017 application layer NEVER modifies TASK-013 records,
NEVER introduces pressure-drop / C4 / cost / new-solver logic,
and NEVER bypasses the TASK-013 closed-set enums.
"""

from hexagent.material_mass_mechanical.mass_calculator import (
    COMPONENT_ROLES_FROZEN_ORDER,
    ERROR_GEOMETRY_CATALOG_INCONSISTENT,
    ERROR_GEOMETRY_CATALOG_UNAPPROVED,
    ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE,
    ERROR_INPUT_DIMENSIONAL_INCONSISTENT,
    ERROR_INPUT_UNIT_INCONSISTENT,
    MassBreakdown,
    MassCalculationRequest,
    MassProvenance,
    calculate_mass_breakdown,
)
from hexagent.material_mass_mechanical.material_selector import (
    COMPONENT_ROLE_CLOSED_SET,
    ERROR_MATERIAL_GOVERNANCE_INCOMPLETE,
    ERROR_MATERIAL_GOVERNANCE_UNAPPROVED,
    ERROR_MATERIAL_RESOLUTION_MISSING_ROLE,
    ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT,
    ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT,
    ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE,
    FROZEN_CONTRACT_AUTHORITY_BASE_SHA,
    FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
    PROPERTY_NAME_ALLOWABLE_STRESS,
    PROPERTY_NAME_DENSITY,
    PROPERTY_NAME_YOUNGS_MODULUS,
    UNIT_ALLOWABLE_STRESS,
    UNIT_DENSITY,
    UNIT_YOUNGS_MODULUS,
    MaterialProvenance,
    MaterialResolutionRequest,
    MaterialResolutionResult,
    MaterialSelectorError,
    float_to_decimal_string,
    resolve_material,
)
from hexagent.material_mass_mechanical.preliminary_checker import (
    MECHANICAL_ROLES_FROZEN_ORDER,
    SUPPORTED_MECHANICAL_ROLES,
    MechanicalCheckReport,
    MechanicalCheckReportProvenance,
    MechanicalCheckRequest,
    MinimumWallCheckProvenance,
    MinimumWallCheckRequest,
    MinimumWallCheckResult,
    PreliminaryCheckProvenance,
    PreliminaryCheckRequest,
    PreliminaryCheckResult,
    StraightPipeSpanCheckProvenance,
    StraightPipeSpanCheckRequest,
    StraightPipeSpanCheckResult,
    check_minimum_wall,
    check_straight_pipe_span,
    preliminary_check,
    run_mechanical_check_report,
)

__all__ = [
    "COMPONENT_ROLE_CLOSED_SET",
    "COMPONENT_ROLES_FROZEN_ORDER",
    "ERROR_GEOMETRY_CATALOG_INCONSISTENT",
    "ERROR_GEOMETRY_CATALOG_UNAPPROVED",
    "ERROR_HAIRPIN_BEND_INPUT_INCOMPLETE",
    "ERROR_INPUT_DIMENSIONAL_INCONSISTENT",
    "ERROR_INPUT_UNIT_INCONSISTENT",
    "ERROR_MATERIAL_GOVERNANCE_INCOMPLETE",
    "ERROR_MATERIAL_GOVERNANCE_UNAPPROVED",
    "ERROR_MATERIAL_RESOLUTION_MISSING_ROLE",
    "ERROR_MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT",
    "ERROR_MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT",
    "ERROR_MECHANICAL_CHECK_UNSUPPORTED_ROLE",
    "FROZEN_CONTRACT_AUTHORITY_BASE_SHA",
    "FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA",
    "MECHANICAL_ROLES_FROZEN_ORDER",
    "MassBreakdown",
    "MassCalculationRequest",
    "MassProvenance",
    "MaterialProvenance",
    "MaterialResolutionRequest",
    "MaterialResolutionResult",
    "MaterialSelectorError",
    "MechanicalCheckReport",
    "MechanicalCheckReportProvenance",
    "MechanicalCheckRequest",
    "MinimumWallCheckProvenance",
    "MinimumWallCheckRequest",
    "MinimumWallCheckResult",
    "PreliminaryCheckProvenance",
    "PreliminaryCheckRequest",
    "PreliminaryCheckResult",
    "PROPERTY_NAME_ALLOWABLE_STRESS",
    "PROPERTY_NAME_DENSITY",
    "PROPERTY_NAME_YOUNGS_MODULUS",
    "StraightPipeSpanCheckProvenance",
    "StraightPipeSpanCheckRequest",
    "StraightPipeSpanCheckResult",
    "SUPPORTED_MECHANICAL_ROLES",
    "UNIT_ALLOWABLE_STRESS",
    "UNIT_DENSITY",
    "UNIT_YOUNGS_MODULUS",
    "calculate_mass_breakdown",
    "check_minimum_wall",
    "check_straight_pipe_span",
    "float_to_decimal_string",
    "preliminary_check",
    "resolve_material",
    "run_mechanical_check_report",
]

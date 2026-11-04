"""V08-01 general user design case input, validation and solver handoff."""

from prototypes.v08_general_user_case.errors import (
    V08UserCaseValidationError,
    V08ValidationCode,
    V08ValidationIssue,
)
from prototypes.v08_general_user_case.loader import (
    load_general_user_design_case,
    load_general_user_design_case_json,
)
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import (
    GENERAL_USER_DESIGN_CASE_SCHEMA_V1,
    GeneralUserDesignCaseV1,
)

__all__ = [
    "GENERAL_USER_DESIGN_CASE_SCHEMA_V1",
    "GeneralUserDesignCaseV1",
    "V08SolverHandoffV1",
    "V08UserCaseValidationError",
    "V08ValidationCode",
    "V08ValidationIssue",
    "load_general_user_design_case",
    "load_general_user_design_case_json",
    "validate_and_build_solver_handoff",
]

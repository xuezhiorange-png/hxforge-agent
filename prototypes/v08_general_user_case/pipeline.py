"""End-to-end V08 user-case validation and solver handoff pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.errors import (
    V08UserCaseValidationError,
    V08ValidationCode,
    V08ValidationIssue,
)
from prototypes.v08_general_user_case.physical_feasibility import (
    PhysicalFeasibilityReport,
    assess_physical_feasibility,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1, build_solver_handoff
from prototypes.v08_general_user_case.user_design_case import (
    GeneralUserDesignCaseV1,
    NormalizedUserDesignCase,
)


@dataclass(frozen=True)
class V08UserCasePipelineResult:
    normalized: NormalizedUserDesignCase
    feasibility: PhysicalFeasibilityReport
    handoff: V08SolverHandoffV1

    def as_dict(self) -> dict[str, Any]:
        return {
            "normalized_input": self.normalized.input_snapshot_dict(),
            "physical_feasibility": self.feasibility.as_dict(),
            "solver_handoff": self.handoff.as_dict(),
        }


def _pydantic_issues(exc: ValidationError) -> tuple[V08ValidationIssue, ...]:
    issues: list[V08ValidationIssue] = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error["loc"])
        issues.append(
            V08ValidationIssue(
                code=V08ValidationCode.INVALID_INPUT,
                field=loc or "case",
                message=error["msg"],
                context={"type": error.get("type", "")},
            )
        )
    return tuple(issues)


def validate_and_build_solver_handoff(
    case: GeneralUserDesignCaseV1,
    provider: CoolPropProvider | None = None,
) -> V08UserCasePipelineResult:
    active_provider = provider or CoolPropProvider()
    try:
        normalized = NormalizedUserDesignCase.from_user_case(case)
    except ValidationError as exc:
        raise V08UserCaseValidationError(_pydantic_issues(exc)) from exc
    except ValueError as exc:
        raise V08UserCaseValidationError(
            (
                V08ValidationIssue(
                    code=V08ValidationCode.INVALID_INPUT,
                    field="case",
                    message=str(exc),
                    context={},
                ),
            )
        ) from exc

    feasibility = assess_physical_feasibility(normalized, active_provider)
    if not feasibility.ok:
        raise V08UserCaseValidationError(feasibility.issues)

    handoff = build_solver_handoff(normalized, feasibility, active_provider)
    return V08UserCasePipelineResult(
        normalized=normalized,
        feasibility=feasibility,
        handoff=handoff,
    )

"""Formal numerical contract posture (decoupled from solver BLOCKED → change contract)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prototypes.v08_thermal_rating.engineering_acceptance_decision_v08 import (
    ContractChangeEvidence,
    ContractReviewStatus,
    EngineeringAcceptanceDecisionPackage,
)
from prototypes.v08_thermal_rating.numerical_contract_terminal_v08 import (
    ProductionTerminalGateAudit,
)
from prototypes.v08_thermal_rating.propagation_defect_verdict_v08 import PropagationDefectVerdict

ContractPosture = Literal[
    "PRODUCTION_BLOCKED_REVIEW_ELIGIBLE",
    "PRODUCTION_BLOCKED_EVIDENCE_INSUFFICIENT",
    "PRODUCTION_PASS",
]


@dataclass(frozen=True)
class NumericalContractReview:
    """Legacy A/B posture derived from eligibility, not from BLOCKED alone."""

    numerical_contract_posture: ContractPosture
    contract_review_status: ContractReviewStatus
    contract_change_evidence: ContractChangeEvidence
    specific_required_change: str
    production_numerical_status: str
    rationale: tuple[str, ...]


def review_numerical_acceptance_contract(
    *,
    terminal: ProductionTerminalGateAudit,
    propagation: PropagationDefectVerdict,
    outer_n4_status: str,
    production_task173: str,
    cell_propagation_j_kg: float,
    decision_package: EngineeringAcceptanceDecisionPackage | None = None,
) -> NumericalContractReview:
    """Map layered decision package to review posture (no if BLOCKED → B)."""
    notes: list[str] = []
    notes.append(f"cell_face_propagation={cell_propagation_j_kg:.6e} J/kg")
    notes.append(f"terminal_h_residual={terminal.terminal_residual_j_kg}")
    notes.append(f"causal_proof={propagation.propagation_defect_causal_proof}")

    if decision_package is not None:
        review = decision_package.contract_review_status
        change_ev = decision_package.contract_change_evidence
        prod = decision_package.production_numerical_status
        scope = decision_package.recommended_contract_change
        posture: ContractPosture
        if prod == "PASS":
            posture = "PRODUCTION_PASS"
        elif review == "ELIGIBLE_FOR_DISCUSSION" and change_ev == "INSUFFICIENT":
            posture = "PRODUCTION_BLOCKED_REVIEW_ELIGIBLE"
        else:
            posture = "PRODUCTION_BLOCKED_EVIDENCE_INSUFFICIENT"
            scope = "none"
        return NumericalContractReview(
            numerical_contract_posture=posture,
            contract_review_status=review,
            contract_change_evidence=change_ev,
            specific_required_change=scope,
            production_numerical_status=prod,
            rationale=tuple(decision_package.rationale) + tuple(notes),
        )

    blocked = production_task173 != "VALIDATED" or outer_n4_status != "ACCEPTED"
    posture = "PRODUCTION_PASS" if not blocked else "PRODUCTION_BLOCKED_EVIDENCE_INSUFFICIENT"
    return NumericalContractReview(
        numerical_contract_posture=posture,
        contract_review_status="NOT_ELIGIBLE",
        contract_change_evidence="INSUFFICIENT",
        specific_required_change="none",
        production_numerical_status="BLOCKED" if blocked else "PASS",
        rationale=tuple(notes),
    )


__all__ = ["NumericalContractReview", "review_numerical_acceptance_contract"]

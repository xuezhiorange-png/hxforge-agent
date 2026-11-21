"""Formal numerical acceptance contract review (prototype closeout; no tolerance edits)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from prototypes.v08_thermal_rating.numerical_contract_terminal_v08 import (
    ProductionTerminalGateAudit,
)
from prototypes.v08_thermal_rating.propagation_defect_verdict_v08 import PropagationDefectVerdict

ContractDecision = Literal["A", "B"]


@dataclass(frozen=True)
class NumericalContractReview:
    numerical_contract_decision: ContractDecision
    specific_required_change: str
    rationale: tuple[str, ...]


def review_numerical_acceptance_contract(
    *,
    terminal: ProductionTerminalGateAudit,
    propagation: PropagationDefectVerdict,
    outer_n4_status: str,
    production_task173: str,
    cell_propagation_j_kg: float,
) -> NumericalContractReview:
    """Path A vs B per V08-03 contract review charter (no tolerance override)."""
    term_h = Decimal(terminal.terminal_residual_j_kg)
    allowed_h = Decimal(terminal.terminal_allowed_j_kg)
    enthalpy_gate = terminal.terminal_enthalpy_gate
    notes: list[str] = []
    notes.append(f"cell_face_propagation={cell_propagation_j_kg:.6e} J/kg")
    notes.append(f"terminal_residual_h={term_h} allowed_h={allowed_h}")

    if propagation.propagation_defect_causal_proof == "false" and cell_propagation_j_kg < float(
        allowed_h
    ):
        notes.append("propagation_cannot_explain_terminal_enthalpy_residual")

    if (
        outer_n4_status != "ACCEPTED"
        or enthalpy_gate == "BLOCKED"
        or production_task173 == "BLOCKED"
    ):
        decision: ContractDecision = "B"
        scope = (
            "Independent engineering review of Task173 terminal K/H contract vs binary64 outer "
            "shooting plateau and N4 mesh refinement; no ad-hoc prototype iteration. "
            "Propagation path A (Decimal authority + same-context PH) insufficient alone: "
            f"causal_proof={propagation.propagation_defect_causal_proof}."
        )
        return NumericalContractReview(decision, scope, tuple(notes))

    decision = "A"
    scope = (
        "Keep original Task172 C-ULP and Task173 terminal contract; complete production "
        "enthalpy-identity / outer-shooting representation fix with reproducible "
        "N4 ACCEPTED evidence."
    )
    return NumericalContractReview(decision, scope, tuple(notes))


__all__ = ["NumericalContractReview", "review_numerical_acceptance_contract"]

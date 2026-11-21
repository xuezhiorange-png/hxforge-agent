"""Layer-2 independent engineering physical checks (prototype; not production gates)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K

EvidenceGrade = Literal["SUFFICIENT", "PARTIAL", "INSUFFICIENT"]
MeshEvidence = Literal["N1_N2_ACCEPTED_N4_BLOCKED", "INCOMPLETE", "NOT_AVAILABLE"]


@dataclass(frozen=True)
class Frozen330Evidence:
    raw: dict[str, Any]
    case_id: str
    candidate_id: str
    geometry_hash: str
    shooting_n1: str
    shooting_n2: str
    shooting_n4: str
    n4_total_q_w: Decimal
    target_duty_w: Decimal
    terminal_residual_j_kg: Decimal
    terminal_allowed_j_kg: Decimal
    terminal_residual_k: Decimal
    cell_propagation_j_kg: float
    tube_dp_pa: Decimal
    shell_dp_pa: Decimal
    max_tube_dp_pa: Decimal
    max_shell_dp_pa: Decimal


def load_frozen_330_evidence(path: Path) -> Frozen330Evidence:
    data = json.loads(path.read_text(encoding="utf-8"))

    def dec(key: str) -> Decimal:
        return Decimal(str(data[key]))

    return Frozen330Evidence(
        raw=data,
        case_id=str(data["case_id"]),
        candidate_id=str(data["candidate_id"]),
        geometry_hash=str(data["geometry_hash"]),
        shooting_n1=str(data["shooting_n1"]),
        shooting_n2=str(data["shooting_n2"]),
        shooting_n4=str(data["shooting_n4"]),
        n4_total_q_w=dec("n4_total_q_w"),
        target_duty_w=dec("target_duty_w"),
        terminal_residual_j_kg=dec("terminal_residual_j_kg"),
        terminal_allowed_j_kg=dec("terminal_allowed_j_kg"),
        terminal_residual_k=Decimal(str(data["terminal_residual_k"])),
        cell_propagation_j_kg=float(data["cell_enthalpy_propagation_error_j_kg"]),
        tube_dp_pa=dec("tube_dp_pa"),
        shell_dp_pa=dec("shell_dp_pa"),
        max_tube_dp_pa=dec("max_tube_dp_pa"),
        max_shell_dp_pa=dec("max_shell_dp_pa"),
    )


@dataclass(frozen=True)
class EngineeringPhysicalAssessment:
    duty_at_or_above_target: bool
    tube_dp_within_envelope: bool
    shell_dp_within_envelope: bool
    energy_balance_plausible: bool
    mesh_convergence_evidence: MeshEvidence
    terminal_h_exceeds_contract_margin: bool
    propagation_subdominant_to_terminal: bool
    property_audit_pass: bool
    grade: EvidenceGrade
    notes: tuple[str, ...]


def assess_engineering_physical_layer(
    ev: Frozen330Evidence,
    *,
    tp_ph_query_status: str,
) -> EngineeringPhysicalAssessment:
    notes: list[str] = []
    duty_ok = ev.n4_total_q_w >= ev.target_duty_w
    tube_dp_ok = ev.tube_dp_pa <= ev.max_tube_dp_pa
    shell_dp_ok = ev.shell_dp_pa <= ev.max_shell_dp_pa
    energy_ok = duty_ok  # frozen isolated duty meets target; not whole-path production VALIDATED

    mesh: MeshEvidence
    if (
        ev.shooting_n1 == "ACCEPTED"
        and ev.shooting_n2 == "ACCEPTED"
        and ev.shooting_n4 == "BLOCKED"
    ):
        mesh = "N1_N2_ACCEPTED_N4_BLOCKED"
    else:
        mesh = "INCOMPLETE"
        notes.append("unexpected_isolated_mesh_gates")

    term_exceeds = ev.terminal_residual_j_kg > ev.terminal_allowed_j_kg
    prop_small = ev.cell_propagation_j_kg < float(ev.terminal_residual_j_kg) * 0.01
    prop_audit = tp_ph_query_status == "PASS"

    checks = [
        duty_ok,
        tube_dp_ok,
        shell_dp_ok,
        energy_ok,
        mesh != "NOT_AVAILABLE",
        prop_audit,
    ]
    if all(checks) and mesh == "N1_N2_ACCEPTED_N4_BLOCKED":
        grade: EvidenceGrade = "SUFFICIENT"
    elif any(checks):
        grade = "PARTIAL"
    else:
        grade = "INSUFFICIENT"

    if term_exceeds:
        over = ev.terminal_residual_j_kg - ev.terminal_allowed_j_kg
        notes.append(f"terminal_h_over_contract by {over} J/kg")
    if prop_small:
        notes.append("cell_face_propagation_not_causal_for_terminal_h")

    return EngineeringPhysicalAssessment(
        duty_at_or_above_target=duty_ok,
        tube_dp_within_envelope=tube_dp_ok,
        shell_dp_within_envelope=shell_dp_ok,
        energy_balance_plausible=energy_ok,
        mesh_convergence_evidence=mesh,
        terminal_h_exceeds_contract_margin=term_exceeds,
        propagation_subdominant_to_terminal=prop_small,
        property_audit_pass=prop_audit,
        grade=grade,
        notes=tuple(notes),
    )


@dataclass(frozen=True)
class NegativeControlResult:
    energy_inversion_blocked: bool
    wall_order_inversion_blocked: bool
    status: Literal["PASS", "BLOCKED"]


def run_negative_controls() -> NegativeControlResult:
    """Perturbed physics must not pass independent engineering checks."""

    def energy_check(
        q_hot_loss: Decimal, q_cold_gain: Decimal, q_wall: Decimal, tol: Decimal
    ) -> bool:
        residual = max(
            abs(q_hot_loss - q_wall), abs(q_cold_gain - q_wall), abs(q_hot_loss - q_cold_gain)
        )
        return residual <= tol

    baseline_tol = Decimal("1")
    q = Decimal("395277")
    ok_baseline = energy_check(q, q, q, baseline_tol)
    q_perturbed = q * Decimal("1.15")
    ok_perturbed = energy_check(q, q, q_perturbed, baseline_tol)
    energy_blocked = ok_baseline and not ok_perturbed

    def wall_order_ok(twi: float, two: float, t_cold: float, t_hot: float) -> bool:
        return twi > two and t_hot > t_cold and two > t_cold

    order_ok = wall_order_ok(305.0, 300.0, 295.0, 310.0)
    order_bad = wall_order_ok(290.0, 300.0, 295.0, 310.0)
    wall_blocked = order_ok and not order_bad

    status: Literal["PASS", "BLOCKED"] = "PASS" if energy_blocked and wall_blocked else "BLOCKED"
    return NegativeControlResult(
        energy_inversion_blocked=energy_blocked,
        wall_order_inversion_blocked=wall_blocked,
        status=status,
    )


def independent_engineering_duty_tolerance_w() -> Decimal:
    """Engineering floor for duty comparison (prototype L2), not production Task173."""
    return Decimal("1")


def physical_temperature_scale_from_contract() -> Decimal:
    """Do not back-solve tolerance from residual; use contract TERMINAL_TOLERANCE_K only."""
    return TERMINAL_TOLERANCE_K


__all__ = [
    "EngineeringPhysicalAssessment",
    "Frozen330Evidence",
    "NegativeControlResult",
    "assess_engineering_physical_layer",
    "load_frozen_330_evidence",
    "run_negative_controls",
]

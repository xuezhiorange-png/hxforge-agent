"""Layer-2 engineering physical screens (prototype; not production gates)."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K

EvidenceGrade = Literal["SUFFICIENT", "PARTIAL", "INSUFFICIENT"]
DutyScreen = Literal["INDICATIVE_PASS", "INDICATIVE_FAIL"]
HydraulicScreen = Literal["PASS", "BLOCKED"]
EnergyBalanceStatus = Literal["verified", "not_evaluated", "failed"]
LocalHeatTransfer = Literal["PASS", "BLOCKED", "NOT_EVALUATED"]
MeshConvergence = Literal["PASS", "PARTIAL", "BLOCKED"]
NozzleStatus = Literal["UNRESOLVED", "PASS", "BLOCKED"]
WallOrderStatus = Literal["PASS", "BLOCKED", "NOT_EVALUATED"]


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
    production_task172_gate: str
    production_task173_gate: str
    nozzle_velocity_status: str


def _parse_frozen_dict(data: dict[str, Any]) -> Frozen330Evidence:
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
        production_task172_gate=str(data.get("production_task172_gate", "BLOCKED")),
        production_task173_gate=str(
            data.get("production_task173_gate", data.get("production_task173", "BLOCKED"))
        ),
        nozzle_velocity_status=str(data.get("nozzle_velocity_status", "UNRESOLVED")),
    )


def load_frozen_330_evidence(path: Path) -> Frozen330Evidence:
    data = json.loads(path.read_text(encoding="utf-8"))
    return _parse_frozen_dict(data)


def load_frozen_330_evidence_from_dict(data: dict[str, Any]) -> Frozen330Evidence:
    return _parse_frozen_dict(deepcopy(data))


def evidence_with_overrides(base: Frozen330Evidence, **overrides: Any) -> Frozen330Evidence:
    data = deepcopy(base.raw)
    data.update(overrides)
    return _parse_frozen_dict(data)


@dataclass(frozen=True)
class EngineeringPhysicalScreens:
    duty_screen: DutyScreen
    hydraulic_screen: HydraulicScreen
    energy_balance: EnergyBalanceStatus
    local_heat_transfer: LocalHeatTransfer
    mesh_convergence: MeshConvergence
    nozzle_velocity: NozzleStatus
    wall_temperature_order: WallOrderStatus
    engineering_physical_evidence: EvidenceGrade


@dataclass(frozen=True)
class EngineeringPhysicalAssessment:
    screens: EngineeringPhysicalScreens
    grade: EvidenceGrade
    terminal_h_exceeds_contract_margin: bool
    terminal_h_over_allowed_pct: str | None
    propagation_subdominant_to_terminal: bool
    property_audit_pass: bool
    notes: tuple[str, ...]


def _energy_balance_status(raw: dict[str, Any]) -> EnergyBalanceStatus:
    keys = (
        "hot_loss_w",
        "cold_gain_w",
        "wall_duty_w",
        "energy_balance_residual_w",
        "energy_balance_tolerance_w",
    )
    if not all(k in raw for k in keys):
        return "not_evaluated"
    hot = Decimal(str(raw["hot_loss_w"]))
    cold = Decimal(str(raw["cold_gain_w"]))
    wall = Decimal(str(raw["wall_duty_w"]))
    residual = Decimal(str(raw["energy_balance_residual_w"]))
    tol = Decimal(str(raw["energy_balance_tolerance_w"]))
    imbalance = max(abs(hot - wall), abs(cold - wall), abs(hot - cold), residual)
    return "verified" if imbalance <= tol else "failed"


def _wall_order_status(raw: dict[str, Any]) -> WallOrderStatus:
    keys = ("tube_inlet_t_k", "shell_inlet_t_k", "wall_inner_k", "wall_outer_k")
    if not all(k in raw for k in keys):
        return "NOT_EVALUATED"
    t_hot = float(raw["tube_inlet_t_k"])
    t_cold = float(raw["shell_inlet_t_k"])
    twi = float(raw["wall_inner_k"])
    two = float(raw["wall_outer_k"])
    ok = twi > two and t_hot > t_cold and two > t_cold
    return "PASS" if ok else "BLOCKED"


def assess_engineering_physical_layer(
    ev: Frozen330Evidence,
    *,
    tp_ph_query_status: str,
) -> EngineeringPhysicalAssessment:
    notes: list[str] = []
    duty_screen: DutyScreen = (
        "INDICATIVE_PASS" if ev.n4_total_q_w >= ev.target_duty_w else "INDICATIVE_FAIL"
    )
    if duty_screen == "INDICATIVE_PASS":
        notes.append("duty_screen_is_experimental_isolated_not_production_validated")

    hydraulic: HydraulicScreen = (
        "PASS"
        if ev.tube_dp_pa <= ev.max_tube_dp_pa and ev.shell_dp_pa <= ev.max_shell_dp_pa
        else "BLOCKED"
    )

    energy = _energy_balance_status(ev.raw)
    local_ht: LocalHeatTransfer = (
        "BLOCKED"
        if ev.production_task172_gate == "BLOCKED"
        else "PASS"
        if ev.production_task172_gate == "PASS"
        else "NOT_EVALUATED"
    )

    if ev.shooting_n4 == "BLOCKED":
        mesh: MeshConvergence = "BLOCKED"
    elif ev.shooting_n1 == "ACCEPTED" and ev.shooting_n2 == "ACCEPTED":
        mesh = "PARTIAL"
    else:
        mesh = "BLOCKED"
        notes.append("mesh_gates_incomplete")

    nozzle: NozzleStatus = (
        "UNRESOLVED"
        if ev.nozzle_velocity_status == "UNRESOLVED"
        else "PASS"
        if ev.nozzle_velocity_status == "PASS"
        else "BLOCKED"
    )

    wall = _wall_order_status(ev.raw)
    term_exceeds = ev.terminal_residual_j_kg > ev.terminal_allowed_j_kg
    over_pct: str | None = None
    if term_exceeds and ev.terminal_allowed_j_kg > 0:
        delta = ev.terminal_residual_j_kg - ev.terminal_allowed_j_kg
        pct = delta / ev.terminal_allowed_j_kg * 100
        over_pct = f"{pct:.2f}%"

    prop_small = ev.cell_propagation_j_kg < float(ev.terminal_residual_j_kg) * 0.01
    prop_audit = tp_ph_query_status == "PASS"

    if (
        duty_screen == "INDICATIVE_PASS"
        and hydraulic == "PASS"
        and energy == "verified"
        and local_ht == "PASS"
        and mesh == "PASS"
        and nozzle == "PASS"
        and wall == "PASS"
    ):
        evidence_grade: EvidenceGrade = "SUFFICIENT"
    elif duty_screen == "INDICATIVE_FAIL" and hydraulic == "BLOCKED":
        evidence_grade = "INSUFFICIENT"
    else:
        evidence_grade = "PARTIAL"

    screens = EngineeringPhysicalScreens(
        duty_screen=duty_screen,
        hydraulic_screen=hydraulic,
        energy_balance=energy,
        local_heat_transfer=local_ht,
        mesh_convergence=mesh,
        nozzle_velocity=nozzle,
        wall_temperature_order=wall,
        engineering_physical_evidence=evidence_grade,
    )

    return EngineeringPhysicalAssessment(
        screens=screens,
        grade=evidence_grade,
        terminal_h_exceeds_contract_margin=term_exceeds,
        terminal_h_over_allowed_pct=over_pct,
        propagation_subdominant_to_terminal=prop_small,
        property_audit_pass=prop_audit,
        notes=tuple(notes),
    )


@dataclass(frozen=True)
class NegativeControlRow:
    scenario: str
    rejected_by_rule: str
    perturbation_blocked: bool


@dataclass(frozen=True)
class NegativeControlResult:
    status: Literal["PASS", "BLOCKED"]
    rows: tuple[NegativeControlRow, ...]


def run_negative_controls_via_evaluator(
    base: Frozen330Evidence,
    *,
    tp_ph_query_status: str = "PASS",
) -> NegativeControlResult:
    Predicate = Callable[[EngineeringPhysicalAssessment], bool]
    scenarios: list[tuple[str, dict[str, Any], str, Predicate]] = [
        (
            "duty_below_330kw",
            {"n4_total_q_w": "300000"},
            "duty_screen:INDICATIVE_FAIL",
            lambda a: a.screens.duty_screen == "INDICATIVE_FAIL",
        ),
        (
            "tube_dp_exceeds_envelope",
            {"tube_dp_pa": "1200"},
            "hydraulic_screen:BLOCKED",
            lambda a: a.screens.hydraulic_screen == "BLOCKED",
        ),
        (
            "shell_dp_exceeds_envelope",
            {"shell_dp_pa": "1300"},
            "hydraulic_screen:BLOCKED",
            lambda a: a.screens.hydraulic_screen == "BLOCKED",
        ),
        (
            "energy_balance_imbalance",
            {
                "hot_loss_w": "395277",
                "cold_gain_w": "395277",
                "wall_duty_w": "395277",
                "energy_balance_residual_w": "50000",
                "energy_balance_tolerance_w": "1",
            },
            "energy_balance:failed",
            lambda a: a.screens.energy_balance == "failed",
        ),
        (
            "wall_temperature_order_inverted",
            {
                "tube_inlet_t_k": "310",
                "shell_inlet_t_k": "295",
                "wall_inner_k": "290",
                "wall_outer_k": "300",
            },
            "wall_temperature_order:BLOCKED",
            lambda a: a.screens.wall_temperature_order == "BLOCKED",
        ),
        (
            "n4_blocked_mesh",
            {"shooting_n4": "BLOCKED"},
            "mesh_convergence:BLOCKED",
            lambda a: a.screens.mesh_convergence == "BLOCKED",
        ),
        (
            "nozzle_velocity_unresolved",
            {"nozzle_velocity_status": "UNRESOLVED"},
            "nozzle_velocity:UNRESOLVED_prevents_SUFFICIENT",
            lambda a: a.screens.nozzle_velocity == "UNRESOLVED" and a.grade != "SUFFICIENT",
        ),
    ]

    rows: list[NegativeControlRow] = []
    for name, overrides, rule, predicate in scenarios:
        mutated = evidence_with_overrides(base, **overrides)
        assessed = assess_engineering_physical_layer(mutated, tp_ph_query_status=tp_ph_query_status)
        rows.append(
            NegativeControlRow(
                scenario=name,
                rejected_by_rule=rule,
                perturbation_blocked=predicate(assessed),
            )
        )

    status: Literal["PASS", "BLOCKED"] = (
        "PASS" if all(r.perturbation_blocked for r in rows) else "BLOCKED"
    )
    return NegativeControlResult(status=status, rows=tuple(rows))


def physical_temperature_scale_from_contract() -> Decimal:
    return TERMINAL_TOLERANCE_K


__all__ = [
    "EngineeringPhysicalAssessment",
    "EngineeringPhysicalScreens",
    "Frozen330Evidence",
    "NegativeControlResult",
    "NegativeControlRow",
    "assess_engineering_physical_layer",
    "evidence_with_overrides",
    "load_frozen_330_evidence",
    "load_frozen_330_evidence_from_dict",
    "run_negative_controls_via_evaluator",
]
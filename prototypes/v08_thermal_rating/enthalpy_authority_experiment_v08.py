"""Isolated authority-vs-property consistency audit (no production patch, no new solver)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _MeshRun,
    _state_from_enthalpy,
    _terminal_tolerance_pass,
)
from hexagent.properties.base import PropertyProvider
from prototypes.v08_thermal_rating.enthalpy_precision_trace_v08 import (
    EnthalpyPrecisionTrace,
    trace_enthalpy_on_mesh_run,
)


@dataclass(frozen=True)
class AuthorityConsistencyVerdict:
    status: Literal["CONSISTENT", "BLOCKED"]
    max_authority_minus_ph_j_kg: float
    first_blocked_cell: int | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class N4AuthorityExperimentOutcome:
    trace: EnthalpyPrecisionTrace
    consistency: AuthorityConsistencyVerdict
    task172_gate: Literal["PASS", "BLOCKED", "NOT_EVALUATED"]
    terminal_gate: Literal["PASS", "BLOCKED"]
    energy_balance_ok: bool
    total_q_w: str | None
    enthalpy_propagation_defect_confirmed: bool
    numerical_decision: Literal["A", "B"]


def _authority_consistency_audit(
    run: _MeshRun,
    *,
    provider: PropertyProvider,
    trace: EnthalpyPrecisionTrace,
) -> AuthorityConsistencyVerdict:
    notes: list[str] = []
    max_delta = 0.0
    first_block: int | None = None
    blocked = False
    ulp_gate = max(1.0e-6, trace.max_ph_roundtrip_error_j_kg * 0.01)

    for row in trace.rows:
        for side, h_str in (
            ("TUBE", row.h_tube_mid_constitutive),
            ("SHELL", row.h_shell_mid_constitutive),
        ):
            h = Decimal(h_str)
            try:
                st = _state_from_enthalpy(provider, h, side=side)
                ph_h = float(st.native.enthalpy_j_kg)
                delta = abs(float(h) - ph_h)
                if delta > max_delta:
                    max_delta = delta
                if delta > ulp_gate and first_block is None:
                    first_block = row.cell_index
                    blocked = True
            except Exception as exc:
                blocked = True
                notes.append(f"cell={row.cell_index}:{side}:{type(exc).__name__}")
                if first_block is None:
                    first_block = row.cell_index

    inlet_delta = abs(float(trace.shell_inlet_face_minus_authority_j_kg))
    if inlet_delta > ulp_gate:
        blocked = True
        notes.append(f"shell_inlet_face_delta_j_kg={inlet_delta}")

    status: Literal["CONSISTENT", "BLOCKED"] = "BLOCKED" if blocked else "CONSISTENT"
    if status == "BLOCKED":
        notes.append("authority_ph_split_would_block_before_energy_closure")
    return AuthorityConsistencyVerdict(
        status=status,
        max_authority_minus_ph_j_kg=max_delta,
        first_blocked_cell=first_block,
        notes=tuple(notes),
    )


def evaluate_n4_authority_experiment(
    run: _MeshRun | None,
    *,
    provider: PropertyProvider,
    outer_status: str,
    holes: int | None = None,
) -> N4AuthorityExperimentOutcome:
    if run is None:
        empty = EnthalpyPrecisionTrace(
            subdivisions=4,
            shooting_enthalpy_j_kg="",
            rows=(),
            cumulative_face_prediction_error_j_kg=0.0,
            max_ph_roundtrip_error_j_kg=0.0,
            first_precision_loss_cell=None,
            shell_cold_inlet_authority_j_kg="",
            shell_cold_inlet_face_j_kg="",
            shell_inlet_face_minus_authority_j_kg="",
            terminal_residual_k="",
            terminal_residual_j_kg="",
            defect_attributed_to="undetermined",
        )
        return N4AuthorityExperimentOutcome(
            trace=empty,
            consistency=AuthorityConsistencyVerdict("BLOCKED", 0.0, None, ("no_mesh_run",)),
            task172_gate="NOT_EVALUATED",
            terminal_gate="BLOCKED",
            energy_balance_ok=False,
            total_q_w=None,
            enthalpy_propagation_defect_confirmed=False,
            numerical_decision="B",
        )

    trace = trace_enthalpy_on_mesh_run(run, provider=provider)
    consistency = _authority_consistency_audit(run, provider=provider, trace=trace)
    term_ok = _terminal_tolerance_pass(run)
    obs = run.observables
    from prototypes.v08_thermal_rating.axial_rating_engine_v1 import ENERGY_ACCEPTANCE_FLOOR_W

    energy_tol = max(
        float(ENERGY_ACCEPTANCE_FLOOR_W),
        float(obs.duty_roundoff_floor_w),
    )
    energy_ok = float(obs.energy_balance_residual_w) <= energy_tol
    hole_count = holes if holes is not None else int(obs.task172_numerical_hole_count)
    t172: Literal["PASS", "BLOCKED", "NOT_EVALUATED"] = "PASS" if hole_count == 0 else "BLOCKED"
    defect = (
        trace.defect_attributed_to in ("enthalpy_state_reconstruction", "mixed")
        or consistency.status == "BLOCKED"
        or trace.max_ph_roundtrip_error_j_kg > 1e-9
    )
    accepted = (
        outer_status == "ACCEPTED"
        and term_ok
        and t172 == "PASS"
        and energy_ok
        and consistency.status == "CONSISTENT"
    )
    decision: Literal["A", "B"] = "A" if accepted else "B"
    return N4AuthorityExperimentOutcome(
        trace=trace,
        consistency=consistency,
        task172_gate=t172,
        terminal_gate="PASS" if term_ok else "BLOCKED",
        energy_balance_ok=energy_ok,
        total_q_w=str(obs.total_duty_w),
        enthalpy_propagation_defect_confirmed=defect,
        numerical_decision=decision,
    )


__all__ = [
    "AuthorityConsistencyVerdict",
    "N4AuthorityExperimentOutcome",
    "evaluate_n4_authority_experiment",
]

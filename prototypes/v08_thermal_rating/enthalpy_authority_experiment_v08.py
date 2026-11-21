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
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    ENERGY_ACCEPTANCE_FLOOR_W,
    CandidateRatingBindings,
)
from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import (
    AuditContextSnapshot,
    InletTerminalInvariant,
    TpPhReconstructionSummary,
    enthalpy_audit_precision_threshold_j_kg,
    inlet_terminal_invariant,
    run_enthalpy_audit_body,
    tp_ph_reconstruction_summary,
    verify_audit_thermal_context,
)
from prototypes.v08_thermal_rating.enthalpy_precision_trace_v08 import (
    EnthalpyPrecisionTrace,
    trace_enthalpy_on_mesh_run,
)

PropagationDefect = bool | Literal["unresolved"]


@dataclass(frozen=True)
class AuthorityConsistencyVerdict:
    status: Literal["CONSISTENT", "BLOCKED", "NOT_EVALUATED"]
    max_authority_minus_ph_j_kg: float
    first_blocked_cell: int | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class N4AuthorityExperimentOutcome:
    trace: EnthalpyPrecisionTrace
    consistency: AuthorityConsistencyVerdict
    context: AuditContextSnapshot
    inlet_invariant: InletTerminalInvariant | None
    tp_ph: TpPhReconstructionSummary | None
    task172_gate: Literal["PASS", "BLOCKED", "NOT_EVALUATED"]
    terminal_gate: Literal["PASS", "BLOCKED"]
    energy_balance_ok: bool
    total_q_w: str | None
    enthalpy_propagation_defect_confirmed: PropagationDefect
    numerical_decision: Literal["A", "B"]
    n4_precision_floor_remains: bool


def _authority_consistency_audit(
    run: _MeshRun,
    *,
    provider: PropertyProvider,
    trace: EnthalpyPrecisionTrace,
    tp_ph: TpPhReconstructionSummary,
) -> AuthorityConsistencyVerdict:
    notes: list[str] = []
    max_delta = 0.0
    first_block: int | None = None
    blocked = False
    ulp_gate = max(enthalpy_audit_precision_threshold_j_kg(), tp_ph.max_delta_h_j_kg * 0.01)

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

    status: Literal["CONSISTENT", "BLOCKED"] = "BLOCKED" if blocked else "CONSISTENT"
    if status == "BLOCKED":
        notes.append("authority_ph_split_would_block_before_energy_closure")
    return AuthorityConsistencyVerdict(
        status=status,
        max_authority_minus_ph_j_kg=max_delta,
        first_blocked_cell=first_block,
        notes=tuple(notes),
    )


def _empty_trace(subdivisions: int = 4) -> EnthalpyPrecisionTrace:
    return EnthalpyPrecisionTrace(
        subdivisions=subdivisions,
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
        max_tp_ph_delta_h_j_kg=0.0,
        max_tp_ph_delta_t_k=0.0,
    )


def _propagation_defect(
    *,
    context: AuditContextSnapshot,
    trace: EnthalpyPrecisionTrace,
    consistency: AuthorityConsistencyVerdict,
    tp_ph: TpPhReconstructionSummary | None,
) -> PropagationDefect:
    if context.status != "VALID":
        return "unresolved"
    if trace.defect_attributed_to == "audit_context_invalid":
        return "unresolved"
    thresh = enthalpy_audit_precision_threshold_j_kg()
    ph_err = trace.max_ph_roundtrip_error_j_kg
    tp_err = tp_ph.max_delta_h_j_kg if tp_ph is not None else 0.0
    prop_err = trace.cumulative_face_prediction_error_j_kg
    recon = trace.defect_attributed_to in ("enthalpy_state_reconstruction", "mixed") or (
        ph_err > thresh and tp_err > thresh
    )
    auth_block = consistency.status == "BLOCKED" and any(
        "shell_inlet_face_delta" not in n for n in consistency.notes
    )
    local = trace.defect_attributed_to == "local_q_root_or_other" or prop_err > thresh
    return bool(recon or auth_block or local)


def evaluate_n4_authority_experiment(
    run: _MeshRun | None,
    *,
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    outer_status: str,
    holes: int | None = None,
) -> N4AuthorityExperimentOutcome:
    if run is None:
        ctx = verify_audit_thermal_context(bindings)
        return N4AuthorityExperimentOutcome(
            trace=_empty_trace(),
            consistency=AuthorityConsistencyVerdict("NOT_EVALUATED", 0.0, None, ("no_mesh_run",)),
            context=ctx if ctx.status == "AUDIT_CONTEXT_MISSING" else ctx,
            inlet_invariant=None,
            tp_ph=None,
            task172_gate="NOT_EVALUATED",
            terminal_gate="BLOCKED",
            energy_balance_ok=False,
            total_q_w=None,
            enthalpy_propagation_defect_confirmed="unresolved",
            numerical_decision="B",
            n4_precision_floor_remains=True,
        )

    def body(_context: object, _btoken: object) -> N4AuthorityExperimentOutcome:
        ctx = verify_audit_thermal_context(bindings)
        if ctx.status != "VALID":
            return N4AuthorityExperimentOutcome(
                trace=_empty_trace(run.subdivisions),
                consistency=AuthorityConsistencyVerdict(
                    "NOT_EVALUATED", 0.0, None, (ctx.status, *ctx.notes)
                ),
                context=ctx,
                inlet_invariant=None,
                tp_ph=None,
                task172_gate="NOT_EVALUATED",
                terminal_gate="BLOCKED",
                energy_balance_ok=False,
                total_q_w=str(run.observables.total_duty_w),
                enthalpy_propagation_defect_confirmed="unresolved",
                numerical_decision="B",
                n4_precision_floor_remains=outer_status != "ACCEPTED",
            )

        tp = tp_ph_reconstruction_summary(provider, bindings)
        trace = trace_enthalpy_on_mesh_run(run, provider=provider)
        trace = EnthalpyPrecisionTrace(
            subdivisions=trace.subdivisions,
            shooting_enthalpy_j_kg=trace.shooting_enthalpy_j_kg,
            rows=trace.rows,
            cumulative_face_prediction_error_j_kg=trace.cumulative_face_prediction_error_j_kg,
            max_ph_roundtrip_error_j_kg=trace.max_ph_roundtrip_error_j_kg,
            first_precision_loss_cell=trace.first_precision_loss_cell,
            shell_cold_inlet_authority_j_kg=trace.shell_cold_inlet_authority_j_kg,
            shell_cold_inlet_face_j_kg=trace.shell_cold_inlet_face_j_kg,
            shell_inlet_face_minus_authority_j_kg=trace.shell_inlet_face_minus_authority_j_kg,
            terminal_residual_k=trace.terminal_residual_k,
            terminal_residual_j_kg=trace.terminal_residual_j_kg,
            defect_attributed_to=trace.defect_attributed_to,
            max_tp_ph_delta_h_j_kg=tp.max_delta_h_j_kg,
            max_tp_ph_delta_t_k=tp.max_delta_t_k,
        )
        inlet_inv = inlet_terminal_invariant(run)
        consistency = _authority_consistency_audit(run, provider=provider, trace=trace, tp_ph=tp)
        term_ok = _terminal_tolerance_pass(run)
        obs = run.observables
        energy_tol = max(float(ENERGY_ACCEPTANCE_FLOOR_W), float(obs.duty_roundoff_floor_w))
        energy_ok = float(obs.energy_balance_residual_w) <= energy_tol
        hole_count = holes if holes is not None else int(obs.task172_numerical_hole_count)
        t172: Literal["PASS", "BLOCKED", "NOT_EVALUATED"] = "PASS" if hole_count == 0 else "BLOCKED"
        defect = _propagation_defect(context=ctx, trace=trace, consistency=consistency, tp_ph=tp)
        accepted = (
            outer_status == "ACCEPTED"
            and term_ok
            and t172 == "PASS"
            and energy_ok
            and consistency.status == "CONSISTENT"
            and inlet_inv.invariant_match == "PASS"
        )
        decision: Literal["A", "B"] = "A" if accepted else "B"
        return N4AuthorityExperimentOutcome(
            trace=trace,
            consistency=consistency,
            context=ctx,
            inlet_invariant=inlet_inv,
            tp_ph=tp,
            task172_gate=t172,
            terminal_gate="PASS" if term_ok else "BLOCKED",
            energy_balance_ok=energy_ok,
            total_q_w=str(obs.total_duty_w),
            enthalpy_propagation_defect_confirmed=defect,
            numerical_decision=decision,
            n4_precision_floor_remains=outer_status != "ACCEPTED",
        )

    return run_enthalpy_audit_body(bindings, provider, subdivisions=run.subdivisions, body=body)


__all__ = [
    "AuthorityConsistencyVerdict",
    "N4AuthorityExperimentOutcome",
    "PropagationDefect",
    "evaluate_n4_authority_experiment",
]

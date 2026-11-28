"""Per-cell enthalpy / P-H trace on an isolated Task173 mesh run (prototype only)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _MeshRun,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_mass_flow_kg_s,
    effective_tube_mass_flow_kg_s,
)
from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import (
    enthalpy_audit_precision_threshold_j_kg,
)


@dataclass(frozen=True)
class CellEnthalpyTraceRow:
    cell_index: int
    tube_cell_id: str
    q_w: str
    h_tube_left_decimal: str
    h_tube_right_decimal: str
    h_tube_right_predicted: str
    tube_face_prediction_error_j_kg: str
    h_shell_left_decimal: str
    h_shell_right_decimal: str
    h_shell_right_predicted: str
    shell_face_prediction_error_j_kg: str
    h_tube_mid_constitutive: str
    h_shell_mid_constitutive: str
    tube_ph_roundtrip_error_j_kg: str | None
    shell_ph_roundtrip_error_j_kg: str | None
    task172_request_hash: str


@dataclass(frozen=True)
class EnthalpyPrecisionTrace:
    subdivisions: int
    shooting_enthalpy_j_kg: str
    rows: tuple[CellEnthalpyTraceRow, ...]
    cumulative_face_prediction_error_j_kg: float
    max_ph_roundtrip_error_j_kg: float
    first_precision_loss_cell: int | None
    shell_cold_inlet_authority_j_kg: str
    shell_cold_inlet_face_j_kg: str
    shell_inlet_face_minus_authority_j_kg: str
    terminal_residual_k: str
    terminal_residual_j_kg: str
    defect_attributed_to: Literal[
        "enthalpy_state_reconstruction",
        "local_q_root_or_other",
        "mixed",
        "undetermined",
        "audit_context_invalid",
    ]
    max_tp_ph_delta_h_j_kg: float
    max_tp_ph_delta_t_k: float


def _ph_roundtrip_delta_j_kg(
    provider: Any, h: Decimal, *, side: Literal["TUBE", "SHELL"]
) -> float | None:
    from hexagent.exchangers.shell_tube.task173_integrated_rating import (
        experimental_thermal_boundary as _etb,
    )
    from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
        effective_shell_property_evaluation_pressure_pa,
        effective_tube_property_evaluation_pressure_pa,
    )
    from hexagent.properties.base import FluidIdentifier, ReferenceStatePolicy

    binding = _etb.active_experimental_thermal_boundary()
    if binding is None:
        return None
    p = (
        float(effective_shell_property_evaluation_pressure_pa())
        if side == "SHELL"
        else float(effective_tube_property_evaluation_pressure_pa())
    )
    try:
        st = provider.state_ph(
            FluidIdentifier(name="Water"),
            pressure_pa=p,
            enthalpy_j_kg=float(h),
            reference_state=ReferenceStatePolicy.DEF,
        )
        return float(h) - float(st.enthalpy_j_kg)
    except Exception:
        return None


def trace_enthalpy_on_mesh_run(
    run: _MeshRun,
    *,
    provider: Any,
) -> EnthalpyPrecisionTrace:
    mt = effective_tube_mass_flow_kg_s()
    ms = effective_shell_mass_flow_kg_s()
    rows: list[CellEnthalpyTraceRow] = []
    cumulative = 0.0
    max_ph = 0.0
    first_loss: int | None = None
    threshold = enthalpy_audit_precision_threshold_j_kg()

    for i, cell in enumerate(run.cells):
        q = cell.solution.q_w
        h_tl = Decimal(str(cell.tube_upstream_face.enthalpy_j_kg))
        h_tr = Decimal(str(cell.tube_downstream_face.enthalpy_j_kg))
        h_sl = Decimal(str(cell.shell_physical_left_face.enthalpy_j_kg))
        h_sr = Decimal(str(cell.shell_physical_right_face.enthalpy_j_kg))
        with localcontext() as ctx:
            ctx.prec = 70
            h_tr_pred = h_tl - q / mt
            h_sr_pred = h_sl - q / ms
        tube_err = float(abs(h_tr - h_tr_pred))
        shell_err = float(abs(h_sr - h_sr_pred))
        cumulative += tube_err + shell_err
        tube_ph = _ph_roundtrip_delta_j_kg(provider, h_tl, side="TUBE")
        shell_ph = _ph_roundtrip_delta_j_kg(provider, h_sl, side="SHELL")
        for ph in (tube_ph, shell_ph):
            if ph is not None and abs(ph) > max_ph:
                max_ph = abs(ph)
                if first_loss is None and abs(ph) > threshold:
                    first_loss = i
        for err in (tube_err, shell_err):
            if first_loss is None and err > threshold:
                first_loss = i
        req_hash = str(cell.rated_cell.task172_request_hash)
        rows.append(
            CellEnthalpyTraceRow(
                cell_index=i,
                tube_cell_id=str(cell.support.tube_cell_id),
                q_w=str(q),
                h_tube_left_decimal=str(h_tl),
                h_tube_right_decimal=str(h_tr),
                h_tube_right_predicted=str(h_tr_pred),
                tube_face_prediction_error_j_kg=str(tube_err),
                h_shell_left_decimal=str(h_sl),
                h_shell_right_decimal=str(h_sr),
                h_shell_right_predicted=str(h_sr_pred),
                shell_face_prediction_error_j_kg=str(shell_err),
                h_tube_mid_constitutive=str(
                    cell.tube_receipt.constitutive_evaluation_enthalpy_j_kg
                ),
                h_shell_mid_constitutive=str(
                    cell.shell_receipt.constitutive_evaluation_enthalpy_j_kg
                ),
                tube_ph_roundtrip_error_j_kg=str(tube_ph) if tube_ph is not None else None,
                shell_ph_roundtrip_error_j_kg=str(shell_ph) if shell_ph is not None else None,
                task172_request_hash=req_hash,
            )
        )

    auth = effective_shell_cold_inlet_enthalpy_j_kg()
    inlet_h = Decimal(str(run.faces_shell[-1].enthalpy_j_kg))
    inlet_delta = inlet_h - auth
    term_k = str(run.observables.terminal_boundary_residual_k)
    term_h = str(run.observables.terminal_boundary_residual_j_kg)
    term_mag = abs(float(term_h))
    if max_ph > 1e-6 and term_mag < max_ph:
        attributed: Literal[
            "enthalpy_state_reconstruction",
            "local_q_root_or_other",
            "mixed",
            "undetermined",
        ] = "enthalpy_state_reconstruction"
    elif cumulative < 1e-6 and term_mag > 1e-6:
        attributed = "local_q_root_or_other"
    elif max_ph > 1e-6 and term_mag > 1e-6:
        attributed = "mixed"
    else:
        attributed = "undetermined"

    prod_term = Decimal(str(term_h))
    if inlet_delta != prod_term:
        attributed = (
            "audit_context_invalid" if abs(float(inlet_delta - prod_term)) > 1e-15 else attributed
        )

    return EnthalpyPrecisionTrace(
        subdivisions=run.subdivisions,
        shooting_enthalpy_j_kg=str(run.shooting_enthalpy),
        rows=tuple(rows),
        cumulative_face_prediction_error_j_kg=cumulative,
        max_ph_roundtrip_error_j_kg=max_ph,
        first_precision_loss_cell=first_loss,
        shell_cold_inlet_authority_j_kg=str(auth),
        shell_cold_inlet_face_j_kg=str(inlet_h),
        shell_inlet_face_minus_authority_j_kg=str(inlet_delta),
        terminal_residual_k=term_k,
        terminal_residual_j_kg=term_h,
        defect_attributed_to=attributed,
        max_tp_ph_delta_h_j_kg=0.0,
        max_tp_ph_delta_t_k=0.0,
    )


__all__ = ["CellEnthalpyTraceRow", "EnthalpyPrecisionTrace", "trace_enthalpy_on_mesh_run"]

"""R27E: tube-side regime and property-domain diagnostics for blocked 0.65 m candidates."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.tube_side_thermal import FlowRegime, ThermalBoundaryCondition
from hexagent.exchangers.shell_tube.tube_side_thermal.single_phase import compute_single_phase
from hexagent.properties.base import FluidIdentifier, ReferenceStatePolicy
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    native_thermal_boundary_session,
)

_WATER = FluidIdentifier("Water", "HEOS")


def _tube_hydraulics_from_record(record: Any) -> tuple[Decimal, Decimal]:
    area = Decimal(str(record.task025_total_parallel_flow_area_m2))
    n = int(record.physical_tube_count)
    tube_id = Decimal(str(math.sqrt(4.0 * float(area) / (n * math.pi))))
    return area, tube_id


def scan_tube_regime_along_temperature(
    case: EngineeringCase,
    *,
    selection: CandidateSelectionOutcome,
    candidate_id: str,
    temperature_steps: int = 40,
) -> dict[str, Any]:
    """Sweep tube bulk T at fixed m_dot to locate first Task026 transition / laminar onset."""
    provider = CoolPropProvider()
    record = next(r for r in selection.records if r.candidate_id == candidate_id)
    parallel_area, tube_id = _tube_hydraulics_from_record(record)
    sweep: list[dict[str, Any]] = []
    first_transition: dict[str, Any] | None = None
    first_laminar: dict[str, Any] | None = None
    with native_thermal_boundary_session(case, provider, enable_live_binding=True):
        m_dot = Decimal(str(t173.effective_tube_mass_flow_kg_s()))
        p_pa = float(t173.effective_tube_property_evaluation_pressure_pa())
        t_in = float(t173.effective_tube_inlet_temperature_k())
        t_shell = float(t173.effective_shell_inlet_temperature_k())
        t_min = min(t_shell + 0.5, t_in - 25.0)
        for step in range(temperature_steps + 1):
            frac = step / temperature_steps
            t_k = t_in - frac * (t_in - t_min)
            state = provider.state_tp(_WATER, t_k, p_pa)
            out = compute_single_phase(
                m_dot,
                Decimal(str(state.density_kg_m3)),
                Decimal(str(state.viscosity_pa_s)),
                Decimal(str(state.conductivity_w_m_k)),
                Decimal(str(state.cp_j_kg_k)),
                parallel_area,
                tube_id,
                ThermalBoundaryCondition.CWT,
            )
            rho = float(state.density_kg_m3)
            mu = float(state.viscosity_pa_s)
            vel = float(m_dot) / (rho * float(parallel_area))
            per_tube = float(m_dot) / record.physical_tube_count
            row = {
                "tube_bulk_temperature_k": t_k,
                "tube_pressure_pa": p_pa,
                "density_kg_m3": rho,
                "dynamic_viscosity_pa_s": mu,
                "tube_mass_flow_kg_s": float(m_dot),
                "tube_mass_flow_per_physical_tube_kg_s": per_tube,
                "parallel_flow_area_m2": float(parallel_area),
                "tube_hydraulic_diameter_m": float(tube_id),
                "bulk_velocity_m_s": vel,
                "reynolds": float(out.reynolds_number),
                "prandtl": float(out.prandtl_number),
                "flow_regime": out.flow_regime.value,
                "correlation_id": out.correlation_id,
            }
            sweep.append(row)
            if first_transition is None and out.flow_regime is FlowRegime.TRANSITION:
                first_transition = {**row, "first_occurrence": True}
            if first_laminar is None and out.flow_regime is FlowRegime.LAMINAR:
                first_laminar = {**row, "first_occurrence": True}
        inlet_state = provider.state_tp(_WATER, t_in, p_pa)
        inlet_out = compute_single_phase(
            m_dot,
            Decimal(str(inlet_state.density_kg_m3)),
            Decimal(str(inlet_state.viscosity_pa_s)),
            Decimal(str(inlet_state.conductivity_w_m_k)),
            Decimal(str(inlet_state.cp_j_kg_k)),
            parallel_area,
            tube_id,
            ThermalBoundaryCondition.CWT,
        )
        inlet_row = {
            "tube_bulk_temperature_k": t_in,
            "reynolds": float(inlet_out.reynolds_number),
            "prandtl": float(inlet_out.prandtl_number),
            "flow_regime": inlet_out.flow_regime.value,
            "bulk_velocity_m_s": float(m_dot)
            / (float(inlet_state.density_kg_m3) * float(parallel_area)),
        }
    return {
        "candidate_id": candidate_id,
        "physical_tube_count": record.physical_tube_count,
        "inlet_bulk_task026": inlet_row,
        "first_laminar_sweep_point": first_laminar,
        "first_transition_sweep_point": first_transition,
        "temperature_sweep": sweep,
    }


def probe_enthalpy_domain_exit(
    *,
    enthalpy_j_kg: float,
    pressure_pa: float,
    side: Literal["TUBE", "SHELL"] = "TUBE",
    rating_admitted_h_min_j_kg: float | None = None,
    rating_admitted_h_max_j_kg: float | None = None,
) -> dict[str, Any]:
    """Keep unrestricted CoolProp P-H capability separate from the rating admission window."""
    provider = CoolPropProvider()
    rating_domain_ok = (
        rating_admitted_h_min_j_kg <= enthalpy_j_kg <= rating_admitted_h_max_j_kg
        if rating_admitted_h_min_j_kg is not None
        and rating_admitted_h_max_j_kg is not None
        else None
    )
    result: dict[str, Any] = {
        "side": side,
        "enthalpy_j_kg": enthalpy_j_kg,
        "pressure_pa": pressure_pa,
        "rating_admitted_h_min_j_kg": rating_admitted_h_min_j_kg,
        "rating_admitted_h_max_j_kg": rating_admitted_h_max_j_kg,
        "rating_admitted_enthalpy_domain_ok": rating_domain_ok,
        "rating_domain_is_not_coolprop_domain": True,
    }
    try:
        state = provider.state_ph(
            _WATER,
            pressure_pa,
            enthalpy_j_kg,
            reference_state=ReferenceStatePolicy.DEF,
        )
        result.update({
            "property_domain_ok": True,
            "temperature_k": state.temperature_k,
            "phase": str(getattr(state, "phase", None)),
        })
    except Exception as exc:
        result.update({
            "property_domain_ok": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        })
    return result

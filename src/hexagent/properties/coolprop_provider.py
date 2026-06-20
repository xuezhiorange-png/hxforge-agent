from __future__ import annotations

import CoolProp
from CoolProp.CoolProp import PropsSI

from hexagent.core.contracts import FluidState


class CoolPropProvider:
    name = "CoolProp"
    version = CoolProp.__version__

    def state_tp(self, fluid_name: str, temperature_k: float, pressure_pa: float) -> FluidState:
        return FluidState(
            temperature_k=temperature_k,
            pressure_pa=pressure_pa,
            density_kg_m3=float(PropsSI("D", "T", temperature_k, "P", pressure_pa, fluid_name)),
            cp_j_kg_k=float(PropsSI("C", "T", temperature_k, "P", pressure_pa, fluid_name)),
            viscosity_pa_s=float(PropsSI("V", "T", temperature_k, "P", pressure_pa, fluid_name)),
            conductivity_w_m_k=float(
                PropsSI("L", "T", temperature_k, "P", pressure_pa, fluid_name)
            ),
            enthalpy_j_kg=float(PropsSI("H", "T", temperature_k, "P", pressure_pa, fluid_name)),
            phase=str(PropsSI("Phase", "T", temperature_k, "P", pressure_pa, fluid_name)),
        )

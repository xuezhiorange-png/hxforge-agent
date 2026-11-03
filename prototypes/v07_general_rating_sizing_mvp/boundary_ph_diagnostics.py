"""Low-cost PH/TP boundary reconstruction diagnostics for R8 evidence."""

# ruff: noqa: E501

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import H_MIN_J_KG, T_MIN_K
from hexagent.properties.base import FluidIdentifier, ReferenceStatePolicy
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    build_native_thermal_boundary_from_case,
    native_thermal_boundary_session,
)


def build_boundary_ph_reconstruction_diagnostics(
    case: EngineeringCase,
    *,
    provider: CoolPropProvider | None = None,
) -> dict[str, Any]:
    active_provider = provider or CoolPropProvider()
    binding = build_native_thermal_boundary_from_case(case, active_provider)
    mid_h = (H_MIN_J_KG + binding.shell_inlet_enthalpy_j_kg) / Decimal(2)
    ph_state = active_provider.state_ph(
        FluidIdentifier(name="Water"),
        pressure_pa=101325.0,
        enthalpy_j_kg=float(mid_h),
        reference_state=ReferenceStatePolicy.DEF,
    )
    tp_shell = active_provider.state_tp(
        FluidIdentifier(name="Water"),
        float(binding.shell_inlet_temperature_k),
        101325.0,
    )
    with native_thermal_boundary_session(case, active_provider, enable_live_binding=True):
        rematerialized = t173._state_from_enthalpy(active_provider, mid_h)
    return {
        "schema_version": "hxforge.boundary-ph-reconstruction-diagnostics.v1",
        "engineering_case_id": case.engineering_case_id,
        "reviewed_constants": {
            "T_MIN_K": str(T_MIN_K),
            "H_MIN_J_KG": str(H_MIN_J_KG),
        },
        "experimental_binding": {
            "tube_inlet_temperature_k": str(binding.tube_inlet_temperature_k),
            "shell_inlet_temperature_k": str(binding.shell_inlet_temperature_k),
            "shell_inlet_enthalpy_j_kg": str(binding.shell_inlet_enthalpy_j_kg),
        },
        "cell_face_mean_enthalpy_j_kg": str(mid_h),
        "ph_query_inputs": {
            "pressure_pa": "101325",
            "enthalpy_j_kg": str(mid_h),
            "reference_state": "DEF",
        },
        "ph_provider_result": {
            "temperature_k": ph_state.temperature_k,
            "enthalpy_j_kg": ph_state.enthalpy_j_kg,
            "provider": "CoolProp",
        },
        "temperature_delta_below_t_min_k": float(T_MIN_K) - ph_state.temperature_k,
        "math_ulp_t_min_k": math.ulp(float(T_MIN_K)),
        "shell_inlet_tp_state_hash": t173._property_snapshot(tp_shell).model_dump(mode="json"),
        "rematerialized_state": {
            "query_type": rematerialized.snapshot.query_type,
            "temperature_k": rematerialized.native.temperature_k,
            "snapshot_hash": rematerialized.snapshot_hash,
        },
        "root_cause_summary": (
            "Cell constitutive shell_mid_h is the arithmetic mean of cold-end enthalpies on "
            "the T_MIN_K isotherm. Native PH inversion returns T epsilon below T_MIN_K; R8 "
            "re-materializes with the TP producer when h lies in [H_MIN, shell_inlet_h] and "
            "shell inlet temperature equals T_MIN_K."
        ),
        "boundary_precision_handling": "TP_REMATERIALIZE_ON_PH_BELOW_T_MIN_COLD_ISOTHERM",
        "real_out_of_domain_still_blocked": True,
        "r6_frozen_reference_note": (
            "Frozen 300 K tube inlet keeps H_MAX hot-end shooting aligned with tube face; "
            "R7 live tube 299.8 K required effective_hot_ceiling_enthalpy_j_kg for outer trials."
        ),
    }

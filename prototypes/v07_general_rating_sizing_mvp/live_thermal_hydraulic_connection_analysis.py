"""P0: document thermal vs hydraulic data sources for experimental live rating (R14)."""

from __future__ import annotations

from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import NativeCellContext


def build_live_thermal_hydraulic_connection_analysis(
    case: EngineeringCase,
    *,
    native: NativeCellContext | None = None,
    mesh: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read-only disclosure of which temperatures and pressures feed each hydraulic path."""
    mesh = mesh or {}
    return {
        "schema_version": "hxforge.live-thermal-hydraulic-connection-analysis.v1",
        "task_id": "V07_LIVE_THERMAL_STATE_HYDRAULIC_EVALUATION_R14",
        "user_inlet_thermal_state": {
            "source": "general engineering case JSON (tube_side / shell_side)",
            "feeds": "Task173 experimental live thermal boundary when enabled",
            "does_not_feed": "Task174 reference hydraulic preview without R14 post-pass",
        },
        "live_rating_outlet_thermal_state": {
            "source": "Task173 n=1 mesh observables when mesh_status=NUMERIC_VALID",
            "fields": (
                "tube_outlet_temperature_k",
                "shell_outlet_temperature_k",
                "total_duty_w",
                "energy_balance_residual_w",
            ),
            "present_in_mesh": mesh.get("status") == "NUMERIC_VALID",
            "tube_outlet_temperature_k": mesh.get("tube_outlet_temperature_k"),
            "shell_outlet_temperature_k": mesh.get("shell_outlet_temperature_k"),
        },
        "task174_reference_hydraulic_preview": {
            "status": "HYDRAULIC_REFERENCE_MODEL_PREVIEW",
            "temperature_pressure_basis": (
                "Task168 evaluation authority frozen property snapshots at sizing templates; "
                "Task174 binds Task029/Task166 at reference 101325 Pa without live outlet states"
            ),
            "modeled_tube_dp_pa": native.modeled_tube_side_pressure_drop_pa if native else None,
            "modeled_shell_dp_pa": native.modeled_shell_side_pressure_drop_pa if native else None,
        },
        "r14_experimental_postpass": {
            "authority_id": "V07-LIVE-THERMAL-STATE-HYDRAULIC-POSTPASS-R14",
            "hydraulic_status": "EXPERIMENTAL_LIVE_THERMAL_STATE_HYDRAULIC_POSTPASS",
            "enabled_by": "engineering_case.experimental_live_thermal_hydraulic_postpass=true",
            "property_evaluation_rule": (
                "Per side: bulk mean temperature (T_inlet + T_outlet)/2 at case inlet "
                "reference pressure; CoolProp HEOS::Water; separate tube and shell snapshots"
            ),
            "recomputes": (
                "Task026→Task027→Task028→Task029 tube path with live snapshot; "
                "Task032→Task166 Bell–Delaware shell path with live snapshot; "
                "actual Task025 parallel area and physical tube count from candidate bundle"
            ),
            "does_not_recompute": (
                "Task172 coupled cell; iterative thermal-hydraulic closure; "
                "Task174 orchestration identity"
            ),
            "outlet_pressure_model": "one_way_inlet_minus_modeled_delta_p",
        },
        "pressure_domain_layers": {
            "coolprop_liquid_water_tp": (
                "Provider-native phase/domain errors surface as post-pass blockers"
            ),
            "task173_reference_pressure_guard": (
                "Property evaluation for R14 post-pass uses inlet reference pressure only "
                "(does not weaken Task174 BLOCKED_PROPERTY_PRESSURE_DOMAIN_EXIT semantics)"
            ),
            "user_max_delta_p": {
                "tube_pa": str(case.max_tube_side_pressure_drop_pa),
                "shell_pa": str(case.max_shell_side_pressure_drop_pa),
            },
        },
    }
